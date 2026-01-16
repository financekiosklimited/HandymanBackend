"""
Test cases for chat models.
"""

from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image as PILImage

from apps.accounts.models import User, UserRole
from apps.chat.models import ChatConversation, ChatMessage, ChatMessageAttachment
from apps.jobs.models import City, Job, JobCategory
from apps.profiles.models import HandymanProfile, HomeownerProfile


class ChatConversationModelTests(TestCase):
    """Test cases for ChatConversation model."""

    def setUp(self):
        """Set up test data."""
        # Create homeowner user
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
        )

        # Create handyman user
        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
        )

        # Create job
        self.category = JobCategory.objects.create(
            name="Plumbing",
            slug="plumbing",
            is_active=True,
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
            title="Fix kitchen sink",
            description="Need to fix a leaky kitchen sink",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
            assigned_handyman=self.handyman,
        )

    def test_create_job_conversation_success(self):
        """Test creating a job conversation."""
        conversation = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.JOB,
            job=self.job,
            homeowner=self.homeowner,
            handyman=self.handyman,
        )

        self.assertEqual(conversation.conversation_type, "job")
        self.assertEqual(conversation.job, self.job)
        self.assertEqual(conversation.homeowner, self.homeowner)
        self.assertEqual(conversation.handyman, self.handyman)
        self.assertEqual(conversation.status, ChatConversation.Status.ACTIVE)
        self.assertEqual(conversation.homeowner_unread_count, 0)
        self.assertEqual(conversation.handyman_unread_count, 0)
        self.assertIsNone(conversation.last_message_at)
        self.assertIsNotNone(conversation.public_id)

    def test_create_general_conversation_success(self):
        """Test creating a general conversation (without job)."""
        conversation = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.GENERAL,
            homeowner=self.homeowner,
            handyman=self.handyman,
        )

        self.assertEqual(conversation.conversation_type, "general")
        self.assertIsNone(conversation.job)
        self.assertEqual(conversation.homeowner, self.homeowner)
        self.assertEqual(conversation.handyman, self.handyman)

    def test_conversation_string_representation_job(self):
        """Test conversation string representation for job chat."""
        conversation = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.JOB,
            job=self.job,
            homeowner=self.homeowner,
            handyman=self.handyman,
        )
        self.assertIn("Fix kitchen sink", str(conversation))

    def test_conversation_string_representation_general(self):
        """Test conversation string representation for general chat."""
        conversation = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.GENERAL,
            homeowner=self.homeowner,
            handyman=self.handyman,
        )
        self.assertIn("homeowner@example.com", str(conversation))
        self.assertIn("handyman@example.com", str(conversation))

    def test_job_conversation_requires_job(self):
        """Test that job conversation requires job reference."""
        with self.assertRaises(ValidationError) as context:
            ChatConversation.objects.create(
                conversation_type=ChatConversation.ConversationType.JOB,
                homeowner=self.homeowner,
                handyman=self.handyman,
            )
        self.assertIn("job", str(context.exception))

    def test_general_conversation_rejects_job(self):
        """Test that general conversation should not have job reference."""
        with self.assertRaises(ValidationError) as context:
            ChatConversation.objects.create(
                conversation_type=ChatConversation.ConversationType.GENERAL,
                job=self.job,
                homeowner=self.homeowner,
                handyman=self.handyman,
            )
        self.assertIn("job", str(context.exception).lower())

    def test_unique_job_conversation(self):
        """Test that only one conversation can exist per job."""
        ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.JOB,
            job=self.job,
            homeowner=self.homeowner,
            handyman=self.handyman,
        )

        # full_clean() in save() catches constraint violation as ValidationError
        with self.assertRaises(ValidationError):
            ChatConversation.objects.create(
                conversation_type=ChatConversation.ConversationType.JOB,
                job=self.job,
                homeowner=self.homeowner,
                handyman=self.handyman,
            )

    def test_unique_general_conversation(self):
        """Test that only one general conversation exists per homeowner-handyman pair."""
        ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.GENERAL,
            homeowner=self.homeowner,
            handyman=self.handyman,
        )

        # full_clean() in save() catches constraint violation as ValidationError
        with self.assertRaises(ValidationError):
            ChatConversation.objects.create(
                conversation_type=ChatConversation.ConversationType.GENERAL,
                homeowner=self.homeowner,
                handyman=self.handyman,
            )

    def test_conversation_ordering(self):
        """Test conversations are ordered by last_message_at descending."""
        conv1 = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.JOB,
            job=self.job,
            homeowner=self.homeowner,
            handyman=self.handyman,
            last_message_at=timezone.now(),
        )

        # Create another job for second conversation
        job2 = Job.objects.create(
            homeowner=self.homeowner,
            title="Paint bedroom",
            description="Need to paint bedroom",
            estimated_budget=200,
            category=self.category,
            city=self.city,
            address="456 Oak St",
            status="in_progress",
            assigned_handyman=self.handyman,
        )

        conv2 = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.JOB,
            job=job2,
            homeowner=self.homeowner,
            handyman=self.handyman,
            last_message_at=timezone.now() + timezone.timedelta(hours=1),
        )

        conversations = list(ChatConversation.objects.all())
        self.assertEqual(conversations[0], conv2)  # More recent first
        self.assertEqual(conversations[1], conv1)


class ChatMessageModelTests(TestCase):
    """Test cases for ChatMessage model."""

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
            name="Plumbing",
            slug="plumbing",
            is_active=True,
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
            title="Fix kitchen sink",
            description="Need to fix a leaky kitchen sink",
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

    def test_create_text_message_success(self):
        """Test creating a text message."""
        message = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role=ChatMessage.SenderRole.HOMEOWNER,
            message_type=ChatMessage.MessageType.TEXT,
            content="Hello, when can you start?",
        )

        self.assertEqual(message.conversation, self.conversation)
        self.assertEqual(message.sender, self.homeowner)
        self.assertEqual(message.sender_role, "homeowner")
        self.assertEqual(message.message_type, "text")
        self.assertEqual(message.content, "Hello, when can you start?")
        self.assertFalse(message.is_read)
        self.assertIsNone(message.read_at)
        self.assertIsNotNone(message.public_id)

    def test_create_attachment_message_success(self):
        """Test creating an attachment message."""
        message = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.handyman,
            sender_role=ChatMessage.SenderRole.HANDYMAN,
            message_type=ChatMessage.MessageType.ATTACHMENT,
            content="",
        )

        self.assertEqual(message.message_type, "attachment")
        self.assertEqual(message.content, "")

    def test_message_string_representation_text(self):
        """Test message string representation for text."""
        message = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role=ChatMessage.SenderRole.HOMEOWNER,
            content="Hello world",
        )
        self.assertIn("homeowner", str(message))
        self.assertIn("Hello world", str(message))

    def test_message_string_representation_attachment(self):
        """Test message string representation for attachment."""
        message = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.handyman,
            sender_role=ChatMessage.SenderRole.HANDYMAN,
            message_type=ChatMessage.MessageType.ATTACHMENT,
            content="",
        )
        self.assertIn("handyman", str(message))
        self.assertIn("attachment", str(message))

    def test_message_content_max_length(self):
        """Test message content max length validation."""
        long_content = "a" * 2001

        with self.assertRaises(ValidationError) as context:
            ChatMessage.objects.create(
                conversation=self.conversation,
                sender=self.homeowner,
                sender_role=ChatMessage.SenderRole.HOMEOWNER,
                content=long_content,
            )
        self.assertIn("2000", str(context.exception))

    def test_message_ordering(self):
        """Test messages are ordered by created_at ascending."""
        msg1 = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role=ChatMessage.SenderRole.HOMEOWNER,
            content="First message",
        )
        msg2 = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.handyman,
            sender_role=ChatMessage.SenderRole.HANDYMAN,
            content="Second message",
        )

        messages = list(self.conversation.messages.all())
        self.assertEqual(messages[0], msg1)  # Oldest first
        self.assertEqual(messages[1], msg2)


class ChatMessageAttachmentModelTests(TestCase):
    """Test cases for ChatMessageAttachment model."""

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
            name="Plumbing",
            slug="plumbing",
            is_active=True,
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
            title="Fix kitchen sink",
            description="Need to fix a leaky kitchen sink",
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

    def _create_image_file(self, name="test.jpg"):
        image_io = BytesIO()
        pil_image = PILImage.new("RGB", (100, 100), color="red")
        pil_image.save(image_io, format="JPEG")
        image_io.seek(0)
        return SimpleUploadedFile(name, image_io.getvalue(), content_type="image/jpeg")

    def test_create_message_attachment_success(self):
        """Test creating a message attachment."""
        image_file = self._create_image_file()
        attachment = ChatMessageAttachment.objects.create(
            message=self.message,
            file=image_file,
            file_type="image",
            file_name=image_file.name,
            file_size=image_file.size,
            order=0,
        )

        self.assertEqual(attachment.message, self.message)
        self.assertEqual(attachment.order, 0)
        self.assertIsNotNone(attachment.public_id)

    def test_message_attachment_string_representation(self):
        """Test message attachment string representation."""
        image_file = self._create_image_file()
        attachment = ChatMessageAttachment.objects.create(
            message=self.message,
            file=image_file,
            file_type="image",
            file_name=image_file.name,
            file_size=image_file.size,
            order=0,
        )
        self.assertIn("Image 0 for message", str(attachment))

    def test_message_attachments_ordering(self):
        """Test message attachments are ordered by order field."""
        image_file1 = self._create_image_file(name="test1.jpg")
        image_file2 = self._create_image_file(name="test2.jpg")
        image_file3 = self._create_image_file(name="test3.jpg")
        att1 = ChatMessageAttachment.objects.create(
            message=self.message,
            file=image_file1,
            file_type="image",
            file_name=image_file1.name,
            file_size=image_file1.size,
            order=1,
        )
        att2 = ChatMessageAttachment.objects.create(
            message=self.message,
            file=image_file2,
            file_type="image",
            file_name=image_file2.name,
            file_size=image_file2.size,
            order=0,
        )
        att3 = ChatMessageAttachment.objects.create(
            message=self.message,
            file=image_file3,
            file_type="image",
            file_name=image_file3.name,
            file_size=image_file3.size,
            order=2,
        )

        attachments = list(self.message.attachments.all())
        self.assertEqual(attachments[0], att2)  # order 0
        self.assertEqual(attachments[1], att1)  # order 1
        self.assertEqual(attachments[2], att3)  # order 2
