"""
Serializers for authentication endpoints.
"""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers

from apps.common.serializers import create_response_serializer

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    """
    Serializer for user registration.
    """

    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    initial_role = serializers.ChoiceField(
        choices=["handyman", "customer"], required=False, allow_null=True
    )

    def validate_email(self, value):
        """Validate email is not already taken."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_password(self, value):
        """Validate password strength."""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """

    email = serializers.EmailField()
    password = serializers.CharField()

    def validate_email(self, value):
        """Normalize email for case-insensitive lookup."""
        return value.lower()


class GoogleLoginSerializer(serializers.Serializer):
    """
    Serializer for Google OAuth login.
    """

    id_token = serializers.CharField()


class ActivateRoleSerializer(serializers.Serializer):
    """
    Serializer for role activation.
    """

    role = serializers.ChoiceField(choices=["handyman", "customer"])

    def validate_role(self, value):
        """Validate user cannot activate admin role."""
        if value == "admin":
            raise serializers.ValidationError(
                "Admin role activation is not allowed through this endpoint."
            )
        return value


class EmailVerificationSerializer(serializers.Serializer):
    """
    Serializer for email verification.
    """

    email = serializers.EmailField(
        required=False,
        allow_null=True,
        help_text="Email address (can be omitted if authenticated)",
    )
    otp = serializers.CharField()

    def validate_otp(self, value):
        """Validate OTP format."""
        if not re.match(r"^[0-9]{6}$", value):
            raise serializers.ValidationError("OTP must be exactly 6 digits.")
        return value

    def validate_email(self, value):
        """Normalize email."""
        if value:
            return value.lower()
        return value


class EmailResendSerializer(serializers.Serializer):
    """
    Serializer for email resend.
    """

    email = serializers.EmailField(required=False, allow_null=True)

    def validate_email(self, value):
        """Normalize email if provided."""
        if value:
            return value.lower()
        return value


class RefreshTokenSerializer(serializers.Serializer):
    """
    Serializer for token refresh.
    """

    refresh_token = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    """
    Serializer for logout.
    """

    refresh_token = serializers.CharField(required=False, allow_null=True)


class ForgotPasswordSerializer(serializers.Serializer):
    """
    Serializer for forgot password.
    """

    email = serializers.EmailField()

    def validate_email(self, value):
        """Normalize email."""
        return value.lower()


class VerifyPasswordResetSerializer(serializers.Serializer):
    """
    Serializer for password reset code verification.
    """

    email = serializers.EmailField()
    otp = serializers.CharField()

    def validate_otp(self, value):
        """Validate OTP format."""
        if not re.match(r"^[0-9]{6}$", value):
            raise serializers.ValidationError("OTP must be exactly 6 digits.")
        return value

    def validate_email(self, value):
        """Normalize email."""
        return value.lower()


class ResetPasswordSerializer(serializers.Serializer):
    """
    Serializer for password reset.
    """

    reset_token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate_new_password(self, value):
        """Validate new password strength."""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change.
    """

    current_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate_new_password(self, value):
        """Validate new password strength."""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


# Response serializers
class TokenResponseSerializer(serializers.Serializer):
    """
    Serializer for token response.
    """

    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField(default="bearer")
    next_action = serializers.CharField(
        allow_null=True,
        help_text="Next action user should take (verify_email, activate_role, fill_profile, none)",
    )
    email_verified = serializers.BooleanField(
        help_text="Whether user's email is verified"
    )


class AuthResponseSerializer(serializers.Serializer):
    """
    Extended auth response with additional fields.
    """

    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField(default="bearer")
    active_role = serializers.CharField(allow_null=True)
    email_verified = serializers.BooleanField()
    next_action = serializers.CharField(allow_null=True)


class PasswordResetTokenResponseSerializer(serializers.Serializer):
    """
    Serializer for password reset token response.
    """

    reset_token = serializers.CharField()
    expires_in = serializers.IntegerField(help_text="Expiry time in seconds")


class SuccessMessageResponseSerializer(serializers.Serializer):
    """
    Serializer for success responses with just a message.
    """

    message = serializers.CharField()
    data = serializers.JSONField(allow_null=True, default=None)
    errors = serializers.JSONField(allow_null=True, default=None)
    meta = serializers.JSONField(allow_null=True, required=False)


# Response wrappers for authentication endpoints
TokenResponseEnvelope = create_response_serializer(
    TokenResponseSerializer, "TokenResponseEnvelope"
)

AuthResponseEnvelope = create_response_serializer(
    AuthResponseSerializer, "AuthResponseEnvelope"
)

PasswordResetTokenResponseEnvelope = create_response_serializer(
    PasswordResetTokenResponseSerializer, "PasswordResetTokenResponseEnvelope"
)
