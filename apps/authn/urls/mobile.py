"""
Mobile authentication URL configuration.
"""

from django.urls import path

from ..views import mobile as mobile_views

urlpatterns = [
    # Authentication endpoints
    path(
        "auth/register",
        mobile_views.RegisterView.as_view(),
        name="mobile_auth_register",
    ),
    path("auth/login", mobile_views.LoginView.as_view(), name="mobile_auth_login"),
    path(
        "auth/login/google",
        mobile_views.GoogleLoginView.as_view(),
        name="mobile_auth_google_login",
    ),
    path(
        "auth/activate-role",
        mobile_views.ActivateRoleView.as_view(),
        name="mobile_auth_activate_role",
    ),
    path(
        "auth/email/verify",
        mobile_views.EmailVerifyView.as_view(),
        name="mobile_auth_email_verify",
    ),
    path(
        "auth/email/resend",
        mobile_views.EmailResendView.as_view(),
        name="mobile_auth_email_resend",
    ),
    path(
        "auth/refresh",
        mobile_views.RefreshTokenView.as_view(),
        name="mobile_auth_refresh",
    ),
    path("auth/logout", mobile_views.LogoutView.as_view(), name="mobile_auth_logout"),
    path(
        "auth/password/forgot",
        mobile_views.ForgotPasswordView.as_view(),
        name="mobile_auth_forgot_password",
    ),
    path(
        "auth/password/verify",
        mobile_views.VerifyPasswordResetView.as_view(),
        name="mobile_auth_verify_password_reset",
    ),
    path(
        "auth/password/reset",
        mobile_views.ResetPasswordView.as_view(),
        name="mobile_auth_reset_password",
    ),
    path(
        "auth/password/change",
        mobile_views.ChangePasswordView.as_view(),
        name="mobile_auth_change_password",
    ),
    # Phone verification endpoints
    path(
        "auth/phone/send",
        mobile_views.PhoneSendView.as_view(),
        name="mobile_auth_phone_send",
    ),
    path(
        "auth/phone/verify",
        mobile_views.PhoneVerifyView.as_view(),
        name="mobile_auth_phone_verify",
    ),
]
