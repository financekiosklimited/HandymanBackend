import json

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.payments.models import StripeEventLog


class StripeWebhookViewTests(APITestCase):
    @override_settings(STRIPE_ENABLED=False)
    def test_webhook_accepts_supported_event(self):
        payload = {
            "id": "evt_123",
            "type": "payment_intent.canceled",
            "data": {"object": {"id": "pi_123", "status": "canceled"}},
        }

        response = self.client.post(
            "/api/v1/webhooks/stripe/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test-signature",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(
            StripeEventLog.objects.filter(stripe_event_id="evt_123").exists()
        )

    @override_settings(STRIPE_ENABLED=False)
    def test_webhook_deduplicates_event(self):
        payload = {
            "id": "evt_123dup",
            "type": "payout.failed",
            "data": {"object": {"id": "po_1", "status": "failed"}},
        }

        for _ in range(2):
            self.client.post(
                "/api/v1/webhooks/stripe/",
                data=json.dumps(payload),
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="test-signature",
            )

        self.assertEqual(
            StripeEventLog.objects.filter(stripe_event_id="evt_123dup").count(),
            1,
        )
