"""
JWT service for handling RS256 token generation and verification.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .models import RefreshSession


class JWTService:
    """
    Service for handling JWT token operations with RS256 algorithm.
    """

    def __init__(self):
        self._private_key = None
        self._public_key = None
        self._algorithm = getattr(settings, "JWT_ALGORITHM", "RS256")
        self._audience = getattr(settings, "JWT_AUDIENCE", None)
        self._nbf_leeway = getattr(settings, "JWT_NBF_LEEWAY", 5)
        self._access_expire_minutes = getattr(
            settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15
        )
        self._refresh_expire_minutes = getattr(
            settings, "REFRESH_TOKEN_EXPIRE_MINUTES", 43200
        )

    @property
    def private_key(self):
        """Get private key for signing tokens."""
        if self._private_key is None:
            # Try to get key from settings
            if hasattr(settings, "JWT_PRIVATE_KEY") and settings.JWT_PRIVATE_KEY:
                self._private_key = settings.JWT_PRIVATE_KEY
            elif (
                hasattr(settings, "JWT_PRIVATE_KEY_PATH")
                and settings.JWT_PRIVATE_KEY_PATH
            ):
                with open(settings.JWT_PRIVATE_KEY_PATH) as f:
                    self._private_key = f.read()
            else:
                raise ImproperlyConfigured(
                    "JWT_PRIVATE_KEY or JWT_PRIVATE_KEY_PATH must be set"
                )
        return self._private_key

    @property
    def public_key(self):
        """Get public key for verifying tokens."""
        if self._public_key is None:
            # Try to get key from settings
            if hasattr(settings, "JWT_PUBLIC_KEY") and settings.JWT_PUBLIC_KEY:
                self._public_key = settings.JWT_PUBLIC_KEY
            elif (
                hasattr(settings, "JWT_PUBLIC_KEY_PATH")
                and settings.JWT_PUBLIC_KEY_PATH
            ):
                with open(settings.JWT_PUBLIC_KEY_PATH) as f:
                    self._public_key = f.read()
            else:
                raise ImproperlyConfigured(
                    "JWT_PUBLIC_KEY or JWT_PUBLIC_KEY_PATH must be set"
                )
        return self._public_key

    def create_token_pair(
        self, user, platform, active_role=None, user_agent="", ip_address=None
    ):
        """
        Create access and refresh token pair for user.

        Args:
            user: User instance
            platform: 'admin', 'web', or 'mobile'
            active_role: Active role ('admin', 'handyman', 'customer', or None)
            user_agent: User agent string
            ip_address: Client IP address

        Returns:
            dict: Contains 'access_token', 'refresh_token', 'token_type'
        """
        now = datetime.now(UTC)

        # Generate JTI for both tokens (same JTI for the pair)
        jti = str(uuid.uuid4())

        # Get user roles
        user_roles = list(user.roles.values_list("role", flat=True))

        # Base claims
        base_claims = {
            "sub": str(user.public_id),
            "roles": user_roles,
            "plat": platform,
            "email_verified": user.is_email_verified,
            "jti": jti,
            "iat": now,
            "nbf": now - timedelta(seconds=self._nbf_leeway),
        }

        if self._audience:
            base_claims["aud"] = self._audience

        # Access token claims
        access_claims = {
            **base_claims,
            "type": "access",
            "active_role": active_role,
            "exp": now + timedelta(minutes=self._access_expire_minutes),
        }

        # Refresh token claims
        refresh_claims = {
            **base_claims,
            "type": "refresh",
            "exp": now + timedelta(minutes=self._refresh_expire_minutes),
        }

        # Generate tokens
        access_token = jwt.encode(
            access_claims, self.private_key, algorithm=self._algorithm
        )
        refresh_token = jwt.encode(
            refresh_claims, self.private_key, algorithm=self._algorithm
        )

        # Store refresh session
        RefreshSession.create_session(
            user=user,
            platform=platform,
            jti=jti,
            user_agent=user_agent,
            ip_address=ip_address,
            ttl_minutes=self._refresh_expire_minutes,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    def decode_token(self, token):
        """
        Decode and validate JWT token.

        Args:
            token: JWT token string

        Returns:
            dict: Token payload

        Raises:
            jwt.InvalidTokenError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self._algorithm],
                audience=self._audience,
                options={"verify_exp": True, "verify_nbf": True},
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise jwt.InvalidTokenError("Token has expired")
        except jwt.InvalidAudienceError:
            raise jwt.InvalidTokenError("Invalid audience")
        except jwt.InvalidSignatureError:
            raise jwt.InvalidTokenError("Invalid signature")
        except jwt.InvalidTokenError:
            raise

    def refresh_token_pair(
        self, refresh_token, platform, user_agent="", ip_address=None
    ):
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Current refresh token
            platform: Platform making the request
            user_agent: User agent string
            ip_address: Client IP address

        Returns:
            dict: New token pair

        Raises:
            jwt.InvalidTokenError: If refresh token is invalid
            ValueError: If session is not found or platform mismatch
        """
        # Decode refresh token
        payload = self.decode_token(refresh_token)

        # Validate token type
        if payload.get("type") != "refresh":
            raise jwt.InvalidTokenError("Invalid token type")

        # Verify refresh session
        session = RefreshSession.verify_session(jti=payload["jti"], platform=platform)

        if not session:
            raise ValueError("Session not found or inactive")

        # Verify platform matches
        if session.platform != platform:
            raise ValueError("Platform mismatch")

        # Revoke current session
        session.revoke()

        # Get current active role (carry forward if user still has it)
        current_active_role = payload.get("active_role")
        if current_active_role and not session.user.has_role(current_active_role):
            current_active_role = None

        # Create new token pair
        return self.create_token_pair(
            user=session.user,
            platform=platform,
            active_role=current_active_role,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    def revoke_refresh_token(self, refresh_token):
        """
        Revoke a refresh token.

        Args:
            refresh_token: Refresh token to revoke
        """
        try:
            payload = self.decode_token(refresh_token)
            if payload.get("type") == "refresh":
                # Find and revoke session by JTI
                import hashlib

                jti_hash = hashlib.sha256(str(payload["jti"]).encode()).hexdigest()

                session = RefreshSession.objects.filter(
                    jti_hash=jti_hash,
                    revoked_at__isnull=True,
                ).first()

                if session:
                    session.revoke()
        except jwt.InvalidTokenError:
            # Token is already invalid, nothing to revoke
            pass


# Global service instance
jwt_service = JWTService()
