"""Admin configuration for waitlist entries."""

from django.contrib import admin

from .models import WaitlistEntry


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    """Admin interface for waitlist entries."""

    list_display = ("user_name", "email", "user_type", "created_at", "updated_at")
    list_filter = ("user_type", "created_at")
    search_fields = ("user_name", "email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
