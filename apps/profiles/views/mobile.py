"""
Mobile profile views.
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

from ..models import CustomerProfile, HandymanProfile
from ..serializers import (
    CustomerProfileResponseSerializer,
    CustomerProfileSerializer,
    CustomerProfileUpdateSerializer,
    HandymanProfileResponseSerializer,
    HandymanProfileSerializer,
    HandymanProfileUpdateSerializer,
)


class CustomerProfileView(APIView):
    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        responses={200: CustomerProfileResponseSerializer},
        description="Get customer profile information for mobile app. Requires authenticated user with customer role and verified email.",
        summary="Get customer profile",
        tags=["Mobile Customer Profile"],
    )
    def get(self, request):
        """Get customer profile."""
        try:
            profile = request.user.customer_profile
            serializer = CustomerProfileSerializer(profile)
            return success_response(
                serializer.data, message="Profile retrieved successfully"
            )
        except CustomerProfile.DoesNotExist:
            return not_found_response("Profile not found")

    @extend_schema(
        request=CustomerProfileUpdateSerializer,
        responses={200: CustomerProfileResponseSerializer},
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
            response_serializer = CustomerProfileSerializer(profile)
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
        description="Get handyman profile information including rating for mobile app. Requires authenticated user with handyman role and verified email.",
        summary="Get handyman profile",
        tags=["Mobile Handyman Profile"],
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
            response_serializer = HandymanProfileSerializer(profile)
            return success_response(
                response_serializer.data, message="Profile updated successfully"
            )

        return validation_error_response(serializer.errors)
