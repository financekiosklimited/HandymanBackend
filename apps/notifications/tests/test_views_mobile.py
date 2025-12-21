"""Tests for notifications mobile views."""

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.notifications.models import Notification, UserDevice


class NotificationListViewTests(APITestCase):
    """Test cases for NotificationListView."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/handyman/notifications/"
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "phone_verified": True,
            "email_verified": True,
        }
        self.client.force_authenticate(user=self.user)

        # Create test notifications
        Notification.objects.create(
            user=self.user,
            notification_type="job_application_received",
            title="New Application",
            body="You have a new application",
            target_role="handyman",
            is_read=False,
        )
        Notification.objects.create(
            user=self.user,
            notification_type="application_approved",
            title="Application Approved",
            body="Your application was approved",
            target_role="handyman",
            is_read=True,
        )

    def test_list_notifications_success(self):
        """Test successfully listing notifications."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

    def test_list_notifications_filter_is_read_false(self):
        """Test filtering notifications by is_read=false."""
        response = self.client.get(self.url, {"is_read": "false"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertFalse(response.data["data"][0]["is_read"])

    def test_list_notifications_filter_is_read_true(self):
        """Test filtering notifications by is_read=true."""
        response = self.client.get(self.url, {"is_read": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertTrue(response.data["data"][0]["is_read"])

    def test_list_notifications_homeowner_path(self):
        """Test listing notifications via homeowner path."""
        url = "/api/v1/mobile/homeowner/notifications/"
        self.user.token_payload["active_role"] = "homeowner"
        self.user.token_payload["roles"] = ["homeowner"]
        self.client.force_authenticate(user=self.user)

        # Create homeowner notification
        Notification.objects.create(
            user=self.user,
            notification_type="job_application_received",
            title="Homeowner Notif",
            body="Test",
            target_role="homeowner",
        )
        # Create handyman notification (should be filtered out)
        Notification.objects.create(
            user=self.user,
            notification_type="application_approved",
            title="Handyman Notif",
            body="Test",
            target_role="handyman",
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Homeowner Notif")

    def test_list_notifications_pagination(self):
        """Test pagination works correctly."""
        # Create more notifications
        for i in range(25):
            Notification.objects.create(
                user=self.user,
                notification_type="job_application_received",
                title=f"Notification {i}",
                body="Test",
                target_role="handyman",
            )

        response = self.client.get(self.url, {"page_size": "10"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 10)
        self.assertIn("pagination", response.data["meta"])

    def test_get_role_from_path_none(self):
        """Test get_role_from_path returns None for unknown path."""
        from unittest.mock import MagicMock

        from apps.notifications.views.mobile import get_role_from_path

        request = MagicMock()
        request.path = "/api/v1/mobile/unknown/notifications/"
        self.assertIsNone(get_role_from_path(request))

    def test_list_notifications_no_role_in_path(self):
        """Test listing notifications when no role is in the path."""
        from rest_framework.test import APIRequestFactory, force_authenticate

        from apps.notifications.views.mobile import NotificationListView

        factory = APIRequestFactory()
        url = "/api/v1/mobile/notifications/"  # Neither handyman nor homeowner
        request = factory.get(url)
        request.user = self.user

        force_authenticate(request, user=self.user)

        view = NotificationListView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return all notifications for user regardless of target_role (2 from setUp)
        self.assertEqual(len(response.data["data"]), 2)

    def test_list_notifications_unauthenticated(self):
        """Test unauthenticated user cannot list notifications."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class NotificationMarkAsReadViewTests(APITestCase):
    """Test cases for NotificationMarkAsReadView."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "phone_verified": True,
            "email_verified": True,
        }
        self.client.force_authenticate(user=self.user)

        self.notification = Notification.objects.create(
            user=self.user,
            notification_type="job_application_received",
            title="Test",
            body="Test body",
            target_role="handyman",
            is_read=False,
        )
        self.url = (
            f"/api/v1/mobile/handyman/notifications/{self.notification.public_id}/read/"
        )

    def test_mark_as_read_success(self):
        """Test successfully marking notification as read."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
        self.assertIsNotNone(self.notification.read_at)

    def test_mark_as_read_not_found(self):
        """Test marking non-existent notification as read returns 404."""
        import uuid

        url = f"/api/v1/mobile/handyman/notifications/{uuid.uuid4()}/read/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class NotificationMarkAllAsReadViewTests(APITestCase):
    """Test cases for NotificationMarkAllAsReadView."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/handyman/notifications/read-all/"
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "phone_verified": True,
            "email_verified": True,
        }
        self.client.force_authenticate(user=self.user)

        # Create unread notifications
        for i in range(3):
            Notification.objects.create(
                user=self.user,
                notification_type="job_application_received",
                title=f"Test {i}",
                body="Test body",
                target_role="handyman",
                is_read=False,
            )

    def test_mark_all_as_read_success(self):
        """Test successfully marking all notifications as read."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        unread_count = Notification.objects.filter(
            user=self.user, is_read=False
        ).count()
        self.assertEqual(unread_count, 0)

    def test_mark_all_as_read_homeowner_success(self):
        """Test successfully marking all notifications as read via homeowner path."""
        url = "/api/v1/mobile/homeowner/notifications/read-all/"
        # Re-authenticate for homeowner
        self.user.token_payload["active_role"] = "homeowner"
        self.user.token_payload["roles"] = ["homeowner"]
        self.client.force_authenticate(user=self.user)

        # Create homeowner notification
        Notification.objects.create(
            user=self.user,
            notification_type="job_application_received",
            title="Test",
            body="Test",
            target_role="homeowner",
            is_read=False,
        )

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        unread_count = Notification.objects.filter(
            user=self.user, is_read=False, target_role="homeowner"
        ).count()
        self.assertEqual(unread_count, 0)


class NotificationUnreadCountViewTests(APITestCase):
    """Test cases for NotificationUnreadCountView."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/handyman/notifications/unread-count/"
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "phone_verified": True,
            "email_verified": True,
        }
        self.client.force_authenticate(user=self.user)

        # Create notifications
        for i in range(3):
            Notification.objects.create(
                user=self.user,
                notification_type="job_application_received",
                title=f"Test {i}",
                body="Test body",
                target_role="handyman",
                is_read=False,
            )
        Notification.objects.create(
            user=self.user,
            notification_type="application_approved",
            title="Read",
            body="Test body",
            target_role="handyman",
            is_read=True,
        )

    def test_get_unread_count_success(self):
        """Test successfully getting unread count."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["unread_count"], 3)


class DeviceRegisterViewTests(APITestCase):
    """Test cases for DeviceRegisterView."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/handyman/devices/"
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "phone_verified": True,
            "email_verified": True,
        }
        self.client.force_authenticate(user=self.user)

    def test_register_device_success(self):
        """Test successfully registering a device."""
        data = {
            "device_token": "test_token_123",
            "device_type": "ios",
        }

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("public_id", response.data["data"])
        self.assertEqual(response.data["data"]["device_type"], "ios")
        self.assertTrue(response.data["data"]["is_active"])

    def test_register_device_validation_error(self):
        """Test device registration with validation error."""
        data = {
            "device_token": "",  # Empty token
            "device_type": "ios",
        }

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DeviceUnregisterViewTests(APITestCase):
    """Test cases for DeviceUnregisterView."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "phone_verified": True,
            "email_verified": True,
        }
        self.client.force_authenticate(user=self.user)

        self.device = UserDevice.objects.create(
            user=self.user,
            device_token="test_token_123",
            device_type="ios",
        )
        self.url = f"/api/v1/mobile/handyman/devices/{self.device.public_id}/"

    def test_unregister_device_success(self):
        """Test successfully unregistering a device."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Device should still exist but be marked as inactive
        self.device.refresh_from_db()
        self.assertFalse(self.device.is_active)

    def test_unregister_device_not_found(self):
        """Test unregistering non-existent device returns 404."""
        import uuid

        url = f"/api/v1/mobile/handyman/devices/{uuid.uuid4()}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
