from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django_jsonform.widgets import JSONFormWidget
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import City, Job, JobApplication, JobCategory, JobImage

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


class JobApplicationInline(TabularInline):
    """
    Inline admin for JobApplication in Job detail view.
    """

    model = JobApplication
    extra = 0
    fields = ("handyman", "status", "status_at", "created_at")
    readonly_fields = ("handyman", "status_at", "created_at")
    ordering = ("-created_at",)
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        """Disable adding applications from inline."""
        return False


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
        "application_count",
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
    inlines = [JobImageInline, JobApplicationInline]
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

    @display(description="Applications")
    def application_count(self, obj):
        """Display count of applications with status breakdown."""
        total = obj.applications.count()
        pending = obj.applications.filter(status="pending").count()
        approved = obj.applications.filter(status="approved").count()

        if total > 0:
            url = f"/admin/jobs/jobapplication/?job__id__exact={obj.pk}"
            parts = []
            if pending > 0:
                parts.append(f"🟡 {pending}")
            if approved > 0:
                parts.append(f"✅ {approved}")
            if not parts:
                parts.append(str(total))

            status_str = " | ".join(parts)
            return format_html(
                '<a href="{}">{} total ({})</a>',
                url,
                total,
                status_str,
            )
        return "0"


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


@admin.register(JobApplication)
class JobApplicationAdmin(ModelAdmin):
    """
    Admin interface for JobApplication model with Unfold styling.
    """

    list_display = (
        "job_link",
        "handyman_link",
        "status_display",
        "status_at",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "job__title",
        "handyman__email",
        "handyman__first_name",
        "handyman__last_name",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("job", "handyman")
    readonly_fields = ("public_id", "status_at", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25
    actions = ["approve_applications", "reject_applications"]

    fieldsets = (
        (
            "Application Information",
            {
                "fields": (
                    "public_id",
                    "job",
                    "handyman",
                    "status",
                    "status_at",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Job")
    def job_link(self, obj):
        """Display job title as clickable link."""
        return format_html(
            '<a href="/admin/jobs/job/{}/change/">{}</a>',
            obj.job.pk,
            obj.job.title,
        )

    @display(description="Handyman")
    def handyman_link(self, obj):
        """Display handyman email as clickable link."""
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.handyman.pk,
            obj.handyman.email,
        )

    @display(description="Status")
    def status_display(self, obj):
        """Display status with color coding."""
        status_colors = {
            "pending": "🟡",
            "approved": "✅",
            "rejected": "🔴",
            "withdrawn": "⬅️",
        }
        icon = status_colors.get(obj.status, "")
        return f"{icon} {obj.get_status_display()}"

    @admin.action(description="Approve selected applications")
    def approve_applications(self, request, queryset):
        """
        Approve selected applications.
        Uses the JobApplicationService to ensure proper business logic.
        """
        from apps.jobs.services import job_application_service

        approved_count = 0
        error_count = 0

        for application in queryset:
            # Only approve pending applications
            if application.status != "pending":
                continue

            try:
                # Use the service to approve (handles notifications, auto-rejection, etc.)
                job_application_service.approve_application(
                    homeowner=application.job.homeowner,
                    application=application,
                )
                approved_count += 1
            except Exception as e:
                error_count += 1
                self.message_user(
                    request,
                    f"Failed to approve application {application.public_id}: {e}",
                    level="error",
                )

        if approved_count > 0:
            self.message_user(
                request,
                f"Successfully approved {approved_count} application(s). "
                f"Jobs set to 'in_progress', other pending applications auto-rejected, "
                f"and notifications sent.",
            )

        if error_count > 0:
            self.message_user(
                request,
                f"{error_count} application(s) could not be approved.",
                level="warning",
            )

    @admin.action(description="Reject selected applications")
    def reject_applications(self, request, queryset):
        """
        Reject selected applications.
        Uses the JobApplicationService to ensure proper business logic.
        """
        from apps.jobs.services import job_application_service

        rejected_count = 0
        error_count = 0

        for application in queryset:
            # Only reject pending applications
            if application.status != "pending":
                continue

            try:
                # Use the service to reject (handles notifications)
                job_application_service.reject_application(
                    homeowner=application.job.homeowner,
                    application=application,
                )
                rejected_count += 1
            except Exception as e:
                error_count += 1
                self.message_user(
                    request,
                    f"Failed to reject application {application.public_id}: {e}",
                    level="error",
                )

        if rejected_count > 0:
            self.message_user(
                request,
                f"Successfully rejected {rejected_count} application(s) and sent notifications.",
            )

        if error_count > 0:
            self.message_user(
                request,
                f"{error_count} application(s) could not be rejected.",
                level="warning",
            )
