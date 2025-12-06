"""Admin configuration for waitlist entries."""

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import WaitlistEntry


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(ModelAdmin):
    """Admin interface for waitlist entries - read-only."""

    list_display = ("user_name", "email", "user_type", "created_at", "updated_at")
    list_filter = ("user_type", "created_at")
    search_fields = ("user_name", "email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Submission Information",
            {"fields": ("user_name", "email", "user_type")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
