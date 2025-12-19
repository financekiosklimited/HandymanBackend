"""Tests for authn permissions."""

from django.test import RequestFactory, TestCase
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.authn.permissions import (
    ActiveRoleRequiredPermission,
    EmailVerifiedPermission,
    GuestPlatformGuardPermission,
    PhoneVerifiedPermission,
    PlatformGuardPermission,
    RoleGuardPermission,
)


class PermissionTests(TestCase):
    """Test cases for custom permissions."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email="test@example.com", password="password"
        )
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
            "phone_verified": True,
        }

    def test_platform_guard_success(self):
        permission = PlatformGuardPermission()
        request = self.factory.get("/api/v1/mobile/test/")
        request.user = self.user
        self.assertTrue(permission.has_permission(request, None))

    def test_platform_guard_mismatch(self):
        permission = PlatformGuardPermission()
        request = self.factory.get("/api/v1/web/test/")
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            permission.has_permission(request, None)

    def test_platform_guard_unauthenticated(self):
        permission = PlatformGuardPermission()
        request = self.factory.get("/api/v1/mobile/test/")
        request.user = None
        self.assertFalse(permission.has_permission(request, None))

    def test_platform_guard_no_payload(self):
        permission = PlatformGuardPermission()
        request = self.factory.get("/api/v1/mobile/test/")
        request.user = self.user
        del request.user.token_payload
        self.assertFalse(permission.has_permission(request, None))

    def test_guest_platform_guard_mobile_success(self):
        permission = GuestPlatformGuardPermission()
        request = self.factory.get("/api/v1/mobile/test/")
        request.user = None
        self.assertTrue(permission.has_permission(request, None))

    def test_guest_platform_guard_web_fail(self):
        permission = GuestPlatformGuardPermission()
        request = self.factory.get("/api/v1/web/test/")
        request.user = None
        with self.assertRaises(PermissionDenied):
            permission.has_permission(request, None)

    def test_guest_platform_guard_auth_mismatch(self):
        permission = GuestPlatformGuardPermission()
        request = self.factory.get("/api/v1/mobile/test/")
        request.user = self.user
        request.user.token_payload["plat"] = "web"
        with self.assertRaises(PermissionDenied):
            permission.has_permission(request, None)

    def test_role_guard_success(self):
        permission = RoleGuardPermission()
        request = self.factory.get("/api/v1/mobile/homeowner/test/")
        request.user = self.user
        self.assertTrue(permission.has_permission(request, None))

    def test_role_guard_mismatch_active_role(self):
        permission = RoleGuardPermission()
        request = self.factory.get("/api/v1/mobile/handyman/test/")
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            permission.has_permission(request, None)

    def test_role_guard_mismatch_user_roles(self):
        permission = RoleGuardPermission()
        request = self.factory.get("/api/v1/mobile/handyman/test/")
        request.user = self.user
        request.user.token_payload["active_role"] = "handyman"
        # user has 'homeowner' in roles, not 'handyman'
        with self.assertRaises(PermissionDenied):
            permission.has_permission(request, None)

    def test_role_guard_unauthenticated(self):
        permission = RoleGuardPermission()
        request = self.factory.get("/api/v1/mobile/homeowner/test/")
        request.user = None
        self.assertFalse(permission.has_permission(request, None))

    def test_email_verified_permission_success(self):
        permission = EmailVerifiedPermission()
        request = self.factory.get("/test/")
        request.user = self.user
        self.assertTrue(permission.has_permission(request, None))

    def test_email_verified_permission_fail(self):
        permission = EmailVerifiedPermission()
        self.user.token_payload["email_verified"] = False
        request = self.factory.get("/test/")
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            permission.has_permission(request, None)

    def test_active_role_required_success(self):
        permission = ActiveRoleRequiredPermission()
        request = self.factory.get("/test/")
        request.user = self.user
        self.assertTrue(permission.has_permission(request, None))

    def test_active_role_required_fail(self):
        permission = ActiveRoleRequiredPermission()
        self.user.token_payload["active_role"] = None
        request = self.factory.get("/test/")
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            permission.has_permission(request, None)

    def test_phone_verified_permission_success(self):
        permission = PhoneVerifiedPermission()
        request = self.factory.get("/test/")
        request.user = self.user
        self.assertTrue(permission.has_permission(request, None))

    def test_active_role_required_unauthenticated(self):
        permission = ActiveRoleRequiredPermission()
        request = self.factory.get("/test/")
        request.user = None
        self.assertFalse(permission.has_permission(request, None))

    def test_active_role_required_no_payload(self):
        permission = ActiveRoleRequiredPermission()
        request = self.factory.get("/test/")
        request.user = self.user
        del request.user.token_payload
        self.assertFalse(permission.has_permission(request, None))

    def test_phone_verified_unauthenticated(self):
        permission = PhoneVerifiedPermission()
        request = self.factory.get("/test/")
        request.user = None
        self.assertFalse(permission.has_permission(request, None))

    def test_phone_verified_no_payload(self):
        permission = PhoneVerifiedPermission()
        request = self.factory.get("/test/")
        request.user = self.user
        del request.user.token_payload
        self.assertFalse(permission.has_permission(request, None))

    def test_email_verified_unauthenticated(self):
        permission = EmailVerifiedPermission()
        request = self.factory.get("/test/")
        request.user = None
        self.assertFalse(permission.has_permission(request, None))

    def test_email_verified_no_payload(self):
        permission = EmailVerifiedPermission()
        request = self.factory.get("/test/")
        request.user = self.user
        del request.user.token_payload
        self.assertFalse(permission.has_permission(request, None))

    def test_extract_platform_fallback(self):
        permission = PlatformGuardPermission()
        self.assertIsNone(permission._extract_platform_from_url("/not/api/v1/"))

    def test_extract_role_fallback(self):
        permission = RoleGuardPermission()
        self.assertIsNone(
            permission._extract_role_from_url("/api/v1/mobile/not-a-role/")
        )

    def test_role_guard_no_payload(self):
        permission = RoleGuardPermission()
        request = self.factory.get("/api/v1/mobile/homeowner/test/")
        request.user = self.user
        del request.user.token_payload
        self.assertFalse(permission.has_permission(request, None))
