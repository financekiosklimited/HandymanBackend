"""
Shared validators for file attachments.
Provides reusable validation functions for image, video, and document uploads.
"""

import os

from rest_framework import serializers

from apps.common.constants import (
    ALLOWED_ATTACHMENT_EXTENSIONS,
    ALLOWED_ATTACHMENT_MIME_TYPES,
    ALLOWED_DOCUMENT_EXTENSIONS,
    ALLOWED_DOCUMENT_MIME_TYPES,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_IMAGE_MIME_TYPES,
    ALLOWED_VIDEO_EXTENSIONS,
    ALLOWED_VIDEO_MIME_TYPES,
    ATTACHMENT_TYPE_DOCUMENT,
    ATTACHMENT_TYPE_IMAGE,
    ATTACHMENT_TYPE_VIDEO,
    MAX_ATTACHMENTS_PER_REQUEST,
    MAX_DOCUMENT_SIZE,
    MAX_IMAGE_SIZE,
    MAX_VIDEO_DURATION_SECONDS,
    MAX_VIDEO_SIZE,
)


def get_file_extension(filename):
    """Extract file extension from filename."""
    if not filename:
        return ""
    return os.path.splitext(filename)[1].lower()


def get_file_type_from_mime(content_type):
    """Determine file type (image/video/document) from MIME type."""
    if content_type in ALLOWED_IMAGE_MIME_TYPES:
        return ATTACHMENT_TYPE_IMAGE
    elif content_type in ALLOWED_VIDEO_MIME_TYPES:
        return ATTACHMENT_TYPE_VIDEO
    elif content_type in ALLOWED_DOCUMENT_MIME_TYPES:
        return ATTACHMENT_TYPE_DOCUMENT
    return None


def get_file_type_from_extension(filename):
    """Determine file type (image/video/document) from file extension."""
    ext = get_file_extension(filename)
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return ATTACHMENT_TYPE_IMAGE
    elif ext in ALLOWED_VIDEO_EXTENSIONS:
        return ATTACHMENT_TYPE_VIDEO
    elif ext in ALLOWED_DOCUMENT_EXTENSIONS:
        return ATTACHMENT_TYPE_DOCUMENT
    return None


def validate_attachment_file(file, file_type=None):
    """
    Validate a single attachment file.

    Args:
        file: The uploaded file object
        file_type: Optional explicit file type ('image', 'video', or 'document').
                   If not provided, will be inferred from content_type.

    Returns:
        tuple: (validated_file_type, error_message or None)
    """
    if not file:
        return None, "File is required."

    # Get content type
    content_type = getattr(file, "content_type", None)
    filename = getattr(file, "name", "")
    file_size = getattr(file, "size", 0)

    # Determine file type
    if file_type:
        detected_type = file_type
        # When file_type is explicitly forced, verify MIME type matches
        if content_type:
            mime_type = get_file_type_from_mime(content_type)
            if mime_type and mime_type != file_type:
                return None, f"Invalid content type '{content_type}' for {file_type}."
    elif content_type:
        detected_type = get_file_type_from_mime(content_type)
    else:
        detected_type = get_file_type_from_extension(filename)

    if not detected_type:
        ext = get_file_extension(filename)
        allowed_exts = ", ".join(ALLOWED_ATTACHMENT_EXTENSIONS)
        return None, f"Unsupported file type '{ext}'. Allowed: {allowed_exts}"

    # Validate MIME type if available
    if content_type and content_type not in ALLOWED_ATTACHMENT_MIME_TYPES:
        return None, f"Invalid content type '{content_type}'."

    # Validate file size based on type
    # Note: detected_type is guaranteed to be one of: image, video, or document
    # at this point (line 93-96 returns early if None). The if/elif chain is exhaustive.
    if detected_type == ATTACHMENT_TYPE_IMAGE:
        if file_size > MAX_IMAGE_SIZE:
            max_mb = MAX_IMAGE_SIZE // (1024 * 1024)
            return None, f"Image '{filename}' exceeds maximum size of {max_mb}MB."
    elif detected_type == ATTACHMENT_TYPE_VIDEO:
        if file_size > MAX_VIDEO_SIZE:
            max_mb = MAX_VIDEO_SIZE // (1024 * 1024)
            return None, f"Video '{filename}' exceeds maximum size of {max_mb}MB."
    elif detected_type == ATTACHMENT_TYPE_DOCUMENT:  # pragma: no branch
        if file_size > MAX_DOCUMENT_SIZE:
            max_mb = MAX_DOCUMENT_SIZE // (1024 * 1024)
            return None, f"Document '{filename}' exceeds maximum size of {max_mb}MB."

    # Validate extension matches detected type
    ext = get_file_extension(filename)
    if detected_type == ATTACHMENT_TYPE_IMAGE and ext not in ALLOWED_IMAGE_EXTENSIONS:
        allowed = ", ".join(ALLOWED_IMAGE_EXTENSIONS)
        return None, f"Image must have extension: {allowed}"
    elif detected_type == ATTACHMENT_TYPE_VIDEO and ext not in ALLOWED_VIDEO_EXTENSIONS:
        allowed = ", ".join(ALLOWED_VIDEO_EXTENSIONS)
        return None, f"Video must have extension: {allowed}"
    elif (
        detected_type == ATTACHMENT_TYPE_DOCUMENT
        and ext not in ALLOWED_DOCUMENT_EXTENSIONS
    ):
        allowed = ", ".join(ALLOWED_DOCUMENT_EXTENSIONS)
        return None, f"Document must have extension: {allowed}"

    return detected_type, None


def validate_attachment_list(files, max_count=None):
    """
    Validate a list of attachment files.

    Args:
        files: List of uploaded file objects
        max_count: Maximum number of files allowed (defaults to MAX_ATTACHMENTS_PER_REQUEST)

    Returns:
        tuple: (list of (file, file_type) tuples, list of error messages)
    """
    if max_count is None:
        max_count = MAX_ATTACHMENTS_PER_REQUEST

    if not files:
        return [], []

    if len(files) > max_count:
        return [], [f"Maximum {max_count} attachments allowed per request."]

    validated = []
    errors = []

    for idx, file in enumerate(files):
        file_type, error = validate_attachment_file(file)
        if error:
            errors.append(f"File {idx + 1}: {error}")
        else:
            validated.append((file, file_type))

    return validated, errors


def validate_video_metadata(duration_seconds, thumbnail=None, require_thumbnail=True):
    """
    Validate video-specific metadata.

    Args:
        duration_seconds: Video duration in seconds
        thumbnail: Optional thumbnail file
        require_thumbnail: Whether thumbnail is required

    Returns:
        list of error messages
    """
    errors = []

    if duration_seconds is None:
        errors.append("Video duration is required.")
    elif duration_seconds <= 0:
        errors.append("Video duration must be greater than 0.")
    elif duration_seconds > MAX_VIDEO_DURATION_SECONDS:
        max_min = MAX_VIDEO_DURATION_SECONDS // 60
        errors.append(f"Video duration exceeds maximum of {max_min} minutes.")

    if require_thumbnail and thumbnail is None:
        errors.append("Thumbnail is required for video uploads.")

    # Validate thumbnail if provided
    if thumbnail:
        thumb_type, thumb_error = validate_attachment_file(thumbnail)
        if thumb_error:
            errors.append(f"Thumbnail: {thumb_error}")
        elif thumb_type != ATTACHMENT_TYPE_IMAGE:
            errors.append("Thumbnail must be an image.")

    return errors


class AttachmentValidationMixin:
    """
    Mixin for serializers that handle attachment uploads.
    Provides common validation methods.
    """

    def validate_attachments(self, value):
        """
        Validate attachments field.
        Override max_attachments in subclass if needed.
        """
        max_count = getattr(self, "max_attachments", MAX_ATTACHMENTS_PER_REQUEST)

        if not value:
            return []

        if len(value) > max_count:
            raise serializers.ValidationError(
                f"Maximum {max_count} attachments allowed."
            )

        validated_files = []
        for file in value:
            file_type, error = validate_attachment_file(file)
            if error:
                raise serializers.ValidationError(error)
            validated_files.append(file)

        return validated_files

    def validate_attachment_with_metadata(self, file_data):
        """
        Validate attachment with explicit metadata.

        Expected file_data format:
        {
            'file': <UploadedFile>,
            'file_type': 'image', 'video', or 'document',
            'thumbnail': <UploadedFile> (optional, required for video),
            'duration_seconds': int (required for video)
        }
        """
        file = file_data.get("file")
        file_type = file_data.get("file_type")
        thumbnail = file_data.get("thumbnail")
        duration_seconds = file_data.get("duration_seconds")

        errors = []

        # Validate file
        detected_type, error = validate_attachment_file(file, file_type)
        if error:
            errors.append(error)
        elif detected_type != file_type:
            errors.append(
                f"File type mismatch: declared '{file_type}' but detected '{detected_type}'."
            )

        # Validate video metadata
        if file_type == ATTACHMENT_TYPE_VIDEO:
            video_errors = validate_video_metadata(
                duration_seconds, thumbnail, require_thumbnail=True
            )
            errors.extend(video_errors)

        if errors:
            raise serializers.ValidationError(errors)

        return file_data
