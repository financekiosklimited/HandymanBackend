"""
Web authentication URL configuration.
"""

from django.urls import path
from ..views import web as web_views

urlpatterns = [
    # Authentication endpoints
    path("auth/register", web_views.RegisterView.as_view(), name="web_auth_register"),
    path("auth/login", web_views.LoginView.as_view(), name="web_auth_login"),
    path(
        "auth/login/google",
        web_views.GoogleLoginView.as_view(),
        name="web_auth_google_login",
    ),
    path(
        "auth/activate-role",
        web_views.ActivateRoleView.as_view(),
        name="web_auth_activate_role",
    ),
    path(
        "auth/email/verify",
        web_views.EmailVerifyView.as_view(),
        name="web_auth_email_verify",
    ),
    path(
        "auth/email/resend",
        web_views.EmailResendView.as_view(),
        name="web_auth_email_resend",
    ),
    path("auth/refresh", web_views.RefreshTokenView.as_view(), name="web_auth_refresh"),
    path("auth/logout", web_views.LogoutView.as_view(), name="web_auth_logout"),
    path(
        "auth/password/forgot",
        web_views.ForgotPasswordView.as_view(),
        name="web_auth_forgot_password",
    ),
    path(
        "auth/password/verify",
        web_views.VerifyPasswordResetView.as_view(),
        name="web_auth_verify_password_reset",
    ),
    path(
        "auth/password/reset",
        web_views.ResetPasswordView.as_view(),
        name="web_auth_reset_password",
    ),
    path(
        "auth/password/change",
        web_views.ChangePasswordView.as_view(),
        name="web_auth_change_password",
    ),
]
