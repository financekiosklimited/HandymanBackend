"""
Admin configuration for profiles app.
"""

from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.common.admin_mixins import CSVExportAdminMixin

from .models import HandymanCategory, HandymanProfile, HomeownerProfile


@admin.register(HandymanCategory)
class HandymanCategoryAdmin(ModelAdmin):
    """
    Admin interface for HandymanCategory model.
    """

    list_display = ("name", "is_active", "created_at")
    search_fields = ("name", "description")
    list_filter = ("is_active", "created_at")
    ordering = ("name",)
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(HandymanProfile)
class HandymanProfileAdmin(CSVExportAdminMixin, ModelAdmin):
    """
    Admin interface for HandymanProfile model with Unfold styling.
    """

    list_display = (
        "avatar_preview",
        "user",
        "display_name",
        "rating_display",
        "hourly_rate",
        "is_approved",
        "is_active",
        "is_available",
        "phone_number",
        "is_phone_verified_display",
        "created_at",
    )
    list_filter = (
        "rating",
        "is_approved",
        "is_active",
        "is_available",
        "category",
        "phone_verified_at",
        "created_at",
    )
    search_fields = (
        "user__email",
        "display_name",
        "phone_number",
        "user__first_name",
        "user__last_name",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("user",)
    readonly_fields = ("public_id", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Profile Information",
            {
                "fields": (
                    "public_id",
                    "user",
                    "display_name",
                    "avatar",
                    "date_of_birth",
                )
            },
        ),
        (
            "Professional Details",
            {"fields": ("job_title", "category", "id_number")},
        ),
        (
            "Listing Status",
            {"fields": ("is_approved", "is_active", "is_available")},
        ),
        (
            "Pricing",
            {"fields": ("hourly_rate",)},
        ),
        (
            "Rating",
            {"fields": ("rating",)},
        ),
        (
            "Location",
            {"fields": ("latitude", "longitude")},
        ),
        (
            "Contact & Verification",
            {"fields": ("phone_number", "phone_verified_at")},
        ),
        (
            "Address",
            {"fields": ("address",)},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Rating")
    def rating_display(self, obj):
        """Display rating with stars."""
        if obj.rating:
            stars = "★" * int(obj.rating)
            return f"{obj.rating} {stars}"
        return "No rating"

    @display(description="Phone Verified", boolean=True)
    def is_phone_verified_display(self, obj):
        """Display whether phone is verified."""
        return obj.is_phone_verified

    @display(description="Avatar")
    def avatar_preview(self, obj):
        """Display avatar thumbnail in list view."""
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; '
                'border-radius: 50%; object-fit: cover;" />',
                obj.avatar.url,
            )
        return format_html(
            '<div style="width: 40px; height: 40px; border-radius: 50%; '
            "background-color: #e0e0e0; display: flex; align-items: center; "
            'justify-content: center; color: #666; font-size: 12px;">N/A</div>'
        )


@admin.register(HomeownerProfile)
class HomeownerProfileAdmin(CSVExportAdminMixin, ModelAdmin):
    """
    Admin interface for HomeownerProfile model with Unfold styling.
    """

    list_display = (
        "avatar_preview",
        "user",
        "display_name",
        "phone_number",
        "is_phone_verified_display",
        "created_at",
    )
    list_filter = ("phone_verified_at", "user__is_active", "created_at")
    search_fields = (
        "user__email",
        "display_name",
        "phone_number",
        "user__first_name",
        "user__last_name",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("user",)
    readonly_fields = ("public_id", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Profile Information",
            {
                "fields": (
                    "public_id",
                    "user",
                    "display_name",
                    "avatar",
                    "date_of_birth",
                )
            },
        ),
        (
            "Contact & Verification",
            {"fields": ("phone_number", "phone_verified_at")},
        ),
        (
            "Address",
            {"fields": ("address",)},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Phone Verified", boolean=True)
    def is_phone_verified_display(self, obj):
        """Display whether phone is verified."""
        return obj.is_phone_verified

    @display(description="Avatar")
    def avatar_preview(self, obj):
        """Display avatar thumbnail in list view."""
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; '
                'border-radius: 50%; object-fit: cover;" />',
                obj.avatar.url,
            )
        return format_html(
            '<div style="width: 40px; height: 40px; border-radius: 50%; '
            "background-color: #e0e0e0; display: flex; align-items: center; "
            'justify-content: center; color: #666; font-size: 12px;">N/A</div>'
        )
