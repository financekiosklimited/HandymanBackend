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
