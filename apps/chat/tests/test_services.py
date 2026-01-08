"""
Test cases for chat services.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.chat.models import ChatConversation, ChatMessage
from apps.chat.services import (
    MAX_IMAGE_SIZE_BYTES,
    MAX_IMAGES_PER_MESSAGE,
    MAX_MESSAGE_LENGTH,
    ChatService,
    chat_service,
)
from apps.jobs.models import City, Job, JobCategory
from apps.profiles.models import HandymanProfile, HomeownerProfile


class ChatServiceGetOrCreateJobConversationTests(TestCase):
    """Test cases for ChatService.get_or_create_job_conversation."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
        )

        # Create handyman
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

    def test_create_conversation_success_as_homeowner(self):
        """Test creating a conversation as homeowner."""
        conversation, created = self.service.get_or_create_job_conversation(
            job=self.job,
            user=self.homeowner,
            user_role="homeowner",
        )

        self.assertTrue(created)
        self.assertEqual(conversation.job, self.job)
        self.assertEqual(conversation.homeowner, self.homeowner)
        self.assertEqual(conversation.handyman, self.handyman)
        self.assertEqual(conversation.conversation_type, "job")
        self.assertEqual(conversation.status, ChatConversation.Status.ACTIVE)

    def test_create_conversation_success_as_handyman(self):
        """Test creating a conversation as handyman."""
        conversation, created = self.service.get_or_create_job_conversation(
            job=self.job,
            user=self.handyman,
            user_role="handyman",
        )

        self.assertTrue(created)
        self.assertEqual(conversation.job, self.job)
        self.assertEqual(conversation.homeowner, self.homeowner)
        self.assertEqual(conversation.handyman, self.handyman)

    def test_get_existing_conversation(self):
        """Test getting an existing conversation."""
        # First create
        conversation1, created1 = self.service.get_or_create_job_conversation(
            job=self.job,
            user=self.homeowner,
            user_role="homeowner",
        )
        self.assertTrue(created1)

        # Second call should get the existing one
        conversation2, created2 = self.service.get_or_create_job_conversation(
            job=self.job,
            user=self.handyman,
            user_role="handyman",
        )
        self.assertFalse(created2)
        self.assertEqual(conversation1.id, conversation2.id)

    def test_job_not_in_progress_raises_error(self):
        """Test that job must be in_progress."""
        self.job.status = "open"
        self.job.save()

        with self.assertRaises(ValueError) as context:
            self.service.get_or_create_job_conversation(
                job=self.job,
                user=self.homeowner,
                user_role="homeowner",
            )
        self.assertIn("in progress", str(context.exception))

    def test_unauthorized_homeowner_raises_error(self):
        """Test that only job homeowner can access."""
        other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )

        with self.assertRaises(ValueError) as context:
            self.service.get_or_create_job_conversation(
                job=self.job,
                user=other_user,
                user_role="homeowner",
            )
        self.assertIn("not authorized", str(context.exception))

    def test_unauthorized_handyman_raises_error(self):
        """Test that only assigned handyman can access."""
        other_handyman = User.objects.create_user(
            email="other.handyman@example.com",
            password="testpass123",
        )

        with self.assertRaises(ValueError) as context:
            self.service.get_or_create_job_conversation(
                job=self.job,
                user=other_handyman,
                user_role="handyman",
            )
        self.assertIn("not authorized", str(context.exception))


class ChatServiceGetConversationByPublicIdTests(TestCase):
    """Test cases for ChatService.get_conversation_by_public_id."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

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

    def test_get_conversation_as_homeowner(self):
        """Test homeowner can get their conversation."""
        result = self.service.get_conversation_by_public_id(
            public_id=self.conversation.public_id,
            user=self.homeowner,
            user_role="homeowner",
        )
        self.assertEqual(result.id, self.conversation.id)

    def test_get_conversation_as_handyman(self):
        """Test handyman can get their conversation."""
        result = self.service.get_conversation_by_public_id(
            public_id=self.conversation.public_id,
            user=self.handyman,
            user_role="handyman",
        )
        self.assertEqual(result.id, self.conversation.id)

    def test_unauthorized_user_raises_error(self):
        """Test unauthorized user cannot get conversation."""
        other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )

        with self.assertRaises(ChatConversation.DoesNotExist):
            self.service.get_conversation_by_public_id(
                public_id=self.conversation.public_id,
                user=other_user,
                user_role="homeowner",
            )


class ChatServiceGetConversationsForUserTests(TestCase):
    """Test cases for ChatService.get_conversations_for_user."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

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
            last_message_at=timezone.now(),
        )

    def test_get_conversations_as_homeowner(self):
        """Test getting conversations as homeowner."""
        conversations = self.service.get_conversations_for_user(
            user=self.homeowner,
            user_role="homeowner",
        )
        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0].id, self.conversation.id)

    def test_get_conversations_as_handyman(self):
        """Test getting conversations as handyman."""
        conversations = self.service.get_conversations_for_user(
            user=self.handyman,
            user_role="handyman",
        )
        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0].id, self.conversation.id)

    def test_filter_by_conversation_type(self):
        """Test filtering by conversation type."""
        conversations = self.service.get_conversations_for_user(
            user=self.homeowner,
            user_role="homeowner",
            conversation_type="job",
        )
        self.assertEqual(len(conversations), 1)

        conversations = self.service.get_conversations_for_user(
            user=self.homeowner,
            user_role="homeowner",
            conversation_type="general",
        )
        self.assertEqual(len(conversations), 0)

    def test_no_conversations_returns_empty(self):
        """Test user with no conversations gets empty list."""
        other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )
        conversations = self.service.get_conversations_for_user(
            user=other_user,
            user_role="homeowner",
        )
        self.assertEqual(len(conversations), 0)


class ChatServiceSendMessageTests(TestCase):
    """Test cases for ChatService.send_message."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
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

    @patch("apps.chat.services.notification_service")
    def test_send_text_message_as_homeowner(self, mock_notification):
        """Test sending text message as homeowner."""
        message = self.service.send_message(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role="homeowner",
            content="Hello handyman!",
        )

        self.assertEqual(message.conversation, self.conversation)
        self.assertEqual(message.sender, self.homeowner)
        self.assertEqual(message.sender_role, "homeowner")
        self.assertEqual(message.content, "Hello handyman!")
        self.assertEqual(message.message_type, "text")
        self.assertFalse(message.is_read)

        # Check conversation metadata updated
        self.conversation.refresh_from_db()
        self.assertIsNotNone(self.conversation.last_message_at)
        self.assertEqual(self.conversation.handyman_unread_count, 1)
        self.assertEqual(self.conversation.homeowner_unread_count, 0)

        # Check notification sent
        mock_notification.create_and_send_notification.assert_called_once()

    @patch("apps.chat.services.notification_service")
    def test_send_text_message_as_handyman(self, mock_notification):
        """Test sending text message as handyman."""
        message = self.service.send_message(
            conversation=self.conversation,
            sender=self.handyman,
            sender_role="handyman",
            content="Hello homeowner!",
        )

        self.assertEqual(message.sender, self.handyman)
        self.assertEqual(message.sender_role, "handyman")

        # Check unread count for homeowner
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.homeowner_unread_count, 1)
        self.assertEqual(self.conversation.handyman_unread_count, 0)

    @patch("apps.chat.services.notification_service")
    def test_send_message_empty_content_raises_error(self, mock_notification):
        """Test sending message with no content raises error."""
        with self.assertRaises(ValueError) as context:
            self.service.send_message(
                conversation=self.conversation,
                sender=self.homeowner,
                sender_role="homeowner",
                content="",
            )
        self.assertIn("content or images", str(context.exception))

    @patch("apps.chat.services.notification_service")
    def test_send_message_content_too_long_raises_error(self, mock_notification):
        """Test sending message with content exceeding max length."""
        long_content = "a" * (MAX_MESSAGE_LENGTH + 1)

        with self.assertRaises(ValueError) as context:
            self.service.send_message(
                conversation=self.conversation,
                sender=self.homeowner,
                sender_role="homeowner",
                content=long_content,
            )
        self.assertIn(str(MAX_MESSAGE_LENGTH), str(context.exception))

    @patch("apps.chat.services.notification_service")
    def test_send_message_too_many_images_raises_error(self, mock_notification):
        """Test sending message with too many images."""
        # Create mock images
        mock_images = []
        for i in range(MAX_IMAGES_PER_MESSAGE + 1):
            mock_img = MagicMock()
            mock_img.size = 1024  # 1KB
            mock_img.name = f"image_{i}.jpg"
            mock_images.append(mock_img)

        with self.assertRaises(ValueError) as context:
            self.service.send_message(
                conversation=self.conversation,
                sender=self.homeowner,
                sender_role="homeowner",
                content="",
                images=mock_images,
            )
        self.assertIn(str(MAX_IMAGES_PER_MESSAGE), str(context.exception))

    @patch("apps.chat.services.notification_service")
    def test_send_message_image_too_large_raises_error(self, mock_notification):
        """Test sending message with image exceeding max size."""
        mock_img = MagicMock()
        mock_img.size = MAX_IMAGE_SIZE_BYTES + 1
        mock_img.name = "large_image.jpg"

        with self.assertRaises(ValueError) as context:
            self.service.send_message(
                conversation=self.conversation,
                sender=self.homeowner,
                sender_role="homeowner",
                content="",
                images=[mock_img],
            )
        self.assertIn("10MB", str(context.exception))

    @patch("apps.chat.services.notification_service")
    def test_send_message_archived_conversation_raises_error(self, mock_notification):
        """Test sending message to archived conversation fails."""
        self.conversation.status = ChatConversation.Status.ARCHIVED
        self.conversation.save()

        with self.assertRaises(ValueError) as context:
            self.service.send_message(
                conversation=self.conversation,
                sender=self.homeowner,
                sender_role="homeowner",
                content="Hello",
            )
        self.assertIn("archived", str(context.exception))

    @patch("apps.chat.services.notification_service")
    def test_send_message_job_not_in_progress_raises_error(self, mock_notification):
        """Test sending message when job is not in_progress."""
        self.job.status = "completed"
        self.job.save()

        with self.assertRaises(ValueError) as context:
            self.service.send_message(
                conversation=self.conversation,
                sender=self.homeowner,
                sender_role="homeowner",
                content="Hello",
            )
        self.assertIn("in progress", str(context.exception))


class ChatServiceMarkMessagesAsReadTests(TestCase):
    """Test cases for ChatService.mark_messages_as_read."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

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
            homeowner_unread_count=2,
            handyman_unread_count=3,
        )

        # Create messages from handyman (for homeowner to read)
        self.handyman_msg1 = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.handyman,
            sender_role=ChatMessage.SenderRole.HANDYMAN,
            content="Message 1",
            is_read=False,
        )
        self.handyman_msg2 = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.handyman,
            sender_role=ChatMessage.SenderRole.HANDYMAN,
            content="Message 2",
            is_read=False,
        )

        # Create messages from homeowner (for handyman to read)
        self.homeowner_msg = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role=ChatMessage.SenderRole.HOMEOWNER,
            content="Message from homeowner",
            is_read=False,
        )

    def test_homeowner_marks_handyman_messages_as_read(self):
        """Test homeowner marks handyman's messages as read."""
        count = self.service.mark_messages_as_read(
            conversation=self.conversation,
            user=self.homeowner,
            user_role="homeowner",
        )

        self.assertEqual(count, 2)

        # Check messages are marked read
        self.handyman_msg1.refresh_from_db()
        self.handyman_msg2.refresh_from_db()
        self.assertTrue(self.handyman_msg1.is_read)
        self.assertTrue(self.handyman_msg2.is_read)
        self.assertIsNotNone(self.handyman_msg1.read_at)

        # Homeowner's own message should not be marked
        self.homeowner_msg.refresh_from_db()
        self.assertFalse(self.homeowner_msg.is_read)

        # Unread count should be reset
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.homeowner_unread_count, 0)
        # Handyman's unread count should remain unchanged
        self.assertEqual(self.conversation.handyman_unread_count, 3)

    def test_handyman_marks_homeowner_messages_as_read(self):
        """Test handyman marks homeowner's messages as read."""
        count = self.service.mark_messages_as_read(
            conversation=self.conversation,
            user=self.handyman,
            user_role="handyman",
        )

        self.assertEqual(count, 1)

        # Check message is marked read
        self.homeowner_msg.refresh_from_db()
        self.assertTrue(self.homeowner_msg.is_read)

        # Handyman's messages should not be marked
        self.handyman_msg1.refresh_from_db()
        self.assertFalse(self.handyman_msg1.is_read)

        # Unread count should be reset
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.handyman_unread_count, 0)
        self.assertEqual(self.conversation.homeowner_unread_count, 2)


class ChatServiceGetTotalUnreadCountTests(TestCase):
    """Test cases for ChatService.get_total_unread_count."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        self.handyman2 = User.objects.create_user(
            email="handyman2@example.com",
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

        # Create multiple jobs and conversations
        self.job1 = Job.objects.create(
            homeowner=self.homeowner,
            title="Job 1",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
            assigned_handyman=self.handyman,
        )
        self.job2 = Job.objects.create(
            homeowner=self.homeowner,
            title="Job 2",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="456 Oak St",
            status="in_progress",
            assigned_handyman=self.handyman2,
        )

        self.conversation1 = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.JOB,
            job=self.job1,
            homeowner=self.homeowner,
            handyman=self.handyman,
            homeowner_unread_count=3,
            handyman_unread_count=1,
        )
        self.conversation2 = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.JOB,
            job=self.job2,
            homeowner=self.homeowner,
            handyman=self.handyman2,
            homeowner_unread_count=2,
            handyman_unread_count=5,
        )

    def test_get_total_unread_count_homeowner(self):
        """Test getting total unread count for homeowner."""
        count = self.service.get_total_unread_count(
            user=self.homeowner,
            user_role="homeowner",
        )
        self.assertEqual(count, 5)  # 3 + 2

    def test_get_total_unread_count_handyman(self):
        """Test getting total unread count for handyman."""
        count = self.service.get_total_unread_count(
            user=self.handyman,
            user_role="handyman",
        )
        self.assertEqual(count, 1)  # Only from conversation1

    def test_get_total_unread_count_with_type_filter(self):
        """Test getting total unread count filtered by type."""
        count = self.service.get_total_unread_count(
            user=self.homeowner,
            user_role="homeowner",
            conversation_type="job",
        )
        self.assertEqual(count, 5)

        count = self.service.get_total_unread_count(
            user=self.homeowner,
            user_role="homeowner",
            conversation_type="general",
        )
        self.assertEqual(count, 0)

    def test_get_total_unread_count_no_conversations(self):
        """Test getting total unread count when no conversations."""
        other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )
        count = self.service.get_total_unread_count(
            user=other_user,
            user_role="homeowner",
        )
        self.assertEqual(count, 0)


class ChatServiceArchiveConversationTests(TestCase):
    """Test cases for ChatService.archive_conversation."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

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

    def test_archive_conversation_success(self):
        """Test archiving an active conversation."""
        self.assertEqual(self.conversation.status, ChatConversation.Status.ACTIVE)

        result = self.service.archive_conversation(self.conversation)

        self.assertEqual(result.status, ChatConversation.Status.ARCHIVED)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.status, ChatConversation.Status.ARCHIVED)

    def test_archive_already_archived_conversation(self):
        """Test archiving an already archived conversation is idempotent."""
        self.conversation.status = ChatConversation.Status.ARCHIVED
        self.conversation.save()

        result = self.service.archive_conversation(self.conversation)
        self.assertEqual(result.status, ChatConversation.Status.ARCHIVED)


class ChatServiceGetJobForChatTests(TestCase):
    """Test cases for ChatService.get_job_for_chat."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

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

    def test_get_job_as_homeowner(self):
        """Test homeowner can get their job."""
        job = self.service.get_job_for_chat(
            job_public_id=self.job.public_id,
            user=self.homeowner,
            user_role="homeowner",
        )
        self.assertEqual(job.id, self.job.id)

    def test_get_job_as_handyman(self):
        """Test handyman can get assigned job."""
        job = self.service.get_job_for_chat(
            job_public_id=self.job.public_id,
            user=self.handyman,
            user_role="handyman",
        )
        self.assertEqual(job.id, self.job.id)

    def test_unauthorized_homeowner_raises_error(self):
        """Test unauthorized homeowner cannot get job."""
        other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )

        with self.assertRaises(Job.DoesNotExist):
            self.service.get_job_for_chat(
                job_public_id=self.job.public_id,
                user=other_user,
                user_role="homeowner",
            )

    def test_unauthorized_handyman_raises_error(self):
        """Test unassigned handyman cannot get job."""
        other_handyman = User.objects.create_user(
            email="other.handyman@example.com",
            password="testpass123",
        )

        with self.assertRaises(Job.DoesNotExist):
            self.service.get_job_for_chat(
                job_public_id=self.job.public_id,
                user=other_handyman,
                user_role="handyman",
            )


class ChatServiceGetMessagesForConversationTests(TestCase):
    """Test cases for ChatService.get_messages_for_conversation."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

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

        # Create messages
        self.msg1 = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role=ChatMessage.SenderRole.HOMEOWNER,
            content="First message",
        )
        self.msg2 = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.handyman,
            sender_role=ChatMessage.SenderRole.HANDYMAN,
            content="Second message",
        )
        self.msg3 = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role=ChatMessage.SenderRole.HOMEOWNER,
            content="Third message",
        )

    def test_get_messages_default(self):
        """Test getting messages with default parameters."""
        messages = list(
            self.service.get_messages_for_conversation(
                conversation=self.conversation,
            )
        )

        self.assertEqual(len(messages), 3)
        # Should be in chronological order
        self.assertEqual(messages[0].id, self.msg1.id)
        self.assertEqual(messages[1].id, self.msg2.id)
        self.assertEqual(messages[2].id, self.msg3.id)

    def test_get_messages_with_limit(self):
        """Test getting messages with limit."""
        messages = list(
            self.service.get_messages_for_conversation(
                conversation=self.conversation,
                limit=2,
            )
        )

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].id, self.msg1.id)
        self.assertEqual(messages[1].id, self.msg2.id)

    def test_get_messages_with_before(self):
        """Test getting messages before a specific message."""
        messages = list(
            self.service.get_messages_for_conversation(
                conversation=self.conversation,
                before=self.msg3.public_id,
            )
        )

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].id, self.msg1.id)
        self.assertEqual(messages[1].id, self.msg2.id)

    def test_get_messages_with_invalid_before(self):
        """Test getting messages with invalid before ID ignores the filter."""
        import uuid

        messages = list(
            self.service.get_messages_for_conversation(
                conversation=self.conversation,
                before=uuid.uuid4(),  # Non-existent ID
            )
        )

        # Should return all messages when before message doesn't exist
        self.assertEqual(len(messages), 3)


class ChatServiceSingletonTests(TestCase):
    """Test that chat_service is a singleton instance."""

    def test_chat_service_is_instance(self):
        """Test that chat_service is a ChatService instance."""
        self.assertIsInstance(chat_service, ChatService)


class ChatServiceGetUserForGeneralChatTests(TestCase):
    """Test cases for ChatService.get_user_for_general_chat."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")

        # Create handyman
        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman, role="handyman")

        # Create user with both roles
        self.dual_role_user = User.objects.create_user(
            email="dualrole@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.dual_role_user, role="homeowner")
        UserRole.objects.create(user=self.dual_role_user, role="handyman")

    def test_homeowner_can_get_handyman(self):
        """Test homeowner can get a user with handyman role."""
        result = self.service.get_user_for_general_chat(
            user_public_id=self.handyman.public_id,
            user_role="homeowner",
        )
        self.assertEqual(result.id, self.handyman.id)

    def test_handyman_can_get_homeowner(self):
        """Test handyman can get a user with homeowner role."""
        result = self.service.get_user_for_general_chat(
            user_public_id=self.homeowner.public_id,
            user_role="handyman",
        )
        self.assertEqual(result.id, self.homeowner.id)

    def test_homeowner_cannot_get_homeowner(self):
        """Test homeowner cannot get a user with only homeowner role."""
        with self.assertRaises(User.DoesNotExist):
            self.service.get_user_for_general_chat(
                user_public_id=self.homeowner.public_id,
                user_role="homeowner",
            )

    def test_handyman_cannot_get_handyman(self):
        """Test handyman cannot get a user with only handyman role."""
        with self.assertRaises(User.DoesNotExist):
            self.service.get_user_for_general_chat(
                user_public_id=self.handyman.public_id,
                user_role="handyman",
            )

    def test_get_user_with_dual_role_as_homeowner(self):
        """Test homeowner can get user with dual roles (has handyman role)."""
        result = self.service.get_user_for_general_chat(
            user_public_id=self.dual_role_user.public_id,
            user_role="homeowner",
        )
        self.assertEqual(result.id, self.dual_role_user.id)

    def test_get_user_with_dual_role_as_handyman(self):
        """Test handyman can get user with dual roles (has homeowner role)."""
        result = self.service.get_user_for_general_chat(
            user_public_id=self.dual_role_user.public_id,
            user_role="handyman",
        )
        self.assertEqual(result.id, self.dual_role_user.id)

    def test_user_not_found(self):
        """Test getting non-existent user raises error."""
        import uuid

        with self.assertRaises(User.DoesNotExist):
            self.service.get_user_for_general_chat(
                user_public_id=uuid.uuid4(),
                user_role="homeowner",
            )


class ChatServiceGetOrCreateGeneralConversationTests(TestCase):
    """Test cases for ChatService.get_or_create_general_conversation."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")

        # Create handyman
        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman, role="handyman")

    def test_create_conversation_as_homeowner(self):
        """Test homeowner creates general conversation with handyman."""
        conversation, created = self.service.get_or_create_general_conversation(
            user=self.homeowner,
            user_role="homeowner",
            target_user=self.handyman,
        )

        self.assertTrue(created)
        self.assertEqual(conversation.conversation_type, "general")
        self.assertEqual(conversation.homeowner, self.homeowner)
        self.assertEqual(conversation.handyman, self.handyman)
        self.assertIsNone(conversation.job)
        self.assertEqual(conversation.status, ChatConversation.Status.ACTIVE)

    def test_create_conversation_as_handyman(self):
        """Test handyman creates general conversation with homeowner."""
        conversation, created = self.service.get_or_create_general_conversation(
            user=self.handyman,
            user_role="handyman",
            target_user=self.homeowner,
        )

        self.assertTrue(created)
        self.assertEqual(conversation.conversation_type, "general")
        self.assertEqual(conversation.homeowner, self.homeowner)
        self.assertEqual(conversation.handyman, self.handyman)
        self.assertIsNone(conversation.job)

    def test_get_existing_conversation_as_homeowner(self):
        """Test homeowner gets existing conversation."""
        # Create first
        conversation1, _ = self.service.get_or_create_general_conversation(
            user=self.homeowner,
            user_role="homeowner",
            target_user=self.handyman,
        )

        # Get existing
        conversation2, created = self.service.get_or_create_general_conversation(
            user=self.homeowner,
            user_role="homeowner",
            target_user=self.handyman,
        )

        self.assertFalse(created)
        self.assertEqual(conversation1.id, conversation2.id)

    def test_get_existing_conversation_as_handyman(self):
        """Test handyman gets existing conversation created by homeowner."""
        # Create as homeowner
        conversation1, _ = self.service.get_or_create_general_conversation(
            user=self.homeowner,
            user_role="homeowner",
            target_user=self.handyman,
        )

        # Get as handyman
        conversation2, created = self.service.get_or_create_general_conversation(
            user=self.handyman,
            user_role="handyman",
            target_user=self.homeowner,
        )

        self.assertFalse(created)
        self.assertEqual(conversation1.id, conversation2.id)

    def test_multiple_handymen_separate_conversations(self):
        """Test homeowner can have separate conversations with different handymen."""
        handyman2 = User.objects.create_user(
            email="handyman2@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=handyman2, role="handyman")

        conv1, _ = self.service.get_or_create_general_conversation(
            user=self.homeowner,
            user_role="homeowner",
            target_user=self.handyman,
        )
        conv2, _ = self.service.get_or_create_general_conversation(
            user=self.homeowner,
            user_role="homeowner",
            target_user=handyman2,
        )

        self.assertNotEqual(conv1.id, conv2.id)
        self.assertEqual(conv1.handyman, self.handyman)
        self.assertEqual(conv2.handyman, handyman2)


class ChatServiceGetJobChatUnreadCountTests(TestCase):
    """Test cases for ChatService.get_job_chat_unread_count."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

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

    def test_get_unread_count_for_homeowner(self):
        """Test getting unread count for homeowner."""
        ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.JOB,
            job=self.job,
            homeowner=self.homeowner,
            handyman=self.handyman,
            homeowner_unread_count=5,
            handyman_unread_count=3,
        )

        count = self.service.get_job_chat_unread_count(
            job=self.job,
            user=self.homeowner,
            user_role="homeowner",
        )
        self.assertEqual(count, 5)

    def test_get_unread_count_for_handyman(self):
        """Test getting unread count for handyman."""
        ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.JOB,
            job=self.job,
            homeowner=self.homeowner,
            handyman=self.handyman,
            homeowner_unread_count=5,
            handyman_unread_count=3,
        )

        count = self.service.get_job_chat_unread_count(
            job=self.job,
            user=self.handyman,
            user_role="handyman",
        )
        self.assertEqual(count, 3)

    def test_no_conversation_returns_zero(self):
        """Test returns 0 when no conversation exists."""
        count = self.service.get_job_chat_unread_count(
            job=self.job,
            user=self.homeowner,
            user_role="homeowner",
        )
        self.assertEqual(count, 0)


class ChatServiceSendMessageWithImagesTests(TestCase):
    """Test cases for ChatService.send_message with images."""

    def setUp(self):
        """Set up test data."""

        self.service = ChatService()

        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
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

    def _create_test_image(self, name="test.jpg"):
        """Create a test image file."""
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)
        return SimpleUploadedFile(
            name=name,
            content=buffer.read(),
            content_type="image/jpeg",
        )

    @patch("apps.chat.services.notification_service")
    def test_send_image_only_message(self, mock_notification):
        """Test sending image-only message sets message_type to image."""
        image = self._create_test_image()

        message = self.service.send_message(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role="homeowner",
            content="",
            images=[image],
        )

        self.assertEqual(message.message_type, "image")
        self.assertEqual(message.images.count(), 1)

    @patch("apps.chat.services.notification_service")
    def test_send_text_with_image_message(self, mock_notification):
        """Test sending message with text and images sets message_type to text_with_image."""
        image = self._create_test_image()

        message = self.service.send_message(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role="homeowner",
            content="Check out this image!",
            images=[image],
        )

        self.assertEqual(message.message_type, "text_with_image")
        self.assertEqual(message.content, "Check out this image!")
        self.assertEqual(message.images.count(), 1)

    @patch("apps.chat.services.notification_service")
    def test_send_multiple_images(self, mock_notification):
        """Test sending message with multiple images."""
        images = [
            self._create_test_image("image1.jpg"),
            self._create_test_image("image2.jpg"),
            self._create_test_image("image3.jpg"),
        ]

        message = self.service.send_message(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role="homeowner",
            content="",
            images=images,
        )

        self.assertEqual(message.images.count(), 3)
        # Verify order is preserved
        orders = list(message.images.values_list("order", flat=True))
        self.assertEqual(orders, [0, 1, 2])

    @patch("apps.chat.services.notification_service")
    def test_image_notification_body_for_image_only_message(self, mock_notification):
        """Test notification body is 'Sent an image' for image-only messages."""
        image = self._create_test_image()

        self.service.send_message(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role="homeowner",
            content="",
            images=[image],
        )

        # Check notification was sent with "Sent an image" body
        call_args = mock_notification.create_and_send_notification.call_args
        self.assertEqual(call_args.kwargs["body"], "Sent an image")

    @patch("apps.chat.services.notification_service")
    def test_notification_includes_job_id(self, mock_notification):
        """Test notification data includes job_id for job conversations."""
        self.service.send_message(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role="homeowner",
            content="Test message",
        )

        call_args = mock_notification.create_and_send_notification.call_args
        self.assertIn("job_id", call_args.kwargs["data"])
        self.assertEqual(call_args.kwargs["data"]["job_id"], str(self.job.public_id))


class ChatServiceNotificationFailureTests(TestCase):
    """Test cases for notification failure handling."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
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

    @patch("apps.chat.services.notification_service")
    def test_notification_failure_does_not_fail_send_message(self, mock_notification):
        """Test that notification failure doesn't prevent message from being sent."""
        mock_notification.create_and_send_notification.side_effect = Exception(
            "Notification failed"
        )

        # Should not raise an exception
        message = self.service.send_message(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role="homeowner",
            content="Test message",
        )

        # Message should still be created
        self.assertIsNotNone(message)
        self.assertEqual(message.content, "Test message")


class ChatServiceDisplayNameFallbackTests(TestCase):
    """Test cases for display name fallback logic."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

        # Create users WITHOUT profiles
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

    @patch("apps.chat.services.notification_service")
    def test_display_name_fallback_to_email_prefix(self, mock_notification):
        """Test display name falls back to email prefix when no profile."""
        self.service.send_message(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role="homeowner",
            content="Test message",
        )

        # Check notification was sent with email prefix in title
        call_args = mock_notification.create_and_send_notification.call_args
        self.assertIn("homeowner", call_args.kwargs["title"])

    @patch("apps.chat.services.notification_service")
    def test_display_name_fallback_when_profile_has_no_display_name(
        self, mock_notification
    ):
        """Test display name falls back when profile exists but has empty display_name."""
        # Create profile with empty display_name
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="",
        )

        self.service.send_message(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role="homeowner",
            content="Test message",
        )

        # Check notification was sent with email prefix in title
        call_args = mock_notification.create_and_send_notification.call_args
        self.assertIn("homeowner", call_args.kwargs["title"])


class ChatServiceSendMessageInGeneralConversationTests(TestCase):
    """Test cases for sending messages in general conversations."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
        )
        # General conversation (no job)
        self.conversation = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.GENERAL,
            homeowner=self.homeowner,
            handyman=self.handyman,
        )

    @patch("apps.chat.services.notification_service")
    def test_send_message_in_general_conversation(self, mock_notification):
        """Test sending message in general conversation (no job check)."""
        message = self.service.send_message(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role="homeowner",
            content="Hello!",
        )

        self.assertEqual(message.content, "Hello!")
        self.assertEqual(message.conversation, self.conversation)

    @patch("apps.chat.services.notification_service")
    def test_general_conversation_notification_has_no_job_id(self, mock_notification):
        """Test notification for general conversation doesn't include job_id."""
        self.service.send_message(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role="homeowner",
            content="Hello!",
        )

        call_args = mock_notification.create_and_send_notification.call_args
        self.assertNotIn("job_id", call_args.kwargs["data"])


class ChatServiceSaveMessageImageTests(TestCase):
    """Test cases for _save_message_image method edge cases."""

    def setUp(self):
        """Set up test data."""
        self.service = ChatService()

        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
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

    def _create_png_with_transparency(self, name="test.png"):
        """Create a PNG test image with transparency (RGBA mode)."""
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return SimpleUploadedFile(
            name=name,
            content=buffer.read(),
            content_type="image/png",
        )

    def _create_p_mode_image(self, name="test.gif"):
        """Create an image with P mode (palette-based)."""
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        img = Image.new("P", (100, 100))
        buffer = BytesIO()
        img.save(buffer, format="GIF")
        buffer.seek(0)
        return SimpleUploadedFile(
            name=name,
            content=buffer.read(),
            content_type="image/gif",
        )

    @patch("apps.chat.services.notification_service")
    def test_send_rgba_png_image(self, mock_notification):
        """Test sending PNG image with transparency is converted to RGB."""
        image = self._create_png_with_transparency()

        message = self.service.send_message(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role="homeowner",
            content="",
            images=[image],
        )

        self.assertEqual(message.images.count(), 1)
        # Thumbnail should be created as JPEG
        chat_image = message.images.first()
        self.assertTrue(chat_image.thumbnail.name.endswith(".jpg"))

    @patch("apps.chat.services.notification_service")
    def test_send_palette_mode_image(self, mock_notification):
        """Test sending P mode (palette) image is converted to RGB."""
        image = self._create_p_mode_image()

        message = self.service.send_message(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role="homeowner",
            content="",
            images=[image],
        )

        self.assertEqual(message.images.count(), 1)
        # Thumbnail should be created as JPEG
        chat_image = message.images.first()
        self.assertTrue(chat_image.thumbnail.name.endswith(".jpg"))

    @patch("apps.chat.services.notification_service")
    @patch("PIL.Image.open")
    def test_thumbnail_generation_failure(self, mock_image_open, mock_notification):
        """Test that thumbnail generation failure doesn't prevent message saving."""
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        # Create a valid test image
        img = Image.new("RGB", (100, 100), color="red")
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)
        image = SimpleUploadedFile(
            name="test.jpg",
            content=buffer.read(),
            content_type="image/jpeg",
        )

        # Make Image.open raise an exception
        mock_image_open.side_effect = Exception("Failed to open image")

        message = self.service.send_message(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role="homeowner",
            content="",
            images=[image],
        )

        # Message should still be created
        self.assertIsNotNone(message)
        self.assertEqual(message.images.count(), 1)
        # Thumbnail should not exist
        chat_image = message.images.first()
        self.assertFalse(bool(chat_image.thumbnail))
