"""
Admin dashboard callback and data utilities.
"""

import json
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone


def get_kpi_cards():
    """
    Get KPI card data for dashboard.
    """
    from apps.accounts.models import User
    from apps.jobs.models import (
        DailyReport,
        Job,
        JobApplication,
        JobDispute,
        WorkSession,
    )

    try:
        from apps.payments.models import JobPayment, StripeEventLog, WithdrawalRequest
    except Exception:
        JobPayment = None
        StripeEventLog = None
        WithdrawalRequest = None

    cards = [
        {
            "title": "Total Users",
            "metric": User.objects.count(),
        },
        {
            "title": "Jobs In Progress",
            "metric": Job.objects.filter(status="in_progress").count(),
        },
        {
            "title": "Pending Completion",
            "metric": Job.objects.filter(status="pending_completion").count(),
        },
        {
            "title": "Pending Daily Reports",
            "metric": DailyReport.objects.filter(status="pending").count(),
        },
        {
            "title": "Open Disputes",
            "metric": JobDispute.objects.exclude(status__startswith="resolved").count(),
        },
        {
            "title": "Active Work Sessions",
            "metric": WorkSession.objects.filter(status="in_progress").count(),
        },
        {
            "title": "Pending Applications",
            "metric": JobApplication.objects.filter(status="pending").count(),
        },
    ]

    if JobPayment is not None:
        cards.extend(
            [
                {
                    "title": "Auth Pending Capture",
                    "metric": JobPayment.objects.filter(status="authorized").count(),
                },
                {
                    "title": "Failed Withdrawals",
                    "metric": WithdrawalRequest.objects.filter(status="failed").count()
                    if WithdrawalRequest is not None
                    else 0,
                },
                {
                    "title": "Failed Stripe Events",
                    "metric": StripeEventLog.objects.filter(
                        processing_status="failed"
                    ).count()
                    if StripeEventLog is not None
                    else 0,
                },
            ]
        )

    return cards


def get_user_signups_chart_data():
    """
    Get user signups over last 30 days.
    """
    from apps.accounts.models import User

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=29)

    signups = (
        User.objects.filter(created_at__date__gte=start_date)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    # Build complete date range with zeros for missing dates
    date_counts = {item["date"]: item["count"] for item in signups}
    labels = []
    data = []
    current = start_date
    while current <= end_date:
        labels.append(current.strftime("%b %d"))
        data.append(date_counts.get(current, 0))
        current += timedelta(days=1)

    return json.dumps(
        {
            "labels": labels,
            "datasets": [
                {
                    "label": "User Signups",
                    "data": data,
                    "borderColor": "rgb(59, 130, 246)",
                    "backgroundColor": "rgba(59, 130, 246, 0.1)",
                    "fill": True,
                    "tension": 0.4,
                }
            ],
        }
    )


def get_jobs_by_status_chart_data():
    """
    Get job counts grouped by status.
    """
    from apps.jobs.models import Job

    status_labels = {
        "draft": "Draft",
        "open": "Open",
        "in_progress": "In Progress",
        "pending_completion": "Pending Completion",
        "completed": "Completed",
        "disputed": "Disputed",
        "cancelled": "Cancelled",
    }

    jobs_by_status = (
        Job.objects.values("status").annotate(count=Count("id")).order_by("status")
    )

    status_counts = {item["status"]: item["count"] for item in jobs_by_status}

    labels = list(status_labels.values())
    data = [status_counts.get(key, 0) for key in status_labels.keys()]

    return json.dumps(
        {
            "labels": labels,
            "datasets": [
                {
                    "label": "Jobs",
                    "data": data,
                    "backgroundColor": [
                        "rgb(156, 163, 175)",  # gray - draft
                        "rgb(59, 130, 246)",  # blue - open
                        "rgb(245, 158, 11)",  # amber - in progress
                        "rgb(34, 197, 94)",  # green - completed
                        "rgb(239, 68, 68)",  # red - cancelled
                    ],
                }
            ],
        }
    )


def dashboard_callback(request, context):
    """
    Unfold dashboard callback.
    Adds custom variables to the admin index template.
    """
    context.update(
        {
            "kpi_cards": get_kpi_cards(),
            "user_signups_chart": get_user_signups_chart_data(),
            "jobs_by_status_chart": get_jobs_by_status_chart_data(),
        }
    )
    return context
