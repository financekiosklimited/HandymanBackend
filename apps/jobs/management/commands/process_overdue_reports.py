"""
Auto-approve daily reports that are pending for more than 3 days.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.jobs.models import DailyReport
from apps.notifications.services import notification_service


class Command(BaseCommand):
    help = "Auto-approve overdue pending daily reports after 3 days"

    def handle(self, *args, **options):
        now = timezone.now()
        overdue_reports = DailyReport.objects.filter(
            status="pending", review_deadline__lte=now
        ).select_related("job", "handyman")

        count = 0
        for report in overdue_reports.iterator():
            report.status = "approved"
            report.reviewed_at = now
            report.save(update_fields=["status", "reviewed_at", "updated_at"])

            # Send notification to handyman about auto-approval
            notification_service.create_and_send_notification(
                user=report.handyman,
                notification_type="daily_report_approved",
                title="Daily report auto-approved",
                body=f"Your report for {report.report_date} was automatically approved after the review deadline.",
                target_role="handyman",
                data={
                    "job_id": str(report.job.public_id),
                    "report_id": str(report.public_id),
                },
                triggered_by=None,
            )

            count += 1

        self.stdout.write(self.style.SUCCESS(f"Auto-approved {count} overdue reports"))
