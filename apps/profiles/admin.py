"""
Admin configuration for profiles app.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import CustomerProfile, HandymanProfile


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
        "created_at",
    )
    list_filter = ("rating", "created_at")
    search_fields = (
        "user__email",
        "display_name",
        "phone_number",
        "user__first_name",
        "user__last_name",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("user",)

    @display(description="Rating")
    def rating_display(self, obj):
        """Display rating with stars."""
        if obj.rating:
            stars = "★" * int(obj.rating)
            return f"{obj.rating} {stars}"
        return "No rating"


@admin.register(CustomerProfile)
class CustomerProfileAdmin(ModelAdmin):
    """
    Admin interface for CustomerProfile model with Unfold styling.
    """

    list_display = ("user", "display_name", "phone_number", "created_at")
    search_fields = (
        "user__email",
        "display_name",
        "phone_number",
        "user__first_name",
        "user__last_name",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("user",)
    list_filter = ("created_at",)
