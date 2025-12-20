"""
Web profile views.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.authn.permissions import (
    EmailVerifiedPermission,
    PlatformGuardPermission,
    RoleGuardPermission,
)
from apps.common.openapi import (
    NOT_FOUND_EXAMPLE,
    UNAUTHORIZED_EXAMPLE,
    VALIDATION_ERROR_EXAMPLE,
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
        operation_id="web_homeowner_profile_retrieve",
        responses={
            200: HomeownerProfileResponseSerializer,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Get homeowner profile information for web app. Requires authenticated user with homeowner role and verified email.",
        summary="Get homeowner profile",
        tags=["Web Homeowner Profile"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Profile retrieved successfully",
                    "data": {
                        "display_name": "Jane Homeowner",
                        "avatar_url": "https://example.com/avatar.jpg",
                        "phone_number": "+16471234567",
                        "is_phone_verified": True,
                        "address": "123 Main St, Toronto, ON",
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
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
        operation_id="web_homeowner_profile_update",
        request=HomeownerProfileUpdateSerializer,
        responses={
            200: HomeownerProfileResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Update homeowner profile information via web app. All fields are optional and will only update provided values. Requires authenticated user with homeowner role and verified email.",
        summary="Update homeowner profile",
        tags=["Web Homeowner Profile"],
        examples=[
            OpenApiExample(
                "Update Request",
                value={
                    "display_name": "Jane Doe",
                    "address": "456 New St, Toronto, ON",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Profile updated successfully",
                    "data": {
                        "display_name": "Jane Doe",
                        "avatar_url": "https://example.com/avatar.jpg",
                        "phone_number": "+16471234567",
                        "is_phone_verified": True,
                        "address": "456 New St, Toronto, ON",
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
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
        operation_id="web_handyman_profile_retrieve",
        responses={
            200: HandymanProfileResponseSerializer,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Get handyman profile information including rating for web app. Requires authenticated user with handyman role and verified email.",
        summary="Get handyman profile",
        tags=["Web Handyman Profile"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Profile retrieved successfully",
                    "data": {
                        "display_name": "John Handyman",
                        "avatar_url": "https://example.com/avatar2.jpg",
                        "rating": 4.8,
                        "hourly_rate": 80.0,
                        "is_active": True,
                        "is_available": True,
                        "phone_number": "+16479876543",
                        "is_phone_verified": True,
                        "address": "789 Work Rd, Toronto, ON",
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
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
        operation_id="web_handyman_profile_update",
        request=HandymanProfileUpdateSerializer,
        responses={
            200: HandymanProfileResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Update handyman profile information via web app including rating, contact details and address. All fields are optional. Requires authenticated user with handyman role and verified email.",
        summary="Update handyman profile",
        tags=["Web Handyman Profile"],
        examples=[
            OpenApiExample(
                "Update Request",
                value={
                    "display_name": "John Builder",
                    "hourly_rate": 85.0,
                    "is_available": False,
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Profile updated successfully",
                    "data": {
                        "display_name": "John Builder",
                        "avatar_url": "https://example.com/avatar2.jpg",
                        "rating": 4.8,
                        "hourly_rate": 85.0,
                        "is_active": True,
                        "is_available": False,
                        "phone_number": "+16479876543",
                        "is_phone_verified": True,
                        "address": "789 Work Rd, Toronto, ON",
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
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
