"""
Django admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserRole, AdminProfile, HandymanProfile, CustomerProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin interface for User model.
    """

    list_display = (
        "email",
        "is_active",
        "is_staff",
        "is_superuser",
        "email_verified_at",
        "date_joined",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "email_verified_at")
    search_fields = ("email",)
    ordering = ("-date_joined",)

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
        ("OAuth", {"fields": ("google_sub",)}),
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


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """
    Admin interface for UserRole model.
    """

    list_display = ("user", "role", "next_action", "created_at")
    list_filter = ("role", "next_action")
    search_fields = ("user__email",)
    ordering = ("-created_at",)


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for AdminProfile model.
    """

    list_display = ("user", "display_name", "created_at")
    search_fields = ("user__email", "display_name")
    ordering = ("-created_at",)


@admin.register(HandymanProfile)
class HandymanProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for HandymanProfile model.
    """

    list_display = ("user", "display_name", "rating", "phone_number", "created_at")
    list_filter = ("rating",)
    search_fields = ("user__email", "display_name", "phone_number")
    ordering = ("-created_at",)


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for CustomerProfile model.
    """

    list_display = ("user", "display_name", "phone_number", "created_at")
    search_fields = ("user__email", "display_name", "phone_number")
    ordering = ("-created_at",)
