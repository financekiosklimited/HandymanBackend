from decimal import Decimal
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.jobs.models import City, Job, JobApplication, JobCategory
from apps.payments.models import JobPayment, StripeConnectedAccount, WithdrawalRequest
from apps.profiles.models import HandymanProfile, HomeownerProfile


class PaymentsMobileViewsTests(APITestCase):
    def setUp(self):
        self.homeowner = User.objects.create_user(
            email="owner@example.com", password="pass123"
        )
        self.handyman = User.objects.create_user(
            email="handy@example.com", password="pass123"
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

        self.homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
            "phone_verified": True,
        }
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

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
            is_direct_offer=True,
            target_handyman=self.handyman,
            offer_status="pending",
        )
        self.application = JobApplication.objects.create(
            job=self.job,
            handyman=self.handyman,
            estimated_total_price=Decimal("120.00"),
            status="pending",
        )

    @override_settings(STRIPE_ENABLED=False)
    def test_handyman_kyc_status(self):
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get("/api/v1/mobile/handyman/kyc/status/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("is_eligible", response.data["data"])

    @override_settings(STRIPE_ENABLED=False)
    def test_application_payment_authorization(self):
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.post(
            f"/api/v1/mobile/homeowner/applications/{self.application.public_id}/payment-authorization/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("payment_intent_id", response.data["data"])

    def test_job_payment_status(self):
        JobPayment.objects.create(
            job=self.job,
            payment_intent_id="pi_test",
            status="authorized",
            service_amount_cents=12000,
            reserve_cents=3600,
            authorized_amount_cents=15600,
            capturable_amount_cents=15600,
            captured_amount_cents=0,
            platform_fee_cents=1200,
            currency="cad",
        )
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(
            f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/payment-status/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["status"], "authorized")

    @override_settings(STRIPE_ENABLED=False)
    def test_direct_offer_payment_authorization(self):
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.post(
            f"/api/v1/mobile/homeowner/direct-offers/{self.job.public_id}/payment-authorization/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("client_secret", response.data["data"])

    @override_settings(STRIPE_WITHDRAW_ENABLED=True)
    @patch("apps.payments.services.withdrawal_service.get_wallet_balance")
    @patch("apps.payments.services.kyc_service.is_handyman_eligible")
    def test_create_withdrawal(self, mock_eligible, mock_balance):
        StripeConnectedAccount.objects.create(
            user=self.handyman,
            stripe_account_id="acct_test",
            charges_enabled=True,
            payouts_enabled=True,
            details_submitted=True,
        )
        mock_eligible.return_value = True
        mock_balance.return_value = {
            "currency": "cad",
            "available_amount": "100.00",
            "pending_amount": "0.00",
            "available_cents": 10000,
            "pending_cents": 0,
        }

        self.client.force_authenticate(user=self.handyman)
        response = self.client.post(
            "/api/v1/mobile/handyman/wallet/withdrawals/",
            {"amount": "25.00", "method": "standard"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["status"], "processing")

    @override_settings(STRIPE_ENABLED=False)
    def test_handyman_connect_onboarding_link_success(self):
        self.client.force_authenticate(user=self.handyman)
        response = self.client.post(
            "/api/v1/mobile/handyman/kyc/connect/onboarding-link/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("url", response.data["data"])

    @patch("apps.payments.views.mobile.kyc_service.create_connect_onboarding_link")
    def test_handyman_connect_onboarding_link_error(self, mock_create_link):
        mock_create_link.side_effect = RuntimeError("boom")
        self.client.force_authenticate(user=self.handyman)
        response = self.client.post(
            "/api/v1/mobile/handyman/kyc/connect/onboarding-link/"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data["errors"])

    @override_settings(STRIPE_ENABLED=False)
    def test_handyman_identity_session_success(self):
        self.client.force_authenticate(user=self.handyman)
        response = self.client.post("/api/v1/mobile/handyman/kyc/identity/session/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("verification_session_id", response.data["data"])

    @patch(
        "apps.payments.views.mobile.kyc_service.create_identity_verification_session"
    )
    def test_handyman_identity_session_error(self, mock_create_session):
        mock_create_session.side_effect = RuntimeError("boom")
        self.client.force_authenticate(user=self.handyman)
        response = self.client.post("/api/v1/mobile/handyman/kyc/identity/session/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data["errors"])

    @patch("apps.payments.views.mobile.withdrawal_service.get_wallet_balance")
    def test_handyman_wallet_balance_success(self, mock_get_wallet_balance):
        mock_get_wallet_balance.return_value = {
            "currency": "cad",
            "available_amount": "100.00",
            "pending_amount": "10.00",
            "available_cents": 10000,
            "pending_cents": 1000,
        }
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get("/api/v1/mobile/handyman/wallet/balance/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("available_cents", response.data["data"])
        self.assertNotIn("pending_cents", response.data["data"])

    def test_handyman_withdrawals_list_pagination(self):
        connected = StripeConnectedAccount.objects.create(
            user=self.handyman,
            stripe_account_id="acct_list",
            charges_enabled=True,
            payouts_enabled=True,
            details_submitted=True,
        )
        WithdrawalRequest.objects.create(
            handyman=self.handyman,
            connected_account=connected,
            amount_cents=1000,
            currency="cad",
            method="standard",
            status="processing",
            stripe_payout_id="po_1",
        )
        WithdrawalRequest.objects.create(
            handyman=self.handyman,
            connected_account=connected,
            amount_cents=2000,
            currency="cad",
            method="instant",
            instant_fee_cents=20,
            status="processing",
            stripe_payout_id="po_2",
        )

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(
            "/api/v1/mobile/handyman/wallet/withdrawals/?page=1&page_size=1"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 2)

    @override_settings(STRIPE_WITHDRAW_ENABLED=True)
    def test_create_withdrawal_validation_error(self):
        self.client.force_authenticate(user=self.handyman)
        response = self.client.post(
            "/api/v1/mobile/handyman/wallet/withdrawals/",
            {"amount": "0.00", "method": "standard"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("amount", response.data["errors"])

    @override_settings(STRIPE_WITHDRAW_ENABLED=True)
    @patch("apps.payments.views.mobile.withdrawal_service.create_withdrawal")
    def test_create_withdrawal_service_error(self, mock_create_withdrawal):
        mock_create_withdrawal.side_effect = RuntimeError("boom")
        self.client.force_authenticate(user=self.handyman)
        response = self.client.post(
            "/api/v1/mobile/handyman/wallet/withdrawals/",
            {"amount": "1.00", "method": "standard"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data["errors"])

    @patch("apps.payments.views.mobile.job_payment_service.authorize_for_application")
    def test_application_payment_authorization_error(self, mock_authorize):
        mock_authorize.side_effect = RuntimeError("boom")
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.post(
            f"/api/v1/mobile/homeowner/applications/{self.application.public_id}/payment-authorization/"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data["errors"])

    @patch("apps.payments.views.mobile.job_payment_service.authorize_for_direct_offer")
    def test_direct_offer_payment_authorization_error(self, mock_authorize):
        mock_authorize.side_effect = RuntimeError("boom")
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.post(
            f"/api/v1/mobile/homeowner/direct-offers/{self.job.public_id}/payment-authorization/"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data["errors"])
