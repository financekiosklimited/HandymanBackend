"""Replay failed Stripe webhook events from event log."""

from django.core.management.base import BaseCommand

from apps.payments.models import StripeEventLog
from apps.payments.services import stripe_webhook_service


class Command(BaseCommand):
    help = "Replay failed Stripe webhook events"

    def handle(self, *args, **options):
        failed_events = StripeEventLog.objects.filter(processing_status="failed")

        replayed = 0
        errors = 0
        for event_log in failed_events.iterator():
            try:
                stripe_webhook_service.replay_log(event_log)
                replayed += 1
            except Exception:
                errors += 1

        self.stdout.write(self.style.SUCCESS(f"Replayed {replayed} event(s)"))
        if errors:
            self.stdout.write(self.style.WARNING(f"Failed to replay {errors} event(s)"))
