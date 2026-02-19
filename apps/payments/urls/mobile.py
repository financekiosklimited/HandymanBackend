from django.urls import path

from apps.payments.views.mobile import (
    HandymanConnectOnboardingLinkView,
    HandymanIdentitySessionView,
    HandymanKycStatusView,
    HandymanWalletBalanceView,
    HandymanWithdrawListCreateView,
    HomeownerApplicationPaymentAuthorizationView,
    HomeownerDirectOfferPaymentAuthorizationView,
    HomeownerJobPaymentStatusView,
)

urlpatterns = [
    path(
        "handyman/kyc/connect/onboarding-link/",
        HandymanConnectOnboardingLinkView.as_view(),
        name="mobile_handyman_kyc_connect_onboarding_link",
    ),
    path(
        "handyman/kyc/identity/session/",
        HandymanIdentitySessionView.as_view(),
        name="mobile_handyman_kyc_identity_session",
    ),
    path(
        "handyman/kyc/status/",
        HandymanKycStatusView.as_view(),
        name="mobile_handyman_kyc_status",
    ),
    path(
        "handyman/wallet/balance/",
        HandymanWalletBalanceView.as_view(),
        name="mobile_handyman_wallet_balance",
    ),
    path(
        "handyman/wallet/withdrawals/",
        HandymanWithdrawListCreateView.as_view(),
        name="mobile_handyman_wallet_withdrawals",
    ),
    path(
        "homeowner/applications/<uuid:public_id>/payment-authorization/",
        HomeownerApplicationPaymentAuthorizationView.as_view(),
        name="mobile_homeowner_application_payment_authorization",
    ),
    path(
        "homeowner/direct-offers/<uuid:public_id>/payment-authorization/",
        HomeownerDirectOfferPaymentAuthorizationView.as_view(),
        name="mobile_homeowner_direct_offer_payment_authorization",
    ),
    path(
        "homeowner/jobs/<uuid:public_id>/payment-status/",
        HomeownerJobPaymentStatusView.as_view(),
        name="mobile_homeowner_job_payment_status",
    ),
]
