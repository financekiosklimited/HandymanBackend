"""
Mobile authentication views.
"""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.common.responses import (
    accepted_response,
    created_response,
    error_response,
    no_content_response,
    success_response,
    unauthorized_response,
    validation_error_response,
)

from ..jwt_service import jwt_service
from ..serializers import (
    ActivateRoleSerializer,
    AuthResponseSerializer,
    ChangePasswordSerializer,
    EmailResendSerializer,
    EmailVerificationSerializer,
    ForgotPasswordSerializer,
    GoogleLoginSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetTokenResponseSerializer,
    RefreshTokenSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    SuccessMessageResponseSerializer,
    TokenResponseSerializer,
    VerifyPasswordResetSerializer,
)
from ..services import auth_service

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]
    platform = "mobile"
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
        return self._handle_post(request)

    def _handle_post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                tokens = auth_service.register_user(
                    email=serializer.validated_data["email"],
                    password=serializer.validated_data["password"],
                    initial_role=serializer.validated_data.get("initial_role"),
                    platform=self.platform,
                )

                # Get user for next action determination
                try:
                    user = User.objects.get(email=serializer.validated_data["email"])
                    next_action = auth_service.get_next_action_for_user(user)
                    tokens.update(
                        {
                            "next_action": next_action,
                            "email_verified": user.is_email_verified,
                        }
                    )
                except User.DoesNotExist:
                    # Fallback values
                    tokens.update(
                        {
                            "next_action": "verify_email",
                            "email_verified": False,
                        }
                    )

                return created_response(
                    data=tokens, message="User registered successfully"
                )
            except Exception as e:
                return error_response(
                    errors={"registration": str(e)},
                    message="Registration failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
        return validation_error_response(serializer.errors)


class LoginView(APIView):
    permission_classes = [AllowAny]
    platform = "mobile"
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
        return self._handle_post(request)

    def _handle_post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            tokens = auth_service.login_user(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
                platform=self.platform,
            )

            if tokens:
                # Get user for next action determination
                try:
                    user = User.objects.get(email=serializer.validated_data["email"])
                    next_action = auth_service.get_next_action_for_user(user)
                    tokens.update(
                        {
                            "next_action": next_action,
                            "email_verified": user.is_email_verified,
                        }
                    )
                except User.DoesNotExist:
                    # This shouldn't happen if login succeeded, but fallback
                    tokens.update(
                        {
                            "next_action": "none",
                            "email_verified": False,
                        }
                    )

                return success_response(data=tokens, message="Login successful")
            else:
                return unauthorized_response("Invalid credentials")

        return validation_error_response(serializer.errors)


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]
    platform = "mobile"
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
        return self._handle_post(request)

    def _handle_post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        if serializer.is_valid():
            try:
                tokens = auth_service.google_login(
                    id_token=serializer.validated_data["id_token"],
                    platform=self.platform,
                )

                # Add next_action and email_verified to Google login response
                try:
                    payload = jwt_service.decode_token(tokens["access_token"])
                    user = User.objects.get(public_id=payload["sub"])
                    next_action = auth_service.get_next_action_for_user(user)
                    tokens.update(
                        {
                            "next_action": next_action,
                            "email_verified": user.is_email_verified,
                        }
                    )
                except (User.DoesNotExist, Exception):
                    # Fallback values for Google users (usually email verified)
                    tokens.update(
                        {
                            "next_action": "none",
                            "email_verified": True,
                        }
                    )

                return success_response(data=tokens, message="Google login successful")
            except ValueError as e:
                return error_response(
                    errors={"google": str(e)},
                    message="Google authentication failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        return validation_error_response(serializer.errors)


class ActivateRoleView(APIView):
    permission_classes = [IsAuthenticated]
    platform = "mobile"
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
        return self._handle_post(request)

    def _handle_post(self, request):
        serializer = ActivateRoleSerializer(data=request.data)
        if serializer.is_valid():
            role_info = auth_service.activate_role(
                user=request.user, role=serializer.validated_data["role"]
            )

            # Generate new token pair with active role
            tokens = jwt_service.create_token_pair(
                user=request.user,
                platform=self.platform,
                active_role=role_info["role"],
            )

            # Get updated next action after role activation
            next_action = auth_service.get_next_action_for_user(request.user)

            response_data = {
                **tokens,
                "active_role": role_info["role"],
                "email_verified": role_info["email_verified"],
                "next_action": next_action,
            }

            return success_response(
                data=response_data, message="Role activated successfully"
            )

        return validation_error_response(serializer.errors)


class EmailVerifyView(APIView):
    permission_classes = [AllowAny]
    platform = "mobile"
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
        return self._handle_post(request)

    def _handle_post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            # Get email from JWT token if authenticated, otherwise from payload
            email = serializer.validated_data.get("email")

            if not email and request.user.is_authenticated:
                email = request.user.email
            elif not email:
                return error_response(
                    errors={"email": "Email is required when not authenticated"},
                    message="Email required",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            user = auth_service.verify_email(
                email=email,
                otp=serializer.validated_data["otp"],
            )

            if user:
                # Generate new token pair with updated email verification status
                tokens = jwt_service.create_token_pair(
                    user=user, platform=self.platform, active_role=None
                )

                # Get next action after email verification
                next_action = auth_service.get_next_action_for_user(user)
                tokens.update(
                    {
                        "next_action": next_action,
                        "email_verified": user.is_email_verified,
                    }
                )

                return success_response(
                    data=tokens, message="Email verified successfully"
                )
            else:
                return error_response(
                    errors={"otp": "Invalid or expired OTP"},
                    message="Email verification failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        return validation_error_response(serializer.errors)


class EmailResendView(APIView):
    permission_classes = [AllowAny]
    platform = "mobile"
    # throttle_scope = 'mobile:resend_email'

    @extend_schema(
        request=EmailResendSerializer,
        responses={200: SuccessMessageResponseSerializer},
        description="Resend email verification OTP via mobile app.",
        summary="Resend verification email",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Resend email verification."""
        return self._handle_post(request)

    def _handle_post(self, request):
        serializer = EmailResendSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get("email")

            if not email:
                # User is authenticated, use their email
                if request.user and request.user.is_authenticated:
                    if request.user.is_email_verified:
                        # Already verified, do nothing
                        return accepted_response(message="Email already verified")
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

            return accepted_response(
                message="Verification email sent if account exists"
            )

        return validation_error_response(serializer.errors)


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    platform = "mobile"
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
        return self._handle_post(request)

    def _handle_post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        if serializer.is_valid():
            try:
                tokens = jwt_service.refresh_token_pair(
                    refresh_token=serializer.validated_data["refresh_token"],
                    platform=self.platform,
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    ip_address=request.META.get("REMOTE_ADDR"),
                )
                return success_response(
                    data=tokens, message="Token refreshed successfully"
                )
            except Exception as e:
                return unauthorized_response(str(e))

        return validation_error_response(serializer.errors)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    platform = "mobile"

    @extend_schema(
        request=LogoutSerializer,
        responses={200: SuccessMessageResponseSerializer},
        description="Logout user via mobile app.",
        summary="User logout",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Logout user and optionally revoke refresh token."""
        return self._handle_post(request)

    def _handle_post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            refresh_token = serializer.validated_data.get("refresh_token")

            if refresh_token:
                jwt_service.revoke_refresh_token(refresh_token)

            return no_content_response(message="Logout successful")

        return validation_error_response(serializer.errors)


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    platform = "mobile"
    # throttle_scope = 'mobile:forgot_password'

    @extend_schema(
        request=ForgotPasswordSerializer,
        responses={200: SuccessMessageResponseSerializer},
        description="Initiate password reset process via mobile app.",
        summary="Forgot password",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Initiate password reset process."""
        return self._handle_post(request)

    def _handle_post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            auth_service.forgot_password(email=serializer.validated_data["email"])
            return accepted_response(
                message="Password reset code sent if account exists"
            )

        return validation_error_response(serializer.errors)


class VerifyPasswordResetView(APIView):
    permission_classes = [AllowAny]
    platform = "mobile"
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
        return self._handle_post(request)

    def _handle_post(self, request):
        serializer = VerifyPasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            result = auth_service.verify_password_reset_code(
                email=serializer.validated_data["email"],
                otp=serializer.validated_data["otp"],
            )

            if result:
                return success_response(
                    data=result, message="Reset code verified successfully"
                )
            else:
                return error_response(
                    errors={"otp": "Invalid or expired reset code"},
                    message="Code verification failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        return validation_error_response(serializer.errors)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    platform = "mobile"
    # throttle_scope = 'mobile:reset_password'

    @extend_schema(
        request=ResetPasswordSerializer,
        responses={200: SuccessMessageResponseSerializer},
        description="Reset password with reset token via mobile app.",
        summary="Reset password",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Reset password with reset token."""
        return self._handle_post(request)

    def _handle_post(self, request):
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
    platform = "mobile"
    # throttle_scope = 'mobile:change_password'

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: SuccessMessageResponseSerializer},
        description="Change password for authenticated user via mobile app.",
        summary="Change password",
        tags=["Mobile Authentication"],
    )
    def post(self, request):
        """Change user password."""
        return self._handle_post(request)

    def _handle_post(self, request):
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
