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
    JobApplicationAttachment,
    JobApplicationMaterial,
    JobAttachment,
    JobCategory,
    JobDispute,
    JobReimbursement,
    JobReimbursementAttachment,
    JobReimbursementCategory,
    JobTask,
    Review,
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

    try:
        from apps.payments.models import JobPayment

        kpis.update(
            {
                "authorized_pending_capture": JobPayment.objects.filter(
                    status="authorized"
                ).count(),
                "failed_financial_actions": JobDispute.objects.filter(
                    financial_action_status="failed"
                ).count(),
                "unresolved_chargebacks": JobPayment.objects.filter(
                    status="disputed"
                ).count(),
            }
        )
    except Exception:
        kpis.update(
            {
                "authorized_pending_capture": 0,
                "failed_financial_actions": 0,
                "unresolved_chargebacks": 0,
            }
        )

    disputes = pending_disputes.select_related(
        "job",
        "job__homeowner",
        "job__assigned_handyman",
        "job__payment",
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
    extra = 1
    min_num = 0
    fields = (
        "title",
        "description",
        "order",
        "is_completed",
        "completed_by",
        "completed_at",
    )
    readonly_fields = ("completed_by", "completed_at")
    ordering = ("order", "created_at")


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
        "started_at",
        "ended_at",
        "start_latitude",
        "start_longitude",
        "end_latitude",
        "end_longitude",
    )
    ordering = ("-started_at",)


class DailyReportTaskInline(TabularInline):
    model = DailyReportTask
    extra = 0
    fields = ("task", "marked_complete", "notes")
    ordering = ("task__order",)


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
        "reviewed_at",
        "reviewed_by",
    )
    ordering = ("-report_date",)


class JobDisputeInline(TabularInline):
    model = JobDispute
    extra = 0
    fields = (
        "initiated_by",
        "status",
        "resolution_deadline",
        "resolved_at",
        "resolved_by",
        "refund_percentage",
    )
    readonly_fields = (
        "resolved_at",
        "resolved_by",
    )
    ordering = ("-created_at",)


class JobAttachmentInline(TabularInline):
    """
    Inline admin for JobAttachment model.
    """

    model = JobAttachment
    extra = 0
    fields = ("file", "file_type", "file_name", "file_size", "order")
    readonly_fields = ("file_name", "file_size")
    ordering = ("order",)


class JobApplicationMaterialInline(TabularInline):
    """
    Inline admin for JobApplicationMaterial in JobApplication detail view.
    """

    model = JobApplicationMaterial
    extra = 0
    fields = ("name", "price", "description")
    ordering = ("created_at",)


class JobApplicationAttachmentInline(TabularInline):
    """
    Inline admin for JobApplicationAttachment in JobApplication detail view.
    """

    model = JobApplicationAttachment
    extra = 0
    fields = ("file", "file_name", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("created_at",)


class JobApplicationInline(TabularInline):
    """
    Inline admin for JobApplication in Job detail view.
    """

    model = JobApplication
    extra = 0
    fields = ("handyman", "status", "status_at", "created_at")
    readonly_fields = ("status_at", "created_at")
    ordering = ("-created_at",)
    show_change_link = True


class ReviewInline(TabularInline):
    """
    Inline admin for Review in Job detail view.
    """

    model = Review
    extra = 0
    fields = (
        "reviewer_type",
        "rating",
        "reviewer_name",
        "reviewer_email",
        "reviewee_name",
        "reviewee_email",
        "comment",
        "created_at",
    )
    readonly_fields = (
        "reviewer_name",
        "reviewer_email",
        "reviewee_name",
        "reviewee_email",
        "created_at",
    )
    ordering = ("-created_at",)

    @display(description="Reviewer Name")
    def reviewer_name(self, obj):
        """Display reviewer's full name."""
        return obj.reviewer.get_full_name() or "-"

    @display(description="Reviewer Email")
    def reviewer_email(self, obj):
        """Display reviewer's email."""
        return obj.reviewer.email

    @display(description="Reviewee Name")
    def reviewee_name(self, obj):
        """Display reviewee's full name."""
        return obj.reviewee.get_full_name() or "-"

    @display(description="Reviewee Email")
    def reviewee_email(self, obj):
        """Display reviewee's email."""
        return obj.reviewee.email


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
        "is_direct_offer_display",
        "offer_status_display",
        "target_handyman_link",
        "budget_display",
        "application_count",
        "active_tasks",
        "pending_reports",
        "open_disputes",
        "created_at",
    )
    list_filter = (
        "status",
        "is_direct_offer",
        "offer_status",
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
        "target_handyman__email",
        "target_handyman__first_name",
        "target_handyman__last_name",
        "postal_code",
    )
    ordering = ("-created_at",)
    autocomplete_fields = (
        "homeowner",
        "category",
        "city",
        "assigned_handyman",
        "target_handyman",
    )
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "status_at",
        "completion_requested_at",
        "completed_at",
        "offer_responded_at",
    )
    inlines = [
        JobAttachmentInline,
        JobTaskInline,
        WorkSessionInline,
        DailyReportInline,
        JobDisputeInline,
        JobApplicationInline,
        ReviewInline,
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
            "Direct Offer",
            {
                "fields": (
                    "is_direct_offer",
                    "target_handyman",
                    "offer_status",
                    "offer_expires_at",
                    "offer_responded_at",
                    "offer_rejection_reason",
                ),
                "classes": ("collapse",),
                "description": "Direct offer settings for jobs sent to specific handymen",
            },
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

    @display(description="Direct", boolean=True)
    def is_direct_offer_display(self, obj):
        """Display whether this is a direct offer."""
        return obj.is_direct_offer

    @display(description="Offer Status")
    def offer_status_display(self, obj):
        """Display offer status with color coding for direct offers."""
        if not obj.is_direct_offer:
            return "-"
        if not obj.offer_status:
            return "-"
        status_colors = {
            "pending": "🟡",
            "accepted": "✅",
            "rejected": "🔴",
            "expired": "⏰",
            "converted": "🔄",
        }
        icon = status_colors.get(obj.offer_status, "")
        return f"{icon} {obj.get_offer_status_display()}"

    @display(description="Target Handyman")
    def target_handyman_link(self, obj):
        """Display target handyman as clickable link for direct offers."""
        if not obj.is_direct_offer or not obj.target_handyman:
            return "-"
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.target_handyman.pk,
            obj.target_handyman.email,
        )

    def save_model(self, request, obj, form, change):
        """
        Override save_model to log sensitive changes for audit trail.
        Logs status changes and handyman reassignments.
        """
        if change:
            old_obj = Job.objects.get(pk=obj.pk)
            changes = []

            # Track status changes
            if old_obj.status != obj.status:
                changes.append(
                    f"Status changed from '{old_obj.get_status_display()}' "
                    f"to '{obj.get_status_display()}'"
                )

            # Track handyman reassignment
            old_handyman = old_obj.assigned_handyman
            new_handyman = obj.assigned_handyman
            if old_handyman != new_handyman:
                old_name = old_handyman.email if old_handyman else "None"
                new_name = new_handyman.email if new_handyman else "None"
                changes.append(
                    f"Assigned handyman changed from '{old_name}' to '{new_name}'"
                )

            # Log changes using Django's built-in admin logging
            if changes:
                from django.contrib.admin.models import CHANGE, LogEntry
                from django.contrib.contenttypes.models import ContentType

                LogEntry.objects.create(
                    user=request.user,
                    content_type=ContentType.objects.get_for_model(obj),
                    object_id=obj.pk,
                    object_repr=str(obj),
                    action_flag=CHANGE,
                    change_message="; ".join(changes),
                )

        super().save_model(request, obj, form, change)


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
                    "end_photo",
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
        "financial_status_display",
        "financial_outcome_display",
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
                    "financial_action_status",
                    "financial_outcome_amount_cents",
                    "financial_action_error",
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

    @display(description="Financial")
    def financial_status_display(self, obj):
        styles = {
            "not_started": ("gray", "Not Started"),
            "success": ("green", "Success"),
            "failed": ("red", "Failed"),
            "legacy_exempt": ("blue", "Legacy"),
        }
        color, label = styles.get(
            obj.financial_action_status, ("gray", obj.financial_action_status)
        )
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            label,
        )

    @display(description="Outcome")
    def financial_outcome_display(self, obj):
        if obj.financial_outcome_amount_cents is None:
            return "-"
        amount = obj.financial_outcome_amount_cents / 100
        return f"${amount:.2f}"

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
        payment_summary = None
        try:
            payment = getattr(job, "payment", None)
            if payment:
                payment_summary = {
                    "status": payment.status,
                    "authorized": payment.authorized_amount_cents / 100,
                    "capturable": payment.capturable_amount_cents / 100,
                    "captured": payment.captured_amount_cents / 100,
                    "platform_fee": payment.platform_fee_cents / 100,
                    "currency": payment.currency,
                }
        except Exception:
            payment_summary = None

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
            "payment_summary": payment_summary,
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


@admin.register(JobAttachment)
class JobAttachmentAdmin(ModelAdmin):
    """
    Admin interface for JobAttachment model with Unfold styling.
    """

    list_display = (
        "thumbnail_preview",
        "job_title",
        "file_type_display",
        "file_name",
        "file_size_display",
        "file_url_display",
        "order",
        "created_at",
    )
    list_filter = ("file_type", "created_at")
    search_fields = ("job__title", "file_name")
    ordering = ("job", "order")
    autocomplete_fields = ("job",)
    readonly_fields = ("public_id", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Attachment Information",
            {
                "fields": (
                    "public_id",
                    "job",
                    "file",
                    "file_type",
                    "file_name",
                    "file_size",
                    "thumbnail",
                    "duration_seconds",
                    "order",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Preview")
    def thumbnail_preview(self, obj):
        """Display thumbnail preview for images/videos."""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-width: 50px; max-height: 50px; '
                'object-fit: cover; border-radius: 4px;" />',
                obj.thumbnail.url,
            )
        elif obj.file_type == "image" and obj.file:
            return format_html(
                '<img src="{}" style="max-width: 50px; max-height: 50px; '
                'object-fit: cover; border-radius: 4px;" />',
                obj.file.url,
            )
        elif obj.file_type == "video":
            return format_html('<span style="font-size: 24px;" title="Video">🎬</span>')
        return "-"

    @display(description="Job")
    def job_title(self, obj):
        """Display job title."""
        return obj.job.title

    @display(description="Type")
    def file_type_display(self, obj):
        """Display file type with icon."""
        type_icons = {
            "image": "🖼️",
            "video": "🎬",
            "document": "📄",
        }
        icon = type_icons.get(obj.file_type, "📁")
        return f"{icon} {obj.get_file_type_display()}"

    @display(description="File Size")
    def file_size_display(self, obj):
        """Display file size in KB or MB."""
        if obj.file_size:
            if obj.file_size > 1024 * 1024:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
            return f"{obj.file_size / 1024:.1f} KB"
        return "-"

    @display(description="File URL")
    def file_url_display(self, obj):
        """Display file URL as a clickable link."""
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.file.url,
                obj.file_name[:40] + "..."
                if len(obj.file_name) > 40
                else obj.file_name,
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
        "predicted_hours",
        "estimated_total_price",
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
    inlines = [JobApplicationMaterialInline, JobApplicationAttachmentInline]

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
            "Proposal Details",
            {
                "fields": (
                    "predicted_hours",
                    "estimated_total_price",
                    "negotiation_reasoning",
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


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    """
    Admin interface for Review model with Unfold styling.
    """

    list_display = (
        "job_link",
        "reviewer_type_display",
        "rating_display",
        "reviewer_name",
        "reviewer_email_link",
        "reviewee_name",
        "reviewee_email_link",
        "created_at",
    )
    list_filter = ("reviewer_type", "rating", "created_at")
    search_fields = (
        "job__title",
        "reviewer__email",
        "reviewer__first_name",
        "reviewer__last_name",
        "reviewee__email",
        "reviewee__first_name",
        "reviewee__last_name",
        "comment",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("job", "reviewer", "reviewee")
    readonly_fields = ("public_id", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Review Information",
            {
                "fields": (
                    "public_id",
                    "job",
                    "reviewer_type",
                    "reviewer",
                    "reviewee",
                    "rating",
                    "comment",
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
            obj.job.title[:40] + "..." if len(obj.job.title) > 40 else obj.job.title,
        )

    @display(description="Type")
    def reviewer_type_display(self, obj):
        """Display reviewer type with icon."""
        icons = {
            "homeowner": "🏠",
            "handyman": "🔧",
        }
        icon = icons.get(obj.reviewer_type, "")
        return f"{icon} {obj.get_reviewer_type_display()}"

    @display(description="Rating")
    def rating_display(self, obj):
        """Display rating as numeric value."""
        return f"{obj.rating}/5"

    @display(description="Reviewer Name")
    def reviewer_name(self, obj):
        """Display reviewer's full name."""
        return obj.reviewer.get_full_name() or "-"

    @display(description="Reviewer Email")
    def reviewer_email_link(self, obj):
        """Display reviewer's email as clickable link."""
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.reviewer.pk,
            obj.reviewer.email,
        )

    @display(description="Reviewee Name")
    def reviewee_name(self, obj):
        """Display reviewee's full name."""
        return obj.reviewee.get_full_name() or "-"

    @display(description="Reviewee Email")
    def reviewee_email_link(self, obj):
        """Display reviewee's email as clickable link."""
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.reviewee.pk,
            obj.reviewee.email,
        )


@admin.register(JobApplicationMaterial)
class JobApplicationMaterialAdmin(ModelAdmin):
    """
    Admin interface for JobApplicationMaterial model with Unfold styling.
    """

    list_display = (
        "application_link",
        "name",
        "price",
        "description",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = (
        "application__job__title",
        "name",
        "description",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("application",)
    readonly_fields = ("public_id", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Material Information",
            {
                "fields": (
                    "public_id",
                    "application",
                    "name",
                    "price",
                    "description",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Application")
    def application_link(self, obj):
        """Display application as clickable link."""
        return format_html(
            '<a href="/admin/jobs/jobapplication/{}/change/">{}</a>',
            obj.application.pk,
            f"{obj.application.job.title[:30]}...",
        )


@admin.register(JobApplicationAttachment)
class JobApplicationAttachmentAdmin(ModelAdmin):
    """
    Admin interface for JobApplicationAttachment model with Unfold styling.
    """

    list_display = (
        "thumbnail_preview",
        "application_link",
        "file_type_display",
        "file_name",
        "file_size_display",
        "file_link",
        "created_at",
    )
    list_filter = ("file_type", "created_at")
    search_fields = (
        "application__job__title",
        "file_name",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("application",)
    readonly_fields = ("public_id", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Attachment Information",
            {
                "fields": (
                    "public_id",
                    "application",
                    "file",
                    "file_type",
                    "file_name",
                    "file_size",
                    "thumbnail",
                    "duration_seconds",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Preview")
    def thumbnail_preview(self, obj):
        """Display thumbnail preview for images/videos."""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-width: 50px; max-height: 50px; '
                'object-fit: cover; border-radius: 4px;" />',
                obj.thumbnail.url,
            )
        elif obj.file_type == "image" and obj.file:
            return format_html(
                '<img src="{}" style="max-width: 50px; max-height: 50px; '
                'object-fit: cover; border-radius: 4px;" />',
                obj.file.url,
            )
        elif obj.file_type == "video":
            return format_html('<span style="font-size: 24px;" title="Video">🎬</span>')
        elif obj.file_type == "document":
            return format_html(
                '<span style="font-size: 24px;" title="Document">📄</span>'
            )
        return "-"

    @display(description="Application")
    def application_link(self, obj):
        """Display application as clickable link."""
        return format_html(
            '<a href="/admin/jobs/jobapplication/{}/change/">{}</a>',
            obj.application.pk,
            f"{obj.application.job.title[:30]}...",
        )

    @display(description="Type")
    def file_type_display(self, obj):
        """Display file type with icon."""
        type_icons = {
            "image": "🖼️",
            "video": "🎬",
            "document": "📄",
        }
        icon = type_icons.get(obj.file_type, "📁")
        return f"{icon} {obj.get_file_type_display()}"

    @display(description="Size")
    def file_size_display(self, obj):
        """Display file size in KB or MB."""
        if obj.file_size:
            if obj.file_size > 1024 * 1024:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
            return f"{obj.file_size / 1024:.1f} KB"
        return "-"

    @display(description="File")
    def file_link(self, obj):
        """Display file as clickable link."""
        if obj.file:
            return format_html('<a href="{}" target="_blank">View</a>', obj.file.url)
        return "-"


# =============================================================================
# Reimbursement Admin
# =============================================================================


@admin.register(JobReimbursementCategory)
class JobReimbursementCategoryAdmin(ModelAdmin):
    """Admin interface for JobReimbursementCategory model with Unfold styling."""

    list_display = (
        "name",
        "slug",
        "icon_display",
        "is_active",
        "reimbursement_count",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
    readonly_fields = ("public_id", "created_at", "updated_at")
    list_per_page = 25

    fieldsets = (
        (
            "Category Information",
            {
                "fields": (
                    "public_id",
                    "name",
                    "slug",
                    "description",
                    "icon",
                    "is_active",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Icon")
    def icon_display(self, obj):
        """Display icon with visual representation."""
        if obj.icon:
            return f"{obj.icon}"
        return "-"

    @display(description="Reimbursements")
    def reimbursement_count(self, obj):
        """Display count of reimbursements using this category."""
        count = obj.reimbursements.count()
        if count > 0:
            url = f"/admin/jobs/jobreimbursement/?category__id__exact={obj.pk}"
            return format_html('<a href="{}">{}</a>', url, count)
        return "0"


class JobReimbursementAttachmentInline(TabularInline):
    """Inline for reimbursement attachments."""

    model = JobReimbursementAttachment
    extra = 0
    fields = ("file", "file_name", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("created_at",)


@admin.register(JobReimbursement)
class JobReimbursementAdmin(ModelAdmin):
    """Admin interface for JobReimbursement model with Unfold styling."""

    list_display = (
        "job_link",
        "handyman_link",
        "name",
        "category",
        "amount_display",
        "status_display",
        "reviewed_at",
        "created_at",
    )
    list_filter = ("status", "category", "created_at")
    search_fields = ("job__title", "handyman__email", "name")
    ordering = ("-created_at",)
    autocomplete_fields = ("job", "handyman", "category", "reviewed_by")
    readonly_fields = ("public_id", "created_at", "updated_at", "reviewed_at")
    inlines = [JobReimbursementAttachmentInline]
    date_hierarchy = "created_at"
    list_per_page = 25
    actions = ["approve_reimbursements", "reject_reimbursements"]

    fieldsets = (
        (
            "Reimbursement Information",
            {
                "fields": (
                    "public_id",
                    "job",
                    "handyman",
                    "name",
                    "category",
                    "amount",
                    "notes",
                )
            },
        ),
        (
            "Review",
            {
                "fields": (
                    "status",
                    "homeowner_comment",
                    "reviewed_by",
                    "reviewed_at",
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
            obj.job.title[:40] + "..." if len(obj.job.title) > 40 else obj.job.title,
        )

    @display(description="Handyman")
    def handyman_link(self, obj):
        """Display handyman email as clickable link."""
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.handyman.pk,
            obj.handyman.email,
        )

    @display(description="Amount")
    def amount_display(self, obj):
        """Display amount formatted."""
        return f"${obj.amount}"

    @display(description="Status")
    def status_display(self, obj):
        """Display status with color coding."""
        status_colors = {
            "pending": "🟡",
            "approved": "✅",
            "rejected": "🔴",
        }
        icon = status_colors.get(obj.status, "")
        return f"{icon} {obj.get_status_display()}"

    # -------------------------------------------------------------------------
    # Admin Actions
    # -------------------------------------------------------------------------

    @admin.action(description="Approve selected reimbursements")
    def approve_reimbursements(self, request, queryset):
        """Bulk approve selected pending reimbursements."""
        pending_qs = queryset.filter(status="pending")
        count = pending_qs.count()

        if count == 0:
            self.message_user(
                request,
                "No pending reimbursements selected.",
                level=messages.WARNING,
            )
            return

        pending_qs.update(
            status="approved",
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(
            request,
            f"Successfully approved {count} reimbursement(s).",
            level=messages.SUCCESS,
        )

    @admin.action(description="Reject selected reimbursements")
    def reject_reimbursements(self, request, queryset):
        """Bulk reject selected pending reimbursements."""
        pending_qs = queryset.filter(status="pending")
        count = pending_qs.count()

        if count == 0:
            self.message_user(
                request,
                "No pending reimbursements selected.",
                level=messages.WARNING,
            )
            return

        pending_qs.update(
            status="rejected",
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(
            request,
            f"Successfully rejected {count} reimbursement(s).",
            level=messages.SUCCESS,
        )


@admin.register(JobReimbursementAttachment)
class JobReimbursementAttachmentAdmin(ModelAdmin):
    """Admin interface for JobReimbursementAttachment model with Unfold styling."""

    list_display = (
        "thumbnail_preview",
        "reimbursement_link",
        "file_type_display",
        "file_name",
        "file_size_display",
        "file_link",
        "created_at",
    )
    list_filter = ("file_type", "created_at")
    search_fields = (
        "reimbursement__job__title",
        "reimbursement__name",
        "file_name",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("reimbursement",)
    readonly_fields = ("public_id", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        (
            "Attachment Information",
            {
                "fields": (
                    "public_id",
                    "reimbursement",
                    "file",
                    "file_type",
                    "file_name",
                    "file_size",
                    "thumbnail",
                    "duration_seconds",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Preview")
    def thumbnail_preview(self, obj):
        """Display thumbnail preview for images/videos."""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-width: 50px; max-height: 50px; '
                'object-fit: cover; border-radius: 4px;" />',
                obj.thumbnail.url,
            )
        elif obj.file_type == "image" and obj.file:
            return format_html(
                '<img src="{}" style="max-width: 50px; max-height: 50px; '
                'object-fit: cover; border-radius: 4px;" />',
                obj.file.url,
            )
        elif obj.file_type == "video":
            return format_html('<span style="font-size: 24px;" title="Video">🎬</span>')
        elif obj.file_type == "document":
            return format_html(
                '<span style="font-size: 24px;" title="Document">📄</span>'
            )
        return "-"

    @display(description="Reimbursement")
    def reimbursement_link(self, obj):
        """Display reimbursement as clickable link."""
        return format_html(
            '<a href="/admin/jobs/jobreimbursement/{}/change/">{}</a>',
            obj.reimbursement.pk,
            f"{obj.reimbursement.name[:30]}...",
        )

    @display(description="Type")
    def file_type_display(self, obj):
        """Display file type with icon."""
        type_icons = {
            "image": "🖼️",
            "video": "🎬",
            "document": "📄",
        }
        icon = type_icons.get(obj.file_type, "📁")
        return f"{icon} {obj.get_file_type_display()}"

    @display(description="Size")
    def file_size_display(self, obj):
        """Display file size in KB or MB."""
        if obj.file_size:
            if obj.file_size > 1024 * 1024:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
            return f"{obj.file_size / 1024:.1f} KB"
        return "-"

    @display(description="File")
    def file_link(self, obj):
        """Display file as clickable link."""
        if obj.file:
            return format_html('<a href="{}" target="_blank">View</a>', obj.file.url)
        return "-"
