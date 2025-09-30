"""Tests for authentication and permissions."""

from datetime import UTC, datetime

from django.test import RequestFactory, TestCase, override_settings
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

from apps.accounts.models import User, UserRole
from apps.authn.authentication import JWTAuthentication
from apps.authn.jwt_service import jwt_service
from apps.authn.permissions import (
    ActiveRoleRequiredPermission,
    EmailVerifiedPermission,
    PlatformGuardPermission,
    RoleGuardPermission,
)

TEST_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCCgfzlhVtAL6to
Z/FkBglODIn31C4VjRBot7OpzopFlob7iyt2zC3cuxQq/bzTgMF90g9SMByHsBiR
RQmv+7fb7GQHfRrEcj3LpShv+D0ywJoeYRaxvAwPAhSu1E5Cblzoef470CjhPtGY
4TcvKOzJH8FQIhfj8pTSJMC+qhRSdy5Etisg75Y3/6lExdidQw0KEp8BHm6IPdEO
C0Z2XaeypYGqFN+cm4/IPZaAbfFTz5z7poZEls26GJsIR6FystLXqUW6OSE+Ne2w
KcViEjMhhndoLWiiSl6eXBHqmJnj6S1zhktAj7yBFwBJN80IuRVqfG4CaPIuaXp/
J3TD63S5AgMBAAECggEAHd5QGdt+ed8vFJMNbP3wrTszbFPURDxnr/+zD77kaG69
7933EZZDPMxYHkq6J5HFNt2XghDexrMnvD+Xqv4qIxwj/I7GTIV03SGscovWvcHU
w/Umc4D9JYYtY6HVU2DcxJv+8oN+h6aP47RPo+xy3Mj2vjc/Tn0bUEj3D+vvALxQ
YKaSnqQ5/LPhKFQXOrosyF26ViFPLcffYimWaSdPNI1deeo+TFBRLOsH2dExIaMn
tU+/9uJ8Igma7hdwjNhHdd4lNnNMlQUAa/luV+ujC66m+Ek0oCjJxId6Fh6d2g4k
diU4X+ZzEokoUvxk7gkp6M4F79Nb58Tqfgffqmxi7QKBgQC3ylM6yv8x7rzMO6QP
Ms0EtsWQVf98sCw/uDMLNp7xEtI7QF53jxKFNyaKaNSW6pTiH6G59KcfZmvuQRn1
U88Eni+hKlKGcSSAPraQs+BN3Xh4ooRxukMDIRwax4RYQvbMAIOhG9wye/y+7qYv
lFrQJVyElfAJRb4Q8XPfgp/CDwKBgQC1yH1WjRZ1k7r0cvt1xQhy0bsHvcgzar+a
9gJpzB2JNZGHhZbLEh216AwGfx1SgvZ4SXvbv267wBOchIFYR1xMjtIns3G9qkYg
F5/rAoKcG5eRUTzOq9uQCR3I/hknwm8WFwmV1KOmRHROssev8t+LBtQMwbQw3VKR
5xiuSdiEtwKBgGRIGje3MZ1eJVfOpwq/7kvHKm9B7UBspAg0im1w5TKm0V0RFzpn
L3TOjdHxtyWNY6UqG0Vqr5GbggKjNPW+P/PGGDj47cR7ka4ECftUmmwCDszL6DZh
qlTXyQz3lkfOafkPwsKyf+hv7I2Fi9nkOdTeved+JFX63uVBybbIAEGTAoGASbCv
lpF1JE6xv/yIkVJBPYJlxhqZ+LXyXFgT3F2BL6kGiKCP41xBrQcXMN8AvP0X+uUX
D5rHwdZ4XL+eS3IKKYLQEIX+urs22DWbf0IyPiQ1ShRbiRBD3lzDtUHEYsjADX1j
Rli/ylv/phN1PY9ALXSkK1OuvwxJN5ot+CE5Y3sCgYEArWI0kqj17xzw8nIEiMl8
HtbMs+lghU71glGZc1vXIHg4lzJidcdm/9P5gKP5WyIfFJGEcgmmzPiHPDwHspbD
3TzUcBVdTiF6gsDYp74le2kI7DJ1zkl90F7+8KL5OrWVtyGR+P3/dt4teP8RJv7o
m5CAoE/AzLS1jnEdRNvvVag=
-----END PRIVATE KEY-----"""

TEST_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAgoH85YVbQC+raGfxZAYJ
TgyJ99QuFY0QaLezqc6KRZaG+4srdswt3LsUKv2804DBfdIPUjAch7AYkUUJr/u3
2+xkB30axHI9y6Uob/g9MsCaHmEWsbwMDwIUrtROQm5c6Hn+O9Ao4T7RmOE3Lyjs
yR/BUCIX4/KU0iTAvqoUUncuRLYrIO+WN/+pRMXYnUMNChKfAR5uiD3RDgtGdl2n
sqWBqhTfnJuPyD2WgG3xU8+c+6aGRJbNuhibCEehcrLS16lFujkhPjXtsCnFYhIz
IYZ3aC1ookpenlwR6piZ4+ktc4ZLQI+8gRcASTfNCLkVanxuAmjyLml6fyd0w+t0
uQIDAQAB
-----END PUBLIC KEY-----"""


@override_settings(
    JWT_PRIVATE_KEY=TEST_PRIVATE_KEY,
    JWT_PUBLIC_KEY=TEST_PUBLIC_KEY,
    JWT_ALGORITHM="RS256",
)
class JWTAuthenticationTests(TestCase):
    """Test cases for JWTAuthentication."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.auth = JWTAuthentication()

        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.user.email_verified_at = datetime.now(UTC)
        self.user.save()

        UserRole.objects.create(user=self.user, role="customer")

    def test_authenticate_valid_token(self):
        """Test authentication with valid token."""
        tokens = jwt_service.create_token_pair(
            user=self.user, platform="web", active_role="customer"
        )

        request = self.factory.get("/api/v1/test/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {tokens['access_token']}"

        user, payload = self.auth.authenticate(request)

        self.assertEqual(user, self.user)
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload["type"], "access")

    def test_authenticate_no_header(self):
        """Test authentication without Authorization header."""
        request = self.factory.get("/api/v1/test/")

        result = self.auth.authenticate(request)

        self.assertIsNone(result)

    def test_authenticate_invalid_header_format(self):
        """Test authentication with invalid header format."""
        request = self.factory.get("/api/v1/test/")
        request.META["HTTP_AUTHORIZATION"] = "Invalid token"

        result = self.auth.authenticate(request)

        self.assertIsNone(result)

    def test_authenticate_refresh_token_rejected(self):
        """Test authentication rejects refresh token."""
        tokens = jwt_service.create_token_pair(user=self.user, platform="web")

        request = self.factory.get("/api/v1/test/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {tokens['refresh_token']}"

        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_authenticate_invalid_token(self):
        """Test authentication with invalid token."""
        request = self.factory.get("/api/v1/test/")
        request.META["HTTP_AUTHORIZATION"] = "Bearer invalid-token"

        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_authenticate_nonexistent_user(self):
        """Test authentication with token for nonexistent user."""
        tokens = jwt_service.create_token_pair(user=self.user, platform="web")

        # Delete user
        self.user.delete()

        request = self.factory.get("/api/v1/test/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {tokens['access_token']}"

        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_authenticate_inactive_user(self):
        """Test authentication with inactive user."""
        self.user.is_active = False
        self.user.save()

        tokens = jwt_service.create_token_pair(user=self.user, platform="web")

        request = self.factory.get("/api/v1/test/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {tokens['access_token']}"

        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_authenticate_header_method(self):
        """Test authenticate_header returns Bearer."""
        request = self.factory.get("/api/v1/test/")

        header = self.auth.authenticate_header(request)

        self.assertEqual(header, "Bearer")

    def test_token_payload_attached_to_user(self):
        """Test token payload is attached to user object."""
        tokens = jwt_service.create_token_pair(
            user=self.user, platform="web", active_role="customer"
        )

        request = self.factory.get("/api/v1/test/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {tokens['access_token']}"

        user, _ = self.auth.authenticate(request)

        self.assertTrue(hasattr(user, "token_payload"))
        self.assertEqual(user.token_payload["active_role"], "customer")


@override_settings(
    JWT_PRIVATE_KEY=TEST_PRIVATE_KEY,
    JWT_PUBLIC_KEY=TEST_PUBLIC_KEY,
    JWT_ALGORITHM="RS256",
)
class PlatformGuardPermissionTests(TestCase):
    """Test cases for PlatformGuardPermission."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.permission = PlatformGuardPermission()

        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )

    def test_platform_matches(self):
        """Test permission granted when platform matches."""
        tokens = jwt_service.create_token_pair(user=self.user, platform="web")

        payload = jwt_service.decode_token(tokens["access_token"])
        self.user.token_payload = payload

        request = self.factory.get("/api/v1/web/test/")
        request.user = self.user

        self.assertTrue(self.permission.has_permission(request, None))

    def test_platform_mismatch(self):
        """Test permission denied when platform doesn't match."""
        tokens = jwt_service.create_token_pair(user=self.user, platform="web")

        payload = jwt_service.decode_token(tokens["access_token"])
        self.user.token_payload = payload

        request = self.factory.get("/api/v1/mobile/test/")
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            self.permission.has_permission(request, None)

    def test_no_platform_in_url(self):
        """Test permission granted when no platform in URL."""
        tokens = jwt_service.create_token_pair(user=self.user, platform="web")

        payload = jwt_service.decode_token(tokens["access_token"])
        self.user.token_payload = payload

        request = self.factory.get("/api/other/endpoint/")
        request.user = self.user

        self.assertTrue(self.permission.has_permission(request, None))

    def test_unauthenticated_user(self):
        """Test permission denied for unauthenticated user."""
        request = self.factory.get("/api/v1/web/test/")
        request.user = None

        self.assertFalse(self.permission.has_permission(request, None))

    def test_missing_token_payload_denies(self):
        """Permission denied when token payload is absent."""
        request = self.factory.get("/api/v1/web/test/")
        request.user = self.user

        if hasattr(self.user, "token_payload"):
            delattr(self.user, "token_payload")

        self.assertFalse(self.permission.has_permission(request, None))

    def test_extract_platform_returns_none_for_unknown(self):
        """Unknown platform segments are ignored."""
        self.assertIsNone(self.permission._extract_platform_from_url("/api/v1/desktop/area/"))


@override_settings(
    JWT_PRIVATE_KEY=TEST_PRIVATE_KEY,
    JWT_PUBLIC_KEY=TEST_PUBLIC_KEY,
    JWT_ALGORITHM="RS256",
)
class RoleGuardPermissionTests(TestCase):
    """Test cases for RoleGuardPermission."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.permission = RoleGuardPermission()

        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="customer")
        UserRole.objects.create(user=self.user, role="handyman")

    def test_role_matches(self):
        """Test permission granted when role matches."""
        tokens = jwt_service.create_token_pair(
            user=self.user, platform="web", active_role="customer"
        )

        payload = jwt_service.decode_token(tokens["access_token"])
        self.user.token_payload = payload

        request = self.factory.get("/api/v1/web/customer/profile/")
        request.user = self.user

        self.assertTrue(self.permission.has_permission(request, None))

    def test_role_mismatch(self):
        """Test permission denied when active role doesn't match URL role."""
        tokens = jwt_service.create_token_pair(
            user=self.user, platform="web", active_role="customer"
        )

        payload = jwt_service.decode_token(tokens["access_token"])
        self.user.token_payload = payload

        request = self.factory.get("/api/v1/web/handyman/profile/")
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            self.permission.has_permission(request, None)

    def test_user_doesnt_have_role(self):
        """Test permission denied when user doesn't have the role."""
        tokens = jwt_service.create_token_pair(
            user=self.user,
            platform="web",
            active_role="admin",  # User doesn't have this role
        )

        payload = jwt_service.decode_token(tokens["access_token"])
        self.user.token_payload = payload

        request = self.factory.get("/api/v1/web/admin/settings/")
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            self.permission.has_permission(request, None)

    def test_no_role_in_url(self):
        """Test permission granted when no role in URL."""
        tokens = jwt_service.create_token_pair(
            user=self.user, platform="web", active_role="customer"
        )

        payload = jwt_service.decode_token(tokens["access_token"])
        self.user.token_payload = payload

        request = self.factory.get("/api/v1/web/general/")
        request.user = self.user

        self.assertTrue(self.permission.has_permission(request, None))

    def test_unauthenticated_user(self):
        """Test permission denied for unauthenticated user."""
        request = self.factory.get("/api/v1/web/customer/profile/")
        request.user = None

        self.assertFalse(self.permission.has_permission(request, None))

    def test_missing_token_payload(self):
        """Permission denied when token payload missing."""
        request = self.factory.get("/api/v1/web/customer/profile/")
        request.user = self.user

        if hasattr(self.user, "token_payload"):
            delattr(self.user, "token_payload")

        self.assertFalse(self.permission.has_permission(request, None))

    def test_extract_role_returns_none_for_unknown(self):
        """Unknown role segments are ignored."""
        self.assertIsNone(self.permission._extract_role_from_url("/api/v1/web/guests/list/"))

    def test_extract_role_recognizes_admin(self):
        """Admin role is extracted from URL path."""
        self.assertEqual(
            self.permission._extract_role_from_url("/api/v1/web/admin/dashboard/"),
            "admin",
        )

    def test_extract_role_short_path(self):
        """Paths without expected segments return None."""
        self.assertIsNone(self.permission._extract_role_from_url("/web/customer"))


@override_settings(
    JWT_PRIVATE_KEY=TEST_PRIVATE_KEY,
    JWT_PUBLIC_KEY=TEST_PUBLIC_KEY,
    JWT_ALGORITHM="RS256",
)
class EmailVerifiedPermissionTests(TestCase):
    """Test cases for EmailVerifiedPermission."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.permission = EmailVerifiedPermission()

        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )

    def test_email_verified(self):
        """Test permission granted when email is verified."""
        self.user.email_verified_at = datetime.now(UTC)
        self.user.save()

        tokens = jwt_service.create_token_pair(user=self.user, platform="web")

        payload = jwt_service.decode_token(tokens["access_token"])
        self.user.token_payload = payload

        request = self.factory.get("/api/v1/test/")
        request.user = self.user

        self.assertTrue(self.permission.has_permission(request, None))

    def test_email_not_verified(self):
        """Test permission denied when email is not verified."""
        tokens = jwt_service.create_token_pair(user=self.user, platform="web")

        payload = jwt_service.decode_token(tokens["access_token"])
        self.user.token_payload = payload

        request = self.factory.get("/api/v1/test/")
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            self.permission.has_permission(request, None)

    def test_unauthenticated_user(self):
        """Test permission denied for unauthenticated user."""
        request = self.factory.get("/api/v1/test/")
        request.user = None

        self.assertFalse(self.permission.has_permission(request, None))

    def test_missing_token_payload(self):
        """Permission denied when payload missing."""
        request = self.factory.get("/api/v1/test/")
        request.user = self.user

        if hasattr(self.user, "token_payload"):
            delattr(self.user, "token_payload")

        self.assertFalse(self.permission.has_permission(request, None))


@override_settings(
    JWT_PRIVATE_KEY=TEST_PRIVATE_KEY,
    JWT_PUBLIC_KEY=TEST_PUBLIC_KEY,
    JWT_ALGORITHM="RS256",
)
class ActiveRoleRequiredPermissionTests(TestCase):
    """Test cases for ActiveRoleRequiredPermission."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.permission = ActiveRoleRequiredPermission()

        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="customer")

    def test_active_role_present(self):
        """Test permission granted when active role is present."""
        tokens = jwt_service.create_token_pair(
            user=self.user, platform="web", active_role="customer"
        )

        payload = jwt_service.decode_token(tokens["access_token"])
        self.user.token_payload = payload

        request = self.factory.get("/api/v1/test/")
        request.user = self.user

        self.assertTrue(self.permission.has_permission(request, None))

    def test_no_active_role(self):
        """Test permission denied when no active role."""
        tokens = jwt_service.create_token_pair(
            user=self.user, platform="web", active_role=None
        )

        payload = jwt_service.decode_token(tokens["access_token"])
        self.user.token_payload = payload

        request = self.factory.get("/api/v1/test/")
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            self.permission.has_permission(request, None)

    def test_unauthenticated_user(self):
        """Test permission denied for unauthenticated user."""
        request = self.factory.get("/api/v1/test/")
        request.user = None

        self.assertFalse(self.permission.has_permission(request, None))

    def test_missing_token_payload(self):
        """Permission denied when token payload missing."""
        request = self.factory.get("/api/v1/test/")
        request.user = self.user

        if hasattr(self.user, "token_payload"):
            delattr(self.user, "token_payload")

        self.assertFalse(self.permission.has_permission(request, None))
