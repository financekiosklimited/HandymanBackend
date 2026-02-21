from django.urls import path

from apps.payments.views.redirects import (
    StripeConnectRefreshRedirectView,
    StripeConnectReturnRedirectView,
    StripeIdentityReturnRedirectView,
)

urlpatterns = [
    path(
        "connect/refresh/",
        StripeConnectRefreshRedirectView.as_view(),
        name="stripe_connect_refresh_redirect",
    ),
    path(
        "connect/return/",
        StripeConnectReturnRedirectView.as_view(),
        name="stripe_connect_return_redirect",
    ),
    path(
        "identity/return/",
        StripeIdentityReturnRedirectView.as_view(),
        name="stripe_identity_return_redirect",
    ),
]
