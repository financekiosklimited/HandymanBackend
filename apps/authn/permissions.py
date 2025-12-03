"""
Custom permissions for platform and role-based access control.
"""

from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class PlatformGuardPermission(permissions.BasePermission):
    """
    Guard to ensure token platform matches URL platform.
    """

    def has_permission(self, request, view):
        """
        Check if user's token platform matches the URL platform.
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Get token payload
        token_payload = getattr(request.user, "token_payload", None)
        if not token_payload:
            return False

        # Extract platform from URL
        url_platform = self._extract_platform_from_url(request.path)
        token_platform = token_payload.get("plat")

        if url_platform and token_platform != url_platform:
            raise PermissionDenied(
                {
                    "message": "Platform mismatch",
                    "data": None,
                    "errors": {
                        "platform": "Token platform does not match requested platform"
                    },
                    "meta": None,
                }
            )

        return True

    def _extract_platform_from_url(self, path):
        """
        Extract platform from URL path.
        Expected format: /api/v1/{platform}/...
        """
        path_parts = path.strip("/").split("/")
        if len(path_parts) >= 3 and path_parts[0] == "api" and path_parts[1] == "v1":
            platform = path_parts[2]
            if platform in ["web", "mobile", "admin"]:
                return platform
        return None


class RoleGuardPermission(permissions.BasePermission):
    """
    Guard to ensure user has the required role for role-scoped endpoints.
    """

    def has_permission(self, request, view):
        """
        Check if user has the required role for the endpoint.
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Get token payload
        token_payload = getattr(request.user, "token_payload", None)
        if not token_payload:
            return False

        # Extract role from URL
        url_role = self._extract_role_from_url(request.path)

        if url_role:
            active_role = token_payload.get("active_role")
            user_roles = token_payload.get("roles", [])

            # Check if active role matches URL role
            if active_role != url_role:
                raise PermissionDenied(
                    {
                        "message": "Role mismatch",
                        "data": None,
                        "errors": {
                            "role": f'Active role "{active_role}" cannot access "{url_role}" endpoints'
                        },
                        "meta": None,
                    }
                )

            # Check if user actually has this role
            if url_role not in user_roles:
                raise PermissionDenied(
                    {
                        "message": "Role mismatch",
                        "data": None,
                        "errors": {"role": f'User does not have "{url_role}" role'},
                        "meta": None,
                    }
                )

        return True

    def _extract_role_from_url(self, path):
        """
        Extract role from URL path.
        Expected format: /api/v1/{platform}/{role}/...
        """
        path_parts = path.strip("/").split("/")
        if len(path_parts) >= 4 and path_parts[0] == "api" and path_parts[1] == "v1":
            role = path_parts[3]
            if role in ["customer", "handyman", "admin"]:
                return role
        return None


class EmailVerifiedPermission(permissions.BasePermission):
    """
    Permission to ensure user's email is verified.
    """

    def has_permission(self, request, view):
        """
        Check if user's email is verified.
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Get token payload
        token_payload = getattr(request.user, "token_payload", None)
        if not token_payload:
            return False

        email_verified = token_payload.get("email_verified", False)

        if not email_verified:
            raise PermissionDenied(
                {
                    "message": "Email verification required",
                    "data": None,
                    "errors": {
                        "email": "Email must be verified to access this endpoint"
                    },
                    "meta": None,
                }
            )

        return True


class ActiveRoleRequiredPermission(permissions.BasePermission):
    """
    Permission to ensure user has an active role.
    """

    def has_permission(self, request, view):
        """
        Check if user has an active role.
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Get token payload
        token_payload = getattr(request.user, "token_payload", None)
        if not token_payload:
            return False

        active_role = token_payload.get("active_role")

        if not active_role:
            raise PermissionDenied(
                {
                    "message": "Active role required",
                    "data": None,
                    "errors": {
                        "role": "An active role must be selected to access this endpoint"
                    },
                    "meta": None,
                }
            )

        return True


class PhoneVerifiedPermission(permissions.BasePermission):
    """
    Permission to ensure user's phone number is verified.
    Required for certain actions like creating job listings.
    """

    def has_permission(self, request, view):
        """
        Check if user's phone is verified from token claims.
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Get token payload
        token_payload = getattr(request.user, "token_payload", None)
        if not token_payload:
            return False

        phone_verified = token_payload.get("phone_verified", False)

        if not phone_verified:
            raise PermissionDenied(
                {
                    "message": "Phone verification required",
                    "data": None,
                    "errors": {
                        "phone": "Phone number must be verified to access this endpoint"
                    },
                    "meta": None,
                }
            )

        return True
