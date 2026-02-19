"""Retry failed Stripe payout requests for withdrawals."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.payments.models import WithdrawalRequest
from apps.payments.services import stripe_client_service


class Command(BaseCommand):
    help = "Retry failed withdrawal payouts"

    def handle(self, *args, **options):
        failed_withdrawals = WithdrawalRequest.objects.filter(status="failed")

        retried = 0
        errors = 0
        for item in failed_withdrawals.iterator():
            try:
                payout_amount = item.amount_cents - item.instant_fee_cents
                idempotency_key = stripe_client_service.build_idempotency_key(
                    "withdrawal-command-retry",
                    item.public_id,
                    timezone.now().strftime("%Y%m%d%H%M"),
                )
                payout = stripe_client_service.create_payout(
                    item.connected_account.stripe_account_id,
                    {
                        "amount": payout_amount,
                        "currency": item.currency,
                        "method": "instant" if item.method == "instant" else "standard",
                        "metadata": {
                            "withdrawal_request_public_id": str(item.public_id),
                            "retry_source": "management_command",
                        },
                    },
                    idempotency_key,
                )
                item.status = "processing"
                item.stripe_payout_id = payout.get("id")
                item.failure_code = ""
                item.failure_message = ""
                item.save(
                    update_fields=[
                        "status",
                        "stripe_payout_id",
                        "failure_code",
                        "failure_message",
                        "updated_at",
                    ]
                )
                retried += 1
            except Exception as exc:
                item.failure_message = str(exc)
                item.save(update_fields=["failure_message", "updated_at"])
                errors += 1

        self.stdout.write(self.style.SUCCESS(f"Retried {retried} withdrawal(s)"))
        if errors:
            self.stdout.write(
                self.style.WARNING(f"Failed to retry {errors} withdrawal(s)")
            )
