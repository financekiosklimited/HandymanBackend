"""
Authentication business logic services.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.common.email import email_service
from apps.profiles.models import HandymanProfile, HomeownerProfile

from .jwt_service import jwt_service
from .models import (
    EmailVerificationToken,
    PasswordResetCode,
    PasswordResetToken,
    RefreshSession,
)

User = get_user_model()


class AuthService:
    """
    Service for authentication operations.
    """

    @transaction.atomic
    def register_user(self, email, password, initial_role=None, platform="web"):
        """
        Register a new user.

        Args:
            email: User email
            password: User password
            initial_role: Initial role to create ('handyman' or 'homeowner')
            platform: Platform for token generation

        Returns:
            dict: Token pair and user info
        """
        # Create user
        user = User.objects.create_user(email=email, password=password, is_active=True)

        # Create initial role if specified
        if initial_role:
            UserRole.objects.create(
                user=user, role=initial_role, next_action="verify_email"
            )

            # Create profile
            self._create_profile_for_role(user, initial_role)

        # Generate token pair (no active role initially)
        tokens = jwt_service.create_token_pair(
            user=user, platform=platform, active_role=None
        )

        # Create and send email verification
        verification_token, otp = EmailVerificationToken.create_for_user(user)
        email_service.send_email_verification(user, otp)

        return tokens

    def login_user(self, email, password, platform="web"):
        """
        Authenticate user with email and password.

        Args:
            email: User email
            password: User password
            platform: Platform for token generation

        Returns:
            dict: Token pair or None if authentication fails
        """
        try:
            user = User.objects.get(email=email, is_active=True)

            if check_password(password, user.password):
                # Generate token pair
                tokens = jwt_service.create_token_pair(
                    user=user, platform=platform, active_role=None
                )
                return tokens
        except User.DoesNotExist:
            pass

        return None

    @transaction.atomic
    def google_login(self, id_token, platform="web"):
        """
        Authenticate or create user with Google OAuth.

        Args:
            id_token: Google ID token
            platform: Platform for token generation

        Returns:
            dict: Token pair
        """
        try:
            # Verify Google ID token
            # Note: In production, you would verify against Google's public keys
            # For now, we'll skip actual verification for demo purposes
            # In real implementation:
            # idinfo = google_id_token.verify_oauth2_token(
            #     id_token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            # )

            # Mock Google token payload for demo
            # In production, extract from verified token
            email = "demo@example.com"  # This would come from idinfo['email']
            google_sub = "google_user_id"  # This would come from idinfo['sub']

            # Try to find existing user
            try:
                user = User.objects.get(email=email)

                # Update Google sub if not set
                if not user.google_sub:
                    user.google_sub = google_sub
                    user.save()

            except User.DoesNotExist:
                # Create new user
                user = User.objects.create_user(
                    email=email, google_sub=google_sub, is_active=True
                )

                # Auto-verify email for Google users
                user.email_verified_at = timezone.now()
                user.save()

                # Create default homeowner role and profile
                UserRole.objects.create(
                    user=user,
                    role="homeowner",
                    next_action="none",  # No need to verify email
                )

                HomeownerProfile.objects.create(
                    user=user,
                    display_name=email.split("@")[0],  # Default display name
                )

            # Ensure email is verified for Google users
            if not user.email_verified_at:
                user.email_verified_at = timezone.now()
                user.save()

            # Generate token pair
            tokens = jwt_service.create_token_pair(
                user=user, platform=platform, active_role=None
            )

            return tokens

        except Exception as e:
            # Log error in production
            raise ValueError(f"Google authentication failed: {str(e)}")

    def activate_role(self, user, role):
        """
        Activate a role for user and determine next action.

        Args:
            user: User instance
            role: Role to activate

        Returns:
            dict: Next action and role info
        """
        # Ensure user has this role
        try:
            user_role = user.roles.get(role=role)
        except UserRole.DoesNotExist:
            # Create role and profile if doesn't exist
            user_role = UserRole.objects.create(
                user=user, role=role, next_action="verify_email"
            )
            self._create_profile_for_role(user, role)

        # Determine next action
        if not user.is_email_verified:
            next_action = "verify_email"
        elif not self._has_complete_profile(user, role):
            next_action = "fill_profile"
        else:
            next_action = "none"

        # Update user role next_action
        user_role.next_action = next_action
        user_role.save()

        return {
            "role": role,
            "next_action": next_action,
            "email_verified": user.is_email_verified,
        }

    def verify_email(self, email, otp):
        """
        Verify email with OTP.

        Args:
            email: User email
            otp: 6-digit OTP

        Returns:
            User: User instance if verification successful
        """
        user = EmailVerificationToken.verify_otp(email, otp)

        if user:
            # Mark email as verified
            user.email_verified_at = timezone.now()
            user.save()

            # Update all user roles' next_action
            for user_role in user.roles.all():
                if user_role.next_action == "verify_email":
                    if self._has_complete_profile(user, user_role.role):
                        user_role.next_action = "none"
                    else:
                        user_role.next_action = "fill_profile"
                    user_role.save()

        return user

    def get_next_action_for_user(self, user):
        """
        Determine next action for a user based on current state.

        Args:
            user: User instance

        Returns:
            str: Next action needed ('verify_email', 'activate_role', 'fill_profile', 'none')
        """
        # If email is not verified, that's the priority
        if not user.is_email_verified:
            return "verify_email"

        # If user has no roles, they need to activate one
        if not user.roles.exists():
            return "activate_role"

        # If user has roles but incomplete profiles, they need to fill profile
        for user_role in user.roles.all():
            if not self._has_complete_profile(user, user_role.role):
                return "fill_profile"

        # Everything is complete
        return "none"

    def resend_email_verification(self, user):
        """
        Resend email verification to user.

        Args:
            user: User instance
        """
        # Invalidate old tokens (delete them)
        EmailVerificationToken.objects.filter(user=user, used_at__isnull=True).delete()

        # Create new token
        verification_token, otp = EmailVerificationToken.create_for_user(user)
        email_service.send_email_verification(user, otp)

    def forgot_password(self, email):
        """
        Initiate password reset process.

        Args:
            email: User email
        """
        try:
            user = User.objects.get(email=email, is_active=True)

            # Invalidate old reset codes
            PasswordResetCode.objects.filter(
                user=user, verified_at__isnull=True
            ).delete()

            # Create new reset code
            reset_code_obj, reset_code = PasswordResetCode.create_for_user(user)
            email_service.send_password_reset_code(user, reset_code)

        except User.DoesNotExist:
            # Don't reveal if email exists or not
            pass

    def verify_password_reset_code(self, email, otp):
        """
        Verify password reset code.

        Args:
            email: User email
            otp: 6-digit reset code

        Returns:
            dict: Reset token and expiry info
        """
        reset_code = PasswordResetCode.verify_code(email, otp)

        if not reset_code:
            return None

        # Invalidate old reset tokens
        PasswordResetToken.objects.filter(
            user=reset_code.user, used_at__isnull=True
        ).delete()

        # Create reset token
        reset_token_obj, reset_token = PasswordResetToken.create_for_user(
            reset_code.user
        )

        # Calculate expires_in seconds
        expires_in = int((reset_token_obj.expires_at - timezone.now()).total_seconds())

        return {"reset_token": reset_token, "expires_in": expires_in}

    def reset_password(self, reset_token, new_password):
        """
        Reset user password with reset token.

        Args:
            reset_token: Password reset token
            new_password: New password

        Returns:
            bool: Success status
        """
        user = PasswordResetToken.verify_token(reset_token)

        if user:
            # Set new password
            user.set_password(new_password)
            user.save()

            # Revoke all refresh sessions
            RefreshSession.revoke_all_for_user(user)

            return True

        return False

    def change_password(self, user, current_password, new_password):
        """
        Change user password.

        Args:
            user: User instance
            current_password: Current password
            new_password: New password

        Returns:
            bool: Success status
        """
        if check_password(current_password, user.password):
            # Set new password
            user.set_password(new_password)
            user.save()

            # Revoke all refresh sessions
            RefreshSession.revoke_all_for_user(user)

            return True

        return False

    def _create_profile_for_role(self, user, role):
        """Create profile for user role if it doesn't exist."""
        if role == "homeowner":
            HomeownerProfile.objects.get_or_create(
                user=user, defaults={"display_name": user.email.split("@")[0]}
            )
        elif role == "handyman":
            HandymanProfile.objects.get_or_create(
                user=user, defaults={"display_name": user.email.split("@")[0]}
            )
        # Admin role doesn't need a profile - they use Django admin interface

    def _has_complete_profile(self, user, role):
        """Check if user has a complete profile for the role."""
        try:
            if role == "homeowner":
                profile = user.homeowner_profile
                return bool(profile.display_name)
            elif role == "handyman":
                profile = user.handyman_profile
                return bool(profile.display_name)
            elif role == "admin":
                # Admin role doesn't require a profile - always complete
                return True
        except AttributeError:
            # For admin role, return True even if no profile exists
            if role == "admin":
                return True
            return False

        return False


# Global auth service instance
auth_service = AuthService()
