from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import City, Job, JobCategory, JobImage


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

    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "slug", "description")
    ordering = ("name",)
    prepopulated_fields = {"slug": ("name",)}


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


@admin.register(Job)
class JobAdmin(ModelAdmin):
    """
    Admin interface for Job model with Unfold styling.
    """

    list_display = (
        "title",
        "customer_email",
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
        "customer__email",
        "customer__first_name",
        "customer__last_name",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("customer", "category", "city")
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = [JobImageInline]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "public_id",
                    "customer",
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
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Customer")
    def customer_email(self, obj):
        """Display customer email."""
        return obj.customer.email

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

    list_display = ("job_title", "order", "created_at")
    list_filter = ("created_at",)
    search_fields = ("job__title",)
    ordering = ("job", "order")
    autocomplete_fields = ("job",)

    @display(description="Job")
    def job_title(self, obj):
        """Display job title."""
        return obj.job.title
