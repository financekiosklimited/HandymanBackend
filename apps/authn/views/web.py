"""Web authentication views reusing mobile implementations."""

from drf_spectacular.utils import extend_schema

from ..serializers import (
    ActivateRoleSerializer,
    ChangePasswordSerializer,
    EmailResendSerializer,
    EmailVerificationSerializer,
    ForgotPasswordSerializer,
    GoogleLoginSerializer,
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
    GoogleLoginView as MobileGoogleLoginView,
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

    @extend_schema(
        request=RegisterSerializer,
        responses={201: TokenResponseEnvelope},
        description="Register a new user account for the web app. Creates user with optional initial role and sends email verification.",
        summary="Register new user",
        tags=["Web Authentication"],
    )
    def post(self, request):
        return super()._handle_post(request)


class LoginView(MobileLoginView):
    """Login a user via web."""

    platform = "web"

    @extend_schema(
        request=LoginSerializer,
        responses={200: TokenResponseEnvelope},
        description="Login with email and password via web app. Returns JWT tokens for authenticated access.",
        summary="User login",
        tags=["Web Authentication"],
    )
    def post(self, request):
        return super()._handle_post(request)


class GoogleLoginView(MobileGoogleLoginView):
    """Login with Google OAuth via web."""

    platform = "web"

    @extend_schema(
        request=GoogleLoginSerializer,
        responses={200: TokenResponseEnvelope},
        description="Login with Google OAuth ID token via web app.",
        summary="Google OAuth login",
        tags=["Web Authentication"],
    )
    def post(self, request):
        return super()._handle_post(request)


class ActivateRoleView(MobileActivateRoleView):
    """Activate a role for the web user."""

    platform = "web"

    @extend_schema(
        request=ActivateRoleSerializer,
        responses={200: TokenResponseEnvelope},
        description="Activate a role for authenticated user via web app and receive updated tokens.",
        summary="Activate user role",
        tags=["Web Authentication"],
    )
    def post(self, request):
        return super()._handle_post(request)


class EmailVerifyView(MobileEmailVerifyView):
    """Verify email for web users."""

    platform = "web"

    @extend_schema(
        request=EmailVerificationSerializer,
        responses={200: TokenResponseEnvelope},
        description="Verify email address using 6-digit OTP code sent via email for web users.",
        summary="Verify email with OTP",
        tags=["Web Authentication"],
    )
    def post(self, request):
        return super()._handle_post(request)


class EmailResendView(MobileEmailResendView):
    """Resend verification email for web users."""

    platform = "web"

    @extend_schema(
        request=EmailResendSerializer,
        responses={200: SuccessMessageResponseSerializer},
        description="Resend email verification OTP via web app.",
        summary="Resend verification email",
        tags=["Web Authentication"],
    )
    def post(self, request):
        return super()._handle_post(request)


class RefreshTokenView(MobileRefreshTokenView):
    """Refresh JWT token for web users."""

    platform = "web"

    @extend_schema(
        request=RefreshTokenSerializer,
        responses={200: TokenResponseEnvelope},
        description="Refresh access token using refresh token via web app.",
        summary="Refresh access token",
        tags=["Web Authentication"],
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
    )
    def post(self, request):
        return super()._handle_post(request)


class ForgotPasswordView(MobileForgotPasswordView):
    """Initiate password reset for web users."""

    platform = "web"

    @extend_schema(
        request=ForgotPasswordSerializer,
        responses={200: SuccessMessageResponseSerializer},
        description="Initiate password reset process via web app.",
        summary="Forgot password",
        tags=["Web Authentication"],
    )
    def post(self, request):
        return super()._handle_post(request)


class VerifyPasswordResetView(MobileVerifyPasswordResetView):
    """Verify password reset code for web users."""

    platform = "web"

    @extend_schema(
        request=VerifyPasswordResetSerializer,
        responses={200: PasswordResetTokenResponseEnvelope},
        description="Verify password reset code via web app.",
        summary="Verify reset code",
        tags=["Web Authentication"],
    )
    def post(self, request):
        return super()._handle_post(request)


class ResetPasswordView(MobileResetPasswordView):
    """Reset password for web users."""

    platform = "web"

    @extend_schema(
        request=ResetPasswordSerializer,
        responses={200: SuccessMessageResponseSerializer},
        description="Reset password with reset token via web app.",
        summary="Reset password",
        tags=["Web Authentication"],
    )
    def post(self, request):
        return super()._handle_post(request)


class ChangePasswordView(MobileChangePasswordView):
    """Change password for authenticated web users."""

    platform = "web"

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: SuccessMessageResponseSerializer},
        description="Change password for authenticated user via web app.",
        summary="Change password",
        tags=["Web Authentication"],
    )
    def post(self, request):
        return super()._handle_post(request)
