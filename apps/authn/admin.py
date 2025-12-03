"""
Django admin configuration for authn app.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import (
    EmailVerificationToken,
    PasswordResetCode,
    PasswordResetToken,
    PhoneVerificationCode,
    RefreshSession,
)


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(ModelAdmin):
    """
    Admin interface for EmailVerificationToken model.
    """

    list_display = ("user", "expires_at", "used_at", "created_at")
    list_filter = ("used_at", "expires_at")
    search_fields = ("user__email",)
    ordering = ("-created_at",)
    readonly_fields = ("token_hash", "created_at")


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(ModelAdmin):
    """
    Admin interface for PasswordResetCode model.
    """

    list_display = ("user", "expires_at", "verified_at", "created_at")
    list_filter = ("verified_at", "expires_at")
    search_fields = ("user__email",)
    ordering = ("-created_at",)
    readonly_fields = ("code_hash", "created_at")


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(ModelAdmin):
    """
    Admin interface for PasswordResetToken model.
    """

    list_display = ("user", "expires_at", "used_at", "created_at")
    list_filter = ("used_at", "expires_at")
    search_fields = ("user__email",)
    ordering = ("-created_at",)
    readonly_fields = ("token_hash", "created_at")


@admin.register(RefreshSession)
class RefreshSessionAdmin(ModelAdmin):
    """
    Admin interface for RefreshSession model.
    """

    list_display = ("user", "platform", "expires_at", "revoked_at", "created_at")
    list_filter = ("platform", "revoked_at", "expires_at")
    search_fields = ("user__email", "ip_address")
    ordering = ("-created_at",)
    readonly_fields = ("jti_hash", "created_at")


@admin.register(PhoneVerificationCode)
class PhoneVerificationCodeAdmin(ModelAdmin):
    """
    Admin interface for PhoneVerificationCode model.
    """

    list_display = ("user", "phone_number", "expires_at", "used_at", "created_at")
    list_filter = ("used_at", "expires_at")
    search_fields = ("user__email", "phone_number")
    ordering = ("-created_at",)
    readonly_fields = ("code_hash", "created_at")
