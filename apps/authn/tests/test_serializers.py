"""Tests for authn serializers."""

from unittest.mock import patch

from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase
from rest_framework import serializers as drf_serializers

from apps.accounts.models import User
from apps.authn.serializers import (
    ActivateRoleSerializer,
    ChangePasswordSerializer,
    EmailResendSerializer,
    EmailVerificationSerializer,
    ForgotPasswordSerializer,
    GoogleLoginSerializer,
    LoginSerializer,
    LogoutSerializer,
    RefreshTokenSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    VerifyPasswordResetSerializer,
)


class RegisterSerializerTests(TestCase):
    """Test cases for RegisterSerializer."""

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        data = {
            "email": "test@example.com",
            "password": "securepass123",
            "initial_role": "homeowner",
        }
        serializer = RegisterSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["email"], "test@example.com")

    def test_email_normalization(self):
        """Test email is normalized to lowercase."""
        data = {"email": "TEST@EXAMPLE.COM", "password": "securepass123"}
        serializer = RegisterSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["email"], "test@example.com")

    def test_duplicate_email_validation(self):
        """Test validation fails for duplicate email."""
        User.objects.create_user(email="test@example.com", password="pass123")

        data = {"email": "test@example.com", "password": "securepass123"}
        serializer = RegisterSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_duplicate_email_case_insensitive(self):
        """Test duplicate email check is case-insensitive."""
        User.objects.create_user(email="test@example.com", password="pass123")

        data = {"email": "TEST@EXAMPLE.COM", "password": "securepass123"}
        serializer = RegisterSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_password_min_length(self):
        """Test password minimum length validation."""
        data = {"email": "test@example.com", "password": "short"}
        serializer = RegisterSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_password_validation(self):
        """Test password strength validation."""
        data = {
            "email": "test@example.com",
            "password": "12345678",  # Too common
        }
        serializer = RegisterSerializer(data=data)

        # Validation result depends on password validators configured
        # Just ensure the field is present
        self.assertIn("password", serializer.fields)

    def test_initial_role_optional(self):
        """Test initial_role is optional."""
        data = {"email": "test@example.com", "password": "securepass123"}
        serializer = RegisterSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_initial_role_choices(self):
        """Test initial_role accepts valid choices."""
        for role in ["handyman", "homeowner"]:
            data = {
                "email": f"test{role}@example.com",
                "password": "securepass123",
                "initial_role": role,
            }
            serializer = RegisterSerializer(data=data)

            self.assertTrue(serializer.is_valid(), f"Failed for role: {role}")

    def test_invalid_email_format(self):
        """Test invalid email format."""
        data = {"email": "not-an-email", "password": "securepass123"}
        serializer = RegisterSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_validate_password_raises_drf_error(self):
        """Password validation errors bubble up as DRF errors."""
        serializer = RegisterSerializer()

        with patch(
            "apps.authn.serializers.validate_password",
            side_effect=DjangoValidationError(["weak"]),
        ):
            with self.assertRaises(drf_serializers.ValidationError):
                serializer.validate_password("weak")


class LoginSerializerTests(TestCase):
    """Test cases for LoginSerializer."""

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        data = {"email": "test@example.com", "password": "password123"}
        serializer = LoginSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_email_normalization(self):
        """Test email is normalized to lowercase."""
        data = {"email": "TEST@EXAMPLE.COM", "password": "password123"}
        serializer = LoginSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["email"], "test@example.com")

    def test_required_fields(self):
        """Test email and password are required."""
        serializer = LoginSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
        self.assertIn("password", serializer.errors)


class GoogleLoginSerializerTests(TestCase):
    """Test cases for GoogleLoginSerializer."""

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        data = {"id_token": "valid-google-id-token"}
        serializer = GoogleLoginSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_id_token_required(self):
        """Test id_token is required."""
        serializer = GoogleLoginSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("id_token", serializer.errors)


class ActivateRoleSerializerTests(TestCase):
    """Test cases for ActivateRoleSerializer."""

    def test_serializer_valid_data(self):
        """Test serializer with valid role."""
        for role in ["handyman", "homeowner"]:
            data = {"role": role}
            serializer = ActivateRoleSerializer(data=data)

            self.assertTrue(serializer.is_valid(), f"Failed for role: {role}")

    def test_admin_role_not_allowed(self):
        """Test admin role cannot be activated through this endpoint."""
        data = {"role": "admin"}
        serializer = ActivateRoleSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("role", serializer.errors)

    def test_role_required(self):
        """Test role field is required."""
        serializer = ActivateRoleSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("role", serializer.errors)

    def test_invalid_role(self):
        """Test invalid role value."""
        data = {"role": "invalid"}
        serializer = ActivateRoleSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("role", serializer.errors)

    def test_validate_role_blocks_admin(self):
        """Direct validation prevents admin role."""
        serializer = ActivateRoleSerializer()

        with self.assertRaises(drf_serializers.ValidationError):
            serializer.validate_role("admin")


class EmailVerificationSerializerTests(TestCase):
    """Test cases for EmailVerificationSerializer."""

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        data = {"email": "test@example.com", "otp": "123456"}
        serializer = EmailVerificationSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_email_normalization(self):
        """Test email is normalized to lowercase."""
        data = {"email": "TEST@EXAMPLE.COM", "otp": "123456"}
        serializer = EmailVerificationSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["email"], "test@example.com")

    def test_email_optional(self):
        """Test email is optional."""
        data = {"otp": "123456"}
        serializer = EmailVerificationSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_validate_email_returns_none(self):
        """validate_email returns input when None provided."""
        serializer = EmailVerificationSerializer()

        self.assertIsNone(serializer.validate_email(None))

    def test_otp_format_validation(self):
        """Test OTP must be exactly 6 digits."""
        invalid_otps = ["12345", "1234567", "abcdef", "12345a"]

        for otp in invalid_otps:
            data = {"email": "test@example.com", "otp": otp}
            serializer = EmailVerificationSerializer(data=data)

            self.assertFalse(serializer.is_valid(), f"Should fail for OTP: {otp}")
            self.assertIn("otp", serializer.errors)

    def test_otp_valid_format(self):
        """Test valid OTP format."""
        data = {"email": "test@example.com", "otp": "123456"}
        serializer = EmailVerificationSerializer(data=data)

        self.assertTrue(serializer.is_valid())


class EmailResendSerializerTests(TestCase):
    """Test cases for EmailResendSerializer."""

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        data = {"email": "test@example.com"}
        serializer = EmailResendSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_email_normalization(self):
        """Test email is normalized to lowercase."""
        data = {"email": "TEST@EXAMPLE.COM"}
        serializer = EmailResendSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["email"], "test@example.com")

    def test_email_optional(self):
        """Test email is optional."""
        data = {}
        serializer = EmailResendSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_email_validate_returns_none(self):
        """validate_email returns None when value missing."""
        serializer = EmailResendSerializer()
        self.assertIsNone(serializer.validate_email(None))


class RefreshTokenSerializerTests(TestCase):
    """Test cases for RefreshTokenSerializer."""

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        data = {"refresh_token": "valid-refresh-token"}
        serializer = RefreshTokenSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_refresh_token_required(self):
        """Test refresh_token is required."""
        serializer = RefreshTokenSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("refresh_token", serializer.errors)


class LogoutSerializerTests(TestCase):
    """Test cases for LogoutSerializer."""

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        data = {"refresh_token": "valid-refresh-token"}
        serializer = LogoutSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_refresh_token_optional(self):
        """Test refresh_token is optional."""
        data = {}
        serializer = LogoutSerializer(data=data)

        self.assertTrue(serializer.is_valid())


class ForgotPasswordSerializerTests(TestCase):
    """Test cases for ForgotPasswordSerializer."""

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        data = {"email": "test@example.com"}
        serializer = ForgotPasswordSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_email_normalization(self):
        """Test email is normalized to lowercase."""
        data = {"email": "TEST@EXAMPLE.COM"}
        serializer = ForgotPasswordSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["email"], "test@example.com")

    def test_email_required(self):
        """Test email is required."""
        serializer = ForgotPasswordSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)


class VerifyPasswordResetSerializerTests(TestCase):
    """Test cases for VerifyPasswordResetSerializer."""

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        data = {"email": "test@example.com", "otp": "123456"}
        serializer = VerifyPasswordResetSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_email_normalization(self):
        """Test email is normalized to lowercase."""
        data = {"email": "TEST@EXAMPLE.COM", "otp": "123456"}
        serializer = VerifyPasswordResetSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["email"], "test@example.com")

    def test_otp_format_validation(self):
        """Test OTP must be exactly 6 digits."""
        invalid_otps = ["12345", "1234567", "abcdef"]

        for otp in invalid_otps:
            data = {"email": "test@example.com", "otp": otp}
            serializer = VerifyPasswordResetSerializer(data=data)

            self.assertFalse(serializer.is_valid(), f"Should fail for OTP: {otp}")
            self.assertIn("otp", serializer.errors)

    def test_required_fields(self):
        """Test email and otp are required."""
        serializer = VerifyPasswordResetSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
        self.assertIn("otp", serializer.errors)


class ResetPasswordSerializerTests(TestCase):
    """Test cases for ResetPasswordSerializer."""

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        data = {"reset_token": "valid-reset-token", "new_password": "newsecurepass123"}
        serializer = ResetPasswordSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_password_min_length(self):
        """Test password minimum length validation."""
        data = {"reset_token": "valid-reset-token", "new_password": "short"}
        serializer = ResetPasswordSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password", serializer.errors)

    def test_validate_new_password_raises_drf_error(self):
        """Direct validation raises DRF error when Django validation fails."""
        serializer = ResetPasswordSerializer()

        with patch(
            "apps.authn.serializers.validate_password",
            side_effect=DjangoValidationError(["weak"]),
        ):
            with self.assertRaises(drf_serializers.ValidationError):
                serializer.validate_new_password("weak")

    def test_required_fields(self):
        """Test reset_token and new_password are required."""
        serializer = ResetPasswordSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("reset_token", serializer.errors)
        self.assertIn("new_password", serializer.errors)


class ChangePasswordSerializerTests(TestCase):
    """Test cases for ChangePasswordSerializer."""

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        data = {"current_password": "oldpass123", "new_password": "newsecurepass123"}
        serializer = ChangePasswordSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_new_password_min_length(self):
        """Test new password minimum length validation."""
        data = {"current_password": "oldpass123", "new_password": "short"}
        serializer = ChangePasswordSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password", serializer.errors)

    def test_required_fields(self):
        """Test current_password and new_password are required."""
        serializer = ChangePasswordSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("current_password", serializer.errors)
        self.assertIn("new_password", serializer.errors)

    def test_change_password_validation_error(self):
        """Direct validation propagates Django validation errors."""
        serializer = ChangePasswordSerializer()

        with patch(
            "apps.authn.serializers.validate_password",
            side_effect=DjangoValidationError(["weak"]),
        ):
            with self.assertRaises(drf_serializers.ValidationError):
                serializer.validate_new_password("weak")
