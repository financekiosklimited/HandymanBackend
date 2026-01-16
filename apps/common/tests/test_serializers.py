"""Tests for common serializers."""

from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image as PILImage
from rest_framework import serializers

from apps.common.constants import (
    ATTACHMENT_TYPE_DOCUMENT,
    ATTACHMENT_TYPE_IMAGE,
    ATTACHMENT_TYPE_VIDEO,
    MAX_DOCUMENT_SIZE,
    MAX_IMAGE_SIZE,
    MAX_VIDEO_SIZE,
)
from apps.common.serializers import (
    AttachmentInputSerializer,
    create_list_response_serializer,
    create_response_serializer,
)
from apps.common.validators import (
    AttachmentValidationMixin,
    get_file_extension,
    get_file_type_from_extension,
    get_file_type_from_mime,
    validate_attachment_file,
    validate_attachment_list,
    validate_video_metadata,
)


class DummySerializer(serializers.Serializer):
    """Dummy serializer for testing."""

    name = serializers.CharField()
    value = serializers.IntegerField()


class CreateResponseSerializerTests(TestCase):
    """Test cases for create_response_serializer factory function."""

    def test_create_response_serializer_with_custom_name(self):
        """Test creating response serializer with custom name."""
        ResponseSerializer = create_response_serializer(
            DummySerializer, serializer_name="CustomResponse"
        )

        self.assertEqual(ResponseSerializer.__name__, "CustomResponse")
        self.assertEqual(ResponseSerializer.Meta.ref_name, "CustomResponse")

        # Check that it has envelope fields
        instance = ResponseSerializer()
        self.assertIn("message", instance.fields)
        self.assertIn("data", instance.fields)
        self.assertIn("errors", instance.fields)
        self.assertIn("meta", instance.fields)

    def test_create_response_serializer_auto_name_generation(self):
        """Test auto-generating serializer name when not provided."""
        ResponseSerializer = create_response_serializer(DummySerializer)

        self.assertEqual(ResponseSerializer.__name__, "DummySerializerResponse")
        self.assertEqual(ResponseSerializer.Meta.ref_name, "DummySerializerResponse")


class CreateListResponseSerializerTests(TestCase):
    """Test cases for create_list_response_serializer factory function."""

    def test_create_list_response_serializer_with_custom_name(self):
        """Test creating list response serializer with custom name."""
        ListResponseSerializer = create_list_response_serializer(
            DummySerializer, serializer_name="CustomListResponse"
        )

        self.assertEqual(ListResponseSerializer.__name__, "CustomListResponse")
        self.assertEqual(ListResponseSerializer.Meta.ref_name, "CustomListResponse")

        # Check that it has envelope fields
        instance = ListResponseSerializer()
        self.assertIn("message", instance.fields)
        self.assertIn("data", instance.fields)
        self.assertIn("errors", instance.fields)
        self.assertIn("meta", instance.fields)

        # Check that data field is a list
        self.assertTrue(instance.fields["data"].many)

    def test_create_list_response_serializer_auto_name_generation(self):
        """Test auto-generating list serializer name when not provided."""
        ListResponseSerializer = create_list_response_serializer(DummySerializer)

        self.assertEqual(ListResponseSerializer.__name__, "DummySerializerListResponse")
        self.assertEqual(
            ListResponseSerializer.Meta.ref_name, "DummySerializerListResponse"
        )


class AttachmentValidatorTests(TestCase):
    """Test cases for attachment validator helpers."""

    def _make_file(self, name="test.jpg", content_type="image/jpeg", size=10):
        file_obj = SimpleUploadedFile(name, b"x" * size, content_type=content_type)
        file_obj.size = size
        return file_obj

    def test_get_file_extension(self):
        """Test file extension extraction."""
        self.assertEqual(get_file_extension("photo.JPG"), ".jpg")
        self.assertEqual(get_file_extension(""), "")

    def test_get_file_type_from_mime(self):
        """Test mime type detection."""
        self.assertEqual(get_file_type_from_mime("image/jpeg"), ATTACHMENT_TYPE_IMAGE)
        self.assertEqual(get_file_type_from_mime("video/mp4"), ATTACHMENT_TYPE_VIDEO)
        self.assertEqual(
            get_file_type_from_mime("application/pdf"), ATTACHMENT_TYPE_DOCUMENT
        )
        self.assertEqual(
            get_file_type_from_mime(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            ATTACHMENT_TYPE_DOCUMENT,
        )
        self.assertIsNone(get_file_type_from_mime("application/octet-stream"))

    def test_get_file_type_from_extension(self):
        """Test extension based file type detection."""
        self.assertEqual(
            get_file_type_from_extension("photo.png"), ATTACHMENT_TYPE_IMAGE
        )
        self.assertEqual(
            get_file_type_from_extension("clip.webm"), ATTACHMENT_TYPE_VIDEO
        )
        self.assertEqual(
            get_file_type_from_extension("document.pdf"), ATTACHMENT_TYPE_DOCUMENT
        )
        self.assertEqual(
            get_file_type_from_extension("report.docx"), ATTACHMENT_TYPE_DOCUMENT
        )
        self.assertEqual(
            get_file_type_from_extension("spreadsheet.xlsx"), ATTACHMENT_TYPE_DOCUMENT
        )
        self.assertEqual(
            get_file_type_from_extension("presentation.pptx"), ATTACHMENT_TYPE_DOCUMENT
        )
        self.assertIsNone(get_file_type_from_extension("unknown.xyz"))

    def test_validate_attachment_file_requires_file(self):
        """Test validation requires a file object."""
        file_type, error = validate_attachment_file(None)
        self.assertIsNone(file_type)
        self.assertEqual(error, "File is required.")

    def test_validate_attachment_file_invalid_content_type(self):
        """Test invalid content type error when file_type is forced."""
        file_obj = self._make_file(
            name="photo.jpg", content_type="application/pdf", size=100
        )
        file_type, error = validate_attachment_file(file_obj, file_type="image")
        self.assertIsNone(file_type)
        self.assertIn("Invalid content type", error)

    def test_validate_attachment_file_invalid_extension(self):
        """Test invalid extension errors for image and video."""
        file_obj = self._make_file(name="photo.gif", content_type="image/jpeg")
        file_type, error = validate_attachment_file(file_obj, file_type="image")
        self.assertIsNone(file_type)
        self.assertIn("Image must have extension", error)

        video_obj = self._make_file(name="clip.jpg", content_type="video/mp4")
        file_type, error = validate_attachment_file(video_obj, file_type="video")
        self.assertIsNone(file_type)
        self.assertIn("Video must have extension", error)

    def test_validate_attachment_file_detects_extension_without_mime(self):
        """Test validation falls back to file extension when mime missing."""
        file_obj = self._make_file(name="photo.jpg", content_type="image/jpeg")
        file_obj.content_type = None

        file_type, error = validate_attachment_file(file_obj)

        self.assertEqual(file_type, "image")
        self.assertIsNone(error)

    def test_validate_attachment_file_size_limits(self):
        """Test size validation for image, video, and document."""
        image_obj = self._make_file(name="large.jpg", content_type="image/jpeg")
        image_obj.size = MAX_IMAGE_SIZE + 1
        file_type, error = validate_attachment_file(image_obj, file_type="image")
        self.assertIsNone(file_type)
        self.assertIn("exceeds maximum size", error)

        video_obj = self._make_file(name="large.mp4", content_type="video/mp4")
        video_obj.size = MAX_VIDEO_SIZE + 1
        file_type, error = validate_attachment_file(video_obj, file_type="video")
        self.assertIsNone(file_type)
        self.assertIn("exceeds maximum size", error)

        doc_obj = self._make_file(name="large.pdf", content_type="application/pdf")
        doc_obj.size = MAX_DOCUMENT_SIZE + 1
        file_type, error = validate_attachment_file(doc_obj, file_type="document")
        self.assertIsNone(file_type)
        self.assertIn("exceeds maximum size", error)

    def test_validate_attachment_file_valid_video(self):
        """Test valid video file passes validation."""
        video_obj = self._make_file(name="clip.mp4", content_type="video/mp4")
        file_type, error = validate_attachment_file(video_obj)
        self.assertEqual(file_type, "video")
        self.assertIsNone(error)

        file_type, error = validate_attachment_file(video_obj, file_type="video")
        self.assertEqual(file_type, "video")
        self.assertIsNone(error)

    def test_validate_attachment_file_valid_document(self):
        """Test valid document files pass validation."""
        # PDF - explicitly tests branch 111->117 (document under size limit)
        pdf_obj = self._make_file(name="doc.pdf", content_type="application/pdf")
        file_type, error = validate_attachment_file(pdf_obj)
        self.assertEqual(file_type, "document")
        self.assertIsNone(error)

        file_type, error = validate_attachment_file(pdf_obj, file_type="document")
        self.assertEqual(file_type, "document")
        self.assertIsNone(error)

        # Word document
        docx_obj = self._make_file(
            name="doc.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        file_type, error = validate_attachment_file(docx_obj)
        self.assertEqual(file_type, "document")
        self.assertIsNone(error)

        # Excel spreadsheet
        xlsx_obj = self._make_file(
            name="spreadsheet.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        file_type, error = validate_attachment_file(xlsx_obj)
        self.assertEqual(file_type, "document")
        self.assertIsNone(error)

        # PowerPoint presentation
        pptx_obj = self._make_file(
            name="presentation.pptx",
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
        file_type, error = validate_attachment_file(pptx_obj)
        self.assertEqual(file_type, "document")
        self.assertIsNone(error)

    def test_validate_attachment_file_document_invalid_extension(self):
        """Test invalid document extension with forced file_type."""
        file_obj = self._make_file(name="doc.txt", content_type="application/pdf")
        file_type, error = validate_attachment_file(file_obj, file_type="document")
        self.assertIsNone(file_type)
        self.assertIn("Document must have extension", error)

    def test_validate_attachment_file_unsupported_type(self):
        """Test unsupported extension error."""
        file_obj = self._make_file(
            name="photo.gif", content_type="application/octet-stream"
        )
        file_type, error = validate_attachment_file(file_obj)
        self.assertIsNone(file_type)
        self.assertIn("Unsupported file type", error)

    def test_validate_attachment_file_forced_type_without_content_type(self):
        """Test validation with forced file_type but no content_type."""
        # This covers the branch where file_type is forced but content_type is None
        file_obj = self._make_file(name="photo.jpg", content_type="image/jpeg")
        file_obj.content_type = None

        file_type, error = validate_attachment_file(file_obj, file_type="image")
        self.assertEqual(file_type, "image")
        self.assertIsNone(error)

    def test_validate_attachment_file_invalid_mime_not_in_allowed_list(self):
        """Test invalid MIME type that is not in allowed list."""
        # This covers line 100: content_type not in ALLOWED_ATTACHMENT_MIME_TYPES
        # We need to force file_type to get a detected_type, but use a content_type
        # that's not in the allowed list. When file_type is forced and content_type
        # doesn't map to any known type (mime_type is None at line 85), it skips
        # the mismatch check at line 86 but reaches line 100.
        file_obj = self._make_file(name="file.jpg", content_type="text/html")
        file_type, error = validate_attachment_file(file_obj, file_type="image")
        self.assertIsNone(file_type)
        self.assertIn("Invalid content type", error)

    def test_validate_attachment_list(self):
        """Test list validation and error collection."""
        file_obj = self._make_file(name="photo.jpg", content_type="image/jpeg")
        validated, errors = validate_attachment_list([], max_count=1)
        self.assertEqual(validated, [])
        self.assertEqual(errors, [])

        validated, errors = validate_attachment_list([file_obj] * 2, max_count=1)
        self.assertEqual(validated, [])
        self.assertIn("Maximum 1 attachments", errors[0])

        bad_file = self._make_file(
            name="photo.gif", content_type="application/octet-stream"
        )
        validated, errors = validate_attachment_list([bad_file], max_count=2)
        self.assertEqual(validated, [])
        self.assertIn("File 1", errors[0])

        validated, errors = validate_attachment_list([file_obj])
        self.assertEqual(errors, [])
        self.assertEqual(validated[0][1], "image")

    def test_validate_video_metadata(self):
        """Test video metadata validation errors and success."""
        errors = validate_video_metadata(None)
        self.assertTrue(any("Video duration is required" in error for error in errors))

        errors = validate_video_metadata(0)
        self.assertTrue(
            any("Video duration must be greater" in error for error in errors)
        )

        errors = validate_video_metadata(301)
        self.assertTrue(any("Video duration exceeds" in error for error in errors))

        errors = validate_video_metadata(10)
        self.assertTrue(any("Thumbnail is required" in error for error in errors))

        bad_thumb = self._make_file(name="clip.mp4", content_type="video/mp4")
        errors = validate_video_metadata(
            10, thumbnail=bad_thumb, require_thumbnail=True
        )
        self.assertTrue(any("Thumbnail must be an image" in error for error in errors))

        bad_thumb = self._make_file(
            name="thumb.gif", content_type="application/octet-stream"
        )
        errors = validate_video_metadata(
            10, thumbnail=bad_thumb, require_thumbnail=True
        )
        self.assertTrue(any("Thumbnail:" in error for error in errors))

        good_thumb = self._make_file(name="thumb.jpg", content_type="image/jpeg")
        errors = validate_video_metadata(
            10, thumbnail=good_thumb, require_thumbnail=True
        )
        self.assertEqual(errors, [])


class DummyAttachmentSerializer(AttachmentValidationMixin, serializers.Serializer):
    """Dummy serializer for attachment mixin tests."""

    max_attachments = 1


class AttachmentValidationMixinTests(TestCase):
    """Test cases for AttachmentValidationMixin."""

    def _make_file(self, name="test.jpg", content_type="image/jpeg", size=10):
        file_obj = SimpleUploadedFile(name, b"x" * size, content_type=content_type)
        file_obj.size = size
        return file_obj

    def test_validate_attachments_empty(self):
        """Test empty attachments return empty list."""
        serializer = DummyAttachmentSerializer()
        self.assertEqual(serializer.validate_attachments([]), [])

    def test_validate_attachments_max_count(self):
        """Test max attachments validation."""
        serializer = DummyAttachmentSerializer()
        files = [self._make_file(name="a.jpg"), self._make_file(name="b.jpg")]
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_attachments(files)

    def test_validate_attachments_invalid_file(self):
        """Test invalid file in attachments list raises error."""
        serializer = DummyAttachmentSerializer()
        bad_file = self._make_file(
            name="photo.gif", content_type="application/octet-stream"
        )
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_attachments([bad_file])

    def test_validate_attachments_valid(self):
        """Test valid attachments return files."""
        serializer = DummyAttachmentSerializer()
        file_obj = self._make_file(name="photo.jpg", content_type="image/jpeg")
        validated = serializer.validate_attachments([file_obj])
        self.assertEqual(validated, [file_obj])

    def test_validate_attachment_with_metadata_file_error(self):
        """Test attachment file validation errors are surfaced."""
        serializer = DummyAttachmentSerializer()
        bad_file = self._make_file(name="photo.gif", content_type="image/jpeg")

        with self.assertRaises(serializers.ValidationError) as context:
            serializer.validate_attachment_with_metadata(
                {
                    "file": bad_file,
                    "file_type": "image",
                    "thumbnail": None,
                    "duration_seconds": None,
                }
            )

        self.assertIn("Image must have extension", str(context.exception))

    def test_validate_attachment_with_metadata_mismatch(self):
        """Test file type mismatch error in metadata validation."""
        serializer = DummyAttachmentSerializer()
        file_obj = self._make_file(name="photo.jpg", content_type="image/jpeg")

        with patch(
            "apps.common.validators.validate_attachment_file",
            return_value=("image", None),
        ):
            with self.assertRaises(serializers.ValidationError) as context:
                serializer.validate_attachment_with_metadata(
                    {
                        "file": file_obj,
                        "file_type": "video",
                        "thumbnail": None,
                        "duration_seconds": None,
                    }
                )

        self.assertIn("File type mismatch", str(context.exception))

    def test_validate_attachment_with_metadata_video_errors(self):
        """Test video metadata errors are returned."""
        serializer = DummyAttachmentSerializer()
        file_obj = self._make_file(name="video.mp4", content_type="video/mp4")

        with self.assertRaises(serializers.ValidationError) as context:
            serializer.validate_attachment_with_metadata(
                {
                    "file": file_obj,
                    "file_type": "video",
                    "thumbnail": None,
                    "duration_seconds": None,
                }
            )

        self.assertIn("Video duration is required", str(context.exception))

    def test_validate_attachment_with_metadata_success(self):
        """Test valid attachment with metadata returns data."""
        serializer = DummyAttachmentSerializer()
        file_obj = self._make_file(name="video.mp4", content_type="video/mp4")
        thumbnail = self._make_file(name="thumb.jpg", content_type="image/jpeg")

        data = {
            "file": file_obj,
            "file_type": "video",
            "thumbnail": thumbnail,
            "duration_seconds": 10,
        }
        self.assertEqual(serializer.validate_attachment_with_metadata(data), data)


class AttachmentInputSerializerTests(TestCase):
    """Test cases for AttachmentInputSerializer."""

    def _make_file(self, name="test.jpg", content_type="image/jpeg", size=10):
        file_obj = SimpleUploadedFile(name, b"x" * size, content_type=content_type)
        file_obj.size = size
        return file_obj

    def _make_image_file(self, name="test.jpg", content_type="image/jpeg"):
        """Create a valid image file for tests."""
        image_io = BytesIO()
        image = PILImage.new("RGB", (100, 100), color="red")
        image.save(image_io, format="JPEG")
        image_io.seek(0)
        file_obj = SimpleUploadedFile(name, image_io.read(), content_type=content_type)
        return file_obj

    def test_valid_image_attachment(self):
        """Test valid image attachment passes validation."""
        file_obj = self._make_file(name="photo.jpg", content_type="image/jpeg")
        serializer = AttachmentInputSerializer(data={"file": file_obj})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["file_type"], "image")
        self.assertIsNone(serializer.validated_data["thumbnail"])
        self.assertIsNone(serializer.validated_data["duration_seconds"])

    def test_valid_video_attachment_with_metadata(self):
        """Test valid video attachment with required metadata passes validation."""
        file_obj = self._make_file(name="video.mp4", content_type="video/mp4")
        thumbnail = self._make_image_file(name="thumb.jpg", content_type="image/jpeg")

        serializer = AttachmentInputSerializer(
            data={"file": file_obj, "thumbnail": thumbnail, "duration_seconds": 60}
        )

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["file_type"], "video")
        self.assertIsNotNone(serializer.validated_data["thumbnail"])
        self.assertEqual(serializer.validated_data["duration_seconds"], 60)

    def test_video_attachment_requires_thumbnail(self):
        """Test video attachment requires thumbnail."""
        file_obj = self._make_file(name="video.mp4", content_type="video/mp4")

        serializer = AttachmentInputSerializer(
            data={"file": file_obj, "duration_seconds": 60}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("thumbnail", serializer.errors)

    def test_video_attachment_requires_duration(self):
        """Test video attachment requires duration_seconds."""
        file_obj = self._make_file(name="video.mp4", content_type="video/mp4")
        thumbnail = self._make_image_file(name="thumb.jpg", content_type="image/jpeg")

        serializer = AttachmentInputSerializer(
            data={"file": file_obj, "thumbnail": thumbnail}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("duration_seconds", serializer.errors)

    def test_valid_document_attachment(self):
        """Test valid document attachment passes validation."""
        # PDF
        pdf_obj = self._make_file(name="doc.pdf", content_type="application/pdf")
        serializer = AttachmentInputSerializer(data={"file": pdf_obj})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["file_type"], "document")
        self.assertIsNone(serializer.validated_data["thumbnail"])
        self.assertIsNone(serializer.validated_data["duration_seconds"])

    def test_valid_word_document_attachment(self):
        """Test valid Word document attachment passes validation."""
        docx_obj = self._make_file(
            name="report.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        serializer = AttachmentInputSerializer(data={"file": docx_obj})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["file_type"], "document")

    def test_valid_excel_attachment(self):
        """Test valid Excel spreadsheet attachment passes validation."""
        xlsx_obj = self._make_file(
            name="data.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        serializer = AttachmentInputSerializer(data={"file": xlsx_obj})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["file_type"], "document")

    def test_valid_powerpoint_attachment(self):
        """Test valid PowerPoint attachment passes validation."""
        pptx_obj = self._make_file(
            name="slides.pptx",
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
        serializer = AttachmentInputSerializer(data={"file": pptx_obj})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["file_type"], "document")

    def test_document_ignores_video_metadata(self):
        """Test document attachments ignore video-specific metadata fields."""
        pdf_obj = self._make_file(name="doc.pdf", content_type="application/pdf")
        thumbnail = self._make_image_file(name="thumb.jpg", content_type="image/jpeg")

        # Even if thumbnail and duration are provided, they should be cleared
        serializer = AttachmentInputSerializer(
            data={"file": pdf_obj, "thumbnail": thumbnail, "duration_seconds": 120}
        )

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["file_type"], "document")
        self.assertIsNone(serializer.validated_data["thumbnail"])
        self.assertIsNone(serializer.validated_data["duration_seconds"])

    def test_invalid_file_type_rejected(self):
        """Test unsupported file types are rejected."""
        file_obj = self._make_file(
            name="script.exe", content_type="application/octet-stream"
        )
        serializer = AttachmentInputSerializer(data={"file": file_obj})

        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)

    def test_thumbnail_size_limit(self):
        """Test thumbnail exceeding size limit fails validation."""
        from apps.common.constants import MAX_THUMBNAIL_SIZE

        file_obj = self._make_file(name="video.mp4", content_type="video/mp4")

        # Create an oversized thumbnail
        large_thumbnail = self._make_image_file(
            name="thumb.jpg", content_type="image/jpeg"
        )
        large_thumbnail.size = MAX_THUMBNAIL_SIZE + 1

        serializer = AttachmentInputSerializer(
            data={
                "file": file_obj,
                "thumbnail": large_thumbnail,
                "duration_seconds": 60,
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("thumbnail", serializer.errors)
        self.assertIn("exceeds maximum size", str(serializer.errors["thumbnail"]))

    def test_thumbnail_must_be_image(self):
        """Test thumbnail that is not an image fails validation."""
        file_obj = self._make_file(name="video.mp4", content_type="video/mp4")

        # Create a non-image file as thumbnail
        bad_thumbnail = self._make_file(
            name="thumb.mp4", content_type="video/mp4", size=100
        )

        serializer = AttachmentInputSerializer(
            data={"file": file_obj, "thumbnail": bad_thumbnail, "duration_seconds": 60}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("thumbnail", serializer.errors)

    def test_duration_seconds_must_be_positive(self):
        """Test zero or negative duration_seconds fails validation."""
        file_obj = self._make_file(name="video.mp4", content_type="video/mp4")
        thumbnail = self._make_image_file(name="thumb.jpg", content_type="image/jpeg")

        serializer = AttachmentInputSerializer(
            data={"file": file_obj, "thumbnail": thumbnail, "duration_seconds": 0}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("duration_seconds", serializer.errors)

    def test_duration_seconds_max_limit(self):
        """Test duration_seconds exceeding max fails validation."""
        from apps.common.constants import MAX_VIDEO_DURATION_SECONDS

        file_obj = self._make_file(name="video.mp4", content_type="video/mp4")
        thumbnail = self._make_image_file(name="thumb.jpg", content_type="image/jpeg")

        serializer = AttachmentInputSerializer(
            data={
                "file": file_obj,
                "thumbnail": thumbnail,
                "duration_seconds": MAX_VIDEO_DURATION_SECONDS + 1,
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("duration_seconds", serializer.errors)
        self.assertIn("exceeds maximum", str(serializer.errors["duration_seconds"]))


class AttachmentInputSerializerNullValueTests(TestCase):
    """Test cases for AttachmentInputSerializer with null/None values."""

    def _make_file(self, name="test.jpg", content_type="image/jpeg", size=10):
        file_obj = SimpleUploadedFile(name, b"x" * size, content_type=content_type)
        file_obj.size = size
        return file_obj

    def test_validate_thumbnail_returns_none_when_none(self):
        """Test validate_thumbnail returns None when value is None."""
        file_obj = self._make_file(name="photo.jpg", content_type="image/jpeg")

        serializer = AttachmentInputSerializer(
            data={"file": file_obj, "thumbnail": None}
        )

        self.assertTrue(serializer.is_valid())
        self.assertIsNone(serializer.validated_data["thumbnail"])

    def test_validate_duration_seconds_returns_none_when_none(self):
        """Test validate_duration_seconds returns None when value is None."""
        file_obj = self._make_file(name="photo.jpg", content_type="image/jpeg")

        serializer = AttachmentInputSerializer(
            data={"file": file_obj, "duration_seconds": None}
        )

        self.assertTrue(serializer.is_valid())
        self.assertIsNone(serializer.validated_data["duration_seconds"])


class ParseIndexedAttachmentsTests(TestCase):
    """Test cases for parse_indexed_attachments function."""

    def _make_file(self, name="test.jpg", content_type="image/jpeg", size=10):
        file_obj = SimpleUploadedFile(name, b"x" * size, content_type=content_type)
        file_obj.size = size
        return file_obj

    def test_parse_indexed_attachments_from_files(self):
        """Test parsing indexed attachments from FILES."""
        from django.http import QueryDict
        from django.utils.datastructures import MultiValueDict

        from apps.common.serializers import parse_indexed_attachments

        file1 = self._make_file(name="photo1.jpg")
        file2 = self._make_file(name="photo2.jpg")
        thumb = self._make_file(name="thumb.jpg")

        request_files = MultiValueDict(
            {
                "attachments[0].file": [file1],
                "attachments[1].file": [file2],
                "attachments[1].thumbnail": [thumb],
            }
        )
        request_data = QueryDict(mutable=True)
        request_data["attachments[1].duration_seconds"] = "120"

        result = parse_indexed_attachments(request_data, request_files)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["file"], file1)
        self.assertEqual(result[1]["file"], file2)
        self.assertEqual(result[1]["thumbnail"], thumb)
        self.assertEqual(result[1]["duration_seconds"], 120)

    def test_parse_indexed_attachments_invalid_duration(self):
        """Test parsing with invalid duration_seconds (non-integer)."""
        from django.http import QueryDict
        from django.utils.datastructures import MultiValueDict

        from apps.common.serializers import parse_indexed_attachments

        file1 = self._make_file(name="video.mp4")

        request_files = MultiValueDict({"attachments[0].file": [file1]})
        request_data = QueryDict(mutable=True)
        request_data["attachments[0].duration_seconds"] = "invalid"

        result = parse_indexed_attachments(request_data, request_files)

        # Should still parse, but duration remains as string for serializer to validate
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["duration_seconds"], "invalid")

    def test_parse_indexed_attachments_fallback_plain_files(self):
        """Test fallback to plain attachments field."""
        from django.utils.datastructures import MultiValueDict

        from apps.common.serializers import parse_indexed_attachments

        file1 = self._make_file(name="photo1.jpg")
        file2 = self._make_file(name="photo2.jpg")

        request_files = MultiValueDict({"attachments": [file1, file2]})
        request_data = {}

        result = parse_indexed_attachments(request_data, request_files)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["file"], file1)
        self.assertEqual(result[1]["file"], file2)

    def test_parse_indexed_attachments_fallback_from_data(self):
        """Test fallback to plain attachments from request.data."""
        from django.utils.datastructures import MultiValueDict

        from apps.common.serializers import parse_indexed_attachments

        file1 = self._make_file(name="photo1.jpg")

        request_files = MultiValueDict()
        # Use dict fallback since QueryDict doesn't support files
        request_data_dict = {"attachments": [file1]}

        result = parse_indexed_attachments(request_data_dict, request_files)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["file"], file1)

    def test_parse_indexed_attachments_dict_format(self):
        """Test parsing attachments already in dict format."""
        from django.utils.datastructures import MultiValueDict

        from apps.common.serializers import parse_indexed_attachments

        file1 = self._make_file(name="photo1.jpg")

        request_files = MultiValueDict()
        request_data = {"attachments": [{"file": file1}]}

        result = parse_indexed_attachments(request_data, request_files)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["file"], file1)

    def test_parse_indexed_attachments_empty(self):
        """Test parsing with no attachments returns empty list."""
        from django.utils.datastructures import MultiValueDict

        from apps.common.serializers import parse_indexed_attachments

        request_files = MultiValueDict()
        request_data = {}

        result = parse_indexed_attachments(request_data, request_files)

        self.assertEqual(result, [])

    def test_parse_indexed_attachments_invalid_files_filtered(self):
        """Test that non-file objects are filtered out."""
        from django.utils.datastructures import MultiValueDict

        from apps.common.serializers import parse_indexed_attachments

        request_files = MultiValueDict()
        request_data = {"attachments": ["not a file", 123, None]}

        result = parse_indexed_attachments(request_data, request_files)

        self.assertEqual(result, [])

    def test_parse_indexed_attachments_data_key_new_index(self):
        """Test creating new attachment entry from data when index not in files.

        Covers line 280: attachments[idx] = {} for data keys with new index.
        """
        from django.http import QueryDict
        from django.utils.datastructures import MultiValueDict

        from apps.common.serializers import parse_indexed_attachments

        file1 = self._make_file(name="video.mp4", content_type="video/mp4")

        # Only add file at index 0
        request_files = MultiValueDict({"attachments[0].file": [file1]})
        request_data = QueryDict(mutable=True)
        # Add duration at index 1 (not in files yet)
        request_data["attachments[1].duration_seconds"] = "60"

        result = parse_indexed_attachments(request_data, request_files)

        # Should have 2 entries, one from files and one from data
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["file"], file1)
        self.assertEqual(result[1]["duration_seconds"], 60)

    def test_parse_indexed_attachments_sparse_indexes(self):
        """Test parsing with sparse/non-contiguous indexes.

        Covers branch 324->323: when index is not in attachments dict.
        """
        from django.http import QueryDict
        from django.utils.datastructures import MultiValueDict

        from apps.common.serializers import parse_indexed_attachments

        file1 = self._make_file(name="photo1.jpg")
        file2 = self._make_file(name="photo2.jpg")

        # Create sparse indexes: 0 and 2 (skip 1)
        request_files = MultiValueDict(
            {
                "attachments[0].file": [file1],
                "attachments[2].file": [file2],
            }
        )
        request_data = QueryDict(mutable=True)

        result = parse_indexed_attachments(request_data, request_files)

        # Should have 2 entries since index 1 is missing
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["file"], file1)
        self.assertEqual(result[1]["file"], file2)

    def test_parse_indexed_attachments_fallback_from_data_getlist(self):
        """Test fallback to attachments from request_data.getlist.

        Covers branch 285->287: when request_files.getlist returns empty but
        request_data.getlist has files.
        """
        from django.utils.datastructures import MultiValueDict

        from apps.common.serializers import parse_indexed_attachments

        file1 = self._make_file(name="photo1.jpg")

        # request_files has getlist but returns empty for "attachments"
        request_files = MultiValueDict()

        # request_data with getlist that has files
        request_data = MultiValueDict({"attachments": [file1]})

        result = parse_indexed_attachments(request_data, request_files)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["file"], file1)

    def test_parse_indexed_attachments_files_without_getlist(self):
        """Test fallback when request_files has no getlist method.

        Covers branch 285->287: when hasattr(request_files, "getlist") is False.
        """
        from apps.common.serializers import parse_indexed_attachments

        file1 = self._make_file(name="photo1.jpg")

        # Use a simple dict without getlist method
        request_files = {}
        request_data = {"attachments": [file1]}

        result = parse_indexed_attachments(request_data, request_files)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["file"], file1)


class NormalizeAttachmentsPayloadTests(TestCase):
    """Test cases for normalize_attachments_payload function."""

    def _make_file(self, name="test.jpg", content_type="image/jpeg", size=10):
        file_obj = SimpleUploadedFile(name, b"x" * size, content_type=content_type)
        file_obj.size = size
        return file_obj

    def test_normalize_handles_list_fields(self):
        """Test normalize_attachments_payload handles list fields correctly."""
        from unittest.mock import MagicMock

        from django.http import QueryDict
        from django.utils.datastructures import MultiValueDict

        from apps.common.serializers import normalize_attachments_payload

        request = MagicMock()
        request.data = QueryDict(mutable=True)
        request.data.setlist("attachments_to_remove", ["uuid1", "uuid2"])
        request.data["name"] = "test"
        request.FILES = MultiValueDict()

        result = normalize_attachments_payload(request)

        self.assertEqual(result["attachments_to_remove"], ["uuid1", "uuid2"])
        self.assertEqual(result["name"], "test")

    def test_normalize_with_custom_list_fields(self):
        """Test normalize_attachments_payload with custom list_fields.

        Covers branch 343->346: when list_fields is not None.
        """
        from unittest.mock import MagicMock

        from django.http import QueryDict
        from django.utils.datastructures import MultiValueDict

        from apps.common.serializers import normalize_attachments_payload

        request = MagicMock()
        request.data = QueryDict(mutable=True)
        request.data.setlist("custom_list", ["val1", "val2"])
        request.data["single_value"] = "single"
        request.FILES = MultiValueDict()

        # Pass custom list_fields
        result = normalize_attachments_payload(
            request, list_fields=["custom_list", "another_list"]
        )

        self.assertEqual(result["custom_list"], ["val1", "val2"])
        self.assertEqual(result["single_value"], "single")
