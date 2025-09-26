"""
Mobile API URL configuration.
"""

from django.urls import path
from . import auth
from .customer import profile as customer_profile
from .handyman import profile as handyman_profile

urlpatterns = [
    # Authentication endpoints
    path("auth/register", auth.RegisterView.as_view(), name="mobile_auth_register"),
    path("auth/login", auth.LoginView.as_view(), name="mobile_auth_login"),
    path(
        "auth/login/google",
        auth.GoogleLoginView.as_view(),
        name="mobile_auth_google_login",
    ),
    path(
        "auth/activate-role",
        auth.ActivateRoleView.as_view(),
        name="mobile_auth_activate_role",
    ),
    path(
        "auth/email/verify",
        auth.EmailVerifyView.as_view(),
        name="mobile_auth_email_verify",
    ),
    path(
        "auth/email/resend",
        auth.EmailResendView.as_view(),
        name="mobile_auth_email_resend",
    ),
    path("auth/refresh", auth.RefreshTokenView.as_view(), name="mobile_auth_refresh"),
    path("auth/logout", auth.LogoutView.as_view(), name="mobile_auth_logout"),
    path(
        "auth/password/forgot",
        auth.ForgotPasswordView.as_view(),
        name="mobile_auth_forgot_password",
    ),
    path(
        "auth/password/verify",
        auth.VerifyPasswordResetView.as_view(),
        name="mobile_auth_verify_password_reset",
    ),
    path(
        "auth/password/reset",
        auth.ResetPasswordView.as_view(),
        name="mobile_auth_reset_password",
    ),
    path(
        "auth/password/change",
        auth.ChangePasswordView.as_view(),
        name="mobile_auth_change_password",
    ),
    # Role-specific profile endpoints
    path(
        "customer/profile",
        customer_profile.CustomerProfileView.as_view(),
        name="mobile_customer_profile",
    ),
    path(
        "handyman/profile",
        handyman_profile.HandymanProfileView.as_view(),
        name="mobile_handyman_profile",
    ),
]
