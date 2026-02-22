"""
Django admin configuration for authn app.
"""

from django.contrib import admin
from django.utils import timezone
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.common.admin_mixins import CSVExportAdminMixin

from .models import (
    EmailVerificationToken,
    PasswordResetCode,
    PasswordResetToken,
    PhoneVerificationCode,
    RefreshSession,
)


class RefreshSessionActiveFilter(admin.SimpleListFilter):
    """Filter refresh sessions by computed active state."""

    title = "active status"
    parameter_name = "active_status"

    def lookups(self, request, model_admin):
        return (
            ("active", "Active"),
            ("inactive", "Inactive"),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "active":
            return queryset.filter(revoked_at__isnull=True, expires_at__gt=now)
        if self.value() == "inactive":
            return queryset.exclude(revoked_at__isnull=True, expires_at__gt=now)
        return queryset


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(ModelAdmin):
    """
    Admin interface for EmailVerificationToken model.
    """

    list_display = (
        "user",
        "is_valid_display",
        "expires_at",
        "used_at",
        "created_at",
    )
    list_filter = ("used_at", "expires_at", "created_at")
    search_fields = ("user__email",)
    ordering = ("-created_at",)
    readonly_fields = ("public_id", "token_hash", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Token Information",
            {"fields": ("public_id", "token_hash")},
        ),
        (
            "User",
            {"fields": ("user",)},
        ),
        (
            "Status",
            {"fields": ("expires_at", "used_at")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Valid", boolean=True)
    def is_valid_display(self, obj):
        """Display whether token is still valid."""
        return obj.is_valid()


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(ModelAdmin):
    """
    Admin interface for PasswordResetCode model.
    """

    list_display = (
        "user",
        "is_valid_display",
        "expires_at",
        "verified_at",
        "created_at",
    )
    list_filter = ("verified_at", "expires_at", "created_at")
    search_fields = ("user__email",)
    ordering = ("-created_at",)
    readonly_fields = ("public_id", "code_hash", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Code Information",
            {"fields": ("public_id", "code_hash")},
        ),
        (
            "User",
            {"fields": ("user",)},
        ),
        (
            "Status",
            {"fields": ("expires_at", "verified_at")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Valid", boolean=True)
    def is_valid_display(self, obj):
        """Display whether code is still valid (not verified and not expired)."""
        return obj.verified_at is None and obj.expires_at > timezone.now()


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(ModelAdmin):
    """
    Admin interface for PasswordResetToken model.
    """

    list_display = (
        "user",
        "is_valid_display",
        "expires_at",
        "used_at",
        "created_at",
    )
    list_filter = ("used_at", "expires_at", "created_at")
    search_fields = ("user__email",)
    ordering = ("-created_at",)
    readonly_fields = ("public_id", "token_hash", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Token Information",
            {"fields": ("public_id", "token_hash")},
        ),
        (
            "User",
            {"fields": ("user",)},
        ),
        (
            "Status",
            {"fields": ("expires_at", "used_at")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Valid", boolean=True)
    def is_valid_display(self, obj):
        """Display whether token is still valid."""
        return obj.used_at is None and obj.expires_at > timezone.now()


@admin.register(RefreshSession)
class RefreshSessionAdmin(CSVExportAdminMixin, ModelAdmin):
    """
    Admin interface for RefreshSession model.
    """

    list_display = (
        "user",
        "platform",
        "is_active_display",
        "user_agent_display",
        "ip_address",
        "expires_at",
        "revoked_at",
        "created_at",
    )
    list_filter = (
        RefreshSessionActiveFilter,
        "platform",
        "revoked_at",
        "expires_at",
        "created_at",
    )
    search_fields = ("user__email", "ip_address", "user_agent")
    ordering = ("-created_at",)
    readonly_fields = ("public_id", "jti_hash", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Session Information",
            {"fields": ("public_id", "jti_hash", "platform")},
        ),
        (
            "User",
            {"fields": ("user",)},
        ),
        (
            "Client Details",
            {"fields": ("user_agent", "ip_address")},
        ),
        (
            "Status",
            {"fields": ("expires_at", "revoked_at")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Active", boolean=True)
    def is_active_display(self, obj):
        """Display whether session is still active."""
        return obj.is_active()

    @display(description="User Agent")
    def user_agent_display(self, obj):
        """Display truncated user agent."""
        if obj.user_agent:
            return (
                obj.user_agent[:50] + "..."
                if len(obj.user_agent) > 50
                else obj.user_agent
            )
        return "-"


@admin.register(PhoneVerificationCode)
class PhoneVerificationCodeAdmin(ModelAdmin):
    """
    Admin interface for PhoneVerificationCode model.
    """

    list_display = (
        "user",
        "phone_number",
        "is_valid_display",
        "expires_at",
        "used_at",
        "created_at",
    )
    list_filter = ("used_at", "expires_at", "created_at")
    search_fields = ("user__email", "phone_number")
    ordering = ("-created_at",)
    readonly_fields = ("public_id", "code_hash", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Code Information",
            {"fields": ("public_id", "code_hash", "phone_number")},
        ),
        (
            "User",
            {"fields": ("user",)},
        ),
        (
            "Status",
            {"fields": ("expires_at", "used_at")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Valid", boolean=True)
    def is_valid_display(self, obj):
        """Display whether code is still valid."""
        return obj.is_valid()
