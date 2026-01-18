"""
Mobile profile views.
"""

from django.db.models import Case, Count, F, FloatField, IntegerField, Q, Value, When
from django.db.models.functions import ACos, Coalesce, Cos, Log, Radians, Sin
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.authn.permissions import (
    EmailVerifiedPermission,
    GuestPlatformGuardPermission,
    PlatformGuardPermission,
    RoleGuardPermission,
)
from apps.common.openapi import (
    NOT_FOUND_EXAMPLE,
    UNAUTHORIZED_EXAMPLE,
    VALIDATION_ERROR_EXAMPLE,
    pagination_meta_example,
    reviews_meta_example,
)
from apps.common.responses import (
    not_found_response,
    success_response,
    validation_error_response,
)

from ..models import HandymanCategory, HandymanProfile, HomeownerProfile
from ..serializers import (
    GuestHandymanDetailResponseSerializer,
    GuestHandymanDetailSerializer,
    GuestHandymanListResponseSerializer,
    GuestHandymanListSerializer,
    HandymanCategoryListResponseSerializer,
    HandymanCategorySerializer,
    HandymanProfileResponseSerializer,
    HandymanProfileSerializer,
    HandymanProfileUpdateSerializer,
    HandymanReviewListResponseSerializer,
    HandymanReviewListSerializer,
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
        operation_id="mobile_homeowner_profile_retrieve",
        responses={
            200: HomeownerProfileResponseSerializer,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Get homeowner profile information for mobile app. Requires authenticated user with homeowner role and verified email.",
        summary="Get homeowner profile",
        tags=["Mobile Homeowner Profile"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Profile retrieved successfully",
                    "data": {
                        "display_name": "Jane Homeowner",
                        "avatar_url": "https://example.com/avatar.jpg",
                        "email": "jane@example.com",
                        "phone_number": "+16471234567",
                        "is_phone_verified": True,
                        "address": "123 Main St, Toronto, ON",
                        "date_of_birth": "1990-01-01",
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
        operation_id="mobile_homeowner_profile_update",
        request=HomeownerProfileUpdateSerializer,
        responses={
            200: HomeownerProfileResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Update homeowner profile information via mobile app. All fields are optional and will only update provided values. Requires authenticated user with homeowner role and verified email.",
        summary="Update homeowner profile",
        tags=["Mobile Homeowner Profile"],
        examples=[
            OpenApiExample(
                "Update Request",
                value={
                    "display_name": "Jane Doe",
                    "address": "456 New St, Toronto, ON",
                    "date_of_birth": "1990-01-01",
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
                        "email": "jane@example.com",
                        "phone_number": "+16471234567",
                        "is_phone_verified": True,
                        "address": "456 New St, Toronto, ON",
                        "date_of_birth": "1990-01-01",
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
        operation_id="mobile_handyman_profile_retrieve",
        responses={
            200: HandymanProfileResponseSerializer,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Get handyman profile information for mobile app. "
            "Requires authenticated user with handyman role and verified email."
        ),
        summary="Get handyman profile",
        tags=["Mobile Handyman Profile"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Profile retrieved successfully",
                    "data": {
                        "display_name": "John Handyman",
                        "avatar_url": "https://example.com/avatar2.jpg",
                        "email": "john@example.com",
                        "rating": 4.8,
                        "hourly_rate": 80.0,
                        "job_title": "Senior Electrician",
                        "category": {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "name": "Electrical",
                        },
                        "id_number": "ID123456",
                        "date_of_birth": "1985-05-15",
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
        operation_id="mobile_handyman_profile_update",
        request=HandymanProfileUpdateSerializer,
        responses={
            200: HandymanProfileResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Update handyman profile information via mobile app. "
            "All fields are optional and will only update provided values. "
            "Requires authenticated user with handyman role and verified email."
        ),
        summary="Update handyman profile",
        tags=["Mobile Handyman Profile"],
        examples=[
            OpenApiExample(
                "Update Request",
                value={
                    "display_name": "John Builder",
                    "hourly_rate": 85.0,
                    "is_available": False,
                    "job_title": "Master Electrician",
                    "category_id": "123e4567-e89b-12d3-a456-426614174000",
                    "date_of_birth": "1985-05-15",
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
                        "email": "john@example.com",
                        "rating": 4.8,
                        "hourly_rate": 85.0,
                        "job_title": "Master Electrician",
                        "category": {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "name": "Electrical",
                        },
                        "id_number": "ID123456",
                        "date_of_birth": "1985-05-15",
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


class HomeownerNearbyHandymanListView(APIView):
    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_homeowner_handymen_nearby_list",
        responses={
            200: HomeownerHandymanListResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        parameters=[
            OpenApiParameter(
                name="latitude",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description=(
                    "User's current latitude for distance calculation (optional). "
                    "If provided with longitude, handymen are sorted by popularity "
                    "and distance. Handymen without coordinates appear at the end."
                ),
                required=False,
                examples=[
                    OpenApiExample("Toronto", value=43.651070),
                ],
            ),
            OpenApiParameter(
                name="longitude",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description=(
                    "User's current longitude for distance calculation (optional). "
                    "Must be provided together with latitude."
                ),
                required=False,
                examples=[
                    OpenApiExample("Toronto", value=-79.347015),
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
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search by display name (case-insensitive partial match)",
                required=False,
                examples=[
                    OpenApiExample("Search Example", value="John"),
                ],
            ),
        ],
        description=(
            "List approved, active, available handymen for homeowners. "
            "Returns all handymen sorted by popularity score (rating + review count). "
            "If latitude and longitude are provided, also considers distance in sorting "
            "and handymen without coordinates appear at the end of the list. "
            "Optional text search by display name available. "
            "This endpoint does not expose sensitive fields (phone/address/coordinates). "
            "Requires authenticated homeowner with verified email."
        ),
        summary="List handymen",
        tags=["Mobile Homeowner Handymen"],
        examples=[
            OpenApiExample(
                "Success Response (with coordinates)",
                value={
                    "message": "Handymen retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "display_name": "John Handyman",
                            "avatar_url": "https://example.com/avatar.jpg",
                            "rating": 4.5,
                            "review_count": 25,
                            "hourly_rate": 75.0,
                            "distance_km": 2.1,
                            "is_bookmarked": False,
                        }
                    ],
                    "errors": None,
                    "meta": pagination_meta_example(total_count=1),
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Success Response (without coordinates)",
                value={
                    "message": "Handymen retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "display_name": "John Handyman",
                            "avatar_url": "https://example.com/avatar.jpg",
                            "rating": 4.5,
                            "review_count": 25,
                            "hourly_rate": 75.0,
                            "distance_km": None,
                            "is_bookmarked": True,
                        }
                    ],
                    "errors": None,
                    "meta": pagination_meta_example(total_count=1),
                },
                response_only=True,
                status_codes=["200"],
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
        ],
    )
    def get(self, request):
        """List handymen sorted by popularity and optionally by distance."""
        from django.db.models import Exists, OuterRef

        from apps.bookmarks.models import HandymanBookmark

        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")
        search_query = request.query_params.get("search")

        # Base queryset: only visible handymen
        handymen = HandymanProfile.objects.filter(
            is_approved=True,
            is_active=True,
            is_available=True,
        ).select_related("user")

        # Search filter
        if search_query:
            handymen = handymen.filter(display_name__icontains=search_query)

        # Annotate is_bookmarked for the current user
        handymen = handymen.annotate(
            is_bookmarked=Exists(
                HandymanBookmark.objects.filter(
                    homeowner=request.user,
                    handyman_profile=OuterRef("pk"),
                )
            )
        )

        # Popularity score: rating * 2 + log10(review_count + 1) * 1.5
        # Rating (0-5) contributes up to 10 points
        # Review count uses log scale to prevent dominance
        # PostgreSQL LOG(base, value) = log_base(value), so Log(10, x) = log_10(x)
        popularity_score = Coalesce(
            F("rating"), Value(0.0), output_field=FloatField()
        ) * Value(2.0) + Log(Value(10), F("review_count") + Value(1)) * Value(1.5)

        handymen = handymen.annotate(
            popularity_score=popularity_score,
        )

        # Check if coordinates provided
        has_coordinates = latitude is not None and longitude is not None
        if has_coordinates:
            try:
                user_lat = float(latitude)
                user_lng = float(longitude)

                # Validate coordinate ranges
                if not (-90 <= user_lat <= 90):
                    return validation_error_response(
                        {"latitude": ["Latitude must be between -90 and 90."]}
                    )
                if not (-180 <= user_lng <= 180):
                    return validation_error_response(
                        {"longitude": ["Longitude must be between -180 and 180."]}
                    )

                # Annotate distance_km using Haversine formula
                handymen = handymen.annotate(
                    distance_km=Case(
                        When(
                            latitude__isnull=False,
                            longitude__isnull=False,
                            then=(
                                6371.0
                                * ACos(
                                    Cos(Radians(Value(user_lat)))
                                    * Cos(Radians("latitude"))
                                    * Cos(
                                        Radians("longitude") - Radians(Value(user_lng))
                                    )
                                    + Sin(Radians(Value(user_lat)))
                                    * Sin(Radians("latitude"))
                                )
                            ),
                        ),
                        default=Value(None),
                        output_field=FloatField(),
                    ),
                    # Handymen without coordinates go to the end
                    has_location=Case(
                        When(
                            latitude__isnull=False,
                            longitude__isnull=False,
                            then=Value(0),
                        ),
                        default=Value(1),
                        output_field=IntegerField(),
                    ),
                )

                # Order: has_location first, then by popularity, then by distance
                handymen = handymen.order_by(
                    "has_location",
                    "-popularity_score",
                    "distance_km",
                    "-created_at",
                )
            except (ValueError, TypeError):
                return validation_error_response(
                    {"coordinates": ["Latitude and longitude must be valid numbers."]}
                )
        else:
            # No coordinates - return all without distance, sorted by popularity
            handymen = handymen.annotate(
                distance_km=Value(None, output_field=FloatField())
            )
            handymen = handymen.order_by("-popularity_score", "-created_at")

        # Count total before pagination
        total_count = handymen.count()

        # Pagination
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
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Get a handyman public profile detail for homeowners. "
            "Sensitive fields (phone/address/coordinates) are not returned. "
            "Requires authenticated homeowner with verified email."
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
                        "avatar_url": "https://example.com/avatar.jpg",
                        "rating": 4.5,
                        "review_count": 25,
                        "hourly_rate": 75.0,
                        "is_bookmarked": False,
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
    def get(self, request, public_id):
        """Get handyman detail for homeowners."""
        from django.db.models import Exists, OuterRef

        from apps.bookmarks.models import HandymanBookmark

        try:
            profile = (
                HandymanProfile.objects.select_related("user")
                .annotate(
                    is_bookmarked=Exists(
                        HandymanBookmark.objects.filter(
                            homeowner=request.user,
                            handyman_profile=OuterRef("pk"),
                        )
                    )
                )
                .get(
                    user__public_id=public_id,
                    is_approved=True,
                    is_active=True,
                    is_available=True,
                    latitude__isnull=False,
                    longitude__isnull=False,
                )
            )
        except HandymanProfile.DoesNotExist:
            return not_found_response("Handyman not found")

        serializer = HomeownerHandymanDetailSerializer(
            profile, context={"request": request}
        )
        return success_response(
            serializer.data, message="Handyman retrieved successfully"
        )


class GuestHandymanListView(APIView):
    """
    View for listing handymen for guest users (no authentication required).
    Returns approved, active, available handymen sorted by popularity and optionally distance.
    """

    authentication_classes = []
    permission_classes = [
        GuestPlatformGuardPermission,
    ]

    @extend_schema(
        operation_id="mobile_guest_handymen_list",
        responses={200: GuestHandymanListResponseSerializer},
        parameters=[
            OpenApiParameter(
                name="latitude",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description=(
                    "User's current latitude for distance calculation (optional). "
                    "If provided with longitude, handymen are sorted by popularity "
                    "and distance. Handymen without coordinates appear at the end."
                ),
                required=False,
                examples=[
                    OpenApiExample("Toronto", value=43.651070),
                ],
            ),
            OpenApiParameter(
                name="longitude",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description=(
                    "User's current longitude for distance calculation (optional). "
                    "Must be provided together with latitude."
                ),
                required=False,
                examples=[
                    OpenApiExample("Toronto", value=-79.347015),
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
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search by display name (case-insensitive partial match)",
                required=False,
                examples=[
                    OpenApiExample("Search Example", value="John"),
                ],
            ),
        ],
        description=(
            "List approved, active, available handymen for guest users (no authentication required). "
            "Returns all handymen sorted by popularity score (rating + review count). "
            "If latitude and longitude are provided, also considers distance in sorting "
            "and handymen without coordinates appear at the end of the list. "
            "Optional text search by display name available."
        ),
        summary="Guest - List handymen",
        tags=["Mobile Guest Handymen"],
        examples=[
            OpenApiExample(
                "Success Response (with coordinates)",
                value={
                    "message": "Handymen retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "display_name": "John Handyman",
                            "avatar_url": "https://example.com/avatar.jpg",
                            "rating": 4.5,
                            "review_count": 25,
                            "hourly_rate": 75.0,
                            "distance_km": 2.1,
                            "is_bookmarked": False,
                        }
                    ],
                    "errors": None,
                    "meta": pagination_meta_example(total_count=1),
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Success Response (without coordinates)",
                value={
                    "message": "Handymen retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "display_name": "John Handyman",
                            "avatar_url": "https://example.com/avatar.jpg",
                            "rating": 4.5,
                            "review_count": 25,
                            "hourly_rate": 75.0,
                            "distance_km": None,
                            "is_bookmarked": False,
                        }
                    ],
                    "errors": None,
                    "meta": pagination_meta_example(total_count=1),
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def get(self, request):
        """List handymen for guest users sorted by popularity and optionally distance."""
        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")
        search_query = request.query_params.get("search")

        # Base queryset: only visible handymen
        handymen = HandymanProfile.objects.filter(
            is_approved=True,
            is_active=True,
            is_available=True,
        ).select_related("user")

        # Search filter
        if search_query:
            handymen = handymen.filter(display_name__icontains=search_query)

        # Popularity score: rating * 2 + log10(review_count + 1) * 1.5
        # PostgreSQL LOG(base, value) = log_base(value), so Log(10, x) = log_10(x)
        popularity_score = Coalesce(
            F("rating"), Value(0.0), output_field=FloatField()
        ) * Value(2.0) + Log(Value(10), F("review_count") + Value(1)) * Value(1.5)

        handymen = handymen.annotate(
            popularity_score=popularity_score,
        )

        # Check if coordinates provided
        has_coordinates = latitude is not None and longitude is not None
        if has_coordinates:
            try:
                user_lat = float(latitude)
                user_lng = float(longitude)

                # Validate coordinate ranges - if invalid, treat as no coordinates
                if not (-90 <= user_lat <= 90) or not (-180 <= user_lng <= 180):
                    has_coordinates = False
                else:
                    # Annotate distance_km using Haversine formula
                    handymen = handymen.annotate(
                        distance_km=Case(
                            When(
                                latitude__isnull=False,
                                longitude__isnull=False,
                                then=(
                                    6371.0
                                    * ACos(
                                        Cos(Radians(Value(user_lat)))
                                        * Cos(Radians("latitude"))
                                        * Cos(
                                            Radians("longitude")
                                            - Radians(Value(user_lng))
                                        )
                                        + Sin(Radians(Value(user_lat)))
                                        * Sin(Radians("latitude"))
                                    )
                                ),
                            ),
                            default=Value(None),
                            output_field=FloatField(),
                        ),
                        # Handymen without coordinates go to the end
                        has_location=Case(
                            When(
                                latitude__isnull=False,
                                longitude__isnull=False,
                                then=Value(0),
                            ),
                            default=Value(1),
                            output_field=IntegerField(),
                        ),
                    )

                    # Order: has_location first, then by popularity, then by distance
                    handymen = handymen.order_by(
                        "has_location",
                        "-popularity_score",
                        "distance_km",
                        "-created_at",
                    )
            except (ValueError, TypeError):
                has_coordinates = False

        if not has_coordinates:
            # No coordinates or invalid - return all without distance, sorted by popularity
            handymen = handymen.annotate(
                distance_km=Value(None, output_field=FloatField())
            )
            handymen = handymen.order_by("-popularity_score", "-created_at")

        # Count total before pagination
        total_count = handymen.count()

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 1
        )

        # Slice queryset
        start = (page - 1) * page_size
        end = start + page_size
        handymen_page = handymen[start:end]

        # Serialize
        serializer = GuestHandymanListSerializer(handymen_page, many=True)

        # Build meta
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


class GuestHandymanDetailView(APIView):
    """
    View for getting handyman detail for guest users (no authentication required).
    Only returns approved, active, available handymen.
    """

    authentication_classes = []
    permission_classes = [
        GuestPlatformGuardPermission,
    ]

    @extend_schema(
        operation_id="mobile_guest_handymen_retrieve",
        responses={
            200: GuestHandymanDetailResponseSerializer,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Get handyman detail by public_id for guest users (no authentication required). "
            "Only returns handymen that are approved, active, and available. "
            "Returns 404 if handyman not found or not visible."
        ),
        summary="Guest - Get handyman detail",
        tags=["Mobile Guest Handymen"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Handyman retrieved successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "display_name": "John Handyman",
                        "avatar_url": None,
                        "rating": 4.5,
                        "review_count": 25,
                        "hourly_rate": 75.0,
                        "is_bookmarked": False,
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
        """Get handyman detail for guest users."""
        try:
            profile = HandymanProfile.objects.select_related("user").get(
                user__public_id=public_id,
                is_approved=True,
                is_active=True,
                is_available=True,
            )
        except HandymanProfile.DoesNotExist:
            return not_found_response("Handyman not found")

        serializer = GuestHandymanDetailSerializer(profile)
        return success_response(
            serializer.data, message="Handyman retrieved successfully"
        )


class HandymanCategoryListView(APIView):
    """
    View for listing all active handyman categories.
    No authentication required - accessible by guests.
    """

    authentication_classes = []
    permission_classes = [
        GuestPlatformGuardPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_categories_list",
        responses={200: HandymanCategoryListResponseSerializer},
        description="List all active handyman categories for mobile app. No authentication required.",
        summary="List handyman categories",
        tags=["Mobile Handyman Categories"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Categories retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174001",
                            "name": "Plumbing",
                        },
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174002",
                            "name": "Electrical",
                        },
                    ],
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def get(self, request):
        """List all active handyman categories."""
        categories = HandymanCategory.objects.filter(is_active=True)
        serializer = HandymanCategorySerializer(categories, many=True)
        return success_response(
            serializer.data, message="Categories retrieved successfully"
        )


class HomeownerHandymanReviewListView(APIView):
    """
    View for listing reviews of a specific handyman for homeowners.
    Returns reviews from homeowners (reviewer_type="homeowner") with censored reviewer names.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_homeowner_handyman_reviews_list",
        responses={
            200: HandymanReviewListResponseSerializer,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        parameters=[
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
            "List reviews for a specific handyman. "
            "Only shows reviews from homeowners with censored reviewer names for privacy. "
            "Reviews are ordered by created_at descending (newest first). "
            "Requires authenticated homeowner with verified email."
        ),
        summary="List handyman reviews",
        tags=["Mobile Homeowner Handymen"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Reviews retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "reviewer_avatar_url": "https://example.com/avatar.jpg",
                            "reviewer_display_name": "J*** D**",
                            "rating": 5,
                            "comment": "Excellent work! Very professional.",
                            "created_at": "2024-01-15T10:30:00Z",
                        },
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174001",
                            "reviewer_avatar_url": None,
                            "reviewer_display_name": "M*** S****",
                            "rating": 4,
                            "comment": None,
                            "created_at": "2024-01-14T08:15:00Z",
                        },
                    ],
                    "errors": None,
                    "meta": reviews_meta_example(
                        total_count=25,
                        total_pages=2,
                        has_next=True,
                        average=4.8,
                        star_5=20,
                        star_4=3,
                        star_3=2,
                        star_2=0,
                        star_1=0,
                    ),
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def get(self, request, public_id):
        """List reviews for a handyman."""
        from apps.jobs.models import Review

        # Verify handyman exists and is visible
        try:
            profile = HandymanProfile.objects.select_related("user").get(
                user__public_id=public_id,
                is_approved=True,
                is_active=True,
                is_available=True,
            )
        except HandymanProfile.DoesNotExist:
            return not_found_response("Handyman not found")

        # Get reviews from homeowners for this handyman
        reviews = (
            Review.objects.filter(
                reviewee=profile.user,
                reviewer_type="homeowner",
            )
            .select_related("reviewer__homeowner_profile")
            .order_by("-created_at")
        )

        # Calculate rating stats (before pagination)
        rating_stats = reviews.aggregate(
            total_count=Count("id"),
            star_5=Count("id", filter=Q(rating=5)),
            star_4=Count("id", filter=Q(rating=4)),
            star_3=Count("id", filter=Q(rating=3)),
            star_2=Count("id", filter=Q(rating=2)),
            star_1=Count("id", filter=Q(rating=1)),
        )

        total_count = rating_stats["total_count"]

        # Calculate average rating
        if total_count > 0:
            total_stars = (
                rating_stats["star_5"] * 5
                + rating_stats["star_4"] * 4
                + rating_stats["star_3"] * 3
                + rating_stats["star_2"] * 2
                + rating_stats["star_1"] * 1
            )
            average_rating = round(total_stars / total_count, 1)
        else:
            average_rating = 0.0

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 1
        )

        start = (page - 1) * page_size
        end = start + page_size
        reviews_page = reviews[start:end]

        serializer = HandymanReviewListSerializer(reviews_page, many=True)

        meta = {
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_count": total_count,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
            "rating_stats": {
                "average": average_rating,
                "total_count": total_count,
                "distribution": {
                    "5": rating_stats["star_5"],
                    "4": rating_stats["star_4"],
                    "3": rating_stats["star_3"],
                    "2": rating_stats["star_2"],
                    "1": rating_stats["star_1"],
                },
            },
        }

        return success_response(
            serializer.data, message="Reviews retrieved successfully", meta=meta
        )


class GuestHandymanReviewListView(APIView):
    """
    View for listing reviews of a specific handyman for guest users.
    Returns reviews from homeowners (reviewer_type="homeowner") with censored reviewer names.
    No authentication required.
    """

    authentication_classes = []
    permission_classes = [
        GuestPlatformGuardPermission,
    ]

    @extend_schema(
        operation_id="mobile_guest_handyman_reviews_list",
        responses={
            200: HandymanReviewListResponseSerializer,
            404: OpenApiTypes.OBJECT,
        },
        parameters=[
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
            "List reviews for a specific handyman (no authentication required). "
            "Only shows reviews from homeowners with censored reviewer names for privacy. "
            "Reviews are ordered by created_at descending (newest first)."
        ),
        summary="Guest - List handyman reviews",
        tags=["Mobile Guest Handymen"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Reviews retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "reviewer_avatar_url": "https://example.com/avatar.jpg",
                            "reviewer_display_name": "J*** D**",
                            "rating": 5,
                            "comment": "Excellent work! Very professional.",
                            "created_at": "2024-01-15T10:30:00Z",
                        },
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174001",
                            "reviewer_avatar_url": None,
                            "reviewer_display_name": "M*** S****",
                            "rating": 4,
                            "comment": None,
                            "created_at": "2024-01-14T08:15:00Z",
                        },
                    ],
                    "errors": None,
                    "meta": reviews_meta_example(
                        total_count=25,
                        total_pages=2,
                        has_next=True,
                        average=4.8,
                        star_5=20,
                        star_4=3,
                        star_3=2,
                        star_2=0,
                        star_1=0,
                    ),
                },
                response_only=True,
                status_codes=["200"],
            ),
            NOT_FOUND_EXAMPLE,
        ],
    )
    def get(self, request, public_id):
        """List reviews for a handyman (guest access)."""
        from apps.jobs.models import Review

        # Verify handyman exists and is visible
        try:
            profile = HandymanProfile.objects.select_related("user").get(
                user__public_id=public_id,
                is_approved=True,
                is_active=True,
                is_available=True,
            )
        except HandymanProfile.DoesNotExist:
            return not_found_response("Handyman not found")

        # Get reviews from homeowners for this handyman
        reviews = (
            Review.objects.filter(
                reviewee=profile.user,
                reviewer_type="homeowner",
            )
            .select_related("reviewer__homeowner_profile")
            .order_by("-created_at")
        )

        # Calculate rating stats (before pagination)
        rating_stats = reviews.aggregate(
            total_count=Count("id"),
            star_5=Count("id", filter=Q(rating=5)),
            star_4=Count("id", filter=Q(rating=4)),
            star_3=Count("id", filter=Q(rating=3)),
            star_2=Count("id", filter=Q(rating=2)),
            star_1=Count("id", filter=Q(rating=1)),
        )

        total_count = rating_stats["total_count"]

        # Calculate average rating
        if total_count > 0:
            total_stars = (
                rating_stats["star_5"] * 5
                + rating_stats["star_4"] * 4
                + rating_stats["star_3"] * 3
                + rating_stats["star_2"] * 2
                + rating_stats["star_1"] * 1
            )
            average_rating = round(total_stars / total_count, 1)
        else:
            average_rating = 0.0

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 1
        )

        start = (page - 1) * page_size
        end = start + page_size
        reviews_page = reviews[start:end]

        serializer = HandymanReviewListSerializer(reviews_page, many=True)

        meta = {
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_count": total_count,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
            "rating_stats": {
                "average": average_rating,
                "total_count": total_count,
                "distribution": {
                    "5": rating_stats["star_5"],
                    "4": rating_stats["star_4"],
                    "3": rating_stats["star_3"],
                    "2": rating_stats["star_2"],
                    "1": rating_stats["star_1"],
                },
            },
        }

        return success_response(
            serializer.data, message="Reviews retrieved successfully", meta=meta
        )
