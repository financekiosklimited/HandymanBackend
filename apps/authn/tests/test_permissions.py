"""Tests for authn permissions."""

from django.test import TestCase
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory

from apps.accounts.models import User
from apps.authn.permissions import GuestPlatformGuardPermission, PhoneVerifiedPermission


class GuestPlatformGuardPermissionTests(TestCase):
    """Test cases for GuestPlatformGuardPermission."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()
        self.permission = GuestPlatformGuardPermission()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )

    def test_non_mobile_platform_raises_permission_denied(self):
        """Test that non-mobile platform URL raises PermissionDenied."""
        request = self.factory.get("/api/v1/web/some-endpoint/")
        request.user = None  # Anonymous user

        with self.assertRaises(PermissionDenied):
            self.permission.has_permission(request, None)

    def test_authenticated_user_token_platform_mismatch(self):
        """Test that authenticated user with mismatched token platform is denied."""
        request = self.factory.get("/api/v1/mobile/some-endpoint/")
        request.user = self.user
        request.user.token_payload = {
            "plat": "web",  # Token from web platform
            "active_role": "homeowner",
        }

        with self.assertRaises(PermissionDenied):
            self.permission.has_permission(request, None)

    def test_mobile_platform_anonymous_user_allowed(self):
        """Test that mobile platform with anonymous user is allowed."""
        request = self.factory.get("/api/v1/mobile/some-endpoint/")
        request.user = None

        result = self.permission.has_permission(request, None)
        self.assertTrue(result)

    def test_mobile_platform_authenticated_user_matching_token_allowed(self):
        """Test that mobile platform with matching token platform is allowed."""
        request = self.factory.get("/api/v1/mobile/some-endpoint/")
        request.user = self.user
        request.user.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
        }

        result = self.permission.has_permission(request, None)
        self.assertTrue(result)


class PhoneVerifiedPermissionTests(TestCase):
    """Test cases for PhoneVerifiedPermission."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()
        self.permission = PhoneVerifiedPermission()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )

    def test_unauthenticated_user_returns_false(self):
        """Test that unauthenticated user returns False."""
        request = self.factory.get("/")
        request.user = None

        result = self.permission.has_permission(request, None)
        self.assertFalse(result)

    def test_no_token_payload_returns_false(self):
        """Test that user without token_payload returns False."""
        request = self.factory.get("/")
        request.user = self.user
        # No token_payload attribute

        result = self.permission.has_permission(request, None)
        self.assertFalse(result)

    def test_phone_verified_returns_true(self):
        """Test that user with phone_verified=True returns True."""
        request = self.factory.get("/")
        request.user = self.user
        request.user.token_payload = {
            "phone_verified": True,
        }

        result = self.permission.has_permission(request, None)
        self.assertTrue(result)
