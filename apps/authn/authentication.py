"""
Custom JWT authentication for DRF.
"""

import jwt
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

from .jwt_service import jwt_service

User = get_user_model()


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Custom JWT authentication class for DRF.
    """

    def authenticate(self, request):
        """
        Authenticate request using JWT token.

        Returns:
            tuple: (user, token_payload) or None
        """
        auth_header = request.META.get("HTTP_AUTHORIZATION")

        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        try:
            # Extract token
            token = auth_header.split(" ")[1]

            # Decode token
            payload = jwt_service.decode_token(token)

            # Validate token type (should be access token)
            if payload.get("type") != "access":
                raise exceptions.AuthenticationFailed("Invalid token type")

            # Get user by public_id
            try:
                user = User.objects.get(public_id=payload["sub"])
            except User.DoesNotExist:
                raise exceptions.AuthenticationFailed("User not found")

            # Check if user is active
            if not user.is_active:
                raise exceptions.AuthenticationFailed("User is inactive")

            # Store token payload in user for later use
            user.token_payload = payload

            return (user, payload)

        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f"Invalid token: {str(e)}")
        except Exception as e:
            raise exceptions.AuthenticationFailed(f"Authentication failed: {str(e)}")

    def authenticate_header(self, request):
        """
        Return WWW-Authenticate header for 401 responses.
        """
        return "Bearer"
