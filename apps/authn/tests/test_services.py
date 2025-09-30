"""Tests for auth service."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.accounts.models import User, UserRole
from apps.authn.models import (
    EmailVerificationToken,
    PasswordResetCode,
    PasswordResetToken,
    RefreshSession,
)
from apps.authn.services import AuthService
from apps.profiles.models import CustomerProfile, HandymanProfile

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
class AuthServiceTests(TestCase):
    """Test cases for AuthService."""

    def setUp(self):
        """Set up test data."""
        self.service = AuthService()

    @patch("apps.authn.services.email_service.send_email_verification")
    def test_register_user(self, mock_send_email):
        """Test registering a new user."""
        tokens = self.service.register_user(
            email="test@example.com",
            password="securepass123",
            initial_role="customer",
            platform="web",
        )

        # Check user created
        user = User.objects.get(email="test@example.com")
        self.assertTrue(user.check_password("securepass123"))
        self.assertTrue(user.is_active)

        # Check role created
        self.assertTrue(user.roles.filter(role="customer").exists())

        # Check profile created
        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())

        # Check tokens returned
        self.assertIn("access_token", tokens)
        self.assertIn("refresh_token", tokens)

        # Check email verification sent
        mock_send_email.assert_called_once()

    @patch("apps.authn.services.email_service.send_email_verification")
    def test_register_user_without_initial_role(self, mock_send_email):
        """Test registering user without initial role."""
        tokens = self.service.register_user(
            email="test@example.com", password="securepass123", platform="web"
        )

        user = User.objects.get(email="test@example.com")

        # No roles should be created
        self.assertFalse(user.roles.exists())

        # Tokens should still be returned
        self.assertIn("access_token", tokens)
        self.assertIn("refresh_token", tokens)

        # Email verification should still be sent
        mock_send_email.assert_called_once()

    @patch("apps.authn.services.email_service.send_email_verification")
    def test_register_user_creates_handyman_profile(self, mock_send_email):
        """Test registering user with handyman role creates profile."""
        tokens = self.service.register_user(
            email="handyman@example.com",
            password="securepass123",
            initial_role="handyman",
            platform="web",
        )

        user = User.objects.get(email="handyman@example.com")

        # Check handyman profile created
        self.assertTrue(HandymanProfile.objects.filter(user=user).exists())

        # Tokens should still be returned
        self.assertIn("access_token", tokens)
        self.assertIn("refresh_token", tokens)

    def test_login_user_success(self):
        """Test successful user login."""
        User.objects.create_user(email="test@example.com", password="securepass123")

        tokens = self.service.login_user(
            email="test@example.com", password="securepass123", platform="web"
        )

        self.assertIsNotNone(tokens)
        self.assertIn("access_token", tokens)
        self.assertIn("refresh_token", tokens)

    def test_login_user_wrong_password(self):
        """Test login with wrong password."""
        User.objects.create_user(email="test@example.com", password="securepass123")

        tokens = self.service.login_user(
            email="test@example.com", password="wrongpassword", platform="web"
        )

        self.assertIsNone(tokens)

    def test_login_user_nonexistent(self):
        """Test login with nonexistent user."""
        tokens = self.service.login_user(
            email="nonexistent@example.com", password="password123", platform="web"
        )

        self.assertIsNone(tokens)

    def test_login_inactive_user(self):
        """Test login with inactive user."""
        user = User.objects.create_user(
            email="test@example.com", password="securepass123"
        )
        user.is_active = False
        user.save()

        tokens = self.service.login_user(
            email="test@example.com", password="securepass123", platform="web"
        )

        self.assertIsNone(tokens)

    def test_activate_role_new_role(self):
        """Test activating a new role."""
        user = User.objects.create_user(
            email="test@example.com", password="securepass123"
        )

        result = self.service.activate_role(user, "customer")

        # Check role created
        self.assertTrue(user.roles.filter(role="customer").exists())

        # Check profile created
        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())

        # Check result
        self.assertEqual(result["role"], "customer")
        self.assertEqual(result["next_action"], "verify_email")

    def test_activate_role_existing_role(self):
        """Test activating an existing role."""
        user = User.objects.create_user(
            email="test@example.com", password="securepass123"
        )
        UserRole.objects.create(user=user, role="customer")
        CustomerProfile.objects.create(user=user, display_name="Test")

        result = self.service.activate_role(user, "customer")

        # Should not create duplicate role
        self.assertEqual(user.roles.filter(role="customer").count(), 1)
        self.assertEqual(result["next_action"], "verify_email")

    def test_activate_role_verified_email(self):
        """Test activating role with verified email."""
        user = User.objects.create_user(
            email="test@example.com", password="securepass123"
        )
        user.email_verified_at = datetime.now(UTC)
        user.save()

        UserRole.objects.create(user=user, role="customer")
        CustomerProfile.objects.create(user=user, display_name="Test")

        result = self.service.activate_role(user, "customer")

        # Next action should be none since email is verified and profile complete
        self.assertEqual(result["next_action"], "none")

    def test_activate_role_requires_profile_completion(self):
        """Verified user with empty profile should fill profile next."""
        user = User.objects.create_user(
            email="fill@example.com", password="securepass123"
        )
        user.email_verified_at = datetime.now(UTC)
        user.save()

        UserRole.objects.create(user=user, role="customer")
        CustomerProfile.objects.create(user=user, display_name="")

        result = self.service.activate_role(user, "customer")

        self.assertEqual(result["next_action"], "fill_profile")

    def test_verify_email(self):
        """Test email verification."""
        user = User.objects.create_user(
            email="test@example.com", password="securepass123"
        )
        token, otp = EmailVerificationToken.create_for_user(user)

        verified_user = self.service.verify_email("test@example.com", otp)

        self.assertEqual(verified_user, user)
        user.refresh_from_db()
        self.assertIsNotNone(user.email_verified_at)

    def test_verify_email_invalid_otp(self):
        """Test email verification with invalid OTP."""
        user = User.objects.create_user(
            email="test@example.com", password="securepass123"
        )

        verified_user = self.service.verify_email("test@example.com", "000000")

        self.assertIsNone(verified_user)
        user.refresh_from_db()
        self.assertIsNone(user.email_verified_at)

    def test_get_next_action_unverified_email(self):
        """Test next action for unverified email."""
        user = User.objects.create_user(
            email="test@example.com", password="securepass123"
        )

        next_action = self.service.get_next_action_for_user(user)

        self.assertEqual(next_action, "verify_email")

    def test_get_next_action_no_roles(self):
        """Test next action when user has no roles."""
        user = User.objects.create_user(
            email="test@example.com", password="securepass123"
        )
        user.email_verified_at = datetime.now(UTC)
        user.save()

        next_action = self.service.get_next_action_for_user(user)

        self.assertEqual(next_action, "activate_role")

    def test_get_next_action_incomplete_profile(self):
        """Test next action when profile is incomplete."""
        user = User.objects.create_user(
            email="test@example.com", password="securepass123"
        )
        user.email_verified_at = datetime.now(UTC)
        user.save()

        UserRole.objects.create(user=user, role="customer")
        # Create profile without display_name
        CustomerProfile.objects.create(user=user, display_name="")

        next_action = self.service.get_next_action_for_user(user)

        self.assertEqual(next_action, "fill_profile")

    def test_get_next_action_complete(self):
        """Test next action when everything is complete."""
        user = User.objects.create_user(
            email="test@example.com", password="securepass123"
        )
        user.email_verified_at = datetime.now(UTC)
        user.save()

        UserRole.objects.create(user=user, role="customer")
        CustomerProfile.objects.create(user=user, display_name="Test User")

        next_action = self.service.get_next_action_for_user(user)

        self.assertEqual(next_action, "none")

    @patch("apps.authn.services.email_service.send_email_verification")
    def test_resend_email_verification(self, mock_send_email):
        """Test resending email verification."""
        user = User.objects.create_user(
            email="test@example.com", password="securepass123"
        )

        # Create old token
        old_token, _ = EmailVerificationToken.create_for_user(user)

        self.service.resend_email_verification(user)

        # Old token should be deleted
        self.assertFalse(
            EmailVerificationToken.objects.filter(id=old_token.id).exists()
        )

        # New token should exist
        self.assertTrue(
            EmailVerificationToken.objects.filter(
                user=user, used_at__isnull=True
            ).exists()
        )

        mock_send_email.assert_called_once()

    @patch("apps.authn.services.email_service.send_password_reset_code")
    def test_forgot_password(self, mock_send_email):
        """Test forgot password flow."""
        user = User.objects.create_user(
            email="test@example.com", password="securepass123"
        )

        self.service.forgot_password("test@example.com")

        # Check code was created
        self.assertTrue(
            PasswordResetCode.objects.filter(
                user=user, verified_at__isnull=True
            ).exists()
        )

        mock_send_email.assert_called_once()

    @patch("apps.authn.services.email_service.send_password_reset_code")
    def test_forgot_password_nonexistent_user(self, mock_send_email):
        """Test forgot password for nonexistent user."""
        # Should not raise error (for security)
        self.service.forgot_password("nonexistent@example.com")

        # Email should not be sent
        mock_send_email.assert_not_called()

    def test_verify_password_reset_code(self):
        """Test verifying password reset code."""
        user = User.objects.create_user(
            email="test@example.com", password="securepass123"
        )
        code, otp = PasswordResetCode.create_for_user(user)

        result = self.service.verify_password_reset_code("test@example.com", otp)

        self.assertIsNotNone(result)
        self.assertIn("reset_token", result)
        self.assertIn("expires_in", result)

    def test_verify_password_reset_code_invalid(self):
        """Test verifying invalid reset code."""
        result = self.service.verify_password_reset_code("test@example.com", "000000")

        self.assertIsNone(result)

    def test_reset_password(self):
        """Test resetting password."""
        user = User.objects.create_user(email="test@example.com", password="oldpass123")
        token_obj, token = PasswordResetToken.create_for_user(user)

        success = self.service.reset_password(token, "newpass123")

        self.assertTrue(success)
        user.refresh_from_db()
        self.assertTrue(user.check_password("newpass123"))

    def test_reset_password_revokes_sessions(self):
        """Test resetting password revokes all refresh sessions."""
        user = User.objects.create_user(email="test@example.com", password="oldpass123")

        # Create some sessions
        RefreshSession.create_session(user=user, platform="web", jti="jti1")
        RefreshSession.create_session(user=user, platform="mobile", jti="jti2")

        token_obj, token = PasswordResetToken.create_for_user(user)
        self.service.reset_password(token, "newpass123")

        # All sessions should be revoked
        active_sessions = RefreshSession.objects.filter(
            user=user, revoked_at__isnull=True
        )
        self.assertEqual(active_sessions.count(), 0)

    def test_reset_password_invalid_token(self):
        """Test resetting password with invalid token."""
        success = self.service.reset_password("invalid-token", "newpass123")

        self.assertFalse(success)

    def test_change_password(self):
        """Test changing password."""
        user = User.objects.create_user(email="test@example.com", password="oldpass123")

        success = self.service.change_password(user, "oldpass123", "newpass123")

        self.assertTrue(success)
        user.refresh_from_db()
        self.assertTrue(user.check_password("newpass123"))

    def test_change_password_wrong_current_password(self):
        """Test changing password with wrong current password."""
        user = User.objects.create_user(email="test@example.com", password="oldpass123")

        success = self.service.change_password(user, "wrongpass", "newpass123")

        self.assertFalse(success)

    def test_change_password_revokes_sessions(self):
        """Test changing password revokes all refresh sessions."""
        user = User.objects.create_user(email="test@example.com", password="oldpass123")

        # Create sessions
        RefreshSession.create_session(user=user, platform="web", jti="jti1")

        self.service.change_password(user, "oldpass123", "newpass123")

        # Sessions should be revoked
        active_sessions = RefreshSession.objects.filter(
            user=user, revoked_at__isnull=True
        )
        self.assertEqual(active_sessions.count(), 0)

    def test_has_complete_profile_customer(self):
        """Test checking complete profile for customer."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        # Incomplete profile
        CustomerProfile.objects.create(user=user, display_name="")
        self.assertFalse(self.service._has_complete_profile(user, "customer"))

        # Complete profile
        user.customer_profile.display_name = "Test User"
        user.customer_profile.save()
        self.assertTrue(self.service._has_complete_profile(user, "customer"))

    def test_has_complete_profile_handyman(self):
        """Test checking complete profile for handyman."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        # Incomplete profile
        HandymanProfile.objects.create(user=user, display_name="")
        self.assertFalse(self.service._has_complete_profile(user, "handyman"))

        # Complete profile
        user.handyman_profile.display_name = "Test Handyman"
        user.handyman_profile.save()
        self.assertTrue(self.service._has_complete_profile(user, "handyman"))

    def test_has_complete_profile_admin(self):
        """Test checking complete profile for admin (always complete)."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        # Admin role doesn't require profile
        self.assertTrue(self.service._has_complete_profile(user, "admin"))
    def test_google_login_existing_user_sets_google_sub(self):
        """Existing user receives google_sub and verification timestamp."""
        user = User.objects.create_user(
            email="demo@example.com", password="securepass123", google_sub=None
        )

        with patch(
            "apps.authn.services.jwt_service.create_token_pair",
            return_value={"access_token": "a", "refresh_token": "r"},
        ):
            tokens = self.service.google_login(id_token="ignored", platform="web")

        user.refresh_from_db()
        self.assertEqual(user.google_sub, "google_user_id")
        self.assertIsNotNone(user.email_verified_at)
        self.assertIn("access_token", tokens)

    def test_google_login_existing_user_retains_google_sub(self):
        """Existing google_sub should not be overwritten."""
        user = User.objects.create_user(
            email="demo@example.com", password="securepass123", google_sub="existing"
        )

        with patch(
            "apps.authn.services.jwt_service.create_token_pair",
            return_value={"access_token": "a", "refresh_token": "r"},
        ):
            self.service.google_login(id_token="ignored", platform="web")

        user.refresh_from_db()
        self.assertEqual(user.google_sub, "existing")

    def test_google_login_creates_new_user(self):
        """New Google user is created with profile and role."""
        with patch(
            "apps.authn.services.jwt_service.create_token_pair",
            return_value={"access_token": "a", "refresh_token": "r"},
        ):
            tokens = self.service.google_login(id_token="ignored", platform="mobile")

        user = User.objects.get(email="demo@example.com")
        self.assertTrue(user.is_email_verified)
        self.assertTrue(UserRole.objects.filter(user=user, role="customer").exists())
        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())
        self.assertIn("access_token", tokens)

    def test_google_login_errors_wrapped(self):
        """Underlying errors raise ValueError with helpful message."""
        with patch("apps.authn.services.User.objects.get", side_effect=RuntimeError("boom")):
            with self.assertRaisesRegex(ValueError, "Google authentication failed: boom"):
                self.service.google_login(id_token="ignored", platform="web")

    @patch("apps.authn.services.EmailVerificationToken.verify_otp")
    def test_verify_email_sets_fill_profile(self, mock_verify):
        """Roles awaiting verification move to fill_profile when incomplete."""
        user = User.objects.create_user(
            email="fill@example.com", password="securepass123"
        )
        role = UserRole.objects.create(user=user, role="customer", next_action="verify_email")
        CustomerProfile.objects.create(user=user, display_name="")
        mock_verify.return_value = user

        self.service.verify_email(user.email, "123456")

        role.refresh_from_db()
        self.assertEqual(role.next_action, "fill_profile")

    @patch("apps.authn.services.EmailVerificationToken.verify_otp")
    def test_verify_email_sets_none_when_complete(self, mock_verify):
        """Roles become none when profile already complete."""
        user = User.objects.create_user(
            email="complete@example.com", password="securepass123"
        )
        role = UserRole.objects.create(user=user, role="customer", next_action="verify_email")
        CustomerProfile.objects.create(user=user, display_name="Ready")
        mock_verify.return_value = user

        self.service.verify_email(user.email, "123456")

        role.refresh_from_db()
        self.assertEqual(role.next_action, "none")

    @patch("apps.authn.services.EmailVerificationToken.verify_otp")
    def test_verify_email_leaves_other_roles_unchanged(self, mock_verify):
        """Roles not waiting on verification remain untouched."""
        user = User.objects.create_user(
            email="other@example.com", password="securepass123"
        )
        role = UserRole.objects.create(user=user, role="customer", next_action="fill_profile")
        CustomerProfile.objects.create(user=user, display_name="In progress")
        mock_verify.return_value = user

        self.service.verify_email(user.email, "123456")

        role.refresh_from_db()
        self.assertEqual(role.next_action, "fill_profile")

    def test_create_profile_for_role_customer(self):
        """Customer profile helper creates profile when missing."""
        user = User.objects.create_user(email="customer@example.com", password="securepass123")
        CustomerProfile.objects.filter(user=user).delete()

        self.service._create_profile_for_role(user, "customer")

        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())
    def test_google_login_existing_user_retains_google_sub(self):
        """Existing google_sub value remains when already set."""
        user = User.objects.create_user(
            email="demo@example.com", password="securepass123", google_sub="existing"
        )

        with patch("apps.authn.services.jwt_service.create_token_pair", return_value={"access_token": "a", "refresh_token": "r"}):
            self.service.google_login(id_token="ignored", platform="web")

        user.refresh_from_db()
        self.assertEqual(user.google_sub, "existing")

    @patch("apps.authn.services.EmailVerificationToken.verify_otp")
    def test_verify_email_leaves_other_roles_unchanged(self, mock_verify):
        """Roles not waiting for verification remain untouched."""
        user = User.objects.create_user(
            email="other@example.com", password="securepass123"
        )
        role = UserRole.objects.create(user=user, role="customer", next_action="fill_profile")
        CustomerProfile.objects.create(user=user, display_name="Done")
        mock_verify.return_value = user

        self.service.verify_email(user.email, "123456")

        role.refresh_from_db()
        self.assertEqual(role.next_action, "fill_profile")

    def test_create_profile_for_role_customer(self):
        """Helper creates customer profile when missing."""
        user = User.objects.create_user(
            email="customer@example.com", password="securepass123"
        )

        self.service._create_profile_for_role(user, "customer")

        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())

    def test_create_profile_for_role_admin_noop(self):
        """Admin role does not create a profile."""
        user = User.objects.create_user(email="admin@example.com", password="securepass123")

        self.service._create_profile_for_role(user, "admin")

        self.assertFalse(CustomerProfile.objects.filter(user=user).exists())
        self.assertFalse(HandymanProfile.objects.filter(user=user).exists())

    def test_has_complete_profile_without_customer_profile(self):
        """Missing customer profile results in incomplete status."""
        user = SimpleNamespace()

        self.assertFalse(self.service._has_complete_profile(user, "customer"))

    def test_has_complete_profile_admin_attribute_error(self):
        """Admin role remains complete even if attribute access fails."""

        class ExplodingRole(str):
            def __new__(cls, value):
                obj = super().__new__(cls, value)
                obj._raise_once = True
                return obj

            def __eq__(self, other):
                if other == "admin" and getattr(self, "_raise_once", False):
                    self._raise_once = False
                    raise AttributeError("boom")
                return super().__eq__(other)

        role = ExplodingRole("admin")
        user = User.objects.create_user(email="admin2@example.com", password="pass123")

        self.assertTrue(self.service._has_complete_profile(user, role))

    def test_has_complete_profile_unknown_role(self):
        """Unknown role falls back to False."""
        user = SimpleNamespace()

        self.assertFalse(self.service._has_complete_profile(user, "unknown"))
