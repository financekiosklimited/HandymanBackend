"""Serializers for payment, KYC, wallet, and webhook APIs."""

from decimal import Decimal

from rest_framework import serializers

from apps.common.serializers import (
    create_list_response_serializer,
    create_response_serializer,
)
from apps.payments.models import WithdrawalRequest


class ConnectOnboardingLinkSerializer(serializers.Serializer):
    """Response serializer for Stripe Connect onboarding links."""

    url = serializers.URLField()
    expires_at = serializers.IntegerField()
    account_id = serializers.CharField()


class IdentitySessionSerializer(serializers.Serializer):
    """Response serializer for Stripe Identity session creation."""

    verification_session_id = serializers.CharField()
    status = serializers.CharField()
    url = serializers.URLField(allow_null=True)


class KycStatusSerializer(serializers.Serializer):
    """KYC status summary serializer."""

    identity_status = serializers.CharField()
    charges_enabled = serializers.BooleanField()
    payouts_enabled = serializers.BooleanField()
    details_submitted = serializers.BooleanField()
    requirements_due = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    is_eligible = serializers.BooleanField()


class WalletBalanceSerializer(serializers.Serializer):
    """Wallet balance payload serializer."""

    currency = serializers.CharField()
    available_amount = serializers.CharField()
    pending_amount = serializers.CharField()


class WithdrawalCreateSerializer(serializers.Serializer):
    """Create withdrawal request serializer."""

    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        coerce_to_string=False,
        help_text="Withdrawal amount in CAD",
    )
    method = serializers.ChoiceField(choices=["standard", "instant"])  # nosec B106


class WithdrawalSerializer(serializers.ModelSerializer):
    """Withdrawal response serializer."""

    amount = serializers.SerializerMethodField()
    instant_fee = serializers.SerializerMethodField()

    class Meta:
        model = WithdrawalRequest
        fields = [
            "public_id",
            "amount",
            "currency",
            "method",
            "instant_fee",
            "status",
            "failure_code",
            "failure_message",
            "requested_at",
            "processed_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_amount(self, obj):
        return str(obj.amount_cents / 100)

    def get_instant_fee(self, obj):
        return str(obj.instant_fee_cents / 100)


class PaymentAuthorizationSerializer(serializers.Serializer):
    """Payment authorization response serializer."""

    job_payment_public_id = serializers.UUIDField()
    payment_intent_id = serializers.CharField()
    client_secret = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    authorized_amount = serializers.CharField()
    currency = serializers.CharField()


class JobPaymentStatusSerializer(serializers.Serializer):
    """Job payment status serializer."""

    status = serializers.CharField()
    payment_intent_id = serializers.CharField(required=False, allow_blank=True)
    authorized_amount = serializers.CharField()
    captured_amount = serializers.CharField()
    capturable_amount = serializers.CharField()
    platform_fee = serializers.CharField(required=False)
    currency = serializers.CharField()
    last_failure_code = serializers.CharField(required=False, allow_blank=True)
    last_failure_message = serializers.CharField(required=False, allow_blank=True)


ConnectOnboardingLinkResponseSerializer = create_response_serializer(
    ConnectOnboardingLinkSerializer,
    "ConnectOnboardingLinkResponse",
)

IdentitySessionResponseSerializer = create_response_serializer(
    IdentitySessionSerializer,
    "IdentitySessionResponse",
)

KycStatusResponseSerializer = create_response_serializer(
    KycStatusSerializer,
    "KycStatusResponse",
)

WalletBalanceResponseSerializer = create_response_serializer(
    WalletBalanceSerializer,
    "WalletBalanceResponse",
)

WithdrawalDetailResponseSerializer = create_response_serializer(
    WithdrawalSerializer,
    "WithdrawalDetailResponse",
)

WithdrawalListResponseSerializer = create_list_response_serializer(
    WithdrawalSerializer,
    "WithdrawalListResponse",
)

PaymentAuthorizationResponseSerializer = create_response_serializer(
    PaymentAuthorizationSerializer,
    "PaymentAuthorizationResponse",
)

JobPaymentStatusResponseSerializer = create_response_serializer(
    JobPaymentStatusSerializer,
    "JobPaymentStatusResponse",
)
