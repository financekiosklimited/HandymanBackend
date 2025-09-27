"""
Mobile profile views.
"""

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.authn.permissions import (
    PlatformGuardPermission,
    RoleGuardPermission,
    EmailVerifiedPermission,
)
from ..serializers import (
    CustomerProfileSerializer,
    CustomerProfileUpdateSerializer,
    HandymanProfileSerializer,
    HandymanProfileUpdateSerializer,
)
from ..models import CustomerProfile, HandymanProfile
from apps.common.responses import (
    success_response,
    not_found_response,
    validation_error_response,
)


class CustomerProfileView(APIView):
    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        responses={200: CustomerProfileSerializer},
        description="Get customer profile information for mobile app. Requires authenticated user with customer role and verified email.",
        summary="Get customer profile",
        tags=["Mobile Customer Profile"],
    )
    def get(self, request):
        """Get customer profile."""
        try:
            profile = request.user.customer_profile
            serializer = CustomerProfileSerializer(profile)
            return success_response(serializer.data)
        except CustomerProfile.DoesNotExist:
            return not_found_response("Profile not found")

    @extend_schema(
        request=CustomerProfileUpdateSerializer,
        responses={200: None},
        description="Update customer profile information via mobile app. All fields are optional and will only update provided values.",
        summary="Update customer profile",
        tags=["Mobile Customer Profile"],
    )
    def put(self, request):
        """Update customer profile."""
        try:
            profile = request.user.customer_profile
        except CustomerProfile.DoesNotExist:
            return not_found_response("Profile not found")

        serializer = CustomerProfileUpdateSerializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response(message="Profile updated successfully")

        return validation_error_response(serializer.errors)


class HandymanProfileView(APIView):
    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        responses={200: HandymanProfileSerializer},
        description="Get handyman profile information including rating for mobile app. Requires authenticated user with handyman role and verified email.",
        summary="Get handyman profile",
        tags=["Mobile Handyman Profile"],
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
        description="Update handyman profile information via mobile app including rating, contact details and address. All fields are optional.",
        summary="Update handyman profile",
        tags=["Mobile Handyman Profile"],
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
