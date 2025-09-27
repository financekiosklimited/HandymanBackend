"""
Mobile authentication views.
"""

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema

from ..serializers import (
    RegisterSerializer,
    LoginSerializer,
    GoogleLoginSerializer,
    ActivateRoleSerializer,
    EmailVerificationSerializer,
    EmailResendSerializer,
    RefreshTokenSerializer,
    LogoutSerializer,
    ForgotPasswordSerializer,
    VerifyPasswordResetSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    TokenResponseSerializer,
    AuthResponseSerializer,
    PasswordResetTokenResponseSerializer,
)
from ..services import auth_service
from ..jwt_service import jwt_service
from apps.common.responses import (
    success_response,
    created_response,
    accepted_response,
    no_content_response,
    validation_error_response,
    unauthorized_response,
    error_response,
)

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]
    # throttle_scope = 'mobile:register'

    @extend_schema(
        request=RegisterSerializer,
        responses={201: TokenResponseSerializer},
        description="Register a new user account. Creates user with optional initial role and sends email verification.",
        summary="Register new user",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Register a new user."""
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                tokens = auth_service.register_user(
                    email=serializer.validated_data["email"],
                    password=serializer.validated_data["password"],
                    initial_role=serializer.validated_data.get("initial_role"),
                    platform="mobile",
                )
                return created_response(tokens)
            except Exception as e:
                return error_response(
                    errors={"registration": str(e)},
                    message="Registration failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
        return validation_error_response(serializer.errors)


class LoginView(APIView):
    permission_classes = [AllowAny]
    # # throttle_scope = 'mobile:login'

    @extend_schema(
        request=LoginSerializer,
        responses={200: TokenResponseSerializer},
        description="Login with email and password via mobile app. Returns JWT tokens for authenticated access.",
        summary="User login",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Login with email and password."""
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            tokens = auth_service.login_user(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
                platform="mobile",
            )

            if tokens:
                return success_response(tokens)
            else:
                return unauthorized_response("Invalid credentials")

        return validation_error_response(serializer.errors)


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]
    # throttle_scope = 'mobile:login_google'

    @extend_schema(
        request=GoogleLoginSerializer,
        responses={200: TokenResponseSerializer},
        description="Login with Google OAuth ID token via mobile app.",
        summary="Google OAuth login",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Login with Google OAuth."""
        serializer = GoogleLoginSerializer(data=request.data)
        if serializer.is_valid():
            try:
                tokens = auth_service.google_login(
                    id_token=serializer.validated_data["id_token"], platform="mobile"
                )
                return success_response(tokens)
            except ValueError as e:
                return error_response(
                    errors={"google": str(e)},
                    message="Google authentication failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        return validation_error_response(serializer.errors)


class ActivateRoleView(APIView):
    permission_classes = [IsAuthenticated]
    # throttle_scope = 'mobile:activate_role'

    @extend_schema(
        request=ActivateRoleSerializer,
        responses={200: AuthResponseSerializer},
        description="Activate a role for authenticated user. Issues new tokens with active role and determines next action.",
        summary="Activate user role",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Activate a role for the user."""
        serializer = ActivateRoleSerializer(data=request.data)
        if serializer.is_valid():
            role_info = auth_service.activate_role(
                user=request.user, role=serializer.validated_data["role"]
            )

            # Generate new token pair with active role
            tokens = jwt_service.create_token_pair(
                user=request.user, platform="mobile", active_role=role_info["role"]
            )

            response_data = {
                **tokens,
                "active_role": role_info["role"],
                "email_verified": role_info["email_verified"],
                "next_action": role_info["next_action"],
            }

            return success_response(response_data)

        return validation_error_response(serializer.errors)


class EmailVerifyView(APIView):
    permission_classes = [AllowAny]
    # # throttle_scope = 'mobile:verify_email'

    @extend_schema(
        request=EmailVerificationSerializer,
        responses={200: TokenResponseSerializer},
        description="Verify email address using 6-digit OTP code sent via email for mobile users.",
        summary="Verify email with OTP",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Verify email with OTP."""
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            user = auth_service.verify_email(
                email=serializer.validated_data["email"],
                otp=serializer.validated_data["otp"],
            )

            if user:
                # Generate new token pair with updated email verification status
                tokens = jwt_service.create_token_pair(
                    user=user, platform="mobile", active_role=None
                )
                return success_response(tokens)
            else:
                return error_response(
                    errors={"otp": "Invalid or expired OTP"},
                    message="Email verification failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        return validation_error_response(serializer.errors)


class EmailResendView(APIView):
    permission_classes = [AllowAny]
    # throttle_scope = 'mobile:resend_email'

    @extend_schema(
        request=EmailResendSerializer,
        responses={202: None},
        description="Resend email verification OTP via mobile app.",
        summary="Resend verification email",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Resend email verification."""
        serializer = EmailResendSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get("email")

            if not email:
                # User is authenticated, use their email
                if request.user and request.user.is_authenticated:
                    if request.user.is_email_verified:
                        # Already verified, do nothing
                        return accepted_response()
                    email = request.user.email
                else:
                    return error_response(
                        errors={"email": "Email is required when not authenticated"},
                        message="Email required",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

            # Find user and resend verification
            try:
                user = User.objects.get(email=email, is_active=True)
                if not user.is_email_verified:
                    auth_service.resend_email_verification(user)
            except User.DoesNotExist:
                # Don't reveal if email exists
                pass

            return accepted_response()

        return validation_error_response(serializer.errors)


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    # throttle_scope = 'mobile:refresh'

    @extend_schema(
        request=RefreshTokenSerializer,
        responses={200: TokenResponseSerializer},
        description="Refresh access token using refresh token via mobile app.",
        summary="Refresh access token",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Refresh access token."""
        serializer = RefreshTokenSerializer(data=request.data)
        if serializer.is_valid():
            try:
                tokens = jwt_service.refresh_token_pair(
                    refresh_token=serializer.validated_data["refresh_token"],
                    platform="mobile",
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    ip_address=request.META.get("REMOTE_ADDR"),
                )
                return success_response(tokens)
            except Exception as e:
                return unauthorized_response(str(e))

        return validation_error_response(serializer.errors)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        responses={204: None},
        description="Logout user via mobile app.",
        summary="User logout",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Logout user and optionally revoke refresh token."""
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            refresh_token = serializer.validated_data.get("refresh_token")

            if refresh_token:
                jwt_service.revoke_refresh_token(refresh_token)

            return no_content_response()

        return validation_error_response(serializer.errors)


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    # throttle_scope = 'mobile:forgot_password'

    @extend_schema(
        request=ForgotPasswordSerializer,
        responses={202: None},
        description="Initiate password reset process via mobile app.",
        summary="Forgot password",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Initiate password reset process."""
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            auth_service.forgot_password(email=serializer.validated_data["email"])
            return accepted_response()

        return validation_error_response(serializer.errors)


class VerifyPasswordResetView(APIView):
    permission_classes = [AllowAny]
    # throttle_scope = 'mobile:verify_password_reset'

    @extend_schema(
        request=VerifyPasswordResetSerializer,
        responses={200: PasswordResetTokenResponseSerializer},
        description="Verify password reset code via mobile app.",
        summary="Verify reset code",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Verify password reset code."""
        serializer = VerifyPasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            result = auth_service.verify_password_reset_code(
                email=serializer.validated_data["email"],
                otp=serializer.validated_data["otp"],
            )

            if result:
                return success_response(result)
            else:
                return error_response(
                    errors={"otp": "Invalid or expired reset code"},
                    message="Code verification failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        return validation_error_response(serializer.errors)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    # throttle_scope = 'mobile:reset_password'

    @extend_schema(
        request=ResetPasswordSerializer,
        responses={200: None},
        description="Reset password with reset token via mobile app.",
        summary="Reset password",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Reset password with reset token."""
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            success = auth_service.reset_password(
                reset_token=serializer.validated_data["reset_token"],
                new_password=serializer.validated_data["new_password"],
            )

            if success:
                return success_response(message="Password reset successfully")
            else:
                return error_response(
                    errors={"token": "Invalid or expired reset token"},
                    message="Password reset failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        return validation_error_response(serializer.errors)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    # throttle_scope = 'mobile:change_password'

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: None},
        description="Change password for authenticated user via mobile app.",
        summary="Change password",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Change user password."""
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            success = auth_service.change_password(
                user=request.user,
                current_password=serializer.validated_data["current_password"],
                new_password=serializer.validated_data["new_password"],
            )

            if success:
                return success_response(message="Password changed successfully")
            else:
                return error_response(
                    errors={"current_password": "Current password is incorrect"},
                    message="Password change failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        return validation_error_response(serializer.errors)
