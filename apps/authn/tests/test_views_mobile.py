"""Tests for mobile authentication API views."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.authn.twilio_service import VerificationResult
from apps.authn.views import mobile as mobile_views
from apps.profiles.models import HomeownerProfile

User = get_user_model()


def make_serializer(validated_data=None, *, is_valid=True, errors=None):
    """Create a serializer double with configurable behaviour."""
    serializer = MagicMock()
    serializer.is_valid.return_value = is_valid
    serializer.validated_data = validated_data or {}
    serializer.errors = errors or {"detail": ["invalid"]}
    return serializer


class MobileRegisterViewTests(TestCase):
    """Tests for RegisterView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = mobile_views.RegisterView.as_view()

    def test_register_success_user_found(self):
        data = {
            "email": "new@example.com",
            "password": "Complex123!",
            "initial_role": "homeowner",
        }
        request = self.factory.post("/auth/register", data, format="json")
        serializer = make_serializer(validated_data=data)

        tokens = {
            "access_token": "access",
            "refresh_token": "refresh",
            "token_type": "bearer",
        }

        with (
            patch(
                "apps.authn.views.mobile.RegisterSerializer", return_value=serializer
            ),
            patch(
                "apps.authn.views.mobile.auth_service.register_user",
                return_value=tokens.copy(),
            ),
            patch(
                "apps.authn.views.mobile.auth_service.get_next_action_for_user",
                return_value="fill_profile",
            ) as mock_next_action,
            patch.object(User.objects, "get") as mock_get,
        ):
            mock_get.return_value = SimpleNamespace(
                is_email_verified=True, active_role="homeowner"
            )

            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "User registered successfully")
        self.assertEqual(response.data["data"]["next_action"], "fill_profile")
        self.assertTrue(response.data["data"]["email_verified"])
        self.assertEqual(response.data["data"]["active_role"], "homeowner")
        mock_next_action.assert_called_once()

    def test_register_success_user_missing(self):
        data = {"email": "missing@example.com", "password": "Complex123!"}
        request = self.factory.post("/auth/register", data, format="json")
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.RegisterSerializer", return_value=serializer
            ),
            patch(
                "apps.authn.views.mobile.auth_service.register_user",
                return_value={
                    "access_token": "a",
                    "refresh_token": "b",
                    "token_type": "bearer",
                },
            ),
            patch(
                "apps.authn.views.mobile.auth_service.get_next_action_for_user",
                return_value="verify_email",
            ),
            patch.object(User.objects, "get", side_effect=User.DoesNotExist),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payload = response.data["data"]
        self.assertEqual(payload["next_action"], "verify_email")
        self.assertFalse(payload["email_verified"])
        self.assertIsNone(payload["active_role"])

    def test_register_failure_from_service(self):
        data = {"email": "fail@example.com", "password": "Complex123!"}
        request = self.factory.post("/auth/register", data, format="json")
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.RegisterSerializer", return_value=serializer
            ),
            patch(
                "apps.authn.views.mobile.auth_service.register_user",
                side_effect=RuntimeError("boom"),
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Registration failed")

    def test_register_invalid_serializer(self):
        serializer = make_serializer(is_valid=False)
        request = self.factory.post("/auth/register", {}, format="json")

        with patch(
            "apps.authn.views.mobile.RegisterSerializer", return_value=serializer
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Validation failed")


class MobileLoginViewTests(TestCase):
    """Tests for LoginView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = mobile_views.LoginView.as_view()

    def test_login_success(self):
        data = {"email": "user@example.com", "password": "pass"}
        request = self.factory.post("/auth/login", data, format="json")
        serializer = make_serializer(validated_data=data)
        tokens = {"access_token": "a", "refresh_token": "r", "token_type": "bearer"}

        with (
            patch("apps.authn.views.mobile.LoginSerializer", return_value=serializer),
            patch(
                "apps.authn.views.mobile.auth_service.login_user",
                return_value=tokens.copy(),
            ),
            patch(
                "apps.authn.views.mobile.auth_service.get_next_action_for_user",
                return_value="none",
            ),
            patch.object(User.objects, "get") as mock_get,
        ):
            mock_get.return_value = SimpleNamespace(
                is_email_verified=False, active_role=None
            )
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Login successful")
        payload = response.data["data"]
        self.assertFalse(payload["email_verified"])
        self.assertIsNone(payload["active_role"])
        self.assertEqual(payload["next_action"], "none")

    def test_login_invalid_credentials(self):
        data = {"email": "user@example.com", "password": "wrong"}
        request = self.factory.post("/auth/login", data, format="json")
        serializer = make_serializer(validated_data=data)

        with (
            patch("apps.authn.views.mobile.LoginSerializer", return_value=serializer),
            patch("apps.authn.views.mobile.auth_service.login_user", return_value=None),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["message"], "Invalid credentials")

    def test_login_success_user_lookup_missing(self):
        data = {"email": "user@example.com", "password": "pass"}
        request = self.factory.post("/auth/login", data, format="json")
        serializer = make_serializer(validated_data=data)
        tokens = {"access_token": "a", "refresh_token": "r", "token_type": "bearer"}

        with (
            patch("apps.authn.views.mobile.LoginSerializer", return_value=serializer),
            patch(
                "apps.authn.views.mobile.auth_service.login_user",
                return_value=tokens.copy(),
            ),
            patch.object(User.objects, "get", side_effect=User.DoesNotExist),
        ):
            response = self.view(request)

        payload = response.data["data"]
        self.assertEqual(payload["next_action"], "none")
        self.assertFalse(payload["email_verified"])

    def test_login_invalid_serializer(self):
        serializer = make_serializer(is_valid=False)
        request = self.factory.post("/auth/login", {}, format="json")

        with patch("apps.authn.views.mobile.LoginSerializer", return_value=serializer):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MobileGoogleLoginViewTests(TestCase):
    """Tests for GoogleLoginView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = mobile_views.GoogleLoginView.as_view()

    def test_google_login_success_with_user(self):
        data = {"id_token": "token"}
        request = self.factory.post("/auth/login/google", data, format="json")
        serializer = make_serializer(validated_data=data)
        tokens = {
            "access_token": "access",
            "refresh_token": "refresh",
            "token_type": "bearer",
        }

        with (
            patch(
                "apps.authn.views.mobile.GoogleLoginSerializer", return_value=serializer
            ),
            patch(
                "apps.authn.views.mobile.auth_service.google_login",
                return_value=tokens.copy(),
            ),
            patch(
                "apps.authn.views.mobile.jwt_service.decode_token",
                return_value={"sub": "public-id"},
            ),
            patch.object(User.objects, "get") as mock_get,
            patch(
                "apps.authn.views.mobile.auth_service.get_next_action_for_user",
                return_value="fill_profile",
            ),
        ):
            mock_get.return_value = SimpleNamespace(is_email_verified=True)
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["email_verified"], True)
        self.assertEqual(response.data["data"]["next_action"], "fill_profile")

    def test_google_login_fallback_on_missing_user(self):
        data = {"id_token": "token"}
        request = self.factory.post("/auth/login/google", data, format="json")
        serializer = make_serializer(validated_data=data)
        tokens = {
            "access_token": "access",
            "refresh_token": "refresh",
            "token_type": "bearer",
        }

        with (
            patch(
                "apps.authn.views.mobile.GoogleLoginSerializer", return_value=serializer
            ),
            patch(
                "apps.authn.views.mobile.auth_service.google_login",
                return_value=tokens.copy(),
            ),
            patch(
                "apps.authn.views.mobile.jwt_service.decode_token",
                return_value={"sub": "public-id"},
            ),
            patch.object(User.objects, "get", side_effect=Exception("boom")),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data["data"]
        self.assertEqual(payload["next_action"], "none")
        self.assertTrue(payload["email_verified"])

    def test_google_login_service_error(self):
        data = {"id_token": "token"}
        request = self.factory.post("/auth/login/google", data, format="json")
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.GoogleLoginSerializer", return_value=serializer
            ),
            patch(
                "apps.authn.views.mobile.auth_service.google_login",
                side_effect=ValueError("bad"),
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Google authentication failed")

    def test_google_login_invalid_serializer(self):
        serializer = make_serializer(is_valid=False)
        request = self.factory.post("/auth/login/google", {}, format="json")

        with patch(
            "apps.authn.views.mobile.GoogleLoginSerializer", return_value=serializer
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MobileActivateRoleViewTests(TestCase):
    """Tests for ActivateRoleView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = mobile_views.ActivateRoleView.as_view()
        self.user = User.objects.create_user(
            email="user@example.com", password="Complex123!"
        )

    def test_activate_role_success(self):
        data = {"role": "homeowner"}
        request = self.factory.post("/auth/activate-role", data, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(validated_data=data)

        # Mock user refresh_from_db to actually set active_role
        def mock_refresh():
            self.user.active_role = "homeowner"
            self.user.save(update_fields=["active_role"])

        with (
            patch(
                "apps.authn.views.mobile.ActivateRoleSerializer",
                return_value=serializer,
            ),
            patch(
                "apps.authn.views.mobile.auth_service.activate_role",
                return_value={"role": "homeowner", "email_verified": True},
            ),
            patch(
                "apps.authn.views.mobile.jwt_service.create_token_pair",
                return_value={
                    "access_token": "a",
                    "refresh_token": "r",
                    "token_type": "bearer",
                },
            ),
            patch(
                "apps.authn.views.mobile.auth_service.get_next_action_for_user",
                return_value="none",
            ),
            patch.object(self.user, "refresh_from_db", side_effect=mock_refresh),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data["data"]
        self.assertEqual(payload["active_role"], "homeowner")
        self.assertEqual(payload["next_action"], "none")
        # Verify active_role is set in database
        self.user.refresh_from_db()
        self.assertEqual(self.user.active_role, "homeowner")

    def test_activate_role_invalid_serializer(self):
        request = self.factory.post("/auth/activate-role", {}, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(is_valid=False)

        with patch(
            "apps.authn.views.mobile.ActivateRoleSerializer", return_value=serializer
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MobileEmailVerifyViewTests(TestCase):
    """Tests for EmailVerifyView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = mobile_views.EmailVerifyView.as_view()
        self.user = User.objects.create_user(
            email="user@example.com", password="Password123!"
        )

    def test_email_verify_with_payload_email(self):
        data = {"email": "user@example.com", "otp": "123456"}
        request = self.factory.post("/auth/email/verify", data, format="json")
        serializer = make_serializer(validated_data=data)
        tokens = {"access_token": "a", "refresh_token": "r", "token_type": "bearer"}

        with (
            patch(
                "apps.authn.views.mobile.EmailVerificationSerializer",
                return_value=serializer,
            ),
            patch(
                "apps.authn.views.mobile.auth_service.verify_email",
                return_value=self.user,
            ),
            patch(
                "apps.authn.views.mobile.jwt_service.create_token_pair",
                return_value=tokens.copy(),
            ),
            patch(
                "apps.authn.views.mobile.auth_service.get_next_action_for_user",
                return_value="none",
            ),
        ):
            self.user.email_verified_at = None
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data["data"]
        self.assertIn("next_action", payload)

    def test_email_verify_uses_authenticated_user_email(self):
        data = {"otp": "123456"}
        request = self.factory.post("/auth/email/verify", data, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.EmailVerificationSerializer",
                return_value=serializer,
            ),
            patch(
                "apps.authn.views.mobile.auth_service.verify_email",
                return_value=self.user,
            ),
            patch(
                "apps.authn.views.mobile.jwt_service.create_token_pair",
                return_value={
                    "access_token": "a",
                    "refresh_token": "r",
                    "token_type": "bearer",
                },
            ),
            patch(
                "apps.authn.views.mobile.auth_service.get_next_action_for_user",
                return_value="fill_profile",
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["next_action"], "fill_profile")

    def test_email_verify_requires_email_when_not_authenticated(self):
        data = {"otp": "123456"}
        request = self.factory.post("/auth/email/verify", data, format="json")
        serializer = make_serializer(validated_data=data)

        with patch(
            "apps.authn.views.mobile.EmailVerificationSerializer",
            return_value=serializer,
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Email required")

    def test_email_verify_invalid_otp(self):
        data = {"email": "user@example.com", "otp": "123456"}
        request = self.factory.post("/auth/email/verify", data, format="json")
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.EmailVerificationSerializer",
                return_value=serializer,
            ),
            patch(
                "apps.authn.views.mobile.auth_service.verify_email", return_value=None
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Email verification failed")

    def test_email_verify_invalid_serializer(self):
        serializer = make_serializer(is_valid=False)
        request = self.factory.post("/auth/email/verify", {}, format="json")

        with patch(
            "apps.authn.views.mobile.EmailVerificationSerializer",
            return_value=serializer,
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MobileEmailResendViewTests(TestCase):
    """Tests for EmailResendView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = mobile_views.EmailResendView.as_view()
        self.user = User.objects.create_user(
            email="user@example.com", password="Password123!"
        )

    def test_resend_with_explicit_email(self):
        data = {"email": "user@example.com"}
        request = self.factory.post("/auth/email/resend", data, format="json")
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.EmailResendSerializer", return_value=serializer
            ),
            patch.object(User.objects, "get") as mock_get,
            patch(
                "apps.authn.views.mobile.auth_service.resend_email_verification"
            ) as mock_resend,
        ):
            mock_get.return_value = SimpleNamespace(is_email_verified=False)
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_resend.assert_called_once()

    def test_resend_authenticated_user_already_verified(self):
        data = {"email": None}
        request = self.factory.post("/auth/email/resend", data, format="json")
        self.user.email_verified_at = True
        force_authenticate(request, user=self.user)
        serializer = make_serializer(validated_data=data)

        with patch(
            "apps.authn.views.mobile.EmailResendSerializer", return_value=serializer
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["message"], "Email already verified")
        self.assertIsNone(response.data["data"])
        self.assertIsNone(response.data["errors"])

    def test_resend_authenticated_user_without_existing_record(self):
        data = {"email": None}
        request = self.factory.post("/auth/email/resend", data, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.EmailResendSerializer", return_value=serializer
            ),
            patch.object(User.objects, "get", side_effect=User.DoesNotExist),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_resend_with_verified_user_in_database(self):
        data = {"email": "user@example.com"}
        request = self.factory.post("/auth/email/resend", data, format="json")
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.EmailResendSerializer", return_value=serializer
            ),
            patch.object(User.objects, "get") as mock_get,
            patch(
                "apps.authn.views.mobile.auth_service.resend_email_verification"
            ) as mock_resend,
        ):
            mock_get.return_value = SimpleNamespace(is_email_verified=True)
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_resend.assert_not_called()

    def test_resend_requires_email_when_unauthenticated(self):
        data = {"email": None}
        request = self.factory.post("/auth/email/resend", data, format="json")
        serializer = make_serializer(validated_data=data)

        with patch(
            "apps.authn.views.mobile.EmailResendSerializer", return_value=serializer
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Email required")

    def test_resend_invalid_serializer(self):
        serializer = make_serializer(is_valid=False)
        request = self.factory.post("/auth/email/resend", {}, format="json")

        with patch(
            "apps.authn.views.mobile.EmailResendSerializer", return_value=serializer
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MobileRefreshTokenViewTests(TestCase):
    """Tests for RefreshTokenView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = mobile_views.RefreshTokenView.as_view()

    def test_refresh_success(self):
        data = {"refresh_token": "refresh"}
        request = self.factory.post("/auth/refresh", data, format="json")
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.RefreshTokenSerializer",
                return_value=serializer,
            ),
            patch(
                "apps.authn.views.mobile.jwt_service.refresh_token_pair",
                return_value={"access_token": "a"},
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_refresh_unauthorized_on_error(self):
        data = {"refresh_token": "refresh"}
        request = self.factory.post("/auth/refresh", data, format="json")
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.RefreshTokenSerializer",
                return_value=serializer,
            ),
            patch(
                "apps.authn.views.mobile.jwt_service.refresh_token_pair",
                side_effect=RuntimeError("nope"),
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_invalid_serializer(self):
        serializer = make_serializer(is_valid=False)
        request = self.factory.post("/auth/refresh", {}, format="json")

        with patch(
            "apps.authn.views.mobile.RefreshTokenSerializer", return_value=serializer
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MobileLogoutViewTests(TestCase):
    """Tests for LogoutView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = mobile_views.LogoutView.as_view()
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass12345!"
        )

    def test_logout_with_refresh_token(self):
        request = self.factory.post(
            "/auth/logout", {"refresh_token": "tok"}, format="json"
        )
        force_authenticate(request, user=self.user)
        serializer = make_serializer(validated_data={"refresh_token": "tok"})

        with (
            patch("apps.authn.views.mobile.LogoutSerializer", return_value=serializer),
            patch(
                "apps.authn.views.mobile.jwt_service.revoke_refresh_token"
            ) as mock_revoke,
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Logout successful")
        self.assertIsNone(response.data["data"])
        mock_revoke.assert_called_once_with("tok")

    def test_logout_without_refresh_token(self):
        request = self.factory.post("/auth/logout", {}, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(validated_data={"refresh_token": None})

        with (
            patch("apps.authn.views.mobile.LogoutSerializer", return_value=serializer),
            patch(
                "apps.authn.views.mobile.jwt_service.revoke_refresh_token"
            ) as mock_revoke,
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Logout successful")
        self.assertIsNone(response.data["data"])
        mock_revoke.assert_not_called()

    def test_logout_invalid_serializer(self):
        request = self.factory.post("/auth/logout", {}, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(is_valid=False)

        with patch("apps.authn.views.mobile.LogoutSerializer", return_value=serializer):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MobileForgotPasswordViewTests(TestCase):
    """Tests for ForgotPasswordView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = mobile_views.ForgotPasswordView.as_view()

    def test_forgot_password_success(self):
        data = {"email": "user@example.com"}
        request = self.factory.post("/auth/password/forgot", data, format="json")
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.ForgotPasswordSerializer",
                return_value=serializer,
            ),
            patch(
                "apps.authn.views.mobile.auth_service.forgot_password"
            ) as mock_forgot,
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_forgot.assert_called_once()

    def test_forgot_password_invalid_serializer(self):
        serializer = make_serializer(is_valid=False)
        request = self.factory.post("/auth/password/forgot", {}, format="json")

        with patch(
            "apps.authn.views.mobile.ForgotPasswordSerializer", return_value=serializer
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MobileVerifyPasswordResetViewTests(TestCase):
    """Tests for VerifyPasswordResetView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = mobile_views.VerifyPasswordResetView.as_view()

    def test_verify_reset_success(self):
        data = {"email": "user@example.com", "otp": "123456"}
        request = self.factory.post("/auth/password/verify", data, format="json")
        serializer = make_serializer(validated_data=data)
        result = {"reset_token": "token", "expires_in": 10}

        with (
            patch(
                "apps.authn.views.mobile.VerifyPasswordResetSerializer",
                return_value=serializer,
            ),
            patch(
                "apps.authn.views.mobile.auth_service.verify_password_reset_code",
                return_value=result,
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"], result)

    def test_verify_reset_invalid_code(self):
        data = {"email": "user@example.com", "otp": "123456"}
        request = self.factory.post("/auth/password/verify", data, format="json")
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.VerifyPasswordResetSerializer",
                return_value=serializer,
            ),
            patch(
                "apps.authn.views.mobile.auth_service.verify_password_reset_code",
                return_value=None,
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Code verification failed")

    def test_verify_reset_invalid_serializer(self):
        serializer = make_serializer(is_valid=False)
        request = self.factory.post("/auth/password/verify", {}, format="json")

        with patch(
            "apps.authn.views.mobile.VerifyPasswordResetSerializer",
            return_value=serializer,
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MobileResetPasswordViewTests(TestCase):
    """Tests for ResetPasswordView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = mobile_views.ResetPasswordView.as_view()

    def test_reset_password_success(self):
        data = {"reset_token": "token", "new_password": "NewPass123!"}
        request = self.factory.post("/auth/password/reset", data, format="json")
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.ResetPasswordSerializer",
                return_value=serializer,
            ),
            patch(
                "apps.authn.views.mobile.auth_service.reset_password", return_value=True
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Password reset successfully")

    def test_reset_password_failure(self):
        data = {"reset_token": "token", "new_password": "NewPass123!"}
        request = self.factory.post("/auth/password/reset", data, format="json")
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.ResetPasswordSerializer",
                return_value=serializer,
            ),
            patch(
                "apps.authn.views.mobile.auth_service.reset_password",
                return_value=False,
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Password reset failed")

    def test_reset_password_invalid_serializer(self):
        serializer = make_serializer(is_valid=False)
        request = self.factory.post("/auth/password/reset", {}, format="json")

        with patch(
            "apps.authn.views.mobile.ResetPasswordSerializer", return_value=serializer
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MobileChangePasswordViewTests(TestCase):
    """Tests for ChangePasswordView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = mobile_views.ChangePasswordView.as_view()
        self.user = User.objects.create_user(
            email="user@example.com", password="OldPass123!"
        )

    def test_change_password_success(self):
        data = {"current_password": "old", "new_password": "NewPass123!"}
        request = self.factory.post("/auth/password/change", data, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.ChangePasswordSerializer",
                return_value=serializer,
            ),
            patch(
                "apps.authn.views.mobile.auth_service.change_password",
                return_value=True,
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Password changed successfully")

    def test_change_password_wrong_current(self):
        data = {"current_password": "old", "new_password": "NewPass123!"}
        request = self.factory.post("/auth/password/change", data, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.ChangePasswordSerializer",
                return_value=serializer,
            ),
            patch(
                "apps.authn.views.mobile.auth_service.change_password",
                return_value=False,
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Password change failed")

    def test_change_password_invalid_serializer(self):
        request = self.factory.post("/auth/password/change", {}, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(is_valid=False)

        with patch(
            "apps.authn.views.mobile.ChangePasswordSerializer", return_value=serializer
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MobilePhoneSendViewTests(TestCase):
    """Tests for PhoneSendView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = mobile_views.PhoneSendView.as_view()
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass12345!"
        )

    def test_phone_send_success(self):
        data = {"phone_number": "+6281234567890"}
        request = self.factory.post("/auth/phone/send", data, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.PhoneSendSerializer", return_value=serializer
            ),
            patch(
                "apps.authn.views.mobile.twilio_service.send_verification",
                return_value=VerificationResult(success=True, status="pending"),
            ),
            patch(
                "apps.authn.views.mobile.twilio_service.mask_phone_number",
                return_value="+6281****7890",
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Verification code sent")
        self.assertEqual(response.data["data"]["masked_phone"], "+6281****7890")
        self.assertIn("expires_in", response.data["data"])

    def test_phone_send_twilio_failure(self):
        data = {"phone_number": "+6281234567890"}
        request = self.factory.post("/auth/phone/send", data, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.PhoneSendSerializer", return_value=serializer
            ),
            patch(
                "apps.authn.views.mobile.twilio_service.send_verification",
                return_value=VerificationResult(
                    success=False, error="Invalid phone number"
                ),
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["message"], "Failed to send verification code")

    def test_phone_send_invalid_serializer(self):
        request = self.factory.post("/auth/phone/send", {}, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(is_valid=False)

        with patch(
            "apps.authn.views.mobile.PhoneSendSerializer", return_value=serializer
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_phone_send_unauthenticated(self):
        data = {"phone_number": "+6281234567890"}
        request = self.factory.post("/auth/phone/send", data, format="json")
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MobilePhoneVerifyViewTests(TestCase):
    """Tests for PhoneVerifyView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = mobile_views.PhoneVerifyView.as_view()
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass12345!"
        )

    def test_phone_verify_success(self):
        # Create a real HomeownerProfile for the user
        profile = HomeownerProfile.objects.create(
            user=self.user,
            display_name="Test User",
            phone_number="",
        )

        data = {"phone_number": "+6281234567890", "otp": "123456"}
        request = self.factory.post("/auth/phone/verify", data, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.PhoneVerifySerializer", return_value=serializer
            ),
            patch(
                "apps.authn.views.mobile.twilio_service.check_verification",
                return_value=VerificationResult(success=True, status="approved"),
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Phone number verified successfully")
        self.assertTrue(response.data["data"]["phone_verified"])
        self.assertEqual(response.data["data"]["phone_number"], "+6281234567890")

        # Verify the profile was updated
        profile.refresh_from_db()
        self.assertEqual(profile.phone_number, "+6281234567890")
        self.assertIsNotNone(profile.phone_verified_at)

    def test_phone_verify_invalid_otp(self):
        data = {"phone_number": "+6281234567890", "otp": "000000"}
        request = self.factory.post("/auth/phone/verify", data, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.PhoneVerifySerializer", return_value=serializer
            ),
            patch(
                "apps.authn.views.mobile.twilio_service.check_verification",
                return_value=VerificationResult(
                    success=False, status="pending", error="Invalid or expired code"
                ),
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Phone verification failed")
        self.assertIn("otp", response.data["errors"])

    def test_phone_verify_no_profile(self):
        data = {"phone_number": "+6281234567890", "otp": "123456"}
        request = self.factory.post("/auth/phone/verify", data, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(validated_data=data)

        with (
            patch(
                "apps.authn.views.mobile.PhoneVerifySerializer", return_value=serializer
            ),
            patch(
                "apps.authn.views.mobile.twilio_service.check_verification",
                return_value=VerificationResult(success=True, status="approved"),
            ),
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("profile", response.data["errors"])

    def test_phone_verify_invalid_serializer(self):
        request = self.factory.post("/auth/phone/verify", {}, format="json")
        force_authenticate(request, user=self.user)
        serializer = make_serializer(is_valid=False)

        with patch(
            "apps.authn.views.mobile.PhoneVerifySerializer", return_value=serializer
        ):
            response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_phone_verify_unauthenticated(self):
        data = {"phone_number": "+6281234567890", "otp": "123456"}
        request = self.factory.post("/auth/phone/verify", data, format="json")
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
