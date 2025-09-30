"""Tests for web authentication view wrappers."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.authn.views import web as web_views

User = get_user_model()


class WebViewDelegationTests(TestCase):
    """Ensure web views delegate to shared mobile handlers and expose web platform."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            email="user@example.com", password="Password123!"
        )

    def _assert_delegation(self, view_cls, mobile_attr, *, needs_auth=False):
        request = self.factory.post("/auth/test", {}, format="json")
        if needs_auth:
            force_authenticate(request, user=self.user)

        mobile_base = getattr(web_views, mobile_attr)

        with patch.object(
            mobile_base, "_handle_post", return_value=Response({"message": "ok"})
        ) as mock_handle:
            response = view_cls.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_handle.assert_called_once()
        self.assertEqual(view_cls.platform, "web")

    def test_register_delegates(self):
        self._assert_delegation(web_views.RegisterView, "MobileRegisterView")

    def test_login_delegates(self):
        self._assert_delegation(web_views.LoginView, "MobileLoginView")

    def test_google_login_delegates(self):
        self._assert_delegation(web_views.GoogleLoginView, "MobileGoogleLoginView")

    def test_activate_role_delegates(self):
        self._assert_delegation(
            web_views.ActivateRoleView, "MobileActivateRoleView", needs_auth=True
        )

    def test_email_verify_delegates(self):
        self._assert_delegation(web_views.EmailVerifyView, "MobileEmailVerifyView")

    def test_email_resend_delegates(self):
        self._assert_delegation(web_views.EmailResendView, "MobileEmailResendView")

    def test_refresh_token_delegates(self):
        self._assert_delegation(web_views.RefreshTokenView, "MobileRefreshTokenView")

    def test_logout_delegates(self):
        self._assert_delegation(
            web_views.LogoutView, "MobileLogoutView", needs_auth=True
        )

    def test_forgot_password_delegates(self):
        self._assert_delegation(
            web_views.ForgotPasswordView, "MobileForgotPasswordView"
        )

    def test_verify_reset_delegates(self):
        self._assert_delegation(
            web_views.VerifyPasswordResetView, "MobileVerifyPasswordResetView"
        )

    def test_reset_password_delegates(self):
        self._assert_delegation(web_views.ResetPasswordView, "MobileResetPasswordView")

    def test_change_password_delegates(self):
        self._assert_delegation(
            web_views.ChangePasswordView, "MobileChangePasswordView", needs_auth=True
        )
