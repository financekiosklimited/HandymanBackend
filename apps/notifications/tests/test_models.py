from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.notifications.models import Notification, UserDevice

User = get_user_model()


class UserDeviceModelTest(TestCase):
    """
    Test cases for UserDevice model.
    """

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@test.com", password="testpass123"
        )

    def test_create_device(self):
        """Test creating a device."""
        device = UserDevice.objects.create(
            user=self.user,
            device_token="test_token_123",
            device_type="ios",
            is_active=True,
        )

        self.assertIsNotNone(device.public_id)
        self.assertEqual(device.user, self.user)
        self.assertEqual(device.device_token, "test_token_123")
        self.assertEqual(device.device_type, "ios")
        self.assertTrue(device.is_active)

    def test_unique_device_token(self):
        """Test that device tokens must be unique."""
        UserDevice.objects.create(
            user=self.user,
            device_token="test_token_123",
            device_type="ios",
        )

        # Try to create device with same token
        from django.db import IntegrityError

        user2 = User.objects.create_user(email="test2@test.com", password="testpass123")

        with self.assertRaises(IntegrityError):
            UserDevice.objects.create(
                user=user2,
                device_token="test_token_123",
                device_type="android",
            )

    def test_device_type_choices(self):
        """Test device type choices."""
        valid_types = ["ios", "android", "web"]

        for device_type in valid_types:
            device = UserDevice.objects.create(
                user=self.user,
                device_token=f"token_{device_type}",
                device_type=device_type,
            )
            self.assertEqual(device.device_type, device_type)


class NotificationModelTest(TestCase):
    """
    Test cases for Notification model.
    """

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@test.com", password="testpass123"
        )

    def test_create_notification(self):
        """Test creating a notification."""
        notification = Notification.objects.create(
            user=self.user,
            notification_type="job_application_received",
            title="New Application",
            body="You have a new job application",
            target_role="homeowner",
            data={"job_id": "123"},
        )

        self.assertIsNotNone(notification.public_id)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.notification_type, "job_application_received")
        self.assertEqual(notification.title, "New Application")
        self.assertEqual(notification.body, "You have a new job application")
        self.assertEqual(notification.target_role, "homeowner")
        self.assertEqual(notification.data, {"job_id": "123"})
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

    def test_notification_type_choices(self):
        """Test notification type choices."""
        valid_types = [
            "job_application_received",
            "application_approved",
            "application_rejected",
            "application_withdrawn",
        ]

        for notif_type in valid_types:
            notification = Notification.objects.create(
                user=self.user,
                notification_type=notif_type,
                title="Test",
                body="Test body",
                target_role="homeowner",
            )
            self.assertEqual(notification.notification_type, notif_type)
            # Clean up
            notification.delete()

    def test_invalid_data_field(self):
        """Test that data field must be a dict."""
        notification = Notification(
            user=self.user,
            notification_type="job_application_received",
            title="Test",
            body="Test body",
            target_role="homeowner",
            data="invalid_string",  # Should be a dict
        )

        with self.assertRaises(ValidationError):
            notification.save()

    def test_target_role_choices(self):
        """Test target role choices."""
        valid_roles = ["handyman", "homeowner"]

        for role in valid_roles:
            notification = Notification.objects.create(
                user=self.user,
                notification_type="job_application_received",
                title="Test",
                body="Test body",
                target_role=role,
            )
            self.assertEqual(notification.target_role, role)
            # Clean up
            notification.delete()
