from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.jobs.models import City, Job, JobApplication, JobCategory, JobDispute
from apps.payments.models import JobPayment, StripeConnectedAccount, WithdrawalRequest
from apps.payments.services import (
    job_payment_service,
    kyc_service,
    withdrawal_service,
)
from apps.profiles.models import HandymanProfile, HomeownerProfile


class PaymentServicesTests(TestCase):
    def setUp(self):
        self.homeowner = User.objects.create_user(
            email="owner@example.com", password="pass123"
        )
        self.handyman = User.objects.create_user(
            email="handy@example.com", password="pass123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        UserRole.objects.create(user=self.handyman, role="handyman")
        HomeownerProfile.objects.create(user=self.homeowner, display_name="Owner")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Handy",
            phone_verified_at=timezone.now(),
        )

        self.category = JobCategory.objects.create(
            name="Plumbing", slug="plumbing", is_active=True
        )
        self.city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            is_active=True,
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            title="Fix sink",
            description="Leak",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Street",
            payment_mode="stripe_required",
        )
        self.application = JobApplication.objects.create(
            job=self.job,
            handyman=self.handyman,
            predicted_hours=Decimal("2.5"),
            estimated_total_price=Decimal("150.00"),
            status="pending",
        )

    @override_settings(STRIPE_ENABLED=False)
    def test_create_connected_account(self):
        connected = kyc_service.get_or_create_connected_account(self.handyman)
        self.assertTrue(connected.stripe_account_id.startswith("acct_mock_"))
        self.assertFalse(connected.charges_enabled)

    @override_settings(STRIPE_ENABLED=False)
    def test_create_identity_session(self):
        payload = kyc_service.create_identity_verification_session(self.handyman)
        self.assertIn("verification_session_id", payload)
        self.assertEqual(payload["status"], "pending")

    @override_settings(STRIPE_ENABLED=False, STRIPE_AUTHORIZATION_ENFORCED=True)
    def test_authorize_for_application(self):
        result = job_payment_service.authorize_for_application(
            homeowner=self.homeowner,
            application=self.application,
        )
        payment = result["job_payment"]

        self.assertIsNotNone(payment)
        self.assertEqual(payment.job, self.job)
        self.assertEqual(payment.service_amount_cents, 15000)
        self.assertEqual(payment.reserve_cents, 4500)
        self.assertEqual(payment.authorized_amount_cents, 19500)
        self.assertEqual(payment.platform_fee_cents, 1500)

    @override_settings(STRIPE_AUTHORIZATION_ENFORCED=True)
    def test_ensure_job_authorized_raises_when_missing(self):
        with self.assertRaisesRegex(
            ValidationError, "Payment authorization is required"
        ):
            job_payment_service.ensure_job_authorized(self.job)

    @override_settings(STRIPE_ENABLED=False, STRIPE_AUTHORIZATION_ENFORCED=True)
    def test_capture_for_completion(self):
        job_payment_service.authorize_for_application(self.homeowner, self.application)
        payment = JobPayment.objects.get(job=self.job)
        payment.status = "authorized"
        payment.authorized_amount_cents = 25000
        payment.save(update_fields=["status", "authorized_amount_cents", "updated_at"])

        captured = job_payment_service.capture_for_completion(self.job)
        self.assertEqual(captured.status, "captured")
        self.assertEqual(captured.captured_amount_cents, 15000)

    @override_settings(STRIPE_ENABLED=False, STRIPE_AUTHORIZATION_ENFORCED=True)
    def test_resolve_dispute_full_refund(self):
        job_payment_service.authorize_for_application(self.homeowner, self.application)
        payment = JobPayment.objects.get(job=self.job)
        payment.status = "captured"
        payment.captured_amount_cents = 12000
        payment.save(update_fields=["status", "captured_amount_cents", "updated_at"])

        dispute = JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Issue",
            resolution_deadline=timezone.now() + timedelta(days=1),
        )

        result = job_payment_service.resolve_dispute_financial(
            dispute=dispute,
            status="resolved_full_refund",
            refund_percentage=100,
        )

        self.assertEqual(result["action"], "refunded_full")
        payment.refresh_from_db()
        self.assertIn(payment.status, ["refunded", "partially_refunded"])

    @override_settings(
        STRIPE_ENABLED=False,
        STRIPE_WITHDRAW_ENABLED=True,
        STRIPE_AUTHORIZATION_ENFORCED=True,
    )
    @patch("apps.payments.services.withdrawal_service.get_wallet_balance")
    def test_create_withdrawal(self, mock_get_balance):
        connected = StripeConnectedAccount.objects.create(
            user=self.handyman,
            stripe_account_id="acct_test",
            charges_enabled=True,
            payouts_enabled=True,
            details_submitted=True,
        )
        kyc_service.create_identity_verification_session(self.handyman)
        identity = self.handyman.identity_verification
        identity.status = "verified"
        identity.verified_at = timezone.now()
        identity.save(update_fields=["status", "verified_at", "updated_at"])

        mock_get_balance.return_value = {
            "currency": "cad",
            "available_amount": "100.00",
            "pending_amount": "0.00",
            "available_cents": 10000,
            "pending_cents": 0,
        }

        request = withdrawal_service.create_withdrawal(
            handyman=self.handyman,
            amount=Decimal("50.00"),
            method="instant",
        )

        self.assertEqual(request.status, "processing")
        self.assertEqual(request.connected_account, connected)
        self.assertEqual(request.amount_cents, 5000)

    @override_settings(STRIPE_ENABLED=False)
    def test_sync_payout_event(self):
        connected = StripeConnectedAccount.objects.create(
            user=self.handyman,
            stripe_account_id="acct_sync",
            charges_enabled=True,
            payouts_enabled=True,
            details_submitted=True,
        )
        withdrawal = WithdrawalRequest.objects.create(
            handyman=self.handyman,
            connected_account=connected,
            amount_cents=2000,
            currency="cad",
            method="standard",
            stripe_payout_id="po_sync",
            status="processing",
        )

        withdrawal_service.sync_payout_event("payout.paid", {"id": "po_sync"})
        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, "paid")
        self.assertIsNotNone(withdrawal.processed_at)
