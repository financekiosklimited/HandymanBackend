from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import User
from apps.payments.models import (
    StripeConnectedAccount,
    StripeEventLog,
    WithdrawalRequest,
)


class PaymentsCommandTests(TestCase):
    def setUp(self):
        self.handyman = User.objects.create_user(
            email="handy@example.com", password="pass123"
        )
        self.connected = StripeConnectedAccount.objects.create(
            user=self.handyman,
            stripe_account_id="acct_cmd",
            charges_enabled=True,
            payouts_enabled=True,
            details_submitted=True,
        )

    @patch("apps.payments.services.stripe_client_service.create_payout")
    def test_retry_failed_withdrawals(self, mock_create_payout):
        mock_create_payout.return_value = {"id": "po_new"}
        WithdrawalRequest.objects.create(
            handyman=self.handyman,
            connected_account=self.connected,
            amount_cents=5000,
            instant_fee_cents=0,
            currency="cad",
            method="standard",
            status="failed",
            stripe_payout_id="po_old",
        )

        out = StringIO()
        call_command("retry_failed_withdrawals", stdout=out)

        withdrawal = WithdrawalRequest.objects.get(handyman=self.handyman)
        self.assertEqual(withdrawal.status, "processing")
        self.assertEqual(withdrawal.stripe_payout_id, "po_new")
        self.assertIn("Retried 1 withdrawal(s)", out.getvalue())

    @patch("apps.payments.services.stripe_webhook_service.replay_log")
    def test_replay_failed_stripe_events(self, mock_replay):
        StripeEventLog.objects.create(
            stripe_event_id="evt_failed",
            event_type="payment_intent.payment_failed",
            payload_json={
                "id": "evt_failed",
                "type": "payment_intent.payment_failed",
                "data": {"object": {"id": "pi_1"}},
            },
            processing_status="failed",
        )

        out = StringIO()
        call_command("replay_failed_stripe_events", stdout=out)

        self.assertEqual(mock_replay.call_count, 1)
        self.assertIn("Replayed 1 event(s)", out.getvalue())
