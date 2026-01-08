"""
Mobile views for bookmark endpoints.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.authn.permissions import (
    EmailVerifiedPermission,
    PlatformGuardPermission,
    RoleGuardPermission,
)
from apps.common.openapi import (
    FORBIDDEN_EXAMPLE,
    NOT_FOUND_EXAMPLE,
    UNAUTHORIZED_EXAMPLE,
    VALIDATION_ERROR_EXAMPLE,
    pagination_meta_example,
)
from apps.common.responses import (
    created_response,
    no_content_response,
    not_found_response,
    success_response,
    validation_error_response,
)

from ..models import HandymanBookmark, JobBookmark
from ..serializers import (
    BookmarkedHandymanListResponseSerializer,
    BookmarkedHandymanListSerializer,
    BookmarkedJobListResponseSerializer,
    BookmarkedJobListSerializer,
    HandymanBookmarkCreateSerializer,
    HandymanBookmarkResponseSerializer,
    HandymanBookmarkSerializer,
    JobBookmarkCreateSerializer,
    JobBookmarkResponseSerializer,
    JobBookmarkSerializer,
)

# ======================
# Handyman Job Bookmark Views
# ======================


class HandymanJobBookmarkListCreateView(APIView):
    """
    View for listing and creating job bookmarks for handymen.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_bookmarks_jobs_list",
        responses={
            200: BookmarkedJobListResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        parameters=[
            OpenApiParameter(
                name="latitude",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description="User's current latitude for distance calculation",
                required=False,
            ),
            OpenApiParameter(
                name="longitude",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description="User's current longitude for distance calculation",
                required=False,
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
            "List all bookmarked jobs for the authenticated handyman. "
            "Jobs are ordered by bookmark date (newest first). "
            "Deleted jobs are excluded from the list. "
            "Requires handyman role and verified email."
        ),
        summary="List bookmarked jobs",
        tags=["Mobile Handyman Bookmarks"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Bookmarked jobs retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "Fix leaking kitchen faucet",
                            "description": "Kitchen faucet has been leaking.",
                            "estimated_budget": 50.00,
                            "category": {
                                "public_id": "123e4567-e89b-12d3-a456-426614174001",
                                "name": "Plumbing",
                            },
                            "status": "open",
                            "homeowner_rating": 4.5,
                            "homeowner_review_count": 12,
                            "distance_km": 2.5,
                            "bookmarked_at": "2024-01-15T10:30:00Z",
                        }
                    ],
                    "errors": None,
                    "meta": pagination_meta_example(total_count=1),
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
        ],
    )
    def get(self, request):
        """List bookmarked jobs for the handyman."""
        # Get bookmarks with related jobs (exclude deleted jobs)
        bookmarks = (
            JobBookmark.objects.filter(handyman=request.user)
            .exclude(job__status="deleted")
            .select_related(
                "job__category",
                "job__city",
                "job__homeowner__homeowner_profile",
            )
            .prefetch_related("job__images", "job__tasks")
        )

        # Get coordinates for distance calculation
        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")

        has_coordinates = latitude is not None and longitude is not None
        if has_coordinates:
            try:
                user_lat = float(latitude)
                user_lng = float(longitude)

                if not (-90 <= user_lat <= 90) or not (-180 <= user_lng <= 180):
                    has_coordinates = False
            except (ValueError, TypeError):
                has_coordinates = False

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)

        total_count = bookmarks.count()
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 1
        )

        # Slice bookmarks
        start = (page - 1) * page_size
        end = start + page_size
        bookmarks_page = bookmarks[start:end]

        # Extract jobs from bookmarks and add bookmarked_at
        jobs_data = []
        for bookmark in bookmarks_page:
            job = bookmark.job

            # Calculate distance if coordinates provided
            distance_km = None
            if has_coordinates and job.latitude and job.longitude:
                from math import acos, cos, radians, sin

                distance_km = 6371.0 * acos(
                    cos(radians(user_lat))
                    * cos(radians(float(job.latitude)))
                    * cos(radians(float(job.longitude)) - radians(user_lng))
                    + sin(radians(user_lat)) * sin(radians(float(job.latitude)))
                )

            # Add distance_km attribute to job for serializer
            job.distance_km = distance_km
            job.bookmarked_at = bookmark.created_at
            jobs_data.append(job)

        # Serialize
        serializer = BookmarkedJobListSerializer(
            jobs_data, many=True, context={"request": request}
        )

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
            serializer.data,
            message="Bookmarked jobs retrieved successfully",
            meta=meta,
        )

    @extend_schema(
        operation_id="mobile_handyman_bookmarks_jobs_create",
        request=JobBookmarkCreateSerializer,
        responses={
            201: JobBookmarkResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        description=(
            "Bookmark a job for later reference. "
            "Only open jobs can be bookmarked. "
            "If the job is already bookmarked, returns the existing bookmark. "
            "Requires handyman role and verified email."
        ),
        summary="Bookmark a job",
        tags=["Mobile Handyman Bookmarks"],
        examples=[
            OpenApiExample(
                "Bookmark Request",
                value={"job_id": "123e4567-e89b-12d3-a456-426614174000"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Job bookmarked successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174099",
                        "job": {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "Fix leaking kitchen faucet",
                        },
                        "created_at": "2024-01-15T10:30:00Z",
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["201"],
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
        ],
    )
    def post(self, request):
        """Create a job bookmark."""
        serializer = JobBookmarkCreateSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            bookmark = serializer.save()
            # Refresh to get related data
            bookmark = (
                JobBookmark.objects.select_related(
                    "job__category",
                    "job__city",
                    "job__homeowner__homeowner_profile",
                )
                .prefetch_related("job__images", "job__tasks")
                .get(pk=bookmark.pk)
            )
            response_serializer = JobBookmarkSerializer(
                bookmark, context={"request": request}
            )
            return created_response(
                response_serializer.data, message="Job bookmarked successfully"
            )
        return validation_error_response(serializer.errors)


class HandymanJobBookmarkDeleteView(APIView):
    """
    View for deleting a job bookmark.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_bookmarks_jobs_delete",
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Remove a job from bookmarks. Requires handyman role and verified email."
        ),
        summary="Remove job bookmark",
        tags=["Mobile Handyman Bookmarks"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Bookmark removed successfully",
                    "data": None,
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def delete(self, request, job_id):
        """Delete a job bookmark."""
        try:
            bookmark = JobBookmark.objects.get(
                handyman=request.user,
                job__public_id=job_id,
            )
            bookmark.delete()
            return no_content_response(message="Bookmark removed successfully")
        except JobBookmark.DoesNotExist:
            return not_found_response("Bookmark not found")


# ======================
# Homeowner Handyman Bookmark Views
# ======================


class HomeownerHandymanBookmarkListCreateView(APIView):
    """
    View for listing and creating handyman bookmarks for homeowners.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_homeowner_bookmarks_handymen_list",
        responses={
            200: BookmarkedHandymanListResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        parameters=[
            OpenApiParameter(
                name="latitude",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description="User's current latitude for distance calculation",
                required=False,
            ),
            OpenApiParameter(
                name="longitude",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description="User's current longitude for distance calculation",
                required=False,
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
            "List all bookmarked handymen for the authenticated homeowner. "
            "Handymen are ordered by bookmark date (newest first). "
            "Only active and approved handymen are included. "
            "Requires homeowner role and verified email."
        ),
        summary="List bookmarked handymen",
        tags=["Mobile Homeowner Bookmarks"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Bookmarked handymen retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "display_name": "John Builder",
                            "avatar_url": "https://example.com/avatar.jpg",
                            "rating": 4.8,
                            "hourly_rate": 75.00,
                            "distance_km": 3.2,
                            "bookmarked_at": "2024-01-15T10:30:00Z",
                        }
                    ],
                    "errors": None,
                    "meta": pagination_meta_example(total_count=1),
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
        ],
    )
    def get(self, request):
        """List bookmarked handymen for the homeowner."""
        # Get bookmarks with related handyman profiles
        # Only include active and approved handymen
        bookmarks = (
            HandymanBookmark.objects.filter(homeowner=request.user)
            .filter(
                handyman_profile__is_active=True,
                handyman_profile__is_approved=True,
            )
            .select_related("handyman_profile__user")
        )

        # Get coordinates for distance calculation
        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")

        has_coordinates = latitude is not None and longitude is not None
        if has_coordinates:
            try:
                user_lat = float(latitude)
                user_lng = float(longitude)

                if not (-90 <= user_lat <= 90) or not (-180 <= user_lng <= 180):
                    has_coordinates = False
            except (ValueError, TypeError):
                has_coordinates = False

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)

        total_count = bookmarks.count()
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 1
        )

        # Slice bookmarks
        start = (page - 1) * page_size
        end = start + page_size
        bookmarks_page = bookmarks[start:end]

        # Extract handyman profiles from bookmarks and add bookmarked_at
        handymen_data = []
        for bookmark in bookmarks_page:
            profile = bookmark.handyman_profile

            # Calculate distance if coordinates provided
            distance_km = None
            if has_coordinates and profile.latitude and profile.longitude:
                from math import acos, cos, radians, sin

                distance_km = 6371.0 * acos(
                    cos(radians(user_lat))
                    * cos(radians(float(profile.latitude)))
                    * cos(radians(float(profile.longitude)) - radians(user_lng))
                    + sin(radians(user_lat)) * sin(radians(float(profile.latitude)))
                )

            # Add distance_km attribute to profile for serializer
            profile.distance_km = distance_km
            profile.bookmarked_at = bookmark.created_at
            handymen_data.append(profile)

        # Serialize
        serializer = BookmarkedHandymanListSerializer(
            handymen_data, many=True, context={"request": request}
        )

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
            serializer.data,
            message="Bookmarked handymen retrieved successfully",
            meta=meta,
        )

    @extend_schema(
        operation_id="mobile_homeowner_bookmarks_handymen_create",
        request=HandymanBookmarkCreateSerializer,
        responses={
            201: HandymanBookmarkResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        description=(
            "Bookmark a handyman for later reference. "
            "Only active and approved handymen can be bookmarked. "
            "If the handyman is already bookmarked, returns the existing bookmark. "
            "Requires homeowner role and verified email."
        ),
        summary="Bookmark a handyman",
        tags=["Mobile Homeowner Bookmarks"],
        examples=[
            OpenApiExample(
                "Bookmark Request",
                value={"handyman_id": "123e4567-e89b-12d3-a456-426614174000"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Handyman bookmarked successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174099",
                        "handyman_profile": {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "display_name": "John Builder",
                            "rating": 4.8,
                            "hourly_rate": 75.00,
                        },
                        "created_at": "2024-01-15T10:30:00Z",
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["201"],
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
        ],
    )
    def post(self, request):
        """Create a handyman bookmark."""
        serializer = HandymanBookmarkCreateSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            bookmark = serializer.save()
            # Refresh to get related data
            bookmark = HandymanBookmark.objects.select_related(
                "handyman_profile__user"
            ).get(pk=bookmark.pk)
            response_serializer = HandymanBookmarkSerializer(
                bookmark, context={"request": request}
            )
            return created_response(
                response_serializer.data, message="Handyman bookmarked successfully"
            )
        return validation_error_response(serializer.errors)


class HomeownerHandymanBookmarkDeleteView(APIView):
    """
    View for deleting a handyman bookmark.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_homeowner_bookmarks_handymen_delete",
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Remove a handyman from bookmarks. "
            "Requires homeowner role and verified email."
        ),
        summary="Remove handyman bookmark",
        tags=["Mobile Homeowner Bookmarks"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Bookmark removed successfully",
                    "data": None,
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def delete(self, request, handyman_id):
        """Delete a handyman bookmark."""
        try:
            bookmark = HandymanBookmark.objects.get(
                homeowner=request.user,
                handyman_profile__public_id=handyman_id,
            )
            bookmark.delete()
            return no_content_response(message="Bookmark removed successfully")
        except HandymanBookmark.DoesNotExist:
            return not_found_response("Bookmark not found")
