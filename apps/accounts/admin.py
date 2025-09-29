"""
Admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import User, UserRole


class UserRoleInline(TabularInline):
    """Inline admin for user roles."""

    model = UserRole
    extra = 0
    fields = ("role", "next_action")


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """
    Admin interface for User model with Unfold styling.
    """

    list_display = (
        "email",
        "display_name_field",
        "is_active",
        "is_staff",
        "is_email_verified_display",
        "date_joined",
    )
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "email_verified_at",
        "date_joined",
    )
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)
    inlines = [UserRoleInline]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important dates",
            {"fields": ("last_login", "date_joined", "email_verified_at")},
        ),
        ("OAuth & System", {"fields": ("google_sub", "public_id")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )

    readonly_fields = ("date_joined", "last_login", "public_id")

    @display(description="Full Name")
    def display_name_field(self, obj):
        """Display user's full name or email."""
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        return full_name if full_name else obj.email

    @display(description="Email Verified", boolean=True)
    def is_email_verified_display(self, obj):
        """Display email verification status as boolean."""
        return obj.is_email_verified
