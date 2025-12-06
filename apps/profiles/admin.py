"""
Admin configuration for profiles app.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import HandymanProfile, HomeownerProfile


@admin.register(HandymanProfile)
class HandymanProfileAdmin(ModelAdmin):
    """
    Admin interface for HandymanProfile model with Unfold styling.
    """

    list_display = (
        "user",
        "display_name",
        "rating_display",
        "phone_number",
        "is_phone_verified_display",
        "created_at",
    )
    list_filter = ("rating", "phone_verified_at", "created_at")
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
            {"fields": ("public_id", "user", "display_name")},
        ),
        (
            "Rating",
            {"fields": ("rating",)},
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


@admin.register(HomeownerProfile)
class HomeownerProfileAdmin(ModelAdmin):
    """
    Admin interface for HomeownerProfile model with Unfold styling.
    """

    list_display = (
        "user",
        "display_name",
        "phone_number",
        "is_phone_verified_display",
        "created_at",
    )
    list_filter = ("phone_verified_at", "created_at")
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
            {"fields": ("public_id", "user", "display_name")},
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
