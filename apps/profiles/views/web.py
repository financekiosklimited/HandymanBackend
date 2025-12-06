"""
Web profile views.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.authn.permissions import (
    EmailVerifiedPermission,
    PlatformGuardPermission,
    RoleGuardPermission,
)
from apps.common.responses import (
    not_found_response,
    success_response,
    validation_error_response,
)

from ..models import HandymanProfile, HomeownerProfile
from ..serializers import (
    HandymanProfileResponseSerializer,
    HandymanProfileSerializer,
    HandymanProfileUpdateSerializer,
    HomeownerProfileResponseSerializer,
    HomeownerProfileSerializer,
    HomeownerProfileUpdateSerializer,
)


class HomeownerProfileView(APIView):
    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        responses={200: HomeownerProfileResponseSerializer},
        description="Get homeowner profile information for web app. Requires authenticated user with homeowner role and verified email.",
        summary="Get homeowner profile",
        tags=["Web Homeowner Profile"],
    )
    def get(self, request):
        """Get homeowner profile."""
        try:
            profile = request.user.homeowner_profile
            serializer = HomeownerProfileSerializer(profile)
            return success_response(
                serializer.data, message="Profile retrieved successfully"
            )
        except HomeownerProfile.DoesNotExist:
            return not_found_response("Profile not found")

    @extend_schema(
        request=HomeownerProfileUpdateSerializer,
        responses={200: HomeownerProfileResponseSerializer},
        description="Update homeowner profile information via web app. All fields are optional and will only update provided values.",
        summary="Update homeowner profile",
        tags=["Web Homeowner Profile"],
    )
    def put(self, request):
        """Update homeowner profile."""
        try:
            profile = request.user.homeowner_profile
        except HomeownerProfile.DoesNotExist:
            return not_found_response("Profile not found")

        serializer = HomeownerProfileUpdateSerializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            response_serializer = HomeownerProfileSerializer(profile)
            return success_response(
                response_serializer.data, message="Profile updated successfully"
            )

        return validation_error_response(serializer.errors)


class HandymanProfileView(APIView):
    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        responses={200: HandymanProfileResponseSerializer},
        description="Get handyman profile information including rating for web app. Requires authenticated user with handyman role and verified email.",
        summary="Get handyman profile",
        tags=["Web Handyman Profile"],
    )
    def get(self, request):
        """Get handyman profile."""
        try:
            profile = request.user.handyman_profile
            serializer = HandymanProfileSerializer(profile)
            return success_response(
                serializer.data, message="Profile retrieved successfully"
            )
        except HandymanProfile.DoesNotExist:
            return not_found_response("Profile not found")

    @extend_schema(
        request=HandymanProfileUpdateSerializer,
        responses={200: HandymanProfileResponseSerializer},
        description="Update handyman profile information via web app including rating, contact details and address. All fields are optional.",
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
            response_serializer = HandymanProfileSerializer(profile)
            return success_response(
                response_serializer.data, message="Profile updated successfully"
            )

        return validation_error_response(serializer.errors)
