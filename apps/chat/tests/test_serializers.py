"""
Test cases for chat serializers.
"""

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from apps.accounts.models import User
from apps.chat.models import ChatConversation, ChatMessage, ChatMessageImage
from apps.chat.serializers import ChatMessageImageSerializer
from apps.jobs.models import City, Job, JobCategory


class ChatMessageImageSerializerTests(TestCase):
    """Test cases for ChatMessageImageSerializer."""

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
            message_type=ChatMessage.MessageType.IMAGE,
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

    def test_get_image_url_with_image(self):
        """Test get_image_url returns URL when image exists."""
        chat_image = ChatMessageImage.objects.create(
            message=self.message,
            order=0,
        )
        # Save an actual image
        test_image = self._create_test_image()
        chat_image.image.save("test.jpg", test_image, save=True)

        serializer = ChatMessageImageSerializer(chat_image)
        self.assertIsNotNone(serializer.data["image_url"])
        self.assertIn("test", serializer.data["image_url"])

    def test_get_image_url_without_image(self):
        """Test get_image_url returns None when no image."""
        chat_image = ChatMessageImage.objects.create(
            message=self.message,
            order=0,
        )
        # Don't save any image

        serializer = ChatMessageImageSerializer(chat_image)
        self.assertIsNone(serializer.data["image_url"])

    def test_get_thumbnail_url_with_thumbnail(self):
        """Test get_thumbnail_url returns thumbnail URL when thumbnail exists."""
        chat_image = ChatMessageImage.objects.create(
            message=self.message,
            order=0,
        )
        # Save a thumbnail
        test_image = self._create_test_image()
        chat_image.thumbnail.save("thumb.jpg", test_image, save=True)

        serializer = ChatMessageImageSerializer(chat_image)
        self.assertIsNotNone(serializer.data["thumbnail_url"])
        self.assertIn("thumb", serializer.data["thumbnail_url"])

    def test_get_thumbnail_url_fallback_to_image(self):
        """Test get_thumbnail_url returns image URL when no thumbnail."""
        chat_image = ChatMessageImage.objects.create(
            message=self.message,
            order=0,
        )
        # Save only the main image, no thumbnail
        test_image = self._create_test_image()
        chat_image.image.save("test.jpg", test_image, save=True)

        serializer = ChatMessageImageSerializer(chat_image)
        # Should fallback to image URL
        self.assertIsNotNone(serializer.data["thumbnail_url"])
        self.assertIn("test", serializer.data["thumbnail_url"])

    def test_get_thumbnail_url_without_image_or_thumbnail(self):
        """Test get_thumbnail_url returns None when no image or thumbnail."""
        chat_image = ChatMessageImage.objects.create(
            message=self.message,
            order=0,
        )
        # Don't save any image or thumbnail

        serializer = ChatMessageImageSerializer(chat_image)
        self.assertIsNone(serializer.data["thumbnail_url"])
