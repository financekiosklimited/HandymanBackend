"""Tests for JWT service."""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import jwt
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from apps.accounts.models import User, UserRole
from apps.authn.jwt_service import JWTService
from apps.authn.models import RefreshSession

# Test keys for JWT (project keys)
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
    ACCESS_TOKEN_EXPIRE_MINUTES=15,
    REFRESH_TOKEN_EXPIRE_MINUTES=43200,
)
class JWTServiceTests(TestCase):
    """Test cases for JWTService."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.user.email_verified_at = datetime.now(UTC)
        self.user.save()

        UserRole.objects.create(user=self.user, role="homeowner")
        UserRole.objects.create(user=self.user, role="handyman")

        self.jwt_service = JWTService()

    def test_create_token_pair(self):
        """Test creating access and refresh token pair."""
        tokens = self.jwt_service.create_token_pair(
            user=self.user, platform="web", active_role="homeowner"
        )

        self.assertIn("access_token", tokens)
        self.assertIn("refresh_token", tokens)
        self.assertIn("token_type", tokens)
        self.assertEqual(tokens["token_type"], "bearer")

    def test_access_token_payload(self):
        """Test access token contains correct payload."""
        tokens = self.jwt_service.create_token_pair(
            user=self.user, platform="web", active_role="homeowner"
        )

        payload = self.jwt_service.decode_token(tokens["access_token"])

        self.assertEqual(payload["type"], "access")
        self.assertEqual(payload["sub"], str(self.user.public_id))
        self.assertEqual(payload["plat"], "web")
        self.assertEqual(payload["active_role"], "homeowner")
        self.assertEqual(payload["email_verified"], True)
        self.assertIn("homeowner", payload["roles"])
        self.assertIn("handyman", payload["roles"])
        self.assertIn("jti", payload)
        self.assertIn("iat", payload)
        self.assertIn("exp", payload)

    def test_refresh_token_payload(self):
        """Test refresh token contains correct payload."""
        tokens = self.jwt_service.create_token_pair(
            user=self.user, platform="web", active_role="homeowner"
        )

        payload = self.jwt_service.decode_token(tokens["refresh_token"])

        self.assertEqual(payload["type"], "refresh")
        self.assertEqual(payload["sub"], str(self.user.public_id))
        self.assertEqual(payload["plat"], "web")
        self.assertNotIn("active_role", payload)
        self.assertIn("jti", payload)

    def test_tokens_share_same_jti(self):
        """Test access and refresh tokens share the same JTI."""
        tokens = self.jwt_service.create_token_pair(
            user=self.user, platform="web", active_role="homeowner"
        )

        access_payload = self.jwt_service.decode_token(tokens["access_token"])
        refresh_payload = self.jwt_service.decode_token(tokens["refresh_token"])

        self.assertEqual(access_payload["jti"], refresh_payload["jti"])

    def test_refresh_session_created(self):
        """Test refresh session is created when generating tokens."""
        tokens = self.jwt_service.create_token_pair(
            user=self.user,
            platform="web",
            active_role="homeowner",
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
        )

        payload = self.jwt_service.decode_token(tokens["refresh_token"])
        session = RefreshSession.verify_session(payload["jti"], "web")

        self.assertIsNotNone(session)
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.platform, "web")
        self.assertEqual(session.user_agent, "Mozilla/5.0")
        self.assertEqual(session.ip_address, "192.168.1.1")

    def test_decode_valid_token(self):
        """Test decoding valid token."""
        tokens = self.jwt_service.create_token_pair(user=self.user, platform="web")

        payload = self.jwt_service.decode_token(tokens["access_token"])

        self.assertIsInstance(payload, dict)
        self.assertIn("sub", payload)

    def test_decode_expired_token(self):
        """Test decoding expired token raises error."""
        # Create token with very short expiry
        now = datetime.now(UTC)

        claims = {
            "sub": str(self.user.public_id),
            "type": "access",
            "exp": now - timedelta(seconds=10),
            "iat": now - timedelta(seconds=20),
            "nbf": now - timedelta(seconds=20),
        }

        token = jwt.encode(claims, TEST_PRIVATE_KEY, algorithm="RS256")

        with self.assertRaises(jwt.InvalidTokenError):
            self.jwt_service.decode_token(token)

    def test_decode_invalid_signature(self):
        """Test decoding token with invalid signature raises error."""
        tokens = self.jwt_service.create_token_pair(user=self.user, platform="web")

        # Tamper with the token
        token = tokens["access_token"] + "tampered"

        with self.assertRaises(jwt.InvalidTokenError):
            self.jwt_service.decode_token(token)

    def test_refresh_token_pair(self):
        """Test refreshing token pair."""
        # Create initial tokens
        tokens = self.jwt_service.create_token_pair(
            user=self.user, platform="web", active_role="homeowner"
        )

        # Refresh tokens
        new_tokens = self.jwt_service.refresh_token_pair(
            refresh_token=tokens["refresh_token"],
            platform="web",
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
        )

        self.assertIn("access_token", new_tokens)
        self.assertIn("refresh_token", new_tokens)
        self.assertNotEqual(tokens["access_token"], new_tokens["access_token"])
        self.assertNotEqual(tokens["refresh_token"], new_tokens["refresh_token"])

    def test_refresh_preserves_active_role(self):
        """Test refreshing preserves active role from user.active_role if available."""
        # Set active_role on user
        self.user.active_role = "homeowner"
        self.user.save()

        tokens = self.jwt_service.create_token_pair(
            user=self.user, platform="web", active_role="homeowner"
        )

        # Verify the original access token has the active role
        access_payload = self.jwt_service.decode_token(tokens["access_token"])
        self.assertEqual(access_payload["active_role"], "homeowner")

        new_tokens = self.jwt_service.refresh_token_pair(
            refresh_token=tokens["refresh_token"], platform="web"
        )

        new_payload = self.jwt_service.decode_token(new_tokens["access_token"])

        # After refresh, active_role should be preserved from user.active_role
        self.assertEqual(new_payload["active_role"], "homeowner")

    def test_refresh_revokes_old_session(self):
        """Test refreshing revokes old session."""
        tokens = self.jwt_service.create_token_pair(user=self.user, platform="web")

        old_payload = self.jwt_service.decode_token(tokens["refresh_token"])

        # Refresh tokens
        self.jwt_service.refresh_token_pair(
            refresh_token=tokens["refresh_token"], platform="web"
        )

        # Old session should be revoked
        old_session = RefreshSession.verify_session(old_payload["jti"], "web")

        self.assertIsNone(old_session)

    def test_refresh_with_access_token_fails(self):
        """Test refreshing with access token instead of refresh token fails."""
        tokens = self.jwt_service.create_token_pair(user=self.user, platform="web")

        with self.assertRaises(jwt.InvalidTokenError):
            self.jwt_service.refresh_token_pair(
                refresh_token=tokens["access_token"], platform="web"
            )

    def test_refresh_with_wrong_platform_fails(self):
        """Test refreshing with wrong platform fails."""
        tokens = self.jwt_service.create_token_pair(user=self.user, platform="web")

        with self.assertRaises(ValueError):
            self.jwt_service.refresh_token_pair(
                refresh_token=tokens["refresh_token"], platform="mobile"
            )

    def test_refresh_with_revoked_session_fails(self):
        """Test refreshing with revoked session fails."""
        tokens = self.jwt_service.create_token_pair(user=self.user, platform="web")

        payload = self.jwt_service.decode_token(tokens["refresh_token"])
        session = RefreshSession.verify_session(payload["jti"], "web")
        session.revoke()

        with self.assertRaises(ValueError):
            self.jwt_service.refresh_token_pair(
                refresh_token=tokens["refresh_token"], platform="web"
            )

    def test_revoke_refresh_token(self):
        """Test revoking refresh token."""
        tokens = self.jwt_service.create_token_pair(user=self.user, platform="web")

        payload = self.jwt_service.decode_token(tokens["refresh_token"])

        # Revoke token
        self.jwt_service.revoke_refresh_token(tokens["refresh_token"])

        # Session should be revoked
        session = RefreshSession.verify_session(payload["jti"], "web")

        self.assertIsNone(session)

    def test_revoke_invalid_token_doesnt_error(self):
        """Test revoking invalid token doesn't raise error."""
        # Should not raise an error
        self.jwt_service.revoke_refresh_token("invalid-token")

    def test_token_without_active_role(self):
        """Test creating tokens without active role."""
        tokens = self.jwt_service.create_token_pair(
            user=self.user, platform="web", active_role=None
        )

        payload = self.jwt_service.decode_token(tokens["access_token"])

        self.assertIsNone(payload["active_role"])

    def test_unverified_email_in_token(self):
        """Test token reflects unverified email status."""
        self.user.email_verified_at = None
        self.user.save()

        tokens = self.jwt_service.create_token_pair(user=self.user, platform="web")

        payload = self.jwt_service.decode_token(tokens["access_token"])

        self.assertFalse(payload["email_verified"])

    def test_different_platforms(self):
        """Test creating tokens for different platforms."""
        for platform in ["web", "mobile", "admin"]:
            tokens = self.jwt_service.create_token_pair(
                user=self.user, platform=platform
            )

            payload = self.jwt_service.decode_token(tokens["access_token"])

            self.assertEqual(payload["plat"], platform)

    @override_settings(JWT_AUDIENCE="test-audience")
    def test_token_with_audience(self):
        """Test creating token with audience claim."""
        local_jwt_service = JWTService()

        tokens = local_jwt_service.create_token_pair(user=self.user, platform="web")

        payload = local_jwt_service.decode_token(tokens["access_token"])

        self.assertEqual(payload["aud"], "test-audience")

    def test_nbf_leeway(self):
        """Test not-before claim has leeway."""
        tokens = self.jwt_service.create_token_pair(user=self.user, platform="web")

        payload = self.jwt_service.decode_token(tokens["access_token"])

        # nbf should be slightly in the past (leeway)
        iat = datetime.fromtimestamp(payload["iat"], UTC)
        nbf = datetime.fromtimestamp(payload["nbf"], UTC)

        self.assertLess(nbf, iat)

    @override_settings(JWT_PRIVATE_KEY=None, JWT_PRIVATE_KEY_PATH=None)
    def test_private_key_missing_raises_error(self):
        """Accessing private_key without configuration raises error."""
        service = JWTService()
        service._private_key = None

        with self.assertRaises(ImproperlyConfigured):
            _ = service.private_key

    @override_settings(JWT_PUBLIC_KEY=None, JWT_PUBLIC_KEY_PATH=None)
    def test_public_key_missing_raises_error(self):
        """Accessing public_key without configuration raises error."""
        service = JWTService()
        service._public_key = None

        with self.assertRaises(ImproperlyConfigured):
            _ = service.public_key

    def test_create_token_pair_with_audience(self):
        """Audience claim included when attribute set directly."""
        self.jwt_service._audience = "audience"
        tokens = self.jwt_service.create_token_pair(user=self.user, platform="web")
        payload = self.jwt_service.decode_token(tokens["access_token"])

        self.assertEqual(payload["aud"], "audience")

    def test_create_token_pair_without_audience(self):
        """Audience claim omitted when attribute is falsy."""
        self.jwt_service._audience = None
        tokens = self.jwt_service.create_token_pair(user=self.user, platform="web")
        payload = self.jwt_service.decode_token(tokens["access_token"])

        self.assertNotIn("aud", payload)

    def test_private_key_loaded_from_path(self):
        """Private key is read from configured file path when not cached."""
        tmp_path = Path(self._create_temp_key_file(TEST_PRIVATE_KEY))

        with override_settings(
            JWT_PRIVATE_KEY=None, JWT_PRIVATE_KEY_PATH=str(tmp_path)
        ):
            service = JWTService()
            service._private_key = None
            self.assertEqual(service.private_key.strip(), TEST_PRIVATE_KEY.strip())

    def test_public_key_loaded_from_path(self):
        """Public key is read from configured file path when not cached."""
        tmp_path = Path(self._create_temp_key_file(TEST_PUBLIC_KEY))

        with override_settings(JWT_PUBLIC_KEY=None, JWT_PUBLIC_KEY_PATH=str(tmp_path)):
            service = JWTService()
            service._public_key = None
            self.assertEqual(service.public_key.strip(), TEST_PUBLIC_KEY.strip())

    def test_decode_invalid_audience(self):
        """Invalid audience raises InvalidTokenError."""
        local_service = JWTService()
        local_service._audience = "expected"

        claims = {
            "sub": str(self.user.public_id),
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "iat": datetime.now(UTC),
            "nbf": datetime.now(UTC),
            "aud": "other",
        }
        token = jwt.encode(claims, TEST_PRIVATE_KEY, algorithm="RS256")

        with self.assertRaises(jwt.InvalidTokenError):
            local_service.decode_token(token)

    def test_refresh_clears_missing_active_role(self):
        """Refresh drops active role when user no longer has it."""
        payload = {"type": "refresh", "jti": "abc", "active_role": "homeowner"}
        session = MagicMock()
        session.platform = "web"
        session.user = SimpleNamespace(has_role=lambda role: False)

        with (
            patch.object(self.jwt_service, "decode_token", return_value=payload),
            patch(
                "apps.authn.jwt_service.RefreshSession.verify_session",
                return_value=session,
            ),
            patch.object(
                self.jwt_service,
                "create_token_pair",
                return_value={"access_token": "a", "refresh_token": "b"},
            ) as mock_create,
        ):
            result = self.jwt_service.refresh_token_pair("token", platform="web")

        mock_create.assert_called_once()
        kwargs = mock_create.call_args.kwargs
        self.assertIsNone(kwargs["active_role"])
        self.assertEqual(result["access_token"], "a")

    def test_refresh_platform_mismatch_raises(self):
        """Refresh raises ValueError when session platform differs."""
        payload = {"type": "refresh", "jti": "abc"}
        session = MagicMock()
        session.platform = "mobile"
        session.user = self.user

        with (
            patch.object(self.jwt_service, "decode_token", return_value=payload),
            patch(
                "apps.authn.jwt_service.RefreshSession.verify_session",
                return_value=session,
            ),
        ):
            with self.assertRaises(ValueError):
                self.jwt_service.refresh_token_pair("token", platform="web")

    def test_revoke_refresh_token_non_refresh_payload(self):
        """Revoke ignores tokens that are not refresh tokens."""
        with patch.object(
            self.jwt_service, "decode_token", return_value={"type": "access"}
        ) as mock_decode:
            self.jwt_service.revoke_refresh_token("token")

        mock_decode.assert_called_once_with("token")

    def test_revoke_refresh_token_without_session(self):
        """Revoke handles missing refresh session gracefully."""
        payload = {"type": "refresh", "jti": "abc"}

        manager_mock = MagicMock()
        manager_mock.filter.return_value.first.return_value = None

        with (
            patch.object(self.jwt_service, "decode_token", return_value=payload),
            patch("apps.authn.jwt_service.RefreshSession.objects", manager_mock),
        ):
            self.jwt_service.revoke_refresh_token("token")

        manager_mock.filter.assert_called_once()

    def _create_temp_key_file(self, content):
        """Write PEM content to a temporary file and return its path."""
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write(content)
            file_path = Path(tmp.name)

        self.addCleanup(lambda: file_path.unlink(missing_ok=True))
        return str(file_path)
