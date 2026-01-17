"""
Test cases for handyman chat views.
"""

from decimal import Decimal
from unittest.mock import patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.chat.models import ChatConversation, ChatMessage
from apps.jobs.models import City, Job, JobCategory
from apps.profiles.models import HandymanProfile, HomeownerProfile


class HandymanConversationListViewTests(APITestCase):
    """Test cases for HandymanConversationListView."""

    def setUp(self):
        """Set up test data."""
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
        self.handyman.email_verified_at = "2024-01-01T00:00:00Z"
        self.handyman.save()
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Create job and job conversation
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
            title="Fix kitchen sink",
            description="Need to fix a leaky kitchen sink",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
            assigned_handyman=self.handyman,
        )
        self.job_conversation = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.JOB,
            job=self.job,
            homeowner=self.homeowner,
            handyman=self.handyman,
        )

        # Create general conversation with a message (so it appears in list)
        self.general_conversation = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.GENERAL,
            homeowner=self.homeowner,
            handyman=self.handyman,
            last_message_at=timezone.now(),
        )

        self.url = "/api/v1/mobile/handyman/conversations/"

    def test_list_conversations_returns_only_general(self):
        """Test listing conversations returns only general chat."""
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Conversations retrieved successfully"
        )
        # Should only return general conversation, not job conversation
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(
            str(response.data["data"][0]["public_id"]),
            str(self.general_conversation.public_id),
        )
        self.assertEqual(response.data["data"][0]["conversation_type"], "general")

    def test_list_conversations_empty_when_no_general_chat(self):
        """Test listing conversations returns empty when no general chat exists."""
        # Delete general conversation
        self.general_conversation.delete()

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 0)

    def test_list_conversations_unauthenticated(self):
        """Test listing conversations without authentication fails."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_conversations_wrong_platform(self):
        """Test listing conversations from wrong platform fails."""
        self.handyman.token_payload["plat"] = "web"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_conversations_wrong_role(self):
        """Test listing conversations with wrong role fails."""
        self.handyman.token_payload["active_role"] = "homeowner"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class HandymanUnreadCountViewTests(APITestCase):
    """Test cases for HandymanUnreadCountView."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")

        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        self.handyman.email_verified_at = "2024-01-01T00:00:00Z"
        self.handyman.save()
        UserRole.objects.create(user=self.handyman, role="handyman")
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

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
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
            assigned_handyman=self.handyman,
        )

        # Create job conversation with unread count
        self.job_conversation = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.JOB,
            job=self.job,
            homeowner=self.homeowner,
            handyman=self.handyman,
            handyman_unread_count=5,
        )

        # Create general conversation with unread count
        self.general_conversation = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.GENERAL,
            homeowner=self.homeowner,
            handyman=self.handyman,
            handyman_unread_count=3,
        )

        self.url = "/api/v1/mobile/handyman/conversations/unread-count/"

    def test_get_unread_count_returns_only_general(self):
        """Test getting unread count returns only general chat count."""
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Unread count retrieved successfully"
        )
        # Should only count general conversation (3), not job conversation (5)
        self.assertEqual(response.data["data"]["unread_count"], 3)

    def test_get_unread_count_zero_when_no_general_chat(self):
        """Test unread count is 0 when no general chat exists."""
        # Delete general conversation
        self.general_conversation.delete()

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["unread_count"], 0)

    def test_get_unread_count_unauthenticated(self):
        """Test getting unread count without authentication fails."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class HandymanJobChatViewTests(APITestCase):
    """Test cases for HandymanJobChatView."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
        )

        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        self.handyman.email_verified_at = "2024-01-01T00:00:00Z"
        self.handyman.save()
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

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
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
            assigned_handyman=self.handyman,
        )

    def test_get_or_create_job_chat_creates_new(self):
        """Test creating a new job chat conversation."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/chat/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Conversation created successfully")
        self.assertIn("public_id", response.data["data"])
        self.assertEqual(response.data["data"]["conversation_type"], "job")

        # Verify conversation was created
        self.assertTrue(ChatConversation.objects.filter(job=self.job).exists())

    def test_get_or_create_job_chat_gets_existing(self):
        """Test getting existing job chat conversation."""
        # Create conversation first
        conversation = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.JOB,
            job=self.job,
            homeowner=self.homeowner,
            handyman=self.handyman,
        )

        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/chat/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Conversation retrieved successfully"
        )
        self.assertEqual(
            str(response.data["data"]["public_id"]),
            str(conversation.public_id),
        )

    def test_get_job_chat_not_found(self):
        """Test getting chat for non-existent job."""
        url = "/api/v1/mobile/handyman/jobs/00000000-0000-0000-0000-000000000000/chat/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_job_chat_not_assigned(self):
        """Test getting chat for job not assigned to handyman."""
        other_handyman = User.objects.create_user(
            email="other.handyman@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=other_handyman, role="handyman")
        other_job = Job.objects.create(
            homeowner=self.homeowner,
            title="Other Job",
            description="Test",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="456 Oak St",
            status="in_progress",
            assigned_handyman=other_handyman,
        )

        url = f"/api/v1/mobile/handyman/jobs/{other_job.public_id}/chat/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_job_chat_job_not_in_progress(self):
        """Test getting chat for job not in progress."""
        self.job.status = "open"
        self.job.save()

        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/chat/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_job_chat_unauthenticated(self):
        """Test getting chat without authentication fails."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/chat/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class HandymanConversationMessagesViewTests(APITestCase):
    """Test cases for HandymanConversationMessagesView."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
        )

        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        self.handyman.email_verified_at = "2024-01-01T00:00:00Z"
        self.handyman.save()
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

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
            estimated_budget=Decimal("100.00"),
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

        # Create some messages
        self.message1 = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role=ChatMessage.SenderRole.HOMEOWNER,
            content="Hello handyman!",
        )
        self.message2 = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.handyman,
            sender_role=ChatMessage.SenderRole.HANDYMAN,
            content="Hello homeowner!",
        )

        self.list_url = f"/api/v1/mobile/handyman/conversations/{self.conversation.public_id}/messages/"

    def test_list_messages_success(self):
        """Test listing messages successfully."""
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Messages retrieved successfully")
        self.assertEqual(len(response.data["data"]), 2)
        self.assertIn("has_more", response.data["meta"])

    def test_list_messages_with_limit(self):
        """Test listing messages with limit parameter."""
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(f"{self.list_url}?limit=1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertTrue(response.data["meta"]["has_more"])

    def test_list_messages_with_before_id(self):
        """Test listing messages with before_id parameter."""
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(
            f"{self.list_url}?before_id={self.message2.public_id}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(
            str(response.data["data"][0]["public_id"]),
            str(self.message1.public_id),
        )

    def test_list_messages_conversation_not_found(self):
        """Test listing messages for non-existent conversation."""
        url = "/api/v1/mobile/handyman/conversations/00000000-0000-0000-0000-000000000000/messages/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_messages_unauthenticated(self):
        """Test listing messages without authentication fails."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("apps.chat.services.notification_service")
    def test_send_message_success(self, mock_notification):
        """Test sending a message successfully."""
        self.client.force_authenticate(user=self.handyman)
        data = {"content": "Test message from handyman"}
        response = self.client.post(self.list_url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Message sent successfully")
        self.assertEqual(response.data["data"]["content"], "Test message from handyman")
        self.assertEqual(response.data["data"]["sender_role"], "handyman")

    @patch("apps.chat.services.notification_service")
    def test_send_message_empty_content_fails(self, mock_notification):
        """Test sending message with empty content fails."""
        self.client.force_authenticate(user=self.handyman)
        data = {"content": ""}
        response = self.client.post(self.list_url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.chat.services.notification_service")
    def test_send_message_content_too_long_fails(self, mock_notification):
        """Test sending message with content exceeding max length."""
        self.client.force_authenticate(user=self.handyman)
        data = {"content": "a" * 2001}
        response = self.client.post(self.list_url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_message_conversation_not_found(self):
        """Test sending message to non-existent conversation."""
        url = "/api/v1/mobile/handyman/conversations/00000000-0000-0000-0000-000000000000/messages/"
        self.client.force_authenticate(user=self.handyman)
        data = {"content": "Test"}
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_send_message_unauthenticated(self):
        """Test sending message without authentication fails."""
        data = {"content": "Test"}
        response = self.client.post(self.list_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("apps.chat.services.notification_service")
    def test_send_message_archived_conversation_fails(self, mock_notification):
        """Test sending message to archived conversation fails."""
        self.conversation.status = ChatConversation.Status.ARCHIVED
        self.conversation.save()

        self.client.force_authenticate(user=self.handyman)
        data = {"content": "Test message"}
        response = self.client.post(self.list_url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class HandymanConversationReadViewTests(APITestCase):
    """Test cases for HandymanConversationReadView."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")

        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        self.handyman.email_verified_at = "2024-01-01T00:00:00Z"
        self.handyman.save()
        UserRole.objects.create(user=self.handyman, role="handyman")
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

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
            estimated_budget=Decimal("100.00"),
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
            handyman_unread_count=2,
        )

        # Create unread messages from homeowner
        self.message1 = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role=ChatMessage.SenderRole.HOMEOWNER,
            content="Message 1",
            is_read=False,
        )
        self.message2 = ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.homeowner,
            sender_role=ChatMessage.SenderRole.HOMEOWNER,
            content="Message 2",
            is_read=False,
        )

        self.url = (
            f"/api/v1/mobile/handyman/conversations/{self.conversation.public_id}/read/"
        )

    def test_mark_as_read_success(self):
        """Test marking messages as read successfully."""
        self.client.force_authenticate(user=self.handyman)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Messages marked as read")
        self.assertEqual(response.data["data"]["messages_read"], 2)

        # Verify messages are marked as read
        self.message1.refresh_from_db()
        self.message2.refresh_from_db()
        self.assertTrue(self.message1.is_read)
        self.assertTrue(self.message2.is_read)

        # Verify unread count is reset
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.handyman_unread_count, 0)

    def test_mark_as_read_conversation_not_found(self):
        """Test marking messages as read for non-existent conversation."""
        url = "/api/v1/mobile/handyman/conversations/00000000-0000-0000-0000-000000000000/read/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_as_read_unauthenticated(self):
        """Test marking messages as read without authentication fails."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_mark_as_read_not_own_conversation(self):
        """Test marking messages as read for conversation not owned fails."""
        other_handyman = User.objects.create_user(
            email="other.handyman@example.com",
            password="testpass123",
        )
        other_handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

        self.client.force_authenticate(user=other_handyman)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class HandymanGeneralChatViewTests(APITestCase):
    """Test cases for HandymanGeneralChatView."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
        )

        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        self.handyman.email_verified_at = "2024-01-01T00:00:00Z"
        self.handyman.save()
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

    def test_create_general_chat_success(self):
        """Test creating a new general chat conversation."""
        url = f"/api/v1/mobile/handyman/users/{self.homeowner.public_id}/chat/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Conversation created successfully")
        self.assertIn("public_id", response.data["data"])
        self.assertEqual(response.data["data"]["conversation_type"], "general")
        self.assertIsNone(response.data["data"]["job"])

        # Verify conversation was created
        self.assertTrue(
            ChatConversation.objects.filter(
                conversation_type="general",
                homeowner=self.homeowner,
                handyman=self.handyman,
            ).exists()
        )

    def test_get_existing_general_chat(self):
        """Test getting existing general chat conversation."""
        # Create conversation first
        conversation = ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.GENERAL,
            homeowner=self.homeowner,
            handyman=self.handyman,
        )

        url = f"/api/v1/mobile/handyman/users/{self.homeowner.public_id}/chat/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Conversation retrieved successfully"
        )
        self.assertEqual(
            str(response.data["data"]["public_id"]),
            str(conversation.public_id),
        )

    def test_general_chat_user_not_found(self):
        """Test creating chat with non-existent user."""
        url = "/api/v1/mobile/handyman/users/00000000-0000-0000-0000-000000000000/chat/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_general_chat_user_not_homeowner(self):
        """Test creating chat with user who is not a homeowner."""
        # Create another handyman (not a homeowner)
        other_handyman = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=other_handyman, role="handyman")

        url = f"/api/v1/mobile/handyman/users/{other_handyman.public_id}/chat/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_general_chat_unauthenticated(self):
        """Test creating chat without authentication fails."""
        url = f"/api/v1/mobile/handyman/users/{self.homeowner.public_id}/chat/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class HandymanJobChatUnreadCountViewTests(APITestCase):
    """Test cases for HandymanJobChatUnreadCountView."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")

        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        self.handyman.email_verified_at = "2024-01-01T00:00:00Z"
        self.handyman.save()
        UserRole.objects.create(user=self.handyman, role="handyman")
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

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
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
            assigned_handyman=self.handyman,
        )

    def test_get_job_unread_count_success(self):
        """Test getting unread count for job with conversation."""
        ChatConversation.objects.create(
            conversation_type=ChatConversation.ConversationType.JOB,
            job=self.job,
            homeowner=self.homeowner,
            handyman=self.handyman,
            handyman_unread_count=7,
        )

        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/chat/unread-count/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Unread count retrieved successfully"
        )
        self.assertEqual(response.data["data"]["unread_count"], 7)

    def test_get_job_unread_count_no_conversation(self):
        """Test getting unread count for job without conversation returns 0."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/chat/unread-count/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["unread_count"], 0)

    def test_get_job_unread_count_job_not_found(self):
        """Test getting unread count for non-existent job."""
        url = "/api/v1/mobile/handyman/jobs/00000000-0000-0000-0000-000000000000/chat/unread-count/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_job_unread_count_not_assigned(self):
        """Test getting unread count for job not assigned to handyman."""
        other_handyman = User.objects.create_user(
            email="other.handyman@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=other_handyman, role="handyman")
        other_job = Job.objects.create(
            homeowner=self.homeowner,
            title="Other Job",
            description="Test",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="456 Oak St",
            status="in_progress",
            assigned_handyman=other_handyman,
        )

        url = f"/api/v1/mobile/handyman/jobs/{other_job.public_id}/chat/unread-count/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_job_unread_count_unauthenticated(self):
        """Test getting unread count without authentication fails."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/chat/unread-count/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
