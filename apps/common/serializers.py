"""
Common serializers for API responses with envelope format.
"""

from rest_framework import serializers

from apps.common.constants import (
    ATTACHMENT_TYPE_DOCUMENT,
    ATTACHMENT_TYPE_IMAGE,
    ATTACHMENT_TYPE_VIDEO,
    MAX_THUMBNAIL_SIZE,
    MAX_VIDEO_DURATION_SECONDS,
)
from apps.common.models import CountryPhoneCode
from apps.common.validators import validate_attachment_file


class ResponseEnvelopeSerializer(serializers.Serializer):
    """
    Base envelope serializer for wrapping all API responses.
    """

    message = serializers.CharField(help_text="Response message")
    data = serializers.JSONField(
        allow_null=True, required=False, help_text="Response data"
    )
    errors = serializers.DictField(
        allow_null=True, required=False, help_text="Error details if any"
    )
    meta = serializers.DictField(
        allow_null=True, required=False, help_text="Additional metadata"
    )


def create_response_serializer(data_serializer, serializer_name=None):
    """
    Factory function to create a response envelope serializer wrapping a data serializer.

    Args:
        data_serializer: The serializer class for the 'data' field
        serializer_name: Optional name for the generated serializer class

    Returns:
        A new serializer class with envelope format
    """
    if serializer_name is None:
        serializer_name = f"{data_serializer.__name__}Response"

    class Meta:
        ref_name = serializer_name

    attrs = {
        "message": serializers.CharField(help_text="Response message"),
        "data": data_serializer(help_text="Response data"),
        "errors": serializers.DictField(
            allow_null=True, required=False, help_text="Error details if any"
        ),
        "meta": serializers.DictField(
            allow_null=True, required=False, help_text="Additional metadata"
        ),
        "Meta": Meta,
    }

    return type(serializer_name, (serializers.Serializer,), attrs)


def create_list_response_serializer(data_serializer, serializer_name=None):
    """
    Factory function to create a response envelope serializer wrapping a list of data.

    Args:
        data_serializer: The serializer class for items in the 'data' list
        serializer_name: Optional name for the generated serializer class

    Returns:
        A new serializer class with envelope format for list responses
    """
    if serializer_name is None:
        serializer_name = f"{data_serializer.__name__}ListResponse"

    class Meta:
        ref_name = serializer_name

    attrs = {
        "message": serializers.CharField(help_text="Response message"),
        "data": data_serializer(many=True, help_text="List of response data"),
        "errors": serializers.DictField(
            allow_null=True, required=False, help_text="Error details if any"
        ),
        "meta": serializers.DictField(
            allow_null=True, required=False, help_text="Additional metadata"
        ),
        "Meta": Meta,
    }

    return type(serializer_name, (serializers.Serializer,), attrs)


class CountryPhoneCodeSerializer(serializers.ModelSerializer):
    """
    Serializer for country phone codes.
    """

    class Meta:
        model = CountryPhoneCode
        fields = [
            "country_code",
            "country_name",
            "dial_code",
            "flag_emoji",
        ]


# Response envelope for country codes list
CountryPhoneCodeListResponseEnvelope = create_list_response_serializer(
    CountryPhoneCodeSerializer, "CountryPhoneCodeListResponse"
)


# =============================================================================
# Attachment Input Serializers
# =============================================================================


class AttachmentInputSerializer(serializers.Serializer):
    """
    Serializer for attachment input with indexed object pattern.

    Supports images, videos, and documents with their metadata.
    For videos, thumbnail and duration_seconds are required.
    For documents (PDF, Word, Excel, PowerPoint), no additional metadata is required.

    Usage in multipart/form-data:
        attachments[0].file: photo.jpg
        attachments[1].file: video.mp4
        attachments[1].thumbnail: video_thumb.jpg
        attachments[1].duration_seconds: 120
        attachments[2].file: document.pdf
    """

    file = serializers.FileField(
        required=True,
        allow_empty_file=False,
        help_text="The attachment file (image, video, or document)",
    )
    thumbnail = serializers.ImageField(
        required=False,
        allow_null=True,
        allow_empty_file=False,
        help_text="Thumbnail image (required for videos, ignored for images)",
    )
    duration_seconds = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        help_text="Video duration in seconds (required for videos, ignored for images)",
    )

    def validate_file(self, value):
        """Validate the main file."""
        file_type, error = validate_attachment_file(value)
        if error:
            raise serializers.ValidationError(error)
        # Store the detected file type for use in validate()
        self._detected_file_type = file_type
        return value

    def validate_thumbnail(self, value):
        """Validate thumbnail file."""
        if value is None:
            return None

        # Check file size (ImageField already validates it's a valid image)
        if value.size > MAX_THUMBNAIL_SIZE:
            max_kb = MAX_THUMBNAIL_SIZE // 1024
            raise serializers.ValidationError(
                f"Thumbnail exceeds maximum size of {max_kb}KB."
            )

        return value

    def validate_duration_seconds(self, value):
        """Validate video duration."""
        if value is None:
            return None

        # min_value=1 on the field handles <= 0 validation
        if value > MAX_VIDEO_DURATION_SECONDS:
            max_min = MAX_VIDEO_DURATION_SECONDS // 60
            raise serializers.ValidationError(
                f"Video duration exceeds maximum of {max_min} minutes."
            )

        return value

    def validate(self, data):
        """Cross-field validation for video requirements."""
        file_type = getattr(self, "_detected_file_type", None)

        if file_type == ATTACHMENT_TYPE_VIDEO:
            # For videos, thumbnail and duration are required
            if not data.get("thumbnail"):
                raise serializers.ValidationError(
                    {"thumbnail": "Thumbnail is required for video files."}
                )
            if not data.get("duration_seconds"):
                raise serializers.ValidationError(
                    {"duration_seconds": "Duration is required for video files."}
                )

        # Store the file type in the validated data
        data["file_type"] = file_type

        # For images and documents, clear video-specific fields
        if file_type in (ATTACHMENT_TYPE_IMAGE, ATTACHMENT_TYPE_DOCUMENT):
            data["thumbnail"] = None
            data["duration_seconds"] = None

        return data


def parse_indexed_attachments(request_data, request_files):
    """
    Parse indexed attachment fields from multipart form data.

    Converts:
        attachments[0].file, attachments[0].thumbnail, attachments[0].duration_seconds
        attachments[1].file, ...

    Into:
        [
            {"file": <file>, "thumbnail": <file>, "duration_seconds": 120},
            {"file": <file>, ...},
        ]

    Args:
        request_data: request.data (QueryDict or dict)
        request_files: request.FILES (MultiValueDict)

    Returns:
        list of attachment dicts
    """
    attachments = {}

    # Pattern: attachments[0].file, attachments[0].thumbnail, etc.
    import re

    pattern = re.compile(r"^attachments\[(\d+)\]\.(\w+)$")

    # Process FILES (file and thumbnail)
    for key in request_files.keys():
        match = pattern.match(key)
        if match:
            idx = int(match.group(1))
            field = match.group(2)
            if idx not in attachments:
                attachments[idx] = {}
            # Handle multiple files with same key (shouldn't happen but just in case)
            files = request_files.getlist(key)
            attachments[idx][field] = files[0] if files else None

    # Process DATA (duration_seconds)
    # request_data might be a QueryDict or regular dict
    data_keys = request_data.keys() if hasattr(request_data, "keys") else []
    for key in data_keys:
        match = pattern.match(key)
        if match:
            idx = int(match.group(1))
            field = match.group(2)
            if idx not in attachments:
                attachments[idx] = {}
            value = request_data.get(key)
            # Convert duration_seconds to int
            if field == "duration_seconds" and value is not None:
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    pass  # Let serializer handle validation
            attachments[idx][field] = value

    # Convert to sorted list
    if not attachments:
        # Fallback: support non-indexed attachments field
        plain_files = []
        if hasattr(request_files, "getlist"):
            plain_files = request_files.getlist("attachments")
        if not plain_files and hasattr(request_data, "getlist"):
            plain_files = request_data.getlist("attachments")
        if not plain_files and isinstance(request_data, dict):
            plain_files = request_data.get("attachments", [])
        if plain_files:

            def is_uploaded_file(value):
                return hasattr(value, "read") and hasattr(value, "size")

            if (
                isinstance(plain_files, list)
                and plain_files
                and isinstance(plain_files[0], dict)
            ):
                valid_items = [
                    item for item in plain_files if is_uploaded_file(item.get("file"))
                ]
                return valid_items

            valid_files = [file for file in plain_files if is_uploaded_file(file)]
            if valid_files:
                return [{"file": file} for file in valid_files]
            return []
        return []

    max_idx = max(attachments.keys())
    result = []
    for i in range(max_idx + 1):
        if i in attachments:
            result.append(attachments[i])

    return result


def normalize_attachments_payload(request, field_name="attachments", list_fields=None):
    """
    Normalize request data to include indexed attachment payloads.

    Args:
        request: DRF request
        field_name: Field name for attachments (default: "attachments")
        list_fields: List of field names that should always be treated as lists
                    (default: ["attachments_to_remove"])

    Returns:
        dict suitable for serializer input
    """
    if list_fields is None:
        list_fields = ["attachments_to_remove"]

    data = {}
    if hasattr(request.data, "getlist"):
        for key in request.data.keys():
            values = request.data.getlist(key)
            # Always keep as list if field is in list_fields
            if key in list_fields:
                data[key] = values
            else:
                data[key] = values if len(values) > 1 else values[0]
    else:
        data.update(request.data)

    attachments = parse_indexed_attachments(request.data, request.FILES)
    if attachments:
        data[field_name] = attachments
    else:
        data.pop(field_name, None)

    return data
