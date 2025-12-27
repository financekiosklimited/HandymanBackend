"""
Auto-resolve disputes that passed the 3-day resolution deadline, favoring handyman payment.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.jobs.models import JobDispute
from apps.jobs.services import dispute_service

User = get_user_model()


class Command(BaseCommand):
    help = "Auto-resolve overdue disputes after deadline (pay handyman)"

    def handle(self, *args, **options):
        now = timezone.now()
        overdue = JobDispute.objects.filter(
            status__in=["pending", "in_review"], resolution_deadline__lte=now
        ).select_related("job", "job__homeowner", "job__assigned_handyman")

        # Get system user for auto-resolution (or first superuser as fallback)
        system_user = User.objects.filter(is_superuser=True).first()

        count = 0
        errors = 0
        for dispute in overdue.iterator():
            try:
                dispute_service.resolve_dispute(
                    admin_user=system_user,
                    dispute=dispute,
                    status="resolved_pay_handyman",
                    refund_percentage=None,
                    admin_notes="Auto-resolved: Resolution deadline passed without action.",
                )
                count += 1
            except Exception as e:
                errors += 1
                self.stderr.write(
                    self.style.ERROR(
                        f"Failed to resolve dispute {dispute.public_id}: {e}"
                    )
                )

        self.stdout.write(self.style.SUCCESS(f"Auto-resolved {count} disputes"))
        if errors > 0:
            self.stdout.write(
                self.style.WARNING(f"Failed to resolve {errors} disputes")
            )
