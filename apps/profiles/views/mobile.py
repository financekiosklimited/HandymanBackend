"""
Mobile profile views.
"""

from django.db.models import Case, FloatField, Value, When
from django.db.models.functions import ACos, Cos, Radians, Sin
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
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
    HomeownerHandymanDetailResponseSerializer,
    HomeownerHandymanDetailSerializer,
    HomeownerHandymanListResponseSerializer,
    HomeownerHandymanListSerializer,
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
        description="Get homeowner profile information for mobile app. Requires authenticated user with homeowner role and verified email.",
        summary="Get homeowner profile",
        tags=["Mobile Homeowner Profile"],
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
        description="Update homeowner profile information via mobile app. All fields are optional and will only update provided values.",
        summary="Update homeowner profile",
        tags=["Mobile Homeowner Profile"],
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
        description=(
            "Get handyman profile information for mobile app. "
            "Requires authenticated user with handyman role and verified email."
        ),
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
        description=(
            "Update handyman profile information via mobile app. "
            "All fields are optional and will only update provided values."
        ),
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


class HomeownerNearbyHandymanListView(APIView):
    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_homeowner_handymen_nearby_list",
        responses={200: HomeownerHandymanListResponseSerializer},
        parameters=[
            OpenApiParameter(
                name="latitude",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description="Homeowner current latitude (required)",
                required=True,
                examples=[
                    OpenApiExample("Toronto", value=43.651070),
                ],
            ),
            OpenApiParameter(
                name="longitude",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description="Homeowner current longitude (required)",
                required=True,
                examples=[
                    OpenApiExample("Toronto", value=-79.347015),
                ],
            ),
            OpenApiParameter(
                name="radius_km",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description="Search radius in kilometers (default: 25)",
                required=False,
                examples=[
                    OpenApiExample("Default", value=25),
                    OpenApiExample("Large", value=50),
                ],
            ),
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number (default: 1)",
                required=False,
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Items per page, max 100 (default: 20)",
                required=False,
            ),
        ],
        description=(
            "List approved, active, available handymen near the homeowner. "
            "This endpoint does not expose sensitive fields (phone/address/coordinates). "
            "Requires authenticated homeowner with verified email."
        ),
        summary="List nearby handymen",
        tags=["Mobile Homeowner Handymen"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Handymen retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "display_name": "John Handyman",
                            "rating": 4.5,
                            "hourly_rate": 75.0,
                            "distance_km": 2.1,
                        }
                    ],
                    "errors": None,
                    "meta": {
                        "pagination": {
                            "page": 1,
                            "page_size": 20,
                            "total_pages": 1,
                            "total_count": 1,
                            "has_next": False,
                            "has_previous": False,
                        }
                    },
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Validation Error",
                value={
                    "message": "Validation failed",
                    "data": None,
                    "errors": {"coordinates": ["Latitude and longitude are required."]},
                    "meta": None,
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def get(self, request):
        """List nearby handymen ordered by distance."""
        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")
        radius_km = request.query_params.get("radius_km", "25")

        if latitude is None or longitude is None:
            return validation_error_response(
                {"coordinates": ["Latitude and longitude are required."]}
            )

        try:
            user_lat = float(latitude)
            user_lng = float(longitude)
            radius = float(radius_km)
        except (ValueError, TypeError):
            return validation_error_response(
                {"coordinates": ["Latitude, longitude and radius_km must be numbers."]}
            )

        if not (-90 <= user_lat <= 90):
            return validation_error_response(
                {"latitude": ["Latitude must be between -90 and 90."]}
            )
        if not (-180 <= user_lng <= 180):
            return validation_error_response(
                {"longitude": ["Longitude must be between -180 and 180."]}
            )
        if radius <= 0:
            return validation_error_response(
                {"radius_km": ["Radius must be greater than 0."]}
            )

        # Base queryset: only visible handymen with coordinates
        handymen = (
            HandymanProfile.objects.filter(
                is_approved=True,
                is_active=True,
                is_available=True,
                latitude__isnull=False,
                longitude__isnull=False,
            )
            .select_related("user")
            .annotate(
                distance_km=Case(
                    When(
                        latitude__isnull=False,
                        longitude__isnull=False,
                        then=(
                            6371.0
                            * ACos(
                                Cos(Radians(Value(user_lat)))
                                * Cos(Radians("latitude"))
                                * Cos(Radians("longitude") - Radians(Value(user_lng)))
                                + Sin(Radians(Value(user_lat)))
                                * Sin(Radians("latitude"))
                            )
                        ),
                    ),
                    default=Value(None),
                    output_field=FloatField(),
                )
            )
            .filter(distance_km__lte=radius)
            .order_by("distance_km", "-created_at")
        )

        total_count = handymen.count()

        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 1
        )

        start = (page - 1) * page_size
        end = start + page_size
        handymen_page = handymen[start:end]

        serializer = HomeownerHandymanListSerializer(handymen_page, many=True)

        meta = {
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_count": total_count,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            }
        }

        return success_response(
            serializer.data, message="Handymen retrieved successfully", meta=meta
        )


class HomeownerHandymanDetailView(APIView):
    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_homeowner_handymen_detail",
        responses={
            200: HomeownerHandymanDetailResponseSerializer,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Get a handyman public profile detail for homeowners. "
            "Sensitive fields (phone/address/coordinates) are not returned."
        ),
        summary="Get handyman detail",
        tags=["Mobile Homeowner Handymen"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Handyman retrieved successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "display_name": "John Handyman",
                        "rating": 4.5,
                        "hourly_rate": 75.0,
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Not Found",
                value={
                    "message": "Handyman not found",
                    "data": None,
                    "errors": {"detail": "The requested resource was not found"},
                    "meta": None,
                },
                response_only=True,
                status_codes=["404"],
            ),
        ],
    )
    def get(self, request, public_id):
        """Get handyman detail for homeowners."""
        try:
            profile = HandymanProfile.objects.get(
                public_id=public_id,
                is_approved=True,
                is_active=True,
                is_available=True,
                latitude__isnull=False,
                longitude__isnull=False,
            )
        except HandymanProfile.DoesNotExist:
            return not_found_response("Handyman not found")

        serializer = HomeownerHandymanDetailSerializer(profile)
        return success_response(
            serializer.data, message="Handyman retrieved successfully"
        )
