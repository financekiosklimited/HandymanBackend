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
