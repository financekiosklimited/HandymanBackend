from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.jobs.models import City, Job, JobApplication, JobCategory, JobDispute
from apps.payments.models import (
    HandymanIdentityVerification,
    PaymentRefund,
    StripeConnectedAccount,
    StripeEventLog,
)
from apps.payments.services import (
    JobPaymentService,
    StripeClientService,
    StripeWebhookService,
    WithdrawalService,
    job_payment_service,
    kyc_service,
)
from apps.profiles.models import HandymanProfile, HomeownerProfile


class StripeClientServiceCoverageTests(TestCase):
    def setUp(self):
        self.service = StripeClientService()

    def test_stripe_property_handles_import_error(self):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "stripe":
                raise ImportError("stripe missing")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            self.assertIsNone(self.service.stripe)

        self.assertIsNone(self.service.stripe)

    @override_settings(STRIPE_ENABLED=True)
    def test_as_dict_build_key_and_enabled_true(self):
        fake_obj = SimpleNamespace(api_key=None)
        self.service._stripe = fake_obj

        self.assertTrue(self.service.is_enabled)
        self.assertEqual(self.service._as_dict(None), {})
        self.assertEqual(self.service._as_dict({"a": 1}), {"a": 1})

        class Recursive:
            def to_dict_recursive(self):
                return {"ok": True}

        self.assertEqual(self.service._as_dict(Recursive()), {"ok": True})

        class Plain:
            def __init__(self):
                self.hello = "world"

        self.assertEqual(self.service._as_dict(Plain()), {"hello": "world"})
        self.assertEqual(self.service._as_dict(5), {})

        long_part = "x" * 400
        key = self.service.build_idempotency_key("prefix", long_part)
        self.assertLessEqual(len(key), 255)
        self.assertTrue(key.startswith("prefix:"))

    @override_settings(STRIPE_ENABLED=True, STRIPE_SECRET_KEY="sk_test_cov")
    def test_stripe_property_import_success_sets_module(self):
        service = StripeClientService()
        self.assertIsNotNone(service.stripe)

    @override_settings(STRIPE_ENABLED=False)
    def test_mock_paths_when_disabled(self):
        self.assertIn(
            "cus_mock_",
            self.service.create_customer("a@b.com", {"x": "y"}, "idem")["id"],
        )
        account = self.service.create_connected_account("a@b.com", "CA", {}, "idem")
        self.assertIn("acct_mock_", account["id"])
        self.assertIn("url", self.service.create_account_link("acct_1", "r", "r", "k"))
        self.assertIn(
            "vs_mock_",
            self.service.create_identity_session({}, "https://a", "k")["id"],
        )
        self.assertEqual(
            self.service.retrieve_identity_session("vs_1")["status"], "verified"
        )

        intent = self.service.create_payment_intent(
            {"amount": 123, "currency": "cad"}, "k"
        )
        self.assertIn("pi_mock_", intent["id"])
        self.assertEqual(self.service.retrieve_payment_intent("pi_1")["id"], "pi_1")
        self.assertEqual(
            self.service.capture_payment_intent("pi_1", 100, "k")["amount_received"],
            100,
        )
        self.assertEqual(
            self.service.cancel_payment_intent("pi_1", "k")["status"], "canceled"
        )
        self.assertIn("re_mock_", self.service.create_refund({}, "k")["id"])
        self.assertIn("po_mock_", self.service.create_payout("acct_1", {}, "k")["id"])
        self.assertIn("available", self.service.retrieve_balance("acct_1"))

        payload = b'{"id":"evt_1","type":"payout.paid","data":{"object":{}}}'
        event = self.service.construct_event(payload, "sig", "secret")
        self.assertEqual(event["id"], "evt_1")

    @override_settings(STRIPE_ENABLED=True)
    def test_enabled_paths_call_underlying_stripe_sdk(self):
        fake_stripe = SimpleNamespace()
        fake_stripe.Customer = SimpleNamespace(
            create=MagicMock(return_value={"id": "cus_1"})
        )
        fake_stripe.Account = SimpleNamespace(
            create=MagicMock(return_value={"id": "acct_1"})
        )
        fake_stripe.AccountLink = SimpleNamespace(
            create=MagicMock(return_value={"url": "https://x", "expires_at": 1})
        )
        fake_stripe.identity = SimpleNamespace(
            VerificationSession=SimpleNamespace(
                create=MagicMock(return_value={"id": "vs_1", "url": "https://vs"}),
                retrieve=MagicMock(return_value={"id": "vs_1", "status": "verified"}),
            )
        )
        fake_stripe.PaymentIntent = SimpleNamespace(
            create=MagicMock(return_value={"id": "pi_1"}),
            retrieve=MagicMock(
                return_value={"id": "pi_1", "status": "requires_capture"}
            ),
            capture=MagicMock(return_value={"id": "pi_1", "status": "succeeded"}),
            cancel=MagicMock(return_value={"id": "pi_1", "status": "canceled"}),
        )
        fake_stripe.Refund = SimpleNamespace(
            create=MagicMock(return_value={"id": "re_1"})
        )
        fake_stripe.Payout = SimpleNamespace(
            create=MagicMock(return_value={"id": "po_1"})
        )
        fake_stripe.Balance = SimpleNamespace(
            retrieve=MagicMock(return_value={"available": [], "pending": []})
        )
        fake_stripe.Webhook = SimpleNamespace(
            construct_event=MagicMock(
                return_value={"id": "evt_1", "type": "payout.paid"}
            )
        )

        self.service._stripe = fake_stripe

        self.assertEqual(
            self.service.create_customer("a@b.com", {}, "k")["id"],
            "cus_1",
        )
        self.assertEqual(
            self.service.create_connected_account("a@b.com", "CA", {}, "k")["id"],
            "acct_1",
        )
        self.assertEqual(
            self.service.create_account_link("acct_1", "r", "r", "k")["url"],
            "https://x",
        )
        self.assertEqual(
            self.service.create_identity_session({}, "r", "k")["id"],
            "vs_1",
        )
        self.assertEqual(
            self.service.retrieve_identity_session("vs_1")["status"], "verified"
        )
        self.assertEqual(
            self.service.create_payment_intent({"amount": 100}, "k")["id"],
            "pi_1",
        )
        self.assertEqual(self.service.retrieve_payment_intent("pi_1")["id"], "pi_1")
        self.assertEqual(
            self.service.capture_payment_intent("pi_1", 100, "k")["status"],
            "succeeded",
        )
        self.assertEqual(
            self.service.cancel_payment_intent("pi_1", "k")["status"],
            "canceled",
        )
        self.assertEqual(self.service.create_refund({}, "k")["id"], "re_1")
        self.assertEqual(self.service.create_payout("acct", {}, "k")["id"], "po_1")
        self.assertIn("available", self.service.retrieve_balance("acct_1"))
        self.assertEqual(
            self.service.construct_event(b"{}", "sig", "sec")["id"],
            "evt_1",
        )


class PaymentDomainServiceCoverageTests(TestCase):
    def setUp(self):
        self.homeowner = User.objects.create_user(
            email="owner_cov@example.com", password="pass123"
        )
        self.handyman = User.objects.create_user(
            email="handy_cov@example.com", password="pass123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        UserRole.objects.create(user=self.handyman, role="handyman")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Owner",
            phone_verified_at=timezone.now(),
        )
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Handy",
            phone_verified_at=timezone.now(),
        )

        self.category = JobCategory.objects.create(
            name="Plumbing", slug="plumbing-cov", is_active=True
        )
        self.city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-cov",
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
            is_direct_offer=True,
            target_handyman=self.handyman,
            offer_status="pending",
        )
        self.application = JobApplication.objects.create(
            job=self.job,
            handyman=self.handyman,
            predicted_hours=Decimal("2.5"),
            estimated_total_price=Decimal("120.00"),
            status="pending",
        )

    def _create_connected_and_identity(self):
        connected, _ = StripeConnectedAccount.objects.update_or_create(
            user=self.handyman,
            defaults={
                "stripe_account_id": "acct_cov",
                "charges_enabled": True,
                "payouts_enabled": True,
                "details_submitted": True,
            },
        )
        HandymanIdentityVerification.objects.update_or_create(
            user=self.handyman,
            defaults={
                "verification_session_id": "vs_cov",
                "status": "verified",
                "verified_at": timezone.now(),
            },
        )
        return connected

    @override_settings(STRIPE_ENABLED=False, STRIPE_AUTHORIZATION_ENFORCED=True)
    def test_misc_uncovered_job_payment_branches(self):
        self._create_connected_and_identity()
        self.assertEqual(job_payment_service._to_cents(None), 0)
        self.assertEqual(
            job_payment_service._get_target_handyman(
                self.job, application=self.application
            ),
            self.handyman,
        )

        self.job.assigned_handyman = self.handyman
        self.job.target_handyman = None
        self.job.save(
            update_fields=["assigned_handyman", "target_handyman", "updated_at"]
        )
        self.assertEqual(
            job_payment_service._get_target_handyman(self.job),
            self.handyman,
        )

        self.job.assigned_handyman = None
        self.job.target_handyman = self.handyman
        self.job.save(
            update_fields=["assigned_handyman", "target_handyman", "updated_at"]
        )
        self.assertEqual(
            job_payment_service._get_target_handyman(self.job),
            self.handyman,
        )

        self.job.assigned_handyman = None
        self.job.target_handyman = None
        self.job.save(
            update_fields=["assigned_handyman", "target_handyman", "updated_at"]
        )
        self.assertIsNone(job_payment_service._get_target_handyman(self.job))

        payment = job_payment_service.authorize_for_application(
            homeowner=self.homeowner,
            application=self.application,
        )["job_payment"]
        payment.status = "authorized"
        payment.save(update_fields=["status", "updated_at"])
        job_payment_service.ensure_job_authorized(self.job)

        payment.status = "failed"
        payment.save(update_fields=["status", "updated_at"])
        with self.assertRaisesRegex(ValidationError, "not authorized yet"):
            job_payment_service.ensure_job_authorized(self.job)

    @override_settings(STRIPE_ENABLED=False, STRIPE_AUTHORIZATION_ENFORCED=True)
    def test_authorize_for_job_branch_without_cancel_when_custom_authorized_set(self):
        self._create_connected_and_identity()
        existing = job_payment_service.authorize_for_application(
            homeowner=self.homeowner,
            application=self.application,
        )["job_payment"]
        existing.status = "processing"
        existing.authorized_amount_cents = 1
        existing.save(update_fields=["status", "authorized_amount_cents", "updated_at"])

        original_statuses = job_payment_service.AUTHORIZED_STATUSES
        try:
            job_payment_service.AUTHORIZED_STATUSES = set(original_statuses) | {
                "processing"
            }
            with patch.object(
                JobPaymentService,
                "cancel_uncaptured",
                wraps=job_payment_service.cancel_uncaptured,
            ) as mock_cancel:
                result = job_payment_service.authorize_for_application(
                    homeowner=self.homeowner,
                    application=self.application,
                )
            self.assertFalse(mock_cancel.called)
            self.assertNotEqual(result["payment_intent_id"], existing.payment_intent_id)
        finally:
            job_payment_service.AUTHORIZED_STATUSES = original_statuses

    @override_settings(STRIPE_ENABLED=False)
    def test_kyc_existing_and_onboarding_and_sync_paths(self):
        connected = StripeConnectedAccount.objects.create(
            user=self.handyman,
            stripe_account_id="acct_existing",
            charges_enabled=False,
            payouts_enabled=False,
            details_submitted=False,
        )

        got = kyc_service.get_or_create_connected_account(self.handyman)
        self.assertEqual(got.id, connected.id)

        link = kyc_service.create_connect_onboarding_link(self.handyman)
        self.assertIn("url", link)

        empty_status = kyc_service.get_kyc_status(self.handyman)
        self.assertIn("is_eligible", empty_status)

        kyc_service.sync_connected_account_state({})
        kyc_service.sync_connected_account_state({"id": "acct_missing"})

        kyc_service.sync_connected_account_state(
            {
                "id": "acct_existing",
                "charges_enabled": True,
                "payouts_enabled": True,
                "details_submitted": True,
                "requirements": {"currently_due": ["document"]},
                "disabled_reason": "",
            }
        )
        connected.refresh_from_db()
        self.assertIsNotNone(connected.onboarding_completed_at)

        connected.onboarding_completed_at = None
        connected.save(update_fields=["onboarding_completed_at", "updated_at"])
        kyc_service.sync_connected_account_state(
            {
                "id": "acct_existing",
                "charges_enabled": False,
                "payouts_enabled": True,
                "details_submitted": True,
                "requirements": {"currently_due": []},
            }
        )
        connected.refresh_from_db()
        self.assertIsNone(connected.onboarding_completed_at)

        kyc_service.sync_identity_status({})
        kyc_service.sync_identity_status({"id": "vs_missing"})

        verification = HandymanIdentityVerification.objects.create(
            user=User.objects.create_user(email="x1@example.com", password="pass123"),
            verification_session_id="vs_sync_cov",
            status="pending",
        )
        kyc_service.sync_identity_status({"id": "vs_sync_cov", "status": "verified"})
        verification.refresh_from_db()
        self.assertEqual(verification.status, "verified")

        kyc_service.sync_identity_status(
            {
                "id": "vs_sync_cov",
                "status": "requires_input",
                "last_error": {"code": "bad", "reason": "retry"},
            }
        )
        verification.refresh_from_db()
        self.assertEqual(verification.status, "requires_input")

        kyc_service.sync_identity_status(
            {
                "id": "vs_sync_cov",
                "status": "canceled",
                "last_error": {"code": "fail", "reason": "failed"},
            }
        )
        verification.refresh_from_db()
        self.assertEqual(verification.status, "failed")

    @override_settings(STRIPE_ENABLED=False, STRIPE_AUTHORIZATION_ENFORCED=True)
    def test_job_payment_authorization_and_reuse_paths(self):
        self._create_connected_and_identity()

        with self.assertRaisesRegex(ValidationError, "own job application"):
            job_payment_service.authorize_for_application(
                homeowner=self.handyman,
                application=self.application,
            )

        with self.assertRaisesRegex(ValidationError, "own direct offer"):
            job_payment_service.authorize_for_direct_offer(
                homeowner=self.handyman,
                job=self.job,
            )

        self.job.target_handyman = None
        self.job.save(update_fields=["target_handyman", "updated_at"])
        with self.assertRaisesRegex(ValidationError, "no target handyman"):
            job_payment_service.authorize_for_direct_offer(
                homeowner=self.homeowner,
                job=self.job,
            )
        self.job.target_handyman = self.handyman
        self.job.save(update_fields=["target_handyman", "updated_at"])

        with self.assertRaisesRegex(ValidationError, "No handyman found"):
            job_payment_service._authorize_for_job(
                homeowner=self.homeowner,
                job=self.job,
                service_amount=self.job.estimated_budget,
                target_handyman=None,
            )

        result = job_payment_service.authorize_for_application(
            homeowner=self.homeowner,
            application=self.application,
        )
        payment = result["job_payment"]

        payment.status = "captured"
        payment.save(update_fields=["status", "updated_at"])
        with patch(
            "apps.payments.services.stripe_client_service.retrieve_payment_intent",
            return_value={"client_secret": "sec_1"},
        ) as mock_retrieve:
            reused = job_payment_service.authorize_for_application(
                homeowner=self.homeowner,
                application=self.application,
            )
        self.assertEqual(reused["client_secret"], "sec_1")
        mock_retrieve.assert_called_once()

        payment.refresh_from_db()
        payment.status = "authorized"
        payment.authorized_amount_cents = payment.authorized_amount_cents + 10000
        payment.save(update_fields=["status", "authorized_amount_cents", "updated_at"])
        with patch(
            "apps.payments.services.stripe_client_service.retrieve_payment_intent",
            return_value={"client_secret": "sec_2"},
        ):
            reused = job_payment_service.authorize_for_application(
                homeowner=self.homeowner,
                application=self.application,
            )
        self.assertEqual(reused["client_secret"], "sec_2")

        payment.refresh_from_db()
        payment.status = "authorized"
        payment.authorized_amount_cents = 1
        payment.save(update_fields=["status", "authorized_amount_cents", "updated_at"])
        with patch.object(
            JobPaymentService,
            "cancel_uncaptured",
            wraps=job_payment_service.cancel_uncaptured,
        ) as mock_cancel:
            new_result = job_payment_service.authorize_for_application(
                homeowner=self.homeowner,
                application=self.application,
            )
        self.assertNotEqual(new_result["payment_intent_id"], payment.payment_intent_id)
        self.assertTrue(mock_cancel.called)

    @override_settings(STRIPE_ENABLED=False, STRIPE_AUTHORIZATION_ENFORCED=True)
    def test_job_payment_status_capture_refund_and_sync_paths(self):
        self._create_connected_and_identity()

        self.job.payment_mode = "legacy_exempt"
        self.job.save(update_fields=["payment_mode", "updated_at"])
        self.assertIsNone(job_payment_service.capture_for_completion(self.job))
        job_payment_service.ensure_job_authorized(self.job)

        self.job.payment_mode = "stripe_required"
        self.job.save(update_fields=["payment_mode", "updated_at"])

        with self.assertRaisesRegex(ValidationError, "authorization is required"):
            job_payment_service.ensure_job_authorized(self.job)

        with self.assertRaisesRegex(ValidationError, "not found"):
            job_payment_service.capture_for_completion(self.job)

        not_started = job_payment_service.get_payment_status(self.job)
        self.assertEqual(not_started["status"], "not_started")

        authorized = job_payment_service.authorize_for_application(
            homeowner=self.homeowner,
            application=self.application,
        )["job_payment"]

        authorized.status = "failed"
        authorized.save(update_fields=["status", "updated_at"])
        with self.assertRaisesRegex(ValidationError, "authorized state"):
            job_payment_service.capture_for_completion(self.job)

        authorized.status = "captured"
        authorized.captured_amount_cents = 12000
        authorized.save(update_fields=["status", "captured_amount_cents", "updated_at"])
        returned = job_payment_service.capture_for_completion(self.job)
        self.assertEqual(returned.status, "captured")

        authorized.status = "authorized"
        authorized.authorized_amount_cents = 100
        authorized.service_amount_cents = 10000
        authorized.save(
            update_fields=[
                "status",
                "authorized_amount_cents",
                "service_amount_cents",
                "updated_at",
            ]
        )
        with self.assertRaisesRegex(ValidationError, "top up authorization"):
            job_payment_service.capture_for_completion(self.job)

        authorized.authorized_amount_cents = 20000
        authorized.save(update_fields=["authorized_amount_cents", "updated_at"])
        captured = job_payment_service.capture_for_completion(self.job)
        self.assertEqual(captured.status, "captured")

        self.assertIsNone(
            job_payment_service.refund_captured(
                job_payment=authorized,
                amount_cents=0,
                reason="none",
                source="admin",
            )
        )

        with patch(
            "apps.payments.services.stripe_client_service.create_refund",
            return_value={"id": "re_cov_1", "status": "pending"},
        ):
            refund = job_payment_service.refund_captured(
                job_payment=authorized,
                amount_cents=100,
                reason="partial",
                source="admin",
            )
        self.assertEqual(refund.status, "pending")

        with patch(
            "apps.payments.services.stripe_client_service.create_refund",
            return_value={"id": "re_cov_2", "status": "succeeded"},
        ):
            job_payment_service.refund_captured(
                job_payment=authorized,
                amount_cents=max(authorized.captured_amount_cents - 100, 1),
                reason="rest",
                source="admin",
            )
        authorized.refresh_from_db()
        self.assertIn(authorized.status, ["refunded", "partially_refunded"])

        job_payment_service.sync_payment_intent_event({})
        job_payment_service.sync_payment_intent_event(
            {"id": "pi_missing", "status": "requires_capture"}
        )

        job_payment_service.sync_payment_intent_event(
            {
                "id": authorized.payment_intent_id,
                "status": "requires_capture",
                "amount_capturable": 777,
                "amount_received": 0,
                "last_payment_error": {"code": "code", "message": "msg"},
            }
        )
        authorized.refresh_from_db()
        self.assertEqual(authorized.status, "authorized")

        job_payment_service.sync_payment_intent_event(
            {
                "id": authorized.payment_intent_id,
                "status": "canceled",
                "amount_received": 999,
            }
        )
        authorized.refresh_from_db()
        self.assertEqual(authorized.captured_amount_cents, 0)

        job_payment_service.sync_charge_dispute_event("charge.dispute.created", {})
        job_payment_service.sync_charge_dispute_event(
            "charge.dispute.created",
            {"charge": {"payment_intent": "pi_missing"}},
        )

        authorized.status = "captured"
        authorized.captured_amount_cents = 5000
        authorized.save(update_fields=["status", "captured_amount_cents", "updated_at"])

        job_payment_service.sync_charge_dispute_event(
            "charge.dispute.created",
            {"payment_intent": authorized.payment_intent_id},
        )
        authorized.refresh_from_db()
        self.assertEqual(authorized.status, "disputed")

        job_payment_service.sync_charge_dispute_event(
            "charge.dispute.closed",
            {
                "payment_intent": authorized.payment_intent_id,
                "status": "won",
            },
        )
        authorized.refresh_from_db()
        self.assertEqual(authorized.status, "captured")

        job_payment_service.sync_charge_dispute_event(
            "charge.dispute.closed",
            {
                "payment_intent": authorized.payment_intent_id,
                "status": "lost",
            },
        )
        authorized.refresh_from_db()
        self.assertEqual(authorized.status, "refunded")
        self.assertTrue(
            PaymentRefund.objects.filter(
                job_payment=authorized,
                source="chargeback",
            ).exists()
        )

        job_payment_service.sync_charge_dispute_event(
            "charge.dispute.updated",
            {"payment_intent": authorized.payment_intent_id},
        )
        job_payment_service.sync_charge_dispute_event(
            "charge.dispute.closed",
            {
                "payment_intent": authorized.payment_intent_id,
                "status": "under_review",
            },
        )

    @override_settings(STRIPE_ENABLED=False, STRIPE_AUTHORIZATION_ENFORCED=True)
    def test_resolve_dispute_financial_paths(self):
        self._create_connected_and_identity()
        dispute = JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Issue",
            resolution_deadline=timezone.now() + timedelta(days=1),
        )

        self.job.payment_mode = "legacy_exempt"
        self.job.save(update_fields=["payment_mode", "updated_at"])
        legacy = job_payment_service.resolve_dispute_financial(
            dispute=dispute,
            status="resolved_pay_handyman",
        )
        self.assertEqual(legacy["action"], "legacy_exempt")

        self.job.payment_mode = "stripe_required"
        self.job.save(update_fields=["payment_mode", "updated_at"])

        with self.assertRaisesRegex(ValidationError, "No payment found"):
            job_payment_service.resolve_dispute_financial(
                dispute=dispute,
                status="resolved_pay_handyman",
            )

        payment = job_payment_service.authorize_for_application(
            homeowner=self.homeowner,
            application=self.application,
        )["job_payment"]

        with patch.object(
            JobPaymentService,
            "capture_for_completion",
            return_value=SimpleNamespace(captured_amount_cents=15000),
        ):
            result = job_payment_service.resolve_dispute_financial(
                dispute=dispute,
                status="resolved_pay_handyman",
            )
        self.assertEqual(result["action"], "captured_full")

        payment.refresh_from_db()
        payment.captured_amount_cents = 12000
        payment.status = "captured"
        payment.save(update_fields=["captured_amount_cents", "status", "updated_at"])
        full_refund = job_payment_service.resolve_dispute_financial(
            dispute=dispute,
            status="resolved_full_refund",
        )
        self.assertEqual(full_refund["action"], "refunded_full")

        payment.refresh_from_db()
        payment.captured_amount_cents = 0
        payment.authorized_amount_cents = 14000
        payment.status = "authorized"
        payment.save(
            update_fields=[
                "captured_amount_cents",
                "authorized_amount_cents",
                "status",
                "updated_at",
            ]
        )
        canceled = job_payment_service.resolve_dispute_financial(
            dispute=dispute,
            status="resolved_full_refund",
        )
        self.assertEqual(canceled["action"], "canceled")

        with self.assertRaisesRegex(ValidationError, "Refund percentage is required"):
            job_payment_service.resolve_dispute_financial(
                dispute=dispute,
                status="resolved_partial_refund",
                refund_percentage=None,
            )

        payment.refresh_from_db()
        payment.captured_amount_cents = 10000
        payment.status = "captured"
        payment.save(update_fields=["captured_amount_cents", "status", "updated_at"])
        partial = job_payment_service.resolve_dispute_financial(
            dispute=dispute,
            status="resolved_partial_refund",
            refund_percentage=25,
        )
        self.assertEqual(partial["action"], "refunded_partial")

        payment.refresh_from_db()
        payment.captured_amount_cents = 0
        payment.service_amount_cents = 10000
        payment.status = "authorized"
        payment.save(
            update_fields=[
                "captured_amount_cents",
                "service_amount_cents",
                "status",
                "updated_at",
            ]
        )
        net_partial = job_payment_service.resolve_dispute_financial(
            dispute=dispute,
            status="resolved_partial_refund",
            refund_percentage=40,
        )
        self.assertEqual(net_partial["action"], "captured_net_partial")

        canceled_result = job_payment_service.resolve_dispute_financial(
            dispute=dispute,
            status="cancelled",
        )
        self.assertEqual(canceled_result["action"], "cancelled")

        no_action = job_payment_service.resolve_dispute_financial(
            dispute=dispute,
            status="unknown_status",
        )
        self.assertEqual(no_action["action"], "no_action")

    @override_settings(
        STRIPE_ENABLED=False,
        STRIPE_WITHDRAW_ENABLED=True,
        STRIPE_AUTHORIZATION_ENFORCED=True,
    )
    def test_withdrawal_service_paths(self):
        service = WithdrawalService()

        zero_balance = service.get_wallet_balance(self.handyman)
        self.assertEqual(zero_balance["available_amount"], "0.00")

        connected = self._create_connected_and_identity()
        with patch(
            "apps.payments.services.stripe_client_service.retrieve_balance",
            return_value={
                "available": [
                    {"amount": 100, "currency": "usd"},
                    {"amount": 7000, "currency": "cad"},
                ],
                "pending": [{"amount": 500, "currency": "cad"}],
            },
        ):
            wallet = service.get_wallet_balance(self.handyman)
        self.assertEqual(wallet["available_cents"], 7000)
        self.assertEqual(wallet["pending_cents"], 500)

        with patch(
            "apps.payments.services.stripe_client_service.retrieve_balance",
            return_value={
                "available": [{"amount": 8000, "currency": "cad"}],
                "pending": [{"amount": 200, "currency": "usd"}],
            },
        ):
            wallet_first_hit = service.get_wallet_balance(self.handyman)
        self.assertEqual(wallet_first_hit["available_cents"], 8000)
        self.assertEqual(wallet_first_hit["pending_cents"], 0)

        with patch(
            "apps.payments.services.stripe_client_service.retrieve_balance",
            return_value={
                "available": [],
                "pending": [{"amount": 300, "currency": "cad"}],
            },
        ):
            wallet_available_empty = service.get_wallet_balance(self.handyman)
        self.assertEqual(wallet_available_empty["available_cents"], 0)
        self.assertEqual(wallet_available_empty["pending_cents"], 300)

        with override_settings(STRIPE_WITHDRAW_ENABLED=False):
            with self.assertRaisesRegex(ValidationError, "not enabled"):
                service.create_withdrawal(self.handyman, Decimal("10.00"), "standard")

        with patch(
            "apps.payments.services.kyc_service.is_handyman_eligible",
            return_value=False,
        ):
            with self.assertRaisesRegex(ValidationError, "complete KYC"):
                service.create_withdrawal(self.handyman, Decimal("10.00"), "standard")

        connected.delete()
        with patch(
            "apps.payments.services.kyc_service.is_handyman_eligible", return_value=True
        ):
            with self.assertRaisesRegex(ValidationError, "Connected account not found"):
                service.create_withdrawal(self.handyman, Decimal("10.00"), "standard")

        connected = self._create_connected_and_identity()
        with patch(
            "apps.payments.services.kyc_service.is_handyman_eligible", return_value=True
        ):
            with patch.object(
                service, "get_wallet_balance", return_value={"available_cents": 10000}
            ):
                with self.assertRaisesRegex(ValidationError, "greater than zero"):
                    service.create_withdrawal(
                        self.handyman, Decimal("0.00"), "standard"
                    )

                with self.assertRaisesRegex(ValidationError, "Insufficient"):
                    service.create_withdrawal(
                        self.handyman, Decimal("200.00"), "standard"
                    )

        with patch(
            "apps.payments.services.kyc_service.is_handyman_eligible", return_value=True
        ):
            with patch.object(
                service, "get_wallet_balance", return_value={"available_cents": 10000}
            ):
                with override_settings(STRIPE_INSTANT_PAYOUT_FEE_PERCENT=100):
                    with self.assertRaisesRegex(ValidationError, "too small"):
                        service.create_withdrawal(
                            self.handyman, Decimal("1.00"), "instant"
                        )

        with patch(
            "apps.payments.services.kyc_service.is_handyman_eligible", return_value=True
        ):
            with patch.object(
                service,
                "get_wallet_balance",
                return_value={"available_cents": 10000, "currency": "cad"},
            ):
                standard = service.create_withdrawal(
                    self.handyman,
                    Decimal("10.00"),
                    "standard",
                )
        self.assertEqual(standard.status, "processing")

        with patch(
            "apps.payments.services.kyc_service.is_handyman_eligible", return_value=True
        ):
            with patch.object(
                service,
                "get_wallet_balance",
                return_value={"available_cents": 10000, "currency": "cad"},
            ):
                instant = service.create_withdrawal(
                    self.handyman,
                    Decimal("10.00"),
                    "instant",
                )
        self.assertEqual(instant.method, "instant")

        service.sync_payout_event("payout.paid", {})
        service.sync_payout_event("payout.paid", {"id": "po_missing"})

        instant.stripe_payout_id = "po_cov"
        instant.status = "processing"
        instant.save(update_fields=["stripe_payout_id", "status", "updated_at"])

        service.sync_payout_event(
            "payout.failed",
            {
                "id": "po_cov",
                "failure_code": "code",
                "failure_message": "msg",
            },
        )
        instant.refresh_from_db()
        self.assertEqual(instant.status, "failed")

        service.sync_payout_event("payout.canceled", {"id": "po_cov"})
        instant.refresh_from_db()
        self.assertEqual(instant.status, "canceled")

        service.sync_payout_event("payout.unknown", {"id": "po_cov"})


class StripeWebhookServiceCoverageTests(TestCase):
    def test_verify_event_calls_client(self):
        service = StripeWebhookService()
        with patch(
            "apps.payments.services.stripe_client_service.construct_event",
            return_value={"id": "evt_1", "type": "payout.paid"},
        ) as mock_construct:
            event = service.verify_event(b"{}", "sig")
        self.assertEqual(event["id"], "evt_1")
        mock_construct.assert_called_once()

    def test_process_event_validation_and_dedupe_and_failure(self):
        service = StripeWebhookService()

        with self.assertRaisesRegex(ValidationError, "Invalid Stripe event payload"):
            service.process_event({"id": "", "type": ""})

        result = service.process_event(
            {
                "id": "evt_new",
                "type": "payment_intent.canceled",
                "data": {"object": {}},
            }
        )
        self.assertFalse(result["deduplicated"])

        deduped = service.process_event(
            {
                "id": "evt_new",
                "type": "payment_intent.canceled",
                "data": {"object": {}},
            }
        )
        self.assertTrue(deduped["deduplicated"])

        with patch.object(
            StripeWebhookService, "_dispatch", side_effect=RuntimeError("boom")
        ):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                service.process_event(
                    {
                        "id": "evt_fail",
                        "type": "account.updated",
                        "data": {"object": {}},
                    }
                )

        self.assertFalse(
            StripeEventLog.objects.filter(stripe_event_id="evt_fail").exists()
        )

    def test_replay_log_and_dispatch_routing(self):
        service = StripeWebhookService()
        log = StripeEventLog.objects.create(
            stripe_event_id="evt_replay",
            event_type="payout.paid",
            payload_json={
                "id": "evt_replay",
                "type": "payout.paid",
                "data": {"object": {"id": "po_1"}},
            },
            processing_status="failed",
        )

        replay = service.replay_log(log)
        self.assertFalse(replay["deduplicated"])

        with patch("apps.payments.services.kyc_service.sync_identity_status") as p1:
            service._dispatch("identity.verification_session.verified", {"id": "vs"})
            p1.assert_called_once()

        with patch(
            "apps.payments.services.kyc_service.sync_connected_account_state"
        ) as p2:
            service._dispatch("account.updated", {"id": "acct"})
            p2.assert_called_once()

        with patch(
            "apps.payments.services.job_payment_service.sync_payment_intent_event"
        ) as p3:
            service._dispatch("payment_intent.canceled", {"id": "pi"})
            p3.assert_called_once()

        with patch(
            "apps.payments.services.job_payment_service.sync_charge_dispute_event"
        ) as p4:
            service._dispatch("charge.dispute.updated", {"id": "dp"})
            p4.assert_called_once()

        with patch("apps.payments.services.withdrawal_service.sync_payout_event") as p5:
            service._dispatch("payout.paid", {"id": "po"})
            p5.assert_called_once()

        service._dispatch("unknown.event", {"id": "x"})
        service.SUPPORTED_EVENTS = set(service.SUPPORTED_EVENTS) | {"other.supported"}
        service._dispatch("other.supported", {"id": "x"})
