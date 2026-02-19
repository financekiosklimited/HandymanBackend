from django.urls import path

from apps.payments.views.webhooks import StripeWebhookView

urlpatterns = [
    path("stripe/", StripeWebhookView.as_view(), name="webhooks_stripe"),
]
