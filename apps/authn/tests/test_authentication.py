"""Tests for authentication and permissions."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
from django.test import RequestFactory, TestCase, override_settings
from rest_framework import exceptions

from apps.accounts.models import User, UserRole
from apps.authn.authentication import JWTAuthentication
from apps.authn.jwt_service import jwt_service

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

        UserRole.objects.create(user=self.user, role="homeowner")

    def test_authenticate_valid_token(self):
        """Test authentication with valid token."""
        tokens = jwt_service.create_token_pair(
            user=self.user, platform="web", active_role="homeowner"
        )

        request = self.factory.get("/api/v1/test/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {tokens['access_token']}"

        user, payload = self.auth.authenticate(request)

        self.assertEqual(user, self.user)
        self.assertEqual(payload["plat"], "web")
        self.assertEqual(payload["active_role"], "homeowner")

    def test_authenticate_no_header(self):
        """Test authentication with no header."""
        request = self.factory.get("/api/v1/test/")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_authenticate_invalid_prefix(self):
        """Test authentication with invalid prefix."""
        request = self.factory.get("/api/v1/test/")
        request.META["HTTP_AUTHORIZATION"] = "Token some-token"
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_authenticate_invalid_token_type(self):
        """Test authentication with refresh token (wrong type)."""
        tokens = jwt_service.create_token_pair(user=self.user, platform="web")
        request = self.factory.get("/api/v1/test/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {tokens['refresh_token']}"
        with self.assertRaisesRegex(
            exceptions.AuthenticationFailed, "Invalid token type"
        ):
            self.auth.authenticate(request)

    def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user."""
        tokens = jwt_service.create_token_pair(user=self.user, platform="web")
        self.user.delete()
        request = self.factory.get("/api/v1/test/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {tokens['access_token']}"
        with self.assertRaisesRegex(exceptions.AuthenticationFailed, "User not found"):
            self.auth.authenticate(request)

    def test_authenticate_user_inactive(self):
        """Test authentication with inactive user."""
        tokens = jwt_service.create_token_pair(user=self.user, platform="web")
        self.user.is_active = False
        self.user.save()
        request = self.factory.get("/api/v1/test/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {tokens['access_token']}"
        with self.assertRaisesRegex(
            exceptions.AuthenticationFailed, "User is inactive"
        ):
            self.auth.authenticate(request)

    def test_authenticate_expired_token(self):
        """Test authentication with expired token."""
        # Create a token that is already expired
        with patch("apps.authn.jwt_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.now(UTC) - timedelta(days=1)
            mock_datetime.UTC = UTC
            tokens = jwt_service.create_token_pair(user=self.user, platform="web")

        request = self.factory.get("/api/v1/test/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {tokens['access_token']}"
        with self.assertRaisesRegex(
            exceptions.AuthenticationFailed, "Token has expired"
        ):
            self.auth.authenticate(request)

    def test_authenticate_invalid_token(self):
        """Test authentication with invalid token."""
        request = self.factory.get("/api/v1/test/")
        request.META["HTTP_AUTHORIZATION"] = "Bearer invalid-token"
        with self.assertRaisesRegex(exceptions.AuthenticationFailed, "Invalid token"):
            self.auth.authenticate(request)

    def test_authenticate_header(self):
        """Test authenticate_header method."""
        self.assertEqual(self.auth.authenticate_header(None), "Bearer")

    def test_authenticate_invalid_token_format(self):
        """Test authentication with invalid token format (e.g. malformed JWT)."""
        request = self.factory.get("/api/v1/test/")
        request.META["HTTP_AUTHORIZATION"] = "Bearer malformed.jwt"
        with self.assertRaisesRegex(exceptions.AuthenticationFailed, "Invalid token"):
            self.auth.authenticate(request)

    def test_authenticate_expired_signature_error_direct(self):
        """Test authentication explicitly catching ExpiredSignatureError from service."""
        with patch(
            "apps.authn.authentication.jwt_service.decode_token",
            side_effect=jwt.ExpiredSignatureError,
        ):
            request = self.factory.get("/api/v1/test/")
            request.META["HTTP_AUTHORIZATION"] = "Bearer valid.token.here"
            with self.assertRaisesRegex(
                exceptions.AuthenticationFailed, "Token has expired"
            ):
                self.auth.authenticate(request)

    def test_authenticate_general_exception(self):
        """Test authentication catching general Exception."""
        with patch(
            "apps.authn.authentication.jwt_service.decode_token",
            side_effect=Exception("Unknown error"),
        ):
            request = self.factory.get("/api/v1/test/")
            request.META["HTTP_AUTHORIZATION"] = "Bearer valid.token"
            with self.assertRaisesRegex(
                exceptions.AuthenticationFailed, "Authentication failed: Unknown error"
            ):
                self.auth.authenticate(request)
