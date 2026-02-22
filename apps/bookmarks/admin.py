"""
Admin configuration for bookmarks app.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.common.admin_mixins import CSVExportAdminMixin

from .models import HandymanBookmark, JobBookmark


@admin.register(JobBookmark)
class JobBookmarkAdmin(CSVExportAdminMixin, ModelAdmin):
    list_display = [
        "public_id",
        "handyman",
        "job",
        "created_at",
    ]
    list_filter = ["handyman", "job", "created_at"]
    search_fields = [
        "handyman__email",
        "job__title",
    ]
    raw_id_fields = ["handyman", "job"]
    readonly_fields = ["public_id", "created_at", "updated_at"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"


@admin.register(HandymanBookmark)
class HandymanBookmarkAdmin(CSVExportAdminMixin, ModelAdmin):
    list_display = [
        "public_id",
        "homeowner",
        "handyman_profile",
        "created_at",
    ]
    list_filter = ["homeowner", "handyman_profile", "created_at"]
    search_fields = [
        "homeowner__email",
        "handyman_profile__display_name",
    ]
    raw_id_fields = ["homeowner", "handyman_profile"]
    readonly_fields = ["public_id", "created_at", "updated_at"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
