"""
Test cases for chat serializers.
"""

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from apps.accounts.models import User
from apps.chat.models import ChatConversation, ChatMessage, ChatMessageAttachment
from apps.chat.serializers import ChatMessageAttachmentSerializer, SendMessageSerializer
from apps.jobs.models import City, Job, JobCategory


class ChatMessageAttachmentSerializerTests(TestCase):
    """Test cases for ChatMessageAttachmentSerializer."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        self.category = JobCategory.objects.create(
            name="Plumbing", slug="plumbing", is_active=True
        )
        self.city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            is_active=True,
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            title="Test Job",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
            assigned_handyman=self.handyman,
        )
        self.conversation = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.JOB,
            job=self.job,
            homeowner=self.homeowner,
            handyman=self.handyman,
        )
        self.message = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role=ChatMessage.SenderRole.HOMEOWNER,
            message_type=ChatMessage.MessageType.ATTACHMENT,
            content="",
        )

    def _create_test_image(self):
        """Create a test image file."""
        img = Image.new("RGB", (100, 100), color="red")
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)
        return SimpleUploadedFile(
            name="test_image.jpg",
            content=buffer.read(),
            content_type="image/jpeg",
        )

    def test_get_file_url_with_file(self):
        """Test get_file_url returns URL when file exists."""
        test_image = self._create_test_image()
        chat_attachment = ChatMessageAttachment.objects.create(
            message=self.message,
            file=test_image,
            file_type="image",
            file_name=test_image.name,
            file_size=test_image.size,
            order=0,
        )

        serializer = ChatMessageAttachmentSerializer(chat_attachment)
        self.assertIsNotNone(serializer.data["file_url"])
        self.assertIn("test", serializer.data["file_url"])

    def test_get_file_url_without_file(self):
        """Test get_file_url returns None when no file."""
        chat_attachment = ChatMessageAttachment(
            message=self.message,
            file_type="image",
            file_name="missing.jpg",
            file_size=0,
            order=0,
        )

        serializer = ChatMessageAttachmentSerializer(chat_attachment)
        self.assertIsNone(serializer.data["file_url"])

    def test_get_thumbnail_url_with_thumbnail(self):
        """Test get_thumbnail_url returns thumbnail URL when thumbnail exists."""
        test_image = self._create_test_image()
        chat_attachment = ChatMessageAttachment.objects.create(
            message=self.message,
            file=test_image,
            file_type="image",
            file_name=test_image.name,
            file_size=test_image.size,
            order=0,
        )
        # Save a thumbnail
        chat_attachment.thumbnail.save("thumb.jpg", test_image, save=True)

        serializer = ChatMessageAttachmentSerializer(chat_attachment)
        self.assertIsNotNone(serializer.data["thumbnail_url"])
        self.assertIn("thumb", serializer.data["thumbnail_url"])

    def test_get_thumbnail_url_fallback_to_file(self):
        """Test get_thumbnail_url returns file URL when no thumbnail."""
        test_image = self._create_test_image()
        chat_attachment = ChatMessageAttachment.objects.create(
            message=self.message,
            file=test_image,
            file_type="image",
            file_name=test_image.name,
            file_size=test_image.size,
            order=0,
        )

        serializer = ChatMessageAttachmentSerializer(chat_attachment)
        # Should fallback to file URL for images
        self.assertIsNotNone(serializer.data["thumbnail_url"])
        self.assertIn("test", serializer.data["thumbnail_url"])

    def test_get_thumbnail_url_without_file_or_thumbnail(self):
        """Test get_thumbnail_url returns None when no file or thumbnail."""
        chat_attachment = ChatMessageAttachment(
            message=self.message,
            file_type="image",
            file_name="missing.jpg",
            file_size=0,
            order=0,
        )

        serializer = ChatMessageAttachmentSerializer(chat_attachment)
        self.assertIsNone(serializer.data["thumbnail_url"])


class SendMessageSerializerTests(TestCase):
    """Test cases for SendMessageSerializer validation."""

    def _create_test_image(self, name="test.jpg"):
        img = Image.new("RGB", (100, 100), color="red")
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)
        return SimpleUploadedFile(
            name=name,
            content=buffer.read(),
            content_type="image/jpeg",
        )

    def test_validate_attachments_empty_list(self):
        """Test empty attachments list returns empty list."""
        serializer = SendMessageSerializer()
        self.assertEqual(serializer.validate_attachments([]), [])

    def test_validate_attachments_valid_file(self):
        """Test valid attachment passes validation."""
        image_file = self._create_test_image()
        serializer = SendMessageSerializer(data={"attachments": [{"file": image_file}]})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(len(serializer.validated_data["attachments"]), 1)
        self.assertEqual(
            serializer.validated_data["attachments"][0]["file"], image_file
        )
        self.assertEqual(
            serializer.validated_data["attachments"][0]["file_type"], "image"
        )

    def test_validate_attachments_invalid_file(self):
        """Test invalid attachment raises validation error."""
        bad_file = SimpleUploadedFile(
            "bad.gif", b"gif", content_type="application/octet-stream"
        )
        serializer = SendMessageSerializer(data={"attachments": [{"file": bad_file}]})

        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)
        self.assertIn("unsupported file type", str(serializer.errors).lower())

    def test_validate_attachments_exceeds_max_count(self):
        """Test too many attachments raises validation error."""
        from apps.chat.serializers import MAX_CHAT_ATTACHMENTS

        # Create more attachments than allowed
        attachments = []
        for i in range(MAX_CHAT_ATTACHMENTS + 1):
            attachments.append({"file": self._create_test_image(f"test{i}.jpg")})

        serializer = SendMessageSerializer(data={"attachments": attachments})
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)
        self.assertIn(f"Maximum {MAX_CHAT_ATTACHMENTS}", str(serializer.errors))
