"""Web authentication views reusing mobile implementations."""

from drf_spectacular.utils import OpenApiExample, extend_schema

from ..serializers import (
    ActivateRoleSerializer,
    ChangePasswordSerializer,
    EmailResendSerializer,
    EmailVerificationSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetTokenResponseEnvelope,
    RefreshTokenSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    SuccessMessageResponseSerializer,
    TokenResponseEnvelope,
    VerifyPasswordResetSerializer,
)
from .mobile import (
    ActivateRoleView as MobileActivateRoleView,
)
from .mobile import (
    ChangePasswordView as MobileChangePasswordView,
)
from .mobile import (
    EmailResendView as MobileEmailResendView,
)
from .mobile import (
    EmailVerifyView as MobileEmailVerifyView,
)
from .mobile import (
    ForgotPasswordView as MobileForgotPasswordView,
)
from .mobile import (
    LoginView as MobileLoginView,
)
from .mobile import (
    LogoutView as MobileLogoutView,
)
from .mobile import (
    RefreshTokenView as MobileRefreshTokenView,
)
from .mobile import (
    RegisterView as MobileRegisterView,
)
from .mobile import (
    ResetPasswordView as MobileResetPasswordView,
)
from .mobile import (
    VerifyPasswordResetView as MobileVerifyPasswordResetView,
)


class RegisterView(MobileRegisterView):
    """Register a new user via web."""

    platform = "web"
    throttle_scope = "web:register"

    @extend_schema(
        request=RegisterSerializer,
        responses={201: TokenResponseEnvelope},
        description="Register a new user account for the web app. Creates user with optional initial role and sends email verification.",
        summary="Register new user",
        tags=["Web Authentication"],
        examples=[
            OpenApiExample(
                "Register Request",
                value={
                    "email": "user@example.com",
                    "password": "SecureP@ss123",
                    "initial_role": "homeowner",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "User registered successfully",
                    "data": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "token_type": "bearer",
                        "active_role": "homeowner",
                        "next_action": "verify_email",
                        "email_verified": False,
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    def post(self, request):
        return super()._handle_post(request)


class LoginView(MobileLoginView):
    """Login a user via web."""

    platform = "web"
    throttle_scope = "web:login"

    @extend_schema(
        request=LoginSerializer,
        responses={200: TokenResponseEnvelope},
        description="Login with email and password via web app. Returns JWT tokens for authenticated access.",
        summary="User login",
        tags=["Web Authentication"],
        examples=[
            OpenApiExample(
                "Login Request",
                value={"email": "user@example.com", "password": "SecureP@ss123"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Login successful",
                    "data": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "token_type": "bearer",
                        "active_role": "homeowner",
                        "next_action": "none",
                        "email_verified": True,
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request):
        return super()._handle_post(request)


class ActivateRoleView(MobileActivateRoleView):
    """Activate a role for the web user."""

    platform = "web"
    throttle_scope = "web:activate_role"

    @extend_schema(
        request=ActivateRoleSerializer,
        responses={200: TokenResponseEnvelope},
        description="Activate a role for authenticated user via web app and receive updated tokens.",
        summary="Activate user role",
        tags=["Web Authentication"],
        examples=[
            OpenApiExample(
                "Activate Role Request",
                value={"role": "handyman"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Role activated successfully",
                    "data": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "token_type": "bearer",
                        "active_role": "handyman",
                        "email_verified": True,
                        "next_action": "fill_profile",
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request):
        return super()._handle_post(request)


class EmailVerifyView(MobileEmailVerifyView):
    """Verify email for web users."""

    platform = "web"
    throttle_scope = "web:verify_email"

    @extend_schema(
        request=EmailVerificationSerializer,
        responses={200: TokenResponseEnvelope},
        description="Verify email address using 6-digit OTP code sent via email for web users.",
        summary="Verify email with OTP",
        tags=["Web Authentication"],
        examples=[
            OpenApiExample(
                "Verify Email Request",
                value={"email": "user@example.com", "otp": "123456"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Email verified successfully",
                    "data": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "token_type": "bearer",
                        "active_role": "homeowner",
                        "next_action": "fill_profile",
                        "email_verified": True,
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request):
        return super()._handle_post(request)


class EmailResendView(MobileEmailResendView):
    """Resend verification email for web users."""

    platform = "web"
    throttle_scope = "web:resend_email"

    @extend_schema(
        request=EmailResendSerializer,
        responses={200: SuccessMessageResponseSerializer},
        description="Resend email verification OTP via web app.",
        summary="Resend verification email",
        tags=["Web Authentication"],
        examples=[
            OpenApiExample(
                "Resend Email Request",
                value={"email": "user@example.com"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Verification email sent if account exists",
                    "data": None,
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request):
        return super()._handle_post(request)


class RefreshTokenView(MobileRefreshTokenView):
    """Refresh JWT token for web users."""

    platform = "web"
    throttle_scope = "web:refresh"

    @extend_schema(
        request=RefreshTokenSerializer,
        responses={200: TokenResponseEnvelope},
        description="Refresh access token using refresh token via web app.",
        summary="Refresh access token",
        tags=["Web Authentication"],
        examples=[
            OpenApiExample(
                "Refresh Token Request",
                value={"refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Token refreshed successfully",
                    "data": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "token_type": "bearer",
                        "active_role": "homeowner",
                        "next_action": "none",
                        "email_verified": True,
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request):
        return super()._handle_post(request)


class LogoutView(MobileLogoutView):
    """Logout a web user."""

    platform = "web"

    @extend_schema(
        request=LogoutSerializer,
        responses={200: SuccessMessageResponseSerializer},
        description="Logout user via web app.",
        summary="User logout",
        tags=["Web Authentication"],
        examples=[
            OpenApiExample(
                "Logout Request",
                value={"refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Logout successful",
                    "data": None,
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request):
        return super()._handle_post(request)


class ForgotPasswordView(MobileForgotPasswordView):
    """Initiate password reset for web users."""

    platform = "web"
    throttle_scope = "web:forgot_password"

    @extend_schema(
        request=ForgotPasswordSerializer,
        responses={200: SuccessMessageResponseSerializer},
        description="Initiate password reset process via web app.",
        summary="Forgot password",
        tags=["Web Authentication"],
        examples=[
            OpenApiExample(
                "Forgot Password Request",
                value={"email": "user@example.com"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Password reset code sent if account exists",
                    "data": None,
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request):
        return super()._handle_post(request)


class VerifyPasswordResetView(MobileVerifyPasswordResetView):
    """Verify password reset code for web users."""

    platform = "web"
    throttle_scope = "web:verify_password_reset"

    @extend_schema(
        request=VerifyPasswordResetSerializer,
        responses={200: PasswordResetTokenResponseEnvelope},
        description="Verify password reset code via web app.",
        summary="Verify reset code",
        tags=["Web Authentication"],
        examples=[
            OpenApiExample(
                "Verify Reset Code Request",
                value={"email": "user@example.com", "otp": "123456"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Reset code verified successfully",
                    "data": {"reset_token": "abc123def456...", "expires_in": 900},
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request):
        return super()._handle_post(request)


class ResetPasswordView(MobileResetPasswordView):
    """Reset password for web users."""

    platform = "web"
    throttle_scope = "web:reset_password"

    @extend_schema(
        request=ResetPasswordSerializer,
        responses={200: SuccessMessageResponseSerializer},
        description="Reset password with reset token via web app.",
        summary="Reset password",
        tags=["Web Authentication"],
        examples=[
            OpenApiExample(
                "Reset Password Request",
                value={
                    "reset_token": "abc123def456...",
                    "new_password": "NewSecureP@ss123",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Password reset successfully",
                    "data": None,
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request):
        return super()._handle_post(request)


class ChangePasswordView(MobileChangePasswordView):
    """Change password for authenticated web users."""

    platform = "web"
    throttle_scope = "web:change_password"

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: SuccessMessageResponseSerializer},
        description="Change password for authenticated user via web app.",
        summary="Change password",
        tags=["Web Authentication"],
        examples=[
            OpenApiExample(
                "Change Password Request",
                value={
                    "current_password": "OldSecureP@ss123",
                    "new_password": "NewSecureP@ss123",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Password changed successfully",
                    "data": None,
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request):
        return super()._handle_post(request)
