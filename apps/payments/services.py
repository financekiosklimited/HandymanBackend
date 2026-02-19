"""Service layer for Stripe KYC, payments, withdrawals, and webhook processing."""

import json
import logging
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.payments.models import (
    HandymanIdentityVerification,
    JobPayment,
    PaymentRefund,
    StripeConnectedAccount,
    StripeCustomerProfile,
    StripeEventLog,
    WithdrawalRequest,
)

logger = logging.getLogger(__name__)


class StripeClientService:
    """Thin wrapper for Stripe SDK operations with idempotency support."""

    def __init__(self):
        self._stripe = None

    @property
    def stripe(self):
        """Lazy load Stripe SDK and configure API key."""
        if self._stripe is None:
            try:
                import stripe

                stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")
                self._stripe = stripe
            except ImportError:
                logger.warning("stripe package not installed")
                self._stripe = False

        return self._stripe if self._stripe is not False else None

    @property
    def is_enabled(self):
        """True when Stripe integration is enabled and SDK is available."""
        return (
            bool(getattr(settings, "STRIPE_ENABLED", False)) and self.stripe is not None
        )

    def build_idempotency_key(self, prefix, *parts):
        """Build deterministic idempotency keys."""
        clean_parts = [str(part) for part in parts if part is not None]
        suffix = ":".join(clean_parts)
        return f"{prefix}:{suffix}"[:255]

    def _as_dict(self, value):
        """Normalize Stripe objects to plain dicts."""
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if hasattr(value, "to_dict_recursive"):
            return value.to_dict_recursive()
        if hasattr(value, "__dict__"):
            return dict(value.__dict__)
        return {}

    def create_customer(self, email, metadata, idempotency_key):
        """Create Stripe customer or return mock payload when disabled."""
        if not self.is_enabled:
            mock_id = f"cus_mock_{uuid4().hex[:18]}"
            return {"id": mock_id, "email": email}

        customer = self.stripe.Customer.create(
            email=email,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )
        return self._as_dict(customer)

    def create_connected_account(self, email, country, metadata, idempotency_key):
        """Create connected account for handyman."""
        if not self.is_enabled:
            mock_id = f"acct_mock_{uuid4().hex[:18]}"
            return {
                "id": mock_id,
                "type": "express",
                "charges_enabled": False,
                "payouts_enabled": False,
                "details_submitted": False,
                "requirements": {"currently_due": []},
            }

        account = self.stripe.Account.create(
            type="express",
            country=country,
            email=email,
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
            business_type="individual",
            metadata=metadata,
            idempotency_key=idempotency_key,
        )
        return self._as_dict(account)

    def create_account_link(self, account_id, refresh_url, return_url, idempotency_key):
        """Create Stripe Connect onboarding link."""
        if not self.is_enabled:
            return {
                "url": f"https://connect.stripe.mock/onboarding/{account_id}",
                "expires_at": int((timezone.now() + timedelta(minutes=30)).timestamp()),
            }

        link = self.stripe.AccountLink.create(
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
            idempotency_key=idempotency_key,
        )
        return self._as_dict(link)

    def create_identity_session(self, metadata, return_url, idempotency_key):
        """Create Stripe Identity verification session."""
        if not self.is_enabled:
            mock_id = f"vs_mock_{uuid4().hex[:18]}"
            return {
                "id": mock_id,
                "status": "requires_input",
                "url": f"https://identity.stripe.mock/session/{mock_id}",
            }

        session = self.stripe.identity.VerificationSession.create(
            type="document",
            metadata=metadata,
            return_url=return_url,
            idempotency_key=idempotency_key,
        )
        return self._as_dict(session)

    def retrieve_identity_session(self, verification_session_id):
        """Retrieve Stripe Identity session."""
        if not self.is_enabled:
            return {"id": verification_session_id, "status": "verified"}

        session = self.stripe.identity.VerificationSession.retrieve(
            verification_session_id
        )
        return self._as_dict(session)

    def create_payment_intent(self, payload, idempotency_key):
        """Create payment intent (destination charge with manual capture)."""
        if not self.is_enabled:
            mock_id = f"pi_mock_{uuid4().hex[:18]}"
            return {
                "id": mock_id,
                "status": "requires_confirmation",
                "client_secret": f"{mock_id}_secret_mock",
                "amount": payload.get("amount", 0),
                "amount_capturable": 0,
                "amount_received": 0,
                "currency": payload.get("currency", "cad"),
            }

        intent = self.stripe.PaymentIntent.create(
            idempotency_key=idempotency_key, **payload
        )
        return self._as_dict(intent)

    def retrieve_payment_intent(self, payment_intent_id):
        """Retrieve payment intent."""
        if not self.is_enabled:
            return {
                "id": payment_intent_id,
                "status": "requires_capture",
                "amount": 0,
                "amount_capturable": 0,
                "amount_received": 0,
                "currency": "cad",
            }

        intent = self.stripe.PaymentIntent.retrieve(payment_intent_id)
        return self._as_dict(intent)

    def capture_payment_intent(
        self, payment_intent_id, amount_to_capture, idempotency_key
    ):
        """Capture previously authorized payment intent."""
        if not self.is_enabled:
            return {
                "id": payment_intent_id,
                "status": "succeeded",
                "amount_received": amount_to_capture,
                "amount_capturable": 0,
            }

        intent = self.stripe.PaymentIntent.capture(
            payment_intent_id,
            amount_to_capture=amount_to_capture,
            idempotency_key=idempotency_key,
        )
        return self._as_dict(intent)

    def cancel_payment_intent(self, payment_intent_id, idempotency_key):
        """Cancel uncaptured payment intent."""
        if not self.is_enabled:
            return {"id": payment_intent_id, "status": "canceled"}

        intent = self.stripe.PaymentIntent.cancel(
            payment_intent_id,
            idempotency_key=idempotency_key,
        )
        return self._as_dict(intent)

    def create_refund(self, payload, idempotency_key):
        """Create refund for captured payment."""
        if not self.is_enabled:
            return {"id": f"re_mock_{uuid4().hex[:18]}", "status": "succeeded"}

        refund = self.stripe.Refund.create(idempotency_key=idempotency_key, **payload)
        return self._as_dict(refund)

    def create_payout(self, account_id, payload, idempotency_key):
        """Create payout on connected account."""
        if not self.is_enabled:
            return {
                "id": f"po_mock_{uuid4().hex[:18]}",
                "status": "in_transit",
                "amount": payload.get("amount", 0),
                "currency": payload.get("currency", "cad"),
            }

        payout = self.stripe.Payout.create(
            stripe_account=account_id,
            idempotency_key=idempotency_key,
            **payload,
        )
        return self._as_dict(payout)

    def retrieve_balance(self, account_id):
        """Retrieve connected account balance."""
        if not self.is_enabled:
            return {
                "available": [{"amount": 0, "currency": "cad"}],
                "pending": [{"amount": 0, "currency": "cad"}],
            }

        balance = self.stripe.Balance.retrieve(stripe_account=account_id)
        return self._as_dict(balance)

    def construct_event(self, payload, sig_header, webhook_secret):
        """Verify and construct Stripe webhook event."""
        if not self.is_enabled:
            return json.loads(payload.decode("utf-8"))

        event = self.stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        return self._as_dict(event)


class KycService:
    """KYC business logic for Connect onboarding and Identity checks."""

    def get_or_create_connected_account(self, handyman):
        """Get or create connected account record for handyman."""
        account = StripeConnectedAccount.objects.filter(user=handyman).first()
        if account:
            return account

        country = getattr(settings, "STRIPE_COUNTRY", "CA")
        idempotency_key = stripe_client_service.build_idempotency_key(
            "connect-account-create",
            handyman.public_id,
        )
        created = stripe_client_service.create_connected_account(
            email=handyman.email,
            country=country,
            metadata={"user_public_id": str(handyman.public_id)},
            idempotency_key=idempotency_key,
        )

        requirements = created.get("requirements", {}) or {}
        currently_due = requirements.get("currently_due", [])

        account = StripeConnectedAccount.objects.create(
            user=handyman,
            stripe_account_id=created.get("id", ""),
            account_type=created.get("type", "express"),
            charges_enabled=bool(created.get("charges_enabled", False)),
            payouts_enabled=bool(created.get("payouts_enabled", False)),
            details_submitted=bool(created.get("details_submitted", False)),
            requirements_due=currently_due,
            disabled_reason=created.get("disabled_reason", "") or "",
        )
        return account

    def create_connect_onboarding_link(self, handyman):
        """Create account onboarding link for handyman."""
        account = self.get_or_create_connected_account(handyman)

        refresh_url = getattr(
            settings, "STRIPE_CONNECT_REFRESH_URL", "https://example.com/refresh"
        )
        return_url = getattr(
            settings, "STRIPE_CONNECT_RETURN_URL", "https://example.com/return"
        )

        idempotency_key = stripe_client_service.build_idempotency_key(
            "connect-onboarding-link",
            handyman.public_id,
            timezone.now().strftime("%Y%m%d%H"),
        )

        link = stripe_client_service.create_account_link(
            account_id=account.stripe_account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            idempotency_key=idempotency_key,
        )

        return {
            "url": link.get("url"),
            "expires_at": link.get("expires_at"),
            "account_id": account.stripe_account_id,
        }

    def create_identity_verification_session(self, handyman):
        """Create Stripe Identity verification session for handyman."""
        idempotency_key = stripe_client_service.build_idempotency_key(
            "identity-session-create",
            handyman.public_id,
            timezone.now().strftime("%Y%m%d%H"),
        )
        return_url = getattr(
            settings,
            "STRIPE_IDENTITY_RETURN_URL",
            "https://example.com/identity-return",
        )

        created = stripe_client_service.create_identity_session(
            metadata={"user_public_id": str(handyman.public_id)},
            return_url=return_url,
            idempotency_key=idempotency_key,
        )

        verification, _ = HandymanIdentityVerification.objects.update_or_create(
            user=handyman,
            defaults={
                "verification_session_id": created.get("id", ""),
                "status": "pending",
                "last_error_code": "",
                "last_error_reason": "",
            },
        )

        return {
            "verification_session_id": verification.verification_session_id,
            "status": verification.status,
            "url": created.get("url"),
        }

    def get_kyc_status(self, handyman):
        """Return consolidated KYC status."""
        connected = StripeConnectedAccount.objects.filter(user=handyman).first()
        identity = HandymanIdentityVerification.objects.filter(user=handyman).first()

        identity_status = identity.status if identity else "pending"
        charges_enabled = bool(connected.charges_enabled) if connected else False
        payouts_enabled = bool(connected.payouts_enabled) if connected else False

        is_eligible = (
            identity_status == "verified" and charges_enabled and payouts_enabled
        )

        return {
            "identity_status": identity_status,
            "charges_enabled": charges_enabled,
            "payouts_enabled": payouts_enabled,
            "is_eligible": is_eligible,
            "details_submitted": bool(connected.details_submitted)
            if connected
            else False,
            "requirements_due": connected.requirements_due if connected else [],
        }

    def is_handyman_eligible(self, handyman):
        """Check if handyman is eligible for payments and payouts."""
        return self.get_kyc_status(handyman).get("is_eligible", False)

    def sync_connected_account_state(self, account_data):
        """Sync connected account flags from webhook account.updated."""
        account_id = account_data.get("id")
        if not account_id:
            return

        connected = StripeConnectedAccount.objects.filter(
            stripe_account_id=account_id
        ).first()
        if not connected:
            return

        requirements = account_data.get("requirements", {}) or {}
        connected.charges_enabled = bool(account_data.get("charges_enabled", False))
        connected.payouts_enabled = bool(account_data.get("payouts_enabled", False))
        connected.details_submitted = bool(account_data.get("details_submitted", False))
        connected.requirements_due = requirements.get("currently_due", [])
        connected.disabled_reason = account_data.get("disabled_reason", "") or ""

        if (
            connected.charges_enabled
            and connected.payouts_enabled
            and connected.details_submitted
            and connected.onboarding_completed_at is None
        ):
            connected.onboarding_completed_at = timezone.now()

        connected.save(
            update_fields=[
                "charges_enabled",
                "payouts_enabled",
                "details_submitted",
                "requirements_due",
                "disabled_reason",
                "onboarding_completed_at",
                "updated_at",
            ]
        )

    def sync_identity_status(self, session_data):
        """Sync Identity verification state from webhook session payload."""
        verification_id = session_data.get("id")
        if not verification_id:
            return

        verification = HandymanIdentityVerification.objects.filter(
            verification_session_id=verification_id
        ).first()
        if not verification:
            return

        status = session_data.get("status", "pending")
        last_error = session_data.get("last_error", {}) or {}

        if status == "verified":
            verification.status = "verified"
            verification.verified_at = timezone.now()
            verification.last_error_code = ""
            verification.last_error_reason = ""
        elif status in ("requires_input", "processing"):
            verification.status = "requires_input"
            verification.last_error_code = last_error.get("code", "") or ""
            verification.last_error_reason = last_error.get("reason", "") or ""
        else:
            verification.status = "failed"
            verification.last_error_code = last_error.get("code", "") or ""
            verification.last_error_reason = last_error.get("reason", "") or ""

        verification.save(
            update_fields=[
                "status",
                "verified_at",
                "last_error_code",
                "last_error_reason",
                "updated_at",
            ]
        )


class JobPaymentService:
    """Payment business logic for authorization, capture, cancel, and refunds."""

    AUTHORIZED_STATUSES = {"authorized", "captured", "partially_refunded", "refunded"}

    def _to_cents(self, amount):
        """Convert decimal/number amounts to integer cents."""
        if amount is None:
            return 0
        decimal_amount = Decimal(str(amount))
        cents = (decimal_amount * Decimal("100")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        return int(cents)

    def _to_decimal(self, cents):
        """Convert cents to decimal amount."""
        return Decimal(cents) / Decimal("100")

    def _reserve_percent(self):
        """Configured reserve percentage for reimbursement headroom."""
        return Decimal(str(getattr(settings, "REIMBURSEMENT_RESERVE_PERCENT", 30)))

    def _platform_fee_percent(self):
        """Configured platform fee percentage."""
        return Decimal(str(getattr(settings, "PLATFORM_FEE_PERCENT", 10)))

    def _calculate_reserve_cents(self, service_amount_cents):
        reserve = (
            Decimal(service_amount_cents) * self._reserve_percent() / Decimal("100")
        ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return int(reserve)

    def _calculate_platform_fee_cents(self, service_amount_cents):
        fee = (
            Decimal(service_amount_cents)
            * self._platform_fee_percent()
            / Decimal("100")
        ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return int(fee)

    def _payment_mode_required(self, job):
        """Check if Stripe payment mode is required for this job."""
        if getattr(job, "payment_mode", "legacy_exempt") != "stripe_required":
            return False
        return bool(getattr(settings, "STRIPE_AUTHORIZATION_ENFORCED", False))

    def _create_or_get_customer_profile(self, homeowner):
        """Get or create Stripe customer for homeowner."""
        customer_profile = StripeCustomerProfile.objects.filter(user=homeowner).first()
        if customer_profile:
            return customer_profile

        idempotency_key = stripe_client_service.build_idempotency_key(
            "customer-create",
            homeowner.public_id,
        )
        customer = stripe_client_service.create_customer(
            email=homeowner.email,
            metadata={"user_public_id": str(homeowner.public_id)},
            idempotency_key=idempotency_key,
        )

        customer_profile = StripeCustomerProfile.objects.create(
            user=homeowner,
            stripe_customer_id=customer.get("id", ""),
            currency=getattr(settings, "STRIPE_DEFAULT_CURRENCY", "cad"),
        )
        return customer_profile

    def _get_target_handyman(self, job, application=None):
        """Resolve target handyman based on flow."""
        if application is not None:
            return application.handyman
        if job.assigned_handyman:
            return job.assigned_handyman
        if job.target_handyman:
            return job.target_handyman
        return None

    @transaction.atomic
    def authorize_for_application(self, homeowner, application):
        """Create/reuse authorization for homeowner -> application flow."""
        if application.job.homeowner != homeowner:
            raise ValidationError(
                "You can only authorize payment for your own job application."
            )

        service_amount = (
            application.estimated_total_price or application.job.estimated_budget
        )
        return self._authorize_for_job(
            homeowner=homeowner,
            job=application.job,
            service_amount=service_amount,
            target_handyman=application.handyman,
        )

    @transaction.atomic
    def authorize_for_direct_offer(self, homeowner, job):
        """Create/reuse authorization for direct-offer job."""
        if job.homeowner != homeowner:
            raise ValidationError(
                "You can only authorize payment for your own direct offer."
            )

        target_handyman = job.target_handyman
        if target_handyman is None:
            raise ValidationError("Direct offer has no target handyman.")

        return self._authorize_for_job(
            homeowner=homeowner,
            job=job,
            service_amount=job.estimated_budget,
            target_handyman=target_handyman,
        )

    def _authorize_for_job(self, homeowner, job, service_amount, target_handyman):
        """Shared implementation for payment authorization."""
        if target_handyman is None:
            raise ValidationError("No handyman found for payment authorization.")

        connected = kyc_service.get_or_create_connected_account(target_handyman)
        customer = self._create_or_get_customer_profile(homeowner)

        service_amount_cents = self._to_cents(service_amount)
        reserve_cents = self._calculate_reserve_cents(service_amount_cents)
        approved_reimbursement_cents = self._approved_reimbursement_cents(job)
        authorized_amount_cents = service_amount_cents + max(
            reserve_cents,
            approved_reimbursement_cents,
        )
        platform_fee_cents = self._calculate_platform_fee_cents(service_amount_cents)

        existing_payment = JobPayment.objects.filter(job=job).first()
        if existing_payment and existing_payment.status in self.AUTHORIZED_STATUSES:
            if existing_payment.status in {
                "captured",
                "partially_refunded",
                "refunded",
            }:
                intent = stripe_client_service.retrieve_payment_intent(
                    existing_payment.payment_intent_id
                )
                return {
                    "job_payment": existing_payment,
                    "payment_intent_id": existing_payment.payment_intent_id,
                    "client_secret": intent.get("client_secret", ""),
                }

            if existing_payment.authorized_amount_cents >= authorized_amount_cents:
                intent = stripe_client_service.retrieve_payment_intent(
                    existing_payment.payment_intent_id
                )
                return {
                    "job_payment": existing_payment,
                    "payment_intent_id": existing_payment.payment_intent_id,
                    "client_secret": intent.get("client_secret", ""),
                }

            if existing_payment.status == "authorized":
                self.cancel_uncaptured(
                    existing_payment,
                    "Re-authorization required for top-up amount",
                )

        idempotency_key = stripe_client_service.build_idempotency_key(
            "payment-intent-create",
            job.public_id,
            target_handyman.public_id,
            authorized_amount_cents,
        )
        payload = {
            "amount": authorized_amount_cents,
            "currency": getattr(settings, "STRIPE_DEFAULT_CURRENCY", "cad"),
            "customer": customer.stripe_customer_id,
            "capture_method": "manual",
            "automatic_payment_methods": {"enabled": True},
            "application_fee_amount": platform_fee_cents,
            "transfer_data": {"destination": connected.stripe_account_id},
            "metadata": {
                "job_public_id": str(job.public_id),
                "homeowner_public_id": str(homeowner.public_id),
                "handyman_public_id": str(target_handyman.public_id),
            },
        }
        intent = stripe_client_service.create_payment_intent(payload, idempotency_key)

        status = self._map_intent_status(intent.get("status"))

        job_payment, _ = JobPayment.objects.update_or_create(
            job=job,
            defaults={
                "customer_profile": customer,
                "connected_account": connected,
                "payment_intent_id": intent.get("id", ""),
                "currency": payload["currency"],
                "service_amount_cents": service_amount_cents,
                "reserve_cents": reserve_cents,
                "authorized_amount_cents": authorized_amount_cents,
                "capturable_amount_cents": intent.get("amount_capturable", 0),
                "captured_amount_cents": intent.get("amount_received", 0),
                "platform_fee_cents": platform_fee_cents,
                "status": status,
                "authorized_at": timezone.now() if status == "authorized" else None,
            },
        )

        return {
            "job_payment": job_payment,
            "payment_intent_id": job_payment.payment_intent_id,
            "client_secret": intent.get("client_secret", ""),
        }

    def _map_intent_status(self, intent_status):
        """Map Stripe payment intent statuses to local statuses."""
        mapping = {
            "requires_payment_method": "requires_payment_method",
            "requires_confirmation": "requires_confirmation",
            "requires_capture": "authorized",
            "succeeded": "captured",
            "canceled": "canceled",
            "processing": "authorized",
        }
        return mapping.get(intent_status, "failed")

    def ensure_job_authorized(self, job):
        """Raise validation error if job requires payment authorization and is not authorized."""
        if not self._payment_mode_required(job):
            return

        payment = JobPayment.objects.filter(job=job).first()
        if payment is None:
            raise ValidationError(
                "Payment authorization is required before proceeding."
            )

        if payment.status not in self.AUTHORIZED_STATUSES:
            raise ValidationError(
                "Payment is not authorized yet. Please complete payment authorization."
            )

    def get_payment_status(self, job):
        """Get current payment status snapshot for a job."""
        payment = JobPayment.objects.filter(job=job).first()
        if payment is None:
            return {
                "status": "not_started",
                "authorized_amount": "0.00",
                "captured_amount": "0.00",
                "capturable_amount": "0.00",
                "currency": getattr(settings, "STRIPE_DEFAULT_CURRENCY", "cad"),
            }

        return {
            "status": payment.status,
            "payment_intent_id": payment.payment_intent_id,
            "authorized_amount": str(self._to_decimal(payment.authorized_amount_cents)),
            "captured_amount": str(self._to_decimal(payment.captured_amount_cents)),
            "capturable_amount": str(self._to_decimal(payment.capturable_amount_cents)),
            "platform_fee": str(self._to_decimal(payment.platform_fee_cents)),
            "currency": payment.currency,
            "last_failure_code": payment.last_failure_code,
            "last_failure_message": payment.last_failure_message,
        }

    def _approved_reimbursement_cents(self, job):
        """Sum approved reimbursement amounts in cents."""
        approved_total = job.reimbursements.filter(status="approved").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")
        return self._to_cents(approved_total)

    @transaction.atomic
    def capture_for_completion(self, job):
        """Capture authorized amount at completion with reimbursement adjustments."""
        if not self._payment_mode_required(job):
            return None

        payment = JobPayment.objects.select_for_update().filter(job=job).first()
        if payment is None:
            raise ValidationError("Payment authorization not found for this job.")

        if payment.status in {"captured", "partially_refunded", "refunded"}:
            return payment

        if payment.status != "authorized":
            raise ValidationError("Payment is not in authorized state.")

        reimbursement_cents = self._approved_reimbursement_cents(job)
        target_capture = payment.service_amount_cents + reimbursement_cents

        if target_capture > payment.authorized_amount_cents:
            raise ValidationError(
                "Captured amount exceeds current authorization. Please top up authorization first."
            )

        idempotency_key = stripe_client_service.build_idempotency_key(
            "payment-intent-capture",
            payment.payment_intent_id,
            target_capture,
        )
        captured = stripe_client_service.capture_payment_intent(
            payment.payment_intent_id,
            target_capture,
            idempotency_key,
        )

        payment.reimbursement_approved_cents = reimbursement_cents
        payment.captured_amount_cents = captured.get("amount_received", target_capture)
        payment.capturable_amount_cents = captured.get("amount_capturable", 0)
        payment.captured_at = timezone.now()
        payment.status = "captured"
        payment.save(
            update_fields=[
                "reimbursement_approved_cents",
                "captured_amount_cents",
                "capturable_amount_cents",
                "captured_at",
                "status",
                "updated_at",
            ]
        )

        return payment

    @transaction.atomic
    def cancel_uncaptured(self, job_payment, reason=""):
        """Cancel uncaptured payment intent."""
        idempotency_key = stripe_client_service.build_idempotency_key(
            "payment-intent-cancel",
            job_payment.payment_intent_id,
            reason,
        )
        stripe_client_service.cancel_payment_intent(
            job_payment.payment_intent_id,
            idempotency_key,
        )

        job_payment.status = "canceled"
        job_payment.last_failure_message = reason
        job_payment.save(update_fields=["status", "last_failure_message", "updated_at"])
        return job_payment

    @transaction.atomic
    def refund_captured(self, job_payment, amount_cents, reason, source):
        """Issue refund for captured payment."""
        if amount_cents <= 0:
            return None

        idempotency_key = stripe_client_service.build_idempotency_key(
            "payment-refund",
            job_payment.payment_intent_id,
            amount_cents,
            source,
        )
        refund_payload = {
            "payment_intent": job_payment.payment_intent_id,
            "amount": amount_cents,
            "reason": "requested_by_customer",
            "metadata": {
                "job_public_id": str(job_payment.job.public_id),
                "source": source,
            },
        }
        refund_data = stripe_client_service.create_refund(
            refund_payload, idempotency_key
        )

        refund = PaymentRefund.objects.create(
            job_payment=job_payment,
            stripe_refund_id=refund_data.get("id"),
            amount_cents=amount_cents,
            reason=reason,
            source=source,
            status="succeeded"
            if refund_data.get("status") == "succeeded"
            else "pending",
            processed_at=timezone.now(),
        )

        total_refunded = (
            job_payment.refunds.filter(status__in=["pending", "succeeded"]).aggregate(
                total=Sum("amount_cents")
            )["total"]
            or 0
        )

        if total_refunded >= job_payment.captured_amount_cents:
            job_payment.status = "refunded"
        else:
            job_payment.status = "partially_refunded"
        job_payment.save(update_fields=["status", "updated_at"])

        return refund

    @transaction.atomic
    def resolve_dispute_financial(self, dispute, status, refund_percentage=None):
        """Apply financial consequences for dispute resolution outcomes."""
        job = dispute.job
        if not self._payment_mode_required(job):
            return {"outcome_amount_cents": 0, "action": "legacy_exempt"}

        payment = JobPayment.objects.select_for_update().filter(job=job).first()
        if payment is None:
            raise ValidationError("No payment found for this disputed job.")

        if status == "resolved_pay_handyman":
            captured = self.capture_for_completion(job)
            return {
                "outcome_amount_cents": captured.captured_amount_cents,
                "action": "captured_full",
            }

        if status == "resolved_full_refund":
            if payment.captured_amount_cents > 0:
                self.refund_captured(
                    payment,
                    payment.captured_amount_cents,
                    "Full refund from dispute resolution",
                    "dispute",
                )
                return {
                    "outcome_amount_cents": payment.captured_amount_cents,
                    "action": "refunded_full",
                }

            self.cancel_uncaptured(payment, "Full refund resolution before capture")
            return {
                "outcome_amount_cents": payment.authorized_amount_cents,
                "action": "canceled",
            }

        if status == "resolved_partial_refund":
            if refund_percentage is None:
                raise ValidationError(
                    "Refund percentage is required for partial refund."
                )

            percent = Decimal(str(refund_percentage)) / Decimal("100")

            if payment.captured_amount_cents > 0:
                refund_amount = int(
                    (Decimal(payment.captured_amount_cents) * percent).quantize(
                        Decimal("1"), rounding=ROUND_HALF_UP
                    )
                )
                self.refund_captured(
                    payment,
                    refund_amount,
                    "Partial refund from dispute resolution",
                    "dispute",
                )
                return {
                    "outcome_amount_cents": refund_amount,
                    "action": "refunded_partial",
                }

            target_capture = (
                payment.service_amount_cents + self._approved_reimbursement_cents(job)
            )
            refund_amount = int(
                (Decimal(target_capture) * percent).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )
            net_capture = max(target_capture - refund_amount, 0)

            idempotency_key = stripe_client_service.build_idempotency_key(
                "payment-intent-capture-partial",
                payment.payment_intent_id,
                net_capture,
                refund_percentage,
            )
            captured = stripe_client_service.capture_payment_intent(
                payment.payment_intent_id,
                net_capture,
                idempotency_key,
            )
            payment.captured_amount_cents = captured.get("amount_received", net_capture)
            payment.capturable_amount_cents = captured.get("amount_capturable", 0)
            payment.status = "captured"
            payment.captured_at = timezone.now()
            payment.save(
                update_fields=[
                    "captured_amount_cents",
                    "capturable_amount_cents",
                    "status",
                    "captured_at",
                    "updated_at",
                ]
            )
            return {
                "outcome_amount_cents": payment.captured_amount_cents,
                "action": "captured_net_partial",
            }

        if status == "cancelled":
            self.cancel_uncaptured(payment, "Dispute cancelled")
            return {"outcome_amount_cents": 0, "action": "cancelled"}

        return {"outcome_amount_cents": 0, "action": "no_action"}

    @transaction.atomic
    def sync_payment_intent_event(self, payment_intent):
        """Sync payment state from payment_intent webhook events."""
        payment_intent_id = payment_intent.get("id")
        if not payment_intent_id:
            return

        payment = JobPayment.objects.filter(payment_intent_id=payment_intent_id).first()
        if not payment:
            return

        mapped_status = self._map_intent_status(payment_intent.get("status"))
        payment.status = mapped_status
        payment.capturable_amount_cents = (
            payment_intent.get("amount_capturable", 0) or 0
        )
        payment.captured_amount_cents = payment_intent.get("amount_received", 0) or 0

        if mapped_status == "authorized" and payment.authorized_at is None:
            payment.authorized_at = timezone.now()

        last_error = payment_intent.get("last_payment_error") or {}
        payment.last_failure_code = last_error.get("code", "") or ""
        payment.last_failure_message = last_error.get("message", "") or ""

        if mapped_status == "canceled":
            payment.captured_amount_cents = 0

        payment.save(
            update_fields=[
                "status",
                "capturable_amount_cents",
                "captured_amount_cents",
                "authorized_at",
                "last_failure_code",
                "last_failure_message",
                "updated_at",
            ]
        )

    @transaction.atomic
    def sync_charge_dispute_event(self, event_type, dispute_object):
        """Sync charge dispute events from Stripe."""
        payment_intent_id = dispute_object.get("payment_intent")
        if not payment_intent_id:
            charge = dispute_object.get("charge")
            if isinstance(charge, dict):
                payment_intent_id = charge.get("payment_intent")

        if not payment_intent_id:
            return

        payment = JobPayment.objects.filter(payment_intent_id=payment_intent_id).first()
        if not payment:
            return

        if event_type == "charge.dispute.created":
            payment.status = "disputed"
            payment.save(update_fields=["status", "updated_at"])
            return

        if event_type == "charge.dispute.closed":
            outcome = dispute_object.get("status", "")
            if (
                outcome in {"won", "warning_closed"}
                and payment.captured_amount_cents > 0
            ):
                payment.status = "captured"
            elif outcome in {"lost"} and payment.captured_amount_cents > 0:
                payment.status = "refunded"
                PaymentRefund.objects.create(
                    job_payment=payment,
                    amount_cents=payment.captured_amount_cents,
                    reason="Card chargeback closed as lost",
                    source="chargeback",
                    status="succeeded",
                    processed_at=timezone.now(),
                )
            payment.save(update_fields=["status", "updated_at"])


class WithdrawalService:
    """Withdrawal business logic for handyman payouts."""

    def _instant_fee_percent(self):
        return Decimal(str(getattr(settings, "STRIPE_INSTANT_PAYOUT_FEE_PERCENT", 1)))

    def _to_cents(self, amount):
        decimal_amount = Decimal(str(amount))
        return int(
            (decimal_amount * Decimal("100")).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )

    def _to_decimal(self, cents):
        return Decimal(cents) / Decimal("100")

    def get_wallet_balance(self, handyman):
        """Return available and pending balance from Stripe connected account."""
        connected = StripeConnectedAccount.objects.filter(user=handyman).first()
        if not connected:
            return {
                "currency": getattr(settings, "STRIPE_DEFAULT_CURRENCY", "cad"),
                "available_amount": "0.00",
                "pending_amount": "0.00",
            }

        balance = stripe_client_service.retrieve_balance(connected.stripe_account_id)

        currency = getattr(settings, "STRIPE_DEFAULT_CURRENCY", "cad")
        available_cents = 0
        pending_cents = 0

        for item in balance.get("available", []):
            if item.get("currency", "").lower() == currency.lower():
                available_cents = item.get("amount", 0)
                break

        for item in balance.get("pending", []):
            if item.get("currency", "").lower() == currency.lower():
                pending_cents = item.get("amount", 0)
                break

        return {
            "currency": currency,
            "available_amount": str(self._to_decimal(available_cents)),
            "pending_amount": str(self._to_decimal(pending_cents)),
            "available_cents": available_cents,
            "pending_cents": pending_cents,
        }

    @transaction.atomic
    def create_withdrawal(self, handyman, amount, method):
        """Create a withdrawal request and trigger Stripe payout."""
        if not bool(getattr(settings, "STRIPE_WITHDRAW_ENABLED", False)):
            raise ValidationError("Withdrawals are not enabled yet.")

        if not kyc_service.is_handyman_eligible(handyman):
            raise ValidationError("You must complete KYC before withdrawing funds.")

        connected = StripeConnectedAccount.objects.filter(user=handyman).first()
        if not connected:
            raise ValidationError("Connected account not found.")

        amount_cents = self._to_cents(amount)
        if amount_cents <= 0:
            raise ValidationError("Withdrawal amount must be greater than zero.")

        balance = self.get_wallet_balance(handyman)
        if amount_cents > balance.get("available_cents", 0):
            raise ValidationError("Insufficient available balance for withdrawal.")

        instant_fee_cents = 0
        payout_method = "standard"
        if method == "instant":
            payout_method = "instant"
            instant_fee_cents = int(
                (
                    Decimal(amount_cents) * self._instant_fee_percent() / Decimal("100")
                ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            )

        payout_amount_cents = amount_cents - instant_fee_cents
        if payout_amount_cents <= 0:
            raise ValidationError(
                "Withdrawal amount is too small after instant payout fee."
            )

        request = WithdrawalRequest.objects.create(
            handyman=handyman,
            connected_account=connected,
            amount_cents=amount_cents,
            currency=getattr(settings, "STRIPE_DEFAULT_CURRENCY", "cad"),
            method=method,
            instant_fee_cents=instant_fee_cents,
            status="requested",
        )

        idempotency_key = stripe_client_service.build_idempotency_key(
            "withdrawal-payout-create",
            request.public_id,
            payout_amount_cents,
            method,
        )
        payout_payload = {
            "amount": payout_amount_cents,
            "currency": request.currency,
            "method": payout_method,
            "metadata": {
                "withdrawal_request_public_id": str(request.public_id),
                "handyman_public_id": str(handyman.public_id),
            },
        }
        payout = stripe_client_service.create_payout(
            connected.stripe_account_id,
            payout_payload,
            idempotency_key,
        )

        request.stripe_payout_id = payout.get("id")
        request.status = "processing"
        request.save(update_fields=["stripe_payout_id", "status", "updated_at"])

        return request

    @transaction.atomic
    def sync_payout_event(self, event_type, payout_object):
        """Sync payout lifecycle from webhook events."""
        payout_id = payout_object.get("id")
        if not payout_id:
            return

        request = WithdrawalRequest.objects.filter(stripe_payout_id=payout_id).first()
        if not request:
            return

        if event_type == "payout.paid":
            request.status = "paid"
            request.processed_at = timezone.now()
        elif event_type == "payout.failed":
            request.status = "failed"
            request.processed_at = timezone.now()
            request.failure_code = payout_object.get("failure_code", "") or ""
            request.failure_message = payout_object.get("failure_message", "") or ""
        elif event_type == "payout.canceled":
            request.status = "canceled"
            request.processed_at = timezone.now()

        request.save(
            update_fields=[
                "status",
                "processed_at",
                "failure_code",
                "failure_message",
                "updated_at",
            ]
        )


class StripeWebhookService:
    """Webhook verification, dedupe, and event dispatch."""

    SUPPORTED_EVENTS = {
        "identity.verification_session.verified",
        "identity.verification_session.requires_input",
        "account.updated",
        "payment_intent.amount_capturable_updated",
        "payment_intent.payment_failed",
        "payment_intent.canceled",
        "charge.dispute.created",
        "charge.dispute.updated",
        "charge.dispute.closed",
        "payout.paid",
        "payout.failed",
        "payout.canceled",
    }

    def verify_event(self, payload, signature_header):
        """Verify signature and return constructed event."""
        secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
        return stripe_client_service.construct_event(payload, signature_header, secret)

    @transaction.atomic
    def process_event(self, event):
        """Process a Stripe event with dedupe + status tracking."""
        event_id = event.get("id")
        event_type = event.get("type")

        if not event_id or not event_type:
            raise ValidationError("Invalid Stripe event payload.")

        log_entry, created = StripeEventLog.objects.get_or_create(
            stripe_event_id=event_id,
            defaults={
                "event_type": event_type,
                "payload_json": event,
                "processing_status": "pending",
            },
        )

        if not created and log_entry.processing_status == "processed":
            return {"deduplicated": True, "event_id": event_id}

        log_entry.event_type = event_type
        log_entry.payload_json = event
        log_entry.processing_status = "pending"
        log_entry.error_message = ""
        log_entry.processed_at = None
        log_entry.save(
            update_fields=[
                "event_type",
                "payload_json",
                "processing_status",
                "error_message",
                "processed_at",
                "updated_at",
            ]
        )

        try:
            self._dispatch(event_type, event.get("data", {}).get("object", {}))
            log_entry.processing_status = "processed"
            log_entry.processed_at = timezone.now()
            log_entry.error_message = ""
            log_entry.save(
                update_fields=[
                    "processing_status",
                    "processed_at",
                    "error_message",
                    "updated_at",
                ]
            )
            return {"deduplicated": False, "event_id": event_id}
        except Exception as exc:
            log_entry.processing_status = "failed"
            log_entry.error_message = str(exc)
            log_entry.save(
                update_fields=["processing_status", "error_message", "updated_at"]
            )
            raise

    def replay_log(self, log_entry):
        """Replay a stored Stripe event log entry."""
        event = log_entry.payload_json or {}
        return self.process_event(event)

    def _dispatch(self, event_type, event_object):
        """Dispatch event payload to domain services."""
        if event_type not in self.SUPPORTED_EVENTS:
            return

        if event_type.startswith("identity.verification_session"):
            kyc_service.sync_identity_status(event_object)
            return

        if event_type == "account.updated":
            kyc_service.sync_connected_account_state(event_object)
            return

        if event_type.startswith("payment_intent"):
            job_payment_service.sync_payment_intent_event(event_object)
            return

        if event_type.startswith("charge.dispute"):
            job_payment_service.sync_charge_dispute_event(event_type, event_object)
            return

        if event_type.startswith("payout."):
            withdrawal_service.sync_payout_event(event_type, event_object)


stripe_client_service = StripeClientService()
kyc_service = KycService()
job_payment_service = JobPaymentService()
withdrawal_service = WithdrawalService()
stripe_webhook_service = StripeWebhookService()
