"""Tests for notification serializers."""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.accounts.models import User
from apps.notifications.serializers import DeviceRegisterSerializer


class DeviceRegisterSerializerTests(TestCase):
    """Test cases for DeviceRegisterSerializer."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )

    def test_create_calls_notification_service(self):
        """Test that create method calls notification_service.register_device."""
        request = self.factory.post("/devices/")
        request.user = self.user

        validated_data = {
            "device_token": "test_token_123",
            "device_type": "ios",
        }

        mock_device = MagicMock()
        mock_device.device_token = "test_token_123"
        mock_device.device_type = "ios"

        with patch(
            "apps.notifications.services.notification_service.register_device"
        ) as mock_register:
            mock_register.return_value = mock_device

            serializer = DeviceRegisterSerializer(
                data=validated_data, context={"request": request}
            )
            self.assertTrue(serializer.is_valid())
            device = serializer.save()

            # Verify service was called with correct params
            mock_register.assert_called_once_with(
                user=self.user,
                device_token="test_token_123",
                device_type="ios",
            )

            # Verify device was returned
            self.assertEqual(device.device_token, "test_token_123")
            self.assertEqual(device.device_type, "ios")

    def test_create_with_android_device(self):
        """Test creating device with Android device type."""
        request = self.factory.post("/devices/")
        request.user = self.user

        validated_data = {
            "device_token": "android_token_456",
            "device_type": "android",
        }

        mock_device = MagicMock()
        mock_device.device_token = "android_token_456"
        mock_device.device_type = "android"

        with patch(
            "apps.notifications.services.notification_service.register_device"
        ) as mock_register:
            mock_register.return_value = mock_device

            serializer = DeviceRegisterSerializer(
                data=validated_data, context={"request": request}
            )
            self.assertTrue(serializer.is_valid())
            device = serializer.save()

            mock_register.assert_called_once_with(
                user=self.user,
                device_token="android_token_456",
                device_type="android",
            )

            self.assertEqual(device.device_token, "android_token_456")
            self.assertEqual(device.device_type, "android")


class NotificationSerializerTest(TestCase):
    """Test cases for NotificationSerializer."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@test.com", password="testpass123"
        )
        self.handyman = User.objects.create_user(
            email="handyman@test.com", password="testpass123"
        )

        from apps.profiles.models import HandymanProfile, HomeownerProfile

        HomeownerProfile.objects.create(user=self.homeowner, display_name="John Doe")
        HandymanProfile.objects.create(user=self.handyman, display_name="Jane Smith")

    def test_thumbnail_for_admin_broadcast(self):
        """Test thumbnail returns system icon for admin broadcast."""
        from apps.notifications.models import Notification

        notification = Notification.objects.create(
            user=self.homeowner,
            notification_type="admin_broadcast",
            title="System Update",
            body="New features available!",
            target_role="homeowner",
        )

        from apps.notifications.serializers import NotificationSerializer

        serializer = NotificationSerializer(notification)
        self.assertEqual(
            serializer.data["thumbnail"], "https://placehold.co/300x300?text=!"
        )

    def test_thumbnail_for_user_with_avatar(self):
        """Test thumbnail returns avatar URL when user has avatar."""
        from apps.notifications.models import Notification

        handyman_profile = self.handyman.handyman_profile
        handyman_profile.avatar = "handyman/avatars/2024/01/test.jpg"
        handyman_profile.save()

        notification = Notification.objects.create(
            user=self.homeowner,
            notification_type="job_application_received",
            title="New Application",
            body="You have a new job application.",
            target_role="homeowner",
            triggered_by=self.handyman,
        )

        from apps.notifications.serializers import NotificationSerializer

        serializer = NotificationSerializer(notification)
        self.assertTrue(
            serializer.data["thumbnail"].endswith("handyman/avatars/2024/01/test.jpg")
        )

    def test_thumbnail_for_user_without_avatar(self):
        """Test thumbnail returns initials placeholder when user has no avatar."""
        from apps.notifications.models import Notification

        notification = Notification.objects.create(
            user=self.homeowner,
            notification_type="job_application_received",
            title="New Application",
            body="You have a new job application.",
            target_role="homeowner",
            triggered_by=self.handyman,
        )

        from apps.notifications.serializers import NotificationSerializer

        serializer = NotificationSerializer(notification)
        self.assertEqual(
            serializer.data["thumbnail"], "https://placehold.co/300x300?text=JS"
        )

    def test_thumbnail_for_user_with_single_word_name(self):
        """Test thumbnail returns single initial for single word name."""
        from apps.notifications.models import Notification

        handyman_profile = self.handyman.handyman_profile
        handyman_profile.display_name = "Madonna"
        handyman_profile.save()

        notification = Notification.objects.create(
            user=self.homeowner,
            notification_type="job_application_received",
            title="New Application",
            body="You have a new job application.",
            target_role="homeowner",
            triggered_by=self.handyman,
        )

        from apps.notifications.serializers import NotificationSerializer

        serializer = NotificationSerializer(notification)
        self.assertEqual(
            serializer.data["thumbnail"], "https://placehold.co/300x300?text=M"
        )

    def test_thumbnail_for_handyman_target_role(self):
        """Test thumbnail uses homeowner profile when target_role is handyman."""
        from apps.notifications.models import Notification

        homeowner_profile = self.homeowner.homeowner_profile
        homeowner_profile.avatar = "homeowner/avatars/2024/01/test.jpg"
        homeowner_profile.save()

        notification = Notification.objects.create(
            user=self.handyman,
            notification_type="application_approved",
            title="Application Approved",
            body="Your application was approved!",
            target_role="handyman",
            triggered_by=self.homeowner,
        )

        from apps.notifications.serializers import NotificationSerializer

        serializer = NotificationSerializer(notification)
        self.assertTrue(
            serializer.data["thumbnail"].endswith("homeowner/avatars/2024/01/test.jpg")
        )

    def test_thumbnail_fallback_for_no_triggered_by(self):
        """Test thumbnail returns system icon when no triggered_by."""
        from apps.notifications.models import Notification

        notification = Notification.objects.create(
            user=self.homeowner,
            notification_type="job_application_received",
            title="New Application",
            body="You have a new job application.",
            target_role="homeowner",
        )

        from apps.notifications.serializers import NotificationSerializer

        serializer = NotificationSerializer(notification)
        self.assertEqual(
            serializer.data["thumbnail"], "https://placehold.co/300x300?text=!"
        )

    def test_thumbnail_fallback_for_missing_profile(self):
        """Test thumbnail returns system icon when triggered_by has no profile."""
        from apps.notifications.models import Notification

        user_no_profile = User.objects.create_user(
            email="noprofile@test.com", password="testpass123"
        )

        notification = Notification.objects.create(
            user=self.homeowner,
            notification_type="job_application_received",
            title="New Application",
            body="You have a new job application.",
            target_role="homeowner",
            triggered_by=user_no_profile,
        )

        from apps.notifications.serializers import NotificationSerializer

        serializer = NotificationSerializer(notification)
        self.assertEqual(
            serializer.data["thumbnail"], "https://placehold.co/300x300?text=!"
        )
