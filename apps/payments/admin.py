"""Admin configuration for payments app."""

from django.contrib import admin, messages
from django.utils import timezone
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.payments.models import (
    HandymanIdentityVerification,
    JobPayment,
    PaymentRefund,
    StripeConnectedAccount,
    StripeCustomerProfile,
    StripeEventLog,
    WithdrawalRequest,
)
from apps.payments.services import stripe_client_service, stripe_webhook_service


@admin.register(StripeCustomerProfile)
class StripeCustomerProfileAdmin(ModelAdmin):
    list_display = ("user", "stripe_customer_id", "currency", "created_at")
    search_fields = ("user__email", "stripe_customer_id")
    ordering = ("-created_at",)


@admin.register(StripeConnectedAccount)
class StripeConnectedAccountAdmin(ModelAdmin):
    list_display = (
        "user",
        "stripe_account_id",
        "account_type",
        "charges_enabled",
        "payouts_enabled",
        "details_submitted",
        "onboarding_completed_at",
    )
    list_filter = (
        "account_type",
        "charges_enabled",
        "payouts_enabled",
        "details_submitted",
    )
    search_fields = ("user__email", "stripe_account_id")
    ordering = ("-updated_at",)


@admin.register(HandymanIdentityVerification)
class HandymanIdentityVerificationAdmin(ModelAdmin):
    list_display = (
        "user",
        "verification_session_id",
        "status",
        "verified_at",
        "updated_at",
    )
    list_filter = ("status",)
    search_fields = ("user__email", "verification_session_id")
    ordering = ("-updated_at",)


@admin.register(JobPayment)
class JobPaymentAdmin(ModelAdmin):
    list_display = (
        "job",
        "homeowner_email",
        "handyman_email",
        "status",
        "authorized_amount_display",
        "captured_amount_display",
        "platform_fee_display",
        "currency",
        "updated_at",
    )
    list_filter = ("status", "currency")
    search_fields = (
        "job__title",
        "job__homeowner__email",
        "job__assigned_handyman__email",
        "payment_intent_id",
    )
    ordering = ("-updated_at",)

    @display(description="Homeowner")
    def homeowner_email(self, obj):
        return obj.job.homeowner.email

    @display(description="Handyman")
    def handyman_email(self, obj):
        if obj.job.assigned_handyman:
            return obj.job.assigned_handyman.email
        if obj.job.target_handyman:
            return obj.job.target_handyman.email
        return "-"

    @display(description="Authorized")
    def authorized_amount_display(self, obj):
        return f"{obj.authorized_amount_cents / 100:.2f}"

    @display(description="Captured")
    def captured_amount_display(self, obj):
        return f"{obj.captured_amount_cents / 100:.2f}"

    @display(description="Platform Fee")
    def platform_fee_display(self, obj):
        return f"{obj.platform_fee_cents / 100:.2f}"


@admin.register(PaymentRefund)
class PaymentRefundAdmin(ModelAdmin):
    list_display = (
        "job_payment",
        "stripe_refund_id",
        "amount_display",
        "source",
        "status",
        "processed_at",
    )
    list_filter = ("source", "status")
    search_fields = ("job_payment__payment_intent_id", "stripe_refund_id")
    ordering = ("-created_at",)

    @display(description="Amount")
    def amount_display(self, obj):
        return f"{obj.amount_cents / 100:.2f}"


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(ModelAdmin):
    list_display = (
        "handyman",
        "amount_display",
        "currency",
        "method",
        "instant_fee_display",
        "status",
        "stripe_payout_id",
        "requested_at",
        "processed_at",
    )
    list_filter = ("status", "method", "currency")
    search_fields = ("handyman__email", "stripe_payout_id")
    ordering = ("-requested_at",)
    actions = ["retry_failed_withdrawals"]

    @display(description="Amount")
    def amount_display(self, obj):
        return f"{obj.amount_cents / 100:.2f}"

    @display(description="Instant Fee")
    def instant_fee_display(self, obj):
        return f"{obj.instant_fee_cents / 100:.2f}"

    @admin.action(description="Retry failed withdrawals")
    def retry_failed_withdrawals(self, request, queryset):
        retried = 0
        errors = 0

        for item in queryset.filter(status="failed"):
            try:
                payout_amount = item.amount_cents - item.instant_fee_cents
                idempotency_key = stripe_client_service.build_idempotency_key(
                    "withdrawal-admin-retry",
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
                            "admin_retry": "true",
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
                errors += 1
                item.failure_message = str(exc)
                item.save(update_fields=["failure_message", "updated_at"])

        if retried:
            self.message_user(request, f"Retried {retried} withdrawal(s).")
        if errors:
            self.message_user(
                request,
                f"Failed to retry {errors} withdrawal(s).",
                level=messages.WARNING,
            )


@admin.register(StripeEventLog)
class StripeEventLogAdmin(ModelAdmin):
    list_display = (
        "stripe_event_id",
        "event_type",
        "processing_status",
        "processed_at",
        "created_at",
    )
    list_filter = ("processing_status", "event_type")
    search_fields = ("stripe_event_id", "event_type")
    ordering = ("-created_at",)
    readonly_fields = ("stripe_event_id", "event_type", "payload_json", "processed_at")
    actions = ["replay_failed_events"]

    @admin.action(description="Replay failed events")
    def replay_failed_events(self, request, queryset):
        replayed = 0
        errors = 0

        for event_log in queryset.filter(processing_status="failed"):
            try:
                stripe_webhook_service.replay_log(event_log)
                replayed += 1
            except Exception:
                errors += 1

        if replayed:
            self.message_user(request, f"Replayed {replayed} event(s).")
        if errors:
            self.message_user(
                request,
                f"Failed to replay {errors} event(s).",
                level=messages.WARNING,
            )
