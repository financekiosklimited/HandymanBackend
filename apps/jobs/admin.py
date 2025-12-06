from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django_jsonform.widgets import JSONFormWidget
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import City, Job, JobCategory, JobImage

# Schema for job_items JSONField
JOB_ITEMS_SCHEMA = {
    "type": "array",
    "title": "Job Tasks",
    "items": {
        "type": "string",
        "title": "Task",
        "maxLength": 255,
    },
    "maxItems": 20,
}


class JobImageInline(TabularInline):
    """
    Inline admin for JobImage model.
    """

    model = JobImage
    extra = 0
    fields = ("image", "order")
    ordering = ("order",)


@admin.register(JobCategory)
class JobCategoryAdmin(ModelAdmin):
    """
    Admin interface for JobCategory model with Unfold styling.
    """

    list_display = ("name", "slug", "icon", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "slug", "description")
    ordering = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("public_id", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Category Information",
            {"fields": ("public_id", "name", "slug", "description", "icon")},
        ),
        (
            "Status",
            {"fields": ("is_active",)},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )


@admin.register(City)
class CityAdmin(ModelAdmin):
    """
    Admin interface for City model with Unfold styling.
    """

    list_display = (
        "name",
        "province",
        "province_code",
        "is_active",
        "created_at",
    )
    list_filter = ("province_code", "is_active", "created_at")
    search_fields = ("name", "province", "slug")
    ordering = ("name",)
    prepopulated_fields = {"slug": ("name", "province_code")}
    readonly_fields = ("public_id", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "City Information",
            {"fields": ("public_id", "name", "slug", "province", "province_code")},
        ),
        (
            "Coordinates",
            {"fields": ("latitude", "longitude")},
        ),
        (
            "Status",
            {"fields": ("is_active",)},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )


@admin.register(Job)
class JobAdmin(ModelAdmin):
    """
    Admin interface for Job model with Unfold styling.
    """

    list_display = (
        "title",
        "homeowner_email",
        "category",
        "city",
        "status_display",
        "budget_display",
        "created_at",
    )
    list_filter = ("status", "category", "city__province_code", "created_at")
    search_fields = (
        "title",
        "description",
        "homeowner__email",
        "homeowner__first_name",
        "homeowner__last_name",
        "postal_code",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("homeowner", "category", "city")
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = [JobImageInline]
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "public_id",
                    "homeowner",
                    "title",
                    "description",
                    "status",
                )
            },
        ),
        (
            "Category & Location",
            {
                "fields": (
                    "category",
                    "city",
                    "address",
                    "postal_code",
                    "latitude",
                    "longitude",
                )
            },
        ),
        (
            "Budget",
            {"fields": ("estimated_budget",)},
        ),
        (
            "Tasks",
            {
                "fields": ("job_items",),
                "description": "List of tasks/items to be done for this job (max 20 items, 255 chars each)",
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    formfield_overrides = {
        models.JSONField: {
            "widget": JSONFormWidget(schema=JOB_ITEMS_SCHEMA),
        },
    }

    @display(description="Homeowner")
    def homeowner_email(self, obj):
        """Display homeowner email."""
        return obj.homeowner.email

    @display(description="Status")
    def status_display(self, obj):
        """Display status with color coding."""
        status_colors = {
            "draft": "🟡",
            "open": "🟢",
            "in_progress": "🔵",
            "completed": "✅",
            "cancelled": "🔴",
        }
        icon = status_colors.get(obj.status, "")
        return f"{icon} {obj.get_status_display()}"

    @display(description="Budget")
    def budget_display(self, obj):
        """Display budget."""
        return f"${obj.estimated_budget}"


@admin.register(JobImage)
class JobImageAdmin(ModelAdmin):
    """
    Admin interface for JobImage model with Unfold styling.
    """

    list_display = ("job_title", "image_url_display", "order", "created_at")
    list_filter = ("created_at",)
    search_fields = ("job__title",)
    ordering = ("job", "order")
    autocomplete_fields = ("job",)
    readonly_fields = ("public_id", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Image Information",
            {"fields": ("public_id", "job", "image", "order")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Job")
    def job_title(self, obj):
        """Display job title."""
        return obj.job.title

    @display(description="Image URL")
    def image_url_display(self, obj):
        """Display image URL as a clickable link."""
        if obj.image:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.image.url,
                obj.image.name[:40] + "..."
                if len(obj.image.name) > 40
                else obj.image.name,
            )
        return "-"
