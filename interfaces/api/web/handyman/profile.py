"""
Handyman profile views for web platform.
"""

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.authn.permissions import (
    PlatformGuardPermission,
    RoleGuardPermission,
    EmailVerifiedPermission,
)
from apps.profiles.serializers import (
    HandymanProfileSerializer,
    HandymanProfileUpdateSerializer,
)
from apps.accounts.models import HandymanProfile
from apps.common.responses import (
    success_response,
    not_found_response,
    validation_error_response,
)


class HandymanProfileView(APIView):
    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        responses={200: HandymanProfileSerializer},
        description="Get handyman profile information including rating. Requires authenticated user with handyman role and verified email.",
        summary="Get handyman profile",
        tags=["Web Handyman Profile"],
    )
    def get(self, request):
        """Get handyman profile."""
        try:
            profile = request.user.handyman_profile
            serializer = HandymanProfileSerializer(profile)
            return success_response(serializer.data)
        except HandymanProfile.DoesNotExist:
            return not_found_response("Profile not found")

    @extend_schema(
        request=HandymanProfileUpdateSerializer,
        responses={200: None},
        description="Update handyman profile information including rating, contact details and address. All fields are optional.",
        summary="Update handyman profile",
        tags=["Web Handyman Profile"],
    )
    def put(self, request):
        """Update handyman profile."""
        try:
            profile = request.user.handyman_profile
        except HandymanProfile.DoesNotExist:
            return not_found_response("Profile not found")

        serializer = HandymanProfileUpdateSerializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response(message="Profile updated successfully")

        return validation_error_response(serializer.errors)
