"""
Authentication-related models for tokens and sessions.
"""

import hashlib
import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel


class EmailVerificationToken(BaseModel):
    """
    Email verification tokens (6-digit OTP).
    """

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "email_verification_tokens"
        ordering = ["-created_at"]

    @classmethod
    def create_for_user(cls, user, ttl_hours=24):
        """Create a new email verification token for user."""
        # Generate 6-digit OTP
        otp = f"{secrets.randbelow(1000000):06d}"
        token_hash = hashlib.sha256(otp.encode()).hexdigest()

        # Create token
        token = cls.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=timezone.now() + timedelta(hours=ttl_hours),
        )

        # Return both token object and plain OTP
        return token, otp

    @classmethod
    def verify_otp(cls, email, otp):
        """Verify OTP for email and return user if valid."""
        token_hash = hashlib.sha256(otp.encode()).hexdigest()

        try:
            token = cls.objects.select_related("user").get(
                user__email=email,
                token_hash=token_hash,
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            )

            # Mark as used
            token.used_at = timezone.now()
            token.save()

            return token.user
        except cls.DoesNotExist:
            return None

    def is_valid(self):
        """Check if token is still valid."""
        return self.used_at is None and self.expires_at > timezone.now()


class PasswordResetCode(BaseModel):
    """
    Password reset codes (6-digit OTP, short TTL).
    """

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    code_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "password_reset_codes"
        ordering = ["-created_at"]

    @classmethod
    def create_for_user(cls, user, ttl_minutes=10):
        """Create a new password reset code for user."""
        # Generate 6-digit OTP
        otp = f"{secrets.randbelow(1000000):06d}"
        code_hash = hashlib.sha256(otp.encode()).hexdigest()

        # Create code
        code = cls.objects.create(
            user=user,
            code_hash=code_hash,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )

        # Return both code object and plain OTP
        return code, otp

    @classmethod
    def verify_code(cls, email, otp):
        """Verify reset code for email and mark as verified."""
        code_hash = hashlib.sha256(otp.encode()).hexdigest()

        try:
            code = cls.objects.select_related("user").get(
                user__email=email,
                code_hash=code_hash,
                verified_at__isnull=True,
                expires_at__gt=timezone.now(),
            )

            # Mark as verified
            code.verified_at = timezone.now()
            code.save()

            return code
        except cls.DoesNotExist:
            return None


class PasswordResetToken(BaseModel):
    """
    Password reset tokens (after code verification, longer TTL).
    """

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "password_reset_tokens"
        ordering = ["-created_at"]

    @classmethod
    def create_for_user(cls, user, ttl_minutes=15):
        """Create a new password reset token for user."""
        # Generate random token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Create token
        reset_token = cls.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )

        # Return both token object and plain token
        return reset_token, token

    @classmethod
    def verify_token(cls, token):
        """Verify reset token and return user if valid."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        try:
            reset_token = cls.objects.select_related("user").get(
                token_hash=token_hash,
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            )

            # Mark as used
            reset_token.used_at = timezone.now()
            reset_token.save()

            return reset_token.user
        except cls.DoesNotExist:
            return None


class RefreshSession(BaseModel):
    """
    Refresh token sessions for JWT token rotation.
    """

    PLATFORM_CHOICES = [
        ("admin", "Admin"),
        ("web", "Web"),
        ("mobile", "Mobile"),
    ]

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="refresh_sessions"
    )
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES)
    jti_hash = models.CharField(max_length=64, unique=True)  # Hash of JWT ID
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "refresh_sessions"
        ordering = ["-created_at"]

    @classmethod
    def create_session(
        cls, user, platform, jti, user_agent="", ip_address=None, ttl_minutes=43200
    ):
        """Create a new refresh session."""
        jti_hash = hashlib.sha256(str(jti).encode()).hexdigest()

        return cls.objects.create(
            user=user,
            platform=platform,
            jti_hash=jti_hash,
            user_agent=user_agent[:1000],  # Limit length
            ip_address=ip_address,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )

    @classmethod
    def verify_session(cls, jti, platform):
        """Verify refresh session by JTI and platform."""
        jti_hash = hashlib.sha256(str(jti).encode()).hexdigest()

        try:
            return cls.objects.select_related("user").get(
                jti_hash=jti_hash,
                platform=platform,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
        except cls.DoesNotExist:
            return None

    def revoke(self):
        """Revoke this session."""
        self.revoked_at = timezone.now()
        self.save()

    @classmethod
    def revoke_all_for_user(cls, user):
        """Revoke all sessions for a user."""
        cls.objects.filter(user=user, revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )

    def is_active(self):
        """Check if session is still active."""
        return self.revoked_at is None and self.expires_at > timezone.now()


class PhoneVerificationCode(BaseModel):
    """
    Phone verification codes (6-digit OTP via SMS).
    """

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="phone_verification_codes",
    )
    phone_number = models.CharField(max_length=20, db_index=True)  # E.164 format
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "phone_verification_codes"
        ordering = ["-created_at"]

    @classmethod
    def create_for_user(cls, user, phone_number, ttl_minutes=10):
        """Create a new phone verification code for user."""
        # Generate 6-digit OTP
        otp = f"{secrets.randbelow(1000000):06d}"
        code_hash = hashlib.sha256(otp.encode()).hexdigest()

        # Create code
        code = cls.objects.create(
            user=user,
            phone_number=phone_number,
            code_hash=code_hash,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )

        # Return both code object and plain OTP
        return code, otp

    @classmethod
    def verify_code(cls, user, phone_number, otp):
        """Verify code for phone number and mark as used."""
        code_hash = hashlib.sha256(otp.encode()).hexdigest()

        try:
            code = cls.objects.get(
                user=user,
                phone_number=phone_number,
                code_hash=code_hash,
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            )

            # Mark as used
            code.used_at = timezone.now()
            code.save()

            return code
        except cls.DoesNotExist:
            return None

    def is_valid(self):
        """Check if code is still valid."""
        return self.used_at is None and self.expires_at > timezone.now()
