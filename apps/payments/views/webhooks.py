"""Webhook views for Stripe events."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.common.responses import accepted_response, validation_error_response
from apps.payments.services import stripe_webhook_service


class StripeWebhookView(APIView):
    """Receive and process Stripe webhooks with signature verification."""

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="webhooks_stripe_receive",
        request=OpenApiTypes.OBJECT,
        responses={
            202: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        },
        description=(
            "Receive Stripe webhook events, verify signature, deduplicate by Stripe event ID, "
            "and dispatch to payment/KYC/payout handlers."
        ),
        summary="Receive Stripe webhook",
        tags=["Webhooks"],
        examples=[
            OpenApiExample(
                "Accepted Response",
                value={
                    "message": "Accepted",
                    "data": None,
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["202"],
            ),
        ],
    )
    def post(self, request):
        signature_header = request.headers.get("Stripe-Signature", "")
        payload = request.body

        try:
            event = stripe_webhook_service.verify_event(payload, signature_header)
            stripe_webhook_service.process_event(event)
            return accepted_response(message="Accepted")
        except Exception as exc:
            return validation_error_response(
                {"detail": str(exc)}, message="Webhook rejected"
            )
