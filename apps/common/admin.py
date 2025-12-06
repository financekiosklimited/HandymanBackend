"""
Django admin configuration for common app.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import CountryPhoneCode


@admin.register(CountryPhoneCode)
class CountryPhoneCodeAdmin(ModelAdmin):
    """
    Admin interface for CountryPhoneCode model.
    """

    list_display = (
        "country_code",
        "country_name",
        "dial_code",
        "flag_emoji",
        "is_active",
        "display_order",
    )
    list_filter = ("is_active",)
    search_fields = ("country_code", "country_name", "dial_code")
    ordering = ("display_order", "country_name")
    list_editable = ("is_active", "display_order")
    readonly_fields = ("public_id", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Country Information",
            {
                "fields": (
                    "public_id",
                    "country_code",
                    "country_name",
                    "dial_code",
                    "flag_emoji",
                )
            },
        ),
        (
            "Display Settings",
            {"fields": ("is_active", "display_order")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )
