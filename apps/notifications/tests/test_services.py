"""Tests for notification services."""

from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import User
from apps.notifications.models import BroadcastNotification, Notification, UserDevice
from apps.notifications.services import NotificationService


class NotificationServiceTests(TestCase):
    """Test cases for NotificationService."""

    def setUp(self):
        self.service = NotificationService()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="password123",
            first_name="Test",
            last_name="User",
        )

    def test_get_target_users_handyman(self):
        """Test get_target_users for handyman audience."""
        from apps.accounts.models import UserRole

        UserRole.objects.create(user=self.user, role="handyman")
        users = self.service.get_target_users("handyman")
        self.assertEqual(users.count(), 1)
        self.assertEqual(users.first(), self.user)

    def test_get_target_users_homeowner(self):
        """Test get_target_users for homeowner audience."""
        from apps.accounts.models import UserRole

        UserRole.objects.create(user=self.user, role="homeowner")
        users = self.service.get_target_users("homeowner")
        self.assertEqual(users.count(), 1)
        self.assertEqual(users.first(), self.user)

    def test_get_target_users_specific(self):
        """Test get_target_users for specific audience."""
        broadcast = BroadcastNotification.objects.create(
            title="T", body="B", target_audience="specific"
        )
        broadcast.target_users.add(self.user)
        users = self.service.get_target_users("specific", broadcast)
        self.assertEqual(users.count(), 1)
        self.assertEqual(users.first(), self.user)

    def test_get_target_users_default(self):
        """Test get_target_users for default audience."""
        users = self.service.get_target_users("all")
        self.assertEqual(users.count(), 1)

    def test_send_broadcast_specific_no_users(self):
        """Test send_broadcast with specific audience but no users raises ValueError."""
        broadcast = BroadcastNotification.objects.create(
            title="T", body="B", target_audience="specific"
        )
        with self.assertRaises(ValueError):
            self.service.send_broadcast(broadcast)

    @patch("apps.notifications.services.firebase_service")
    def test_send_broadcast_all_audience(self, mock_firebase):
        """Test send_broadcast with 'all' audience."""
        from apps.accounts.models import UserRole

        UserRole.objects.create(user=self.user, role="handyman")
        UserRole.objects.create(user=self.user, role="homeowner")

        broadcast = BroadcastNotification.objects.create(
            title="T", body="B", target_audience="all", send_push=True
        )

        # Add device for user
        UserDevice.objects.create(user=self.user, device_token="t", device_type="ios")

        mock_firebase.send_multicast_notification.return_value = {
            "success_count": 1,
            "failure_count": 0,
        }

        self.service.send_broadcast(broadcast)

        broadcast.refresh_from_db()
        self.assertEqual(broadcast.status, "completed")
        self.assertEqual(
            broadcast.total_recipients, 2
        )  # 1 for handyman, 1 for homeowner
        self.assertEqual(Notification.objects.count(), 2)

    def test_send_broadcast_no_devices_branch(self):
        """Test send_broadcast skip push if no devices (covers branch 103->133)."""
        broadcast = BroadcastNotification.objects.create(
            title="T", body="B", target_audience="handyman", send_push=True
        )
        from apps.accounts.models import UserRole

        UserRole.objects.create(user=self.user, role="handyman")

        # User has no devices
        self.service.send_broadcast(broadcast)

        broadcast.refresh_from_db()
        self.assertEqual(broadcast.status, "completed")
        self.assertEqual(broadcast.push_success_count, 0)

    def test_create_notification(self):
        """Test creating an in-app notification."""
        notification = self.service.create_notification(
            user=self.user,
            notification_type="job_application_received",
            title="New Application",
            body="You have a new job application.",
            target_role="homeowner",
            data={"job_id": "123"},
        )

        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.notification_type, "job_application_received")
        self.assertEqual(notification.title, "New Application")
        self.assertEqual(notification.body, "You have a new job application.")
        self.assertEqual(notification.target_role, "homeowner")
        self.assertEqual(notification.data, {"job_id": "123"})
        self.assertFalse(notification.is_read)

    @patch("apps.notifications.services.firebase_service")
    def test_send_push_notification_success(self, mock_firebase):
        """Test sending push notification success."""
        # Create active device
        UserDevice.objects.create(
            user=self.user,
            device_token="token123",
            device_type="ios",
            is_active=True,
        )

        mock_firebase.send_multicast_notification.return_value = {
            "success_count": 1,
            "failure_count": 0,
        }

        result = self.service.send_push_notification(
            user=self.user,
            title="Push Title",
            body="Push Body",
            data={"key": "value"},
        )

        self.assertTrue(result)
        mock_firebase.send_multicast_notification.assert_called_once_with(
            device_tokens=["token123"],
            title="Push Title",
            body="Push Body",
            data={"key": "value"},
        )

        # Verify last_used_at was updated
        device = UserDevice.objects.get(device_token="token123")
        self.assertIsNotNone(device.last_used_at)

    @patch("apps.notifications.services.firebase_service")
    def test_send_push_notification_no_devices(self, mock_firebase):
        """Test sending push notification when no active devices exist."""
        result = self.service.send_push_notification(
            user=self.user,
            title="Title",
            body="Body",
        )

        self.assertFalse(result)
        mock_firebase.send_multicast_notification.assert_not_called()

    @patch("apps.notifications.services.firebase_service")
    def test_send_push_notification_failure(self, mock_firebase):
        """Test sending push notification failure."""
        UserDevice.objects.create(
            user=self.user,
            device_token="token123",
            device_type="ios",
            is_active=True,
        )

        mock_firebase.send_multicast_notification.return_value = {
            "success_count": 0,
            "failure_count": 1,
        }

        result = self.service.send_push_notification(
            user=self.user,
            title="Title",
            body="Body",
        )

        self.assertFalse(result)

    def test_create_and_send_notification(self):
        """Test create_and_send_notification utility."""
        with patch.object(self.service, "create_notification") as mock_create:
            with patch.object(self.service, "send_push_notification") as mock_send:
                self.service.create_and_send_notification(
                    user=self.user,
                    notification_type="job_application_received",
                    title="Title",
                    body="Body",
                    target_role="homeowner",
                    data={"d": "v"},
                )

                mock_create.assert_called_once_with(
                    user=self.user,
                    notification_type="job_application_received",
                    title="Title",
                    body="Body",
                    target_role="homeowner",
                    data={"d": "v"},
                )
                mock_send.assert_called_once_with(
                    user=self.user,
                    title="Title",
                    body="Body",
                    data={"d": "v"},
                )

    def test_mark_as_read(self):
        """Test marking a notification as read."""
        notification = Notification.objects.create(
            user=self.user,
            notification_type="job_application_received",
            title="Title",
            body="Body",
            target_role="homeowner",
            is_read=False,
        )

        updated_notif = self.service.mark_as_read(notification)

        self.assertTrue(updated_notif.is_read)
        self.assertIsNotNone(updated_notif.read_at)

        # Test marking again (should not update read_at)
        old_read_at = updated_notif.read_at
        again_notif = self.service.mark_as_read(updated_notif)
        self.assertEqual(again_notif.read_at, old_read_at)

    def test_mark_all_as_read(self):
        """Test marking all notifications as read for a user."""
        Notification.objects.create(
            user=self.user,
            notification_type="job_application_received",
            title="T1",
            body="B1",
            target_role="homeowner",
            is_read=False,
        )
        Notification.objects.create(
            user=self.user,
            notification_type="job_application_received",
            title="T2",
            body="B2",
            target_role="handyman",
            is_read=False,
        )

        # Another user's notification
        other_user = User.objects.create_user(
            email="other@example.com", password="password123"
        )
        Notification.objects.create(
            user=other_user,
            notification_type="job_application_received",
            title="T3",
            body="B3",
            target_role="homeowner",
            is_read=False,
        )

        count = self.service.mark_all_as_read(self.user)
        self.assertEqual(count, 2)
        self.assertEqual(
            Notification.objects.filter(user=self.user, is_read=True).count(), 2
        )
        self.assertEqual(
            Notification.objects.filter(user=other_user, is_read=False).count(), 1
        )

    def test_get_unread_count(self):
        """Test getting unread count."""
        Notification.objects.create(
            user=self.user,
            notification_type="job_application_received",
            title="T1",
            body="B1",
            target_role="homeowner",
            is_read=False,
        )
        Notification.objects.create(
            user=self.user,
            notification_type="job_application_received",
            title="T2",
            body="B2",
            target_role="homeowner",
            is_read=True,
        )

        count = self.service.get_unread_count(self.user)
        self.assertEqual(count, 1)

    def test_register_device(self):
        """Test registering/updating a device."""
        # New registration
        device = self.service.register_device(
            user=self.user, device_token="new_token", device_type="android"
        )
        self.assertEqual(device.device_token, "new_token")
        self.assertEqual(device.user, self.user)
        self.assertTrue(device.is_active)

        # Update existing registration
        device2 = self.service.register_device(
            user=self.user, device_token="new_token", device_type="ios"
        )
        self.assertEqual(device.id, device2.id)
        self.assertEqual(device2.device_type, "ios")

    def test_unregister_device(self):
        """Test unregistering a device."""
        device = UserDevice.objects.create(
            user=self.user,
            device_token="token",
            device_type="ios",
            is_active=True,
        )

        self.service.unregister_device(device)
        device.refresh_from_db()
        self.assertFalse(device.is_active)
