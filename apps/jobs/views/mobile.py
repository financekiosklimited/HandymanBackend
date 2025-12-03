from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.authn.permissions import (
    EmailVerifiedPermission,
    PhoneVerifiedPermission,
    PlatformGuardPermission,
    RoleGuardPermission,
)
from apps.common.responses import (
    created_response,
    success_response,
    validation_error_response,
)
from apps.jobs.models import City, Job, JobCategory
from apps.jobs.serializers import (
    CityListResponseSerializer,
    CitySerializer,
    JobCategoryListResponseSerializer,
    JobCategorySerializer,
    JobCreateResponseSerializer,
    JobCreateSerializer,
    JobDetailResponseSerializer,
    JobDetailSerializer,
    JobListResponseSerializer,
    JobListSerializer,
)


class JobCategoryListView(APIView):
    """
    View for listing all active job categories.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
    ]

    @extend_schema(
        responses={200: JobCategoryListResponseSerializer},
        description="List all active job categories for mobile app. No role required.",
        summary="List job categories",
        tags=["Mobile Job Categories"],
    )
    def get(self, request):
        """List all active job categories."""
        categories = JobCategory.objects.filter(is_active=True)
        serializer = JobCategorySerializer(categories, many=True)
        return success_response(
            serializer.data, message="Categories retrieved successfully"
        )


class CityListView(APIView):
    """
    View for listing all active cities with optional province filter.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
    ]

    @extend_schema(
        responses={200: CityListResponseSerializer},
        parameters=[
            OpenApiParameter(
                name="province",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by province code (e.g., ON, BC, AB)",
                required=False,
            ),
        ],
        description="List all active Canadian cities for mobile app with optional province filter. No role required.",
        summary="List cities",
        tags=["Mobile Cities"],
    )
    def get(self, request):
        """List all active cities with optional province filter."""
        cities = City.objects.filter(is_active=True)

        # Apply province filter if provided
        province = request.query_params.get("province")
        if province:
            cities = cities.filter(province_code__iexact=province)

        serializer = CitySerializer(cities, many=True)
        return success_response(
            serializer.data, message="Cities retrieved successfully"
        )


class JobListCreateView(APIView):
    """
    View for listing customer's jobs and creating new jobs.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    def get_permissions(self):
        """
        Return different permissions for GET vs POST.
        POST (create job) requires phone verification.
        """
        permissions = super().get_permissions()
        if self.request.method == "POST":
            permissions.append(PhoneVerifiedPermission())
        return permissions

    @extend_schema(
        responses={200: JobListResponseSerializer},
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number",
                required=False,
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Items per page (max 100)",
                required=False,
            ),
            OpenApiParameter(
                name="category",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description="Filter by category public_id",
                required=False,
            ),
            OpenApiParameter(
                name="city",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description="Filter by city public_id",
                required=False,
            ),
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by job status (draft, open, in_progress, completed, cancelled)",
                required=False,
            ),
        ],
        description="List all jobs for authenticated customer with pagination and filtering. Returns only jobs created by the customer.",
        summary="List customer jobs",
        tags=["Mobile Customer Jobs"],
    )
    def get(self, request):
        """List customer's jobs with pagination and filtering."""
        # Get customer's jobs only
        jobs = Job.objects.filter(customer=request.user)

        # Apply filters
        category_id = request.query_params.get("category")
        city_id = request.query_params.get("city")
        status = request.query_params.get("status")

        if category_id:
            jobs = jobs.filter(category__public_id=category_id)
        if city_id:
            jobs = jobs.filter(city__public_id=city_id)
        if status:
            jobs = jobs.filter(status=status)

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)

        # Count total
        total_count = jobs.count()
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 1
        )

        # Slice queryset
        start = (page - 1) * page_size
        end = start + page_size
        jobs = jobs[start:end]

        # Optimize queries
        jobs = jobs.select_related("category", "city").prefetch_related("images")

        # Serialize
        serializer = JobListSerializer(jobs, many=True)

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
            serializer.data, message="Jobs retrieved successfully", meta=meta
        )

    @extend_schema(
        request=JobCreateSerializer,
        responses={201: JobCreateResponseSerializer},
        examples=[
            OpenApiExample(
                "Create Job Example",
                value={
                    "title": "Fix leaking kitchen faucet",
                    "description": "Kitchen faucet has been leaking for a few days. Need someone to fix it.",
                    "estimated_budget": 50.00,
                    "category_id": "123e4567-e89b-12d3-a456-426614174000",
                    "city_id": "123e4567-e89b-12d3-a456-426614174001",
                    "address": "123 Main St, Toronto",
                    "postal_code": "M5H 2N2",
                    "latitude": 43.651070,
                    "longitude": -79.347015,
                    "status": "open",
                },
                request_only=True,
            ),
        ],
        description="Create a new job listing for mobile app. "
        "Supports multiple image uploads (max 10 images, each max 5MB, JPEG/PNG only). "
        "Use multipart/form-data encoding for file uploads. "
        "Requires customer role and verified email.",
        summary="Create job",
        tags=["Mobile Customer Jobs"],
    )
    def post(self, request):
        """Create a new job."""
        serializer = JobCreateSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            job = serializer.save()
            # Refresh from DB to get related objects
            job = (
                Job.objects.select_related("category", "city")
                .prefetch_related("images")
                .get(pk=job.pk)
            )
            response_serializer = JobDetailSerializer(job)
            return created_response(
                response_serializer.data, message="Job created successfully"
            )
        return validation_error_response(serializer.errors)


class JobDetailView(APIView):
    """
    View for getting job detail.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        responses={200: JobDetailResponseSerializer},
        description="Get job detail by public_id for mobile app. Only returns job if it belongs to the authenticated customer.",
        summary="Get job detail",
        tags=["Mobile Customer Jobs"],
    )
    def get(self, request, public_id):
        """Get job detail."""
        # Verify job belongs to authenticated customer
        job = get_object_or_404(
            Job.objects.select_related("category", "city").prefetch_related("images"),
            public_id=public_id,
            customer=request.user,
        )

        serializer = JobDetailSerializer(job)
        return success_response(serializer.data, message="Job retrieved successfully")
