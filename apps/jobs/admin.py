from datetime import timedelta

from django import forms
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import (
    City,
    DailyReport,
    DailyReportTask,
    Job,
    JobApplication,
    JobCategory,
    JobDispute,
    JobImage,
    JobTask,
    WorkSession,
    WorkSessionMedia,
)

# =============================================================================
# Dispute Dashboard Utilities
# =============================================================================


def get_dispute_dashboard_data():
    """
    Get KPI and list data for the disputes dashboard.

    Returns a dictionary with:
    - kpis: Count metrics for dashboard cards
    - disputes: Queryset of pending/in-review disputes with related data
    """
    now = timezone.now()

    pending_disputes = JobDispute.objects.filter(status__in=["pending", "in_review"])

    kpis = {
        "pending_count": pending_disputes.filter(status="pending").count(),
        "in_review_count": pending_disputes.filter(status="in_review").count(),
        "overdue_count": pending_disputes.filter(resolution_deadline__lt=now).count(),
        "due_soon_count": pending_disputes.filter(
            resolution_deadline__gte=now,
            resolution_deadline__lt=now + timedelta(hours=24),
        ).count(),
        "resolved_this_week": JobDispute.objects.filter(
            resolved_at__gte=now - timedelta(days=7)
        ).count(),
    }

    disputes = pending_disputes.select_related(
        "job",
        "job__homeowner",
        "job__assigned_handyman",
        "initiated_by",
    ).order_by("resolution_deadline")

    return {
        "kpis": kpis,
        "disputes": disputes,
        "now": now,
    }


# =============================================================================
# Dispute Admin Forms
# =============================================================================


class DisputeResolveForm(forms.Form):
    """Form for resolving disputes in the admin interface."""

    RESOLUTION_CHOICES = [
        ("resolved_full_refund", "Full Refund to Homeowner"),
        ("resolved_partial_refund", "Partial Refund"),
        ("resolved_pay_handyman", "Pay Handyman (No Refund)"),
    ]

    status = forms.ChoiceField(
        choices=RESOLUTION_CHOICES,
        widget=forms.RadioSelect,
        help_text="Select the resolution outcome for this dispute.",
    )
    refund_percentage = forms.IntegerField(
        min_value=1,
        max_value=99,
        required=False,
        help_text="Required for partial refund. Enter a value between 1-99%.",
    )
    admin_notes = forms.CharField(
        widget=forms.Textarea(
            attrs={"rows": 4, "placeholder": "Enter resolution notes..."}
        ),
        required=False,
        help_text="Internal notes about the resolution decision.",
    )

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        refund_percentage = cleaned_data.get("refund_percentage")

        if status == "resolved_partial_refund" and not refund_percentage:
            self.add_error(
                "refund_percentage",
                "Refund percentage is required for partial refund resolution.",
            )
        elif status == "resolved_full_refund":
            # Full refund is implicitly 100%
            cleaned_data["refund_percentage"] = 100

        return cleaned_data


# =============================================================================
# Dispute Admin Filters
# =============================================================================


class DisputeDeadlineFilter(admin.SimpleListFilter):
    """Filter disputes by their deadline status."""

    title = "deadline status"
    parameter_name = "deadline_status"

    def lookups(self, request, model_admin):
        return [
            ("overdue", "Overdue"),
            ("due_soon", "Due Soon (24h)"),
            ("on_track", "On Track"),
        ]

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "overdue":
            return queryset.filter(resolution_deadline__lt=now)
        if self.value() == "due_soon":
            return queryset.filter(
                resolution_deadline__gte=now,
                resolution_deadline__lt=now + timedelta(hours=24),
            )
        if self.value() == "on_track":
            return queryset.filter(resolution_deadline__gte=now + timedelta(hours=24))
        return queryset


class JobTaskInline(TabularInline):
    model = JobTask
    extra = 0
    fields = ("title", "order", "is_completed", "completed_by", "completed_at")
    readonly_fields = ("completed_by", "completed_at")
    ordering = ("order", "created_at")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class WorkSessionMediaInline(TabularInline):
    model = WorkSessionMedia
    extra = 0
    fields = (
        "media_type",
        "file",
        "thumbnail",
        "file_size",
        "duration_seconds",
        "description",
        "task",
    )
    readonly_fields = ("file_size", "duration_seconds")
    ordering = ("-created_at",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class WorkSessionInline(TabularInline):
    model = WorkSession
    extra = 0
    fields = (
        "handyman",
        "status",
        "started_at",
        "ended_at",
        "start_latitude",
        "start_longitude",
        "end_latitude",
        "end_longitude",
    )
    readonly_fields = (
        "handyman",
        "status",
        "started_at",
        "ended_at",
        "start_latitude",
        "start_longitude",
        "end_latitude",
        "end_longitude",
    )
    ordering = ("-started_at",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DailyReportTaskInline(TabularInline):
    model = DailyReportTask
    extra = 0
    fields = ("task", "marked_complete", "notes")
    readonly_fields = ("task",)
    ordering = ("task__order",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DailyReportInline(TabularInline):
    model = DailyReport
    extra = 0
    fields = (
        "handyman",
        "report_date",
        "status",
        "review_deadline",
        "reviewed_at",
        "reviewed_by",
    )
    readonly_fields = (
        "handyman",
        "report_date",
        "status",
        "review_deadline",
        "reviewed_at",
        "reviewed_by",
    )
    ordering = ("-report_date",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class JobDisputeInline(TabularInline):
    model = JobDispute
    extra = 0
    fields = (
        "initiated_by",
        "status",
        "resolution_deadline",
        "resolved_at",
        "refund_percentage",
    )
    readonly_fields = (
        "initiated_by",
        "status",
        "resolution_deadline",
        "resolved_at",
        "refund_percentage",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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
        "active_tasks",
        "pending_reports",
        "open_disputes",
        "created_at",
    )
    list_filter = (
        "status",
        "category",
        "city__province_code",
        "created_at",
        "daily_reports__status",
        "disputes__status",
    )
    search_fields = (
        "title",
        "description",
        "homeowner__email",
        "homeowner__first_name",
        "homeowner__last_name",
        "postal_code",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("homeowner", "category", "city", "assigned_handyman")
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "status_at",
        "completion_requested_at",
        "completed_at",
    )
    inlines = [
        JobImageInline,
        JobTaskInline,
        WorkSessionInline,
        DailyReportInline,
        JobDisputeInline,
        JobApplicationInline,
    ]
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "public_id",
                    "homeowner",
                    "assigned_handyman",
                    "title",
                    "description",
                    "status",
                    "status_at",
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
            "Completion",
            {
                "fields": ("completion_requested_at", "completed_at"),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

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

    @display(description="Active Tasks")
    def active_tasks(self, obj):
        return obj.tasks.filter(is_completed=False).count()

    @display(description="Pending Reports")
    def pending_reports(self, obj):
        return obj.daily_reports.filter(status="pending").count()

    @display(description="Open Disputes")
    def open_disputes(self, obj):
        return obj.disputes.exclude(status__startswith="resolved").count()


@admin.register(JobTask)
class JobTaskAdmin(ModelAdmin):
    list_display = ("job", "title", "order", "is_completed", "completed_at")
    list_filter = ("is_completed", "job")
    search_fields = ("title", "job__title")
    ordering = ("job", "order")
    autocomplete_fields = ("job", "completed_by")
    readonly_fields = ("public_id", "created_at", "updated_at")
    list_per_page = 25

    fieldsets = (
        (
            "Task",
            {
                "fields": (
                    "public_id",
                    "job",
                    "title",
                    "description",
                    "order",
                    "is_completed",
                    "completed_at",
                    "completed_by",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )


@admin.register(DailyReportTask)
class DailyReportTaskAdmin(ModelAdmin):
    list_display = ("daily_report", "task", "marked_complete")
    list_filter = ("marked_complete",)
    search_fields = ("task__title",)
    ordering = ("daily_report", "task__order")
    autocomplete_fields = ("daily_report", "task")
    readonly_fields = ("public_id", "created_at", "updated_at")

    fieldsets = (
        (
            "Daily Report Task",
            {
                "fields": (
                    "public_id",
                    "daily_report",
                    "task",
                    "marked_complete",
                    "notes",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )


@admin.register(WorkSession)
class WorkSessionAdmin(ModelAdmin):
    list_display = (
        "job",
        "handyman",
        "status",
        "started_at",
        "ended_at",
    )
    list_filter = ("status", "job", "handyman")
    search_fields = ("job__title", "handyman__email")
    ordering = ("-started_at",)
    autocomplete_fields = ("job", "handyman")
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "duration_seconds",
    )
    inlines = [WorkSessionMediaInline]

    fieldsets = (
        (
            "Session",
            {
                "fields": (
                    "public_id",
                    "job",
                    "handyman",
                    "status",
                    "started_at",
                    "ended_at",
                    "start_latitude",
                    "start_longitude",
                    "start_accuracy",
                    "start_photo",
                    "end_latitude",
                    "end_longitude",
                    "end_accuracy",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )


@admin.register(WorkSessionMedia)
class WorkSessionMediaAdmin(ModelAdmin):
    list_display = (
        "work_session",
        "media_type",
        "file",
        "file_size",
        "duration_seconds",
        "created_at",
    )
    list_filter = ("media_type",)
    search_fields = ("work_session__job__title",)
    ordering = ("-created_at",)
    autocomplete_fields = ("work_session", "task")
    readonly_fields = ("public_id", "created_at", "updated_at")

    fieldsets = (
        (
            "Media",
            {
                "fields": (
                    "public_id",
                    "work_session",
                    "media_type",
                    "file",
                    "thumbnail",
                    "file_size",
                    "duration_seconds",
                    "description",
                    "task",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )


@admin.register(DailyReport)
class DailyReportAdmin(ModelAdmin):
    list_display = (
        "job",
        "handyman",
        "report_date",
        "status",
        "review_deadline",
        "reviewed_at",
    )
    list_filter = ("status", "report_date")
    search_fields = ("job__title", "handyman__email")
    ordering = ("-report_date",)
    autocomplete_fields = ("job", "handyman", "reviewed_by")
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "reviewed_at",
    )
    inlines = [DailyReportTaskInline]

    fieldsets = (
        (
            "Report",
            {
                "fields": (
                    "public_id",
                    "job",
                    "handyman",
                    "report_date",
                    "summary",
                    "total_work_duration",
                    "status",
                    "homeowner_comment",
                    "review_deadline",
                    "reviewed_at",
                    "reviewed_by",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )


@admin.register(JobDispute)
class JobDisputeAdmin(ModelAdmin):
    list_display = (
        "job_link",
        "initiated_by_link",
        "status_display",
        "deadline_display",
        "resolved_at",
        "refund_percentage",
    )
    list_filter = ("status", DisputeDeadlineFilter)
    search_fields = ("job__title", "initiated_by__email", "reason")
    ordering = ("-created_at",)
    autocomplete_fields = ("job", "initiated_by", "resolved_by")
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "resolved_at",
    )
    actions = ["resolve_pay_handyman", "resolve_full_refund", "mark_in_review"]

    fieldsets = (
        (
            "Dispute",
            {
                "fields": (
                    "public_id",
                    "job",
                    "initiated_by",
                    "reason",
                    "disputed_reports",
                    "status",
                    "admin_notes",
                    "resolved_by",
                    "resolved_at",
                    "refund_percentage",
                    "resolution_deadline",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    # -------------------------------------------------------------------------
    # Custom Display Methods
    # -------------------------------------------------------------------------

    @display(description="Job")
    def job_link(self, obj):
        """Display job title as clickable link."""
        return format_html(
            '<a href="/admin/jobs/job/{}/change/">{}</a>',
            obj.job.pk,
            obj.job.title[:40] + "..." if len(obj.job.title) > 40 else obj.job.title,
        )

    @display(description="Initiated By")
    def initiated_by_link(self, obj):
        """Display initiator email as clickable link."""
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.initiated_by.pk,
            obj.initiated_by.email,
        )

    @display(description="Status")
    def status_display(self, obj):
        """Display status with color coding."""
        status_styles = {
            "pending": ("orange", "Pending"),
            "in_review": ("blue", "In Review"),
            "resolved_full_refund": ("green", "Full Refund"),
            "resolved_partial_refund": ("green", "Partial Refund"),
            "resolved_pay_handyman": ("green", "Pay Handyman"),
            "cancelled": ("gray", "Cancelled"),
        }
        color, label = status_styles.get(obj.status, ("gray", obj.status))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            label,
        )

    @display(description="Deadline")
    def deadline_display(self, obj):
        """Display deadline with overdue/due-soon highlighting."""
        now = timezone.now()
        deadline = obj.resolution_deadline

        if obj.status.startswith("resolved") or obj.status == "cancelled":
            return format_html(
                '<span style="color: gray;">{}</span>',
                deadline.strftime("%Y-%m-%d %H:%M"),
            )

        if deadline < now:
            return format_html(
                '<span style="color: red; font-weight: bold;">OVERDUE: {}</span>',
                deadline.strftime("%Y-%m-%d %H:%M"),
            )
        elif deadline < now + timedelta(hours=24):
            return format_html(
                '<span style="color: orange; font-weight: bold;">DUE SOON: {}</span>',
                deadline.strftime("%Y-%m-%d %H:%M"),
            )
        else:
            return deadline.strftime("%Y-%m-%d %H:%M")

    # -------------------------------------------------------------------------
    # Custom URLs and Views
    # -------------------------------------------------------------------------

    def get_urls(self):
        """Add custom URLs for disputes dashboard and resolution."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "dashboard/",
                self.admin_site.admin_view(self.dashboard_view),
                name="jobs_jobdispute_dashboard",
            ),
            path(
                "<int:dispute_id>/resolve/",
                self.admin_site.admin_view(self.resolve_view),
                name="jobs_jobdispute_resolve",
            ),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        """Disputes dashboard view with KPIs and pending disputes list."""
        data = get_dispute_dashboard_data()
        context = {
            **self.admin_site.each_context(request),
            "title": "Disputes Dashboard",
            "opts": self.model._meta,
            "can_manage": request.user.has_perm("jobs.can_manage_disputes"),
            **data,
        }
        return render(request, "admin/jobs/disputes_dashboard.html", context)

    def resolve_view(self, request, dispute_id):
        """Individual dispute resolution view with full context."""
        from apps.jobs.services import dispute_service

        dispute = get_object_or_404(
            JobDispute.objects.select_related(
                "job",
                "job__homeowner",
                "job__assigned_handyman",
                "job__category",
                "job__city",
                "initiated_by",
            ).prefetch_related("disputed_reports"),
            pk=dispute_id,
        )

        can_manage = request.user.has_perm("jobs.can_manage_disputes")

        # Check if already resolved
        if dispute.status.startswith("resolved") or dispute.status == "cancelled":
            messages.warning(request, "This dispute has already been resolved.")
            return redirect("admin:jobs_jobdispute_dashboard")

        if request.method == "POST":
            if not can_manage:
                messages.error(
                    request, "You don't have permission to resolve disputes."
                )
                return redirect("admin:jobs_jobdispute_dashboard")

            form = DisputeResolveForm(request.POST)
            if form.is_valid():
                try:
                    dispute_service.resolve_dispute(
                        admin_user=request.user,
                        dispute=dispute,
                        status=form.cleaned_data["status"],
                        refund_percentage=form.cleaned_data.get("refund_percentage"),
                        admin_notes=form.cleaned_data.get("admin_notes", ""),
                    )
                    messages.success(
                        request,
                        f"Dispute for '{dispute.job.title}' resolved successfully. "
                        "Notifications have been sent to both parties.",
                    )
                except Exception as e:
                    messages.error(request, f"Failed to resolve dispute: {str(e)}")
                return redirect("admin:jobs_jobdispute_dashboard")
        else:
            form = DisputeResolveForm()

        # Get related data for context
        job = dispute.job
        work_sessions = job.work_sessions.select_related("handyman").order_by(
            "-started_at"
        )[:5]
        daily_reports = job.daily_reports.select_related("handyman").order_by(
            "-report_date"
        )

        # Calculate deadline status
        now = timezone.now()
        is_overdue = dispute.resolution_deadline < now
        is_due_soon = not is_overdue and dispute.resolution_deadline < now + timedelta(
            hours=24
        )

        context = {
            **self.admin_site.each_context(request),
            "title": f"Resolve Dispute: {job.title}",
            "opts": self.model._meta,
            "dispute": dispute,
            "job": job,
            "form": form,
            "work_sessions": work_sessions,
            "daily_reports": daily_reports,
            "can_manage": can_manage,
            "is_overdue": is_overdue,
            "is_due_soon": is_due_soon,
            "now": now,
        }
        return render(request, "admin/jobs/dispute_resolve.html", context)

    # -------------------------------------------------------------------------
    # Admin Actions
    # -------------------------------------------------------------------------

    @admin.action(description="Resolve - Pay Handyman (No Refund)")
    def resolve_pay_handyman(self, request, queryset):
        """Resolve selected disputes as pay handyman."""
        self._bulk_resolve(request, queryset, "resolved_pay_handyman")

    @admin.action(description="Resolve - Full Refund to Homeowner")
    def resolve_full_refund(self, request, queryset):
        """Resolve selected disputes with full refund."""
        self._bulk_resolve(request, queryset, "resolved_full_refund")

    @admin.action(description="Mark as In Review")
    def mark_in_review(self, request, queryset):
        """Mark selected pending disputes as in review."""
        updated = queryset.filter(status="pending").update(status="in_review")
        self.message_user(
            request,
            f"Marked {updated} dispute(s) as in review.",
        )

    def _bulk_resolve(self, request, queryset, status):
        """Helper method for bulk resolution actions."""
        from apps.jobs.services import dispute_service

        if not request.user.has_perm("jobs.can_manage_disputes"):
            self.message_user(
                request,
                "You don't have permission to resolve disputes.",
                level=messages.ERROR,
            )
            return

        resolved = 0
        errors = 0
        for dispute in queryset.filter(status__in=["pending", "in_review"]):
            try:
                dispute_service.resolve_dispute(
                    admin_user=request.user,
                    dispute=dispute,
                    status=status,
                    refund_percentage=None,
                    admin_notes="Resolved via admin bulk action",
                )
                resolved += 1
            except Exception:
                errors += 1

        if resolved > 0:
            self.message_user(
                request,
                f"Resolved {resolved} dispute(s) as '{status.replace('resolved_', '').replace('_', ' ')}'.",
            )
        if errors > 0:
            self.message_user(
                request,
                f"Failed to resolve {errors} dispute(s).",
                level=messages.WARNING,
            )


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
