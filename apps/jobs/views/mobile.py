from django.db.models import Case, FloatField, Value, When
from django.db.models.functions import ACos, Cos, Radians, Sin
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.authn.permissions import (
    EmailVerifiedPermission,
    GuestPlatformGuardPermission,
    PhoneVerifiedPermission,
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
    forbidden_response,
    no_content_response,
    not_found_response,
    success_response,
    validation_error_response,
)
from apps.jobs.models import City, Job, JobApplication, JobCategory
from apps.jobs.serializers import (
    CityListResponseSerializer,
    CitySerializer,
    ForYouJobListResponseSerializer,
    ForYouJobSerializer,
    GuestJobDetailResponseSerializer,
    GuestJobDetailSerializer,
    GuestJobListResponseSerializer,
    GuestJobListSerializer,
    HandymanForYouJobListResponseSerializer,
    HandymanJobDetailResponseSerializer,
    HandymanJobDetailSerializer,
    HomeownerJobApplicationDetailResponseSerializer,
    HomeownerJobApplicationDetailSerializer,
    HomeownerJobApplicationListResponseSerializer,
    HomeownerJobApplicationListSerializer,
    JobApplicationCreateSerializer,
    JobApplicationDetailResponseSerializer,
    JobApplicationDetailSerializer,
    JobApplicationListResponseSerializer,
    JobApplicationListSerializer,
    JobCategoryListResponseSerializer,
    JobCategorySerializer,
    JobCreateResponseSerializer,
    JobCreateSerializer,
    JobDetailResponseSerializer,
    JobDetailSerializer,
    JobListResponseSerializer,
    JobListSerializer,
    JobUpdateResponseSerializer,
    JobUpdateSerializer,
)


class JobCategoryListView(APIView):
    """
    View for listing all active job categories.
    No authentication required - accessible by guests.
    """

    authentication_classes = []
    permission_classes = [
        GuestPlatformGuardPermission,
    ]

    @extend_schema(
        operation_id="mobile_job_categories_list",
        responses={200: JobCategoryListResponseSerializer},
        description="List all active job categories for mobile app. No authentication required.",
        summary="List job categories",
        tags=["Mobile Job Categories"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Categories retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174001",
                            "name": "Plumbing",
                            "slug": "plumbing",
                            "description": "Plumbing services",
                            "icon": "plumbing",
                        }
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
        """List all active job categories."""
        categories = JobCategory.objects.filter(is_active=True)
        serializer = JobCategorySerializer(categories, many=True)
        return success_response(
            serializer.data, message="Categories retrieved successfully"
        )


class CityListView(APIView):
    """
    View for listing all active cities with optional province filter.
    No authentication required - accessible by guests.
    """

    authentication_classes = []
    permission_classes = [
        GuestPlatformGuardPermission,
    ]

    @extend_schema(
        operation_id="mobile_cities_list",
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
        description="List all active Canadian cities for mobile app with optional province filter. No authentication required.",
        summary="List cities",
        tags=["Mobile Cities"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Cities retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174002",
                            "name": "Toronto",
                            "province": "Ontario",
                            "province_code": "ON",
                            "slug": "toronto-on",
                        }
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
    View for listing homeowner's jobs and creating new jobs.
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
        operation_id="mobile_homeowner_jobs_list",
        responses={
            200: JobListResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
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
        description="List all jobs for authenticated homeowner with pagination and filtering. Returns only jobs created by the homeowner. Requires homeowner role and verified email.",
        summary="List homeowner jobs",
        tags=["Mobile Homeowner Jobs"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Jobs retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "Fix leaking kitchen faucet",
                            "description": "Kitchen faucet has been leaking for a few days.",
                            "estimated_budget": 50.0,
                            "category": {
                                "public_id": "123e4567-e89b-12d3-a456-426614174001",
                                "name": "Plumbing",
                            },
                            "status": "open",
                            "created_at": "2024-01-15T10:30:00Z",
                        }
                    ],
                    "meta": pagination_meta_example(total_count=1),
                    "errors": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
        ],
    )
    def get(self, request):
        """List homeowner's jobs with pagination and filtering."""
        # Get homeowner's jobs only (exclude deleted)
        jobs = Job.objects.filter(homeowner=request.user).exclude(status="deleted")

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

        # Optimize queries
        jobs = jobs.select_related("category", "city").prefetch_related("images")

        # Slice queryset
        start = (page - 1) * page_size
        end = start + page_size
        jobs = jobs[start:end]

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
        operation_id="mobile_homeowner_jobs_create",
        request=JobCreateSerializer,
        responses={
            201: JobCreateResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
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
                    "job_items": [
                        "Inspect faucet and pipes",
                        "Replace worn washers",
                        "Test for leaks",
                    ],
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Job created successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Fix leaking kitchen faucet",
                        "description": "Kitchen faucet has been leaking for a few days.",
                        "estimated_budget": 50.0,
                        "category": {
                            "public_id": "123e4567-e89b-12d3-a456-426614174001",
                            "name": "Plumbing",
                        },
                        "status": "open",
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
        description="Create a new job listing for mobile app. "
        "Supports multiple image uploads (max 10 images, each max 5MB, JPEG/PNG only). "
        "Use multipart/form-data encoding for file uploads. "
        "Requires homeowner role and verified email and phone number.",
        summary="Create job",
        tags=["Mobile Homeowner Jobs"],
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
    View for getting, updating, and deleting job detail.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    def get_permissions(self):
        """
        Return different permissions for GET vs PUT/DELETE.
        PUT and DELETE require phone verification.
        """
        permissions = super().get_permissions()
        if self.request.method in ["PUT", "DELETE"]:
            permissions.append(PhoneVerifiedPermission())
        return permissions

    @extend_schema(
        operation_id="mobile_homeowner_jobs_retrieve",
        responses={
            200: JobDetailResponseSerializer,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Get job detail by public_id for mobile app. "
            "Only returns job if it belongs to the authenticated homeowner. "
            "Returns 404 for deleted jobs or jobs not found. "
            "Requires authenticated homeowner with verified email."
        ),
        summary="Get job detail",
        tags=["Mobile Homeowner Jobs"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Job retrieved successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Fix leaking kitchen faucet",
                        "description": "Kitchen faucet has been leaking for a few days. Need someone to fix it.",
                        "estimated_budget": 50.00,
                        "category": {
                            "public_id": "123e4567-e89b-12d3-a456-426614174001",
                            "name": "Plumbing",
                            "slug": "plumbing",
                            "description": "Plumbing services",
                            "icon": "plumbing",
                        },
                        "city": {
                            "public_id": "123e4567-e89b-12d3-a456-426614174002",
                            "name": "Toronto",
                            "province": "Ontario",
                            "province_code": "ON",
                            "slug": "toronto-on",
                        },
                        "address": "123 Main St, Toronto",
                        "postal_code": "M5H 2N2",
                        "latitude": 43.651070,
                        "longitude": -79.347015,
                        "status": "open",
                        "status_at": "2024-01-15T10:30:00Z",
                        "job_items": [
                            "Inspect faucet and pipes",
                            "Replace worn washers",
                            "Test for leaks",
                        ],
                        "images": [
                            {
                                "public_id": "123e4567-e89b-12d3-a456-426614174010",
                                "image": "https://example.com/media/jobs/images/2024/01/15/faucet.jpg",
                                "order": 0,
                            }
                        ],
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
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
        """Get job detail."""
        # Verify job belongs to authenticated homeowner
        job = get_object_or_404(
            Job.objects.select_related("category", "city").prefetch_related("images"),
            public_id=public_id,
            homeowner=request.user,
        )

        # Return 404 for deleted jobs
        if job.status == "deleted":
            return not_found_response("Job not found")

        serializer = JobDetailSerializer(job)
        return success_response(serializer.data, message="Job retrieved successfully")

    @extend_schema(
        operation_id="mobile_homeowner_jobs_update",
        request=JobUpdateSerializer,
        responses={
            200: JobUpdateResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Update a job by public_id for mobile app. "
            "Only the job owner can update. All fields are optional (partial update supported). "
            "Cannot update completed, cancelled, or deleted jobs. "
            "Status can only be changed to draft, open, or in_progress. "
            "Requires verified email and phone verification."
        ),
        summary="Update job",
        tags=["Mobile Homeowner Jobs"],
        examples=[
            OpenApiExample(
                "Update Title and Description",
                value={
                    "title": "Fix leaking kitchen faucet - URGENT",
                    "description": "Kitchen faucet has been leaking for a week now. Need someone to fix it ASAP.",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Update Status to Open",
                value={
                    "status": "open",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Update Budget and Location",
                value={
                    "estimated_budget": 75.00,
                    "address": "456 Oak Ave, Toronto",
                    "postal_code": "M5H 2N2",
                    "latitude": 43.651070,
                    "longitude": -79.347015,
                },
                request_only=True,
            ),
            OpenApiExample(
                "Update Category and City",
                value={
                    "category_id": "123e4567-e89b-12d3-a456-426614174001",
                    "city_id": "123e4567-e89b-12d3-a456-426614174002",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Update Job Items",
                value={
                    "job_items": [
                        "Inspect faucet and pipes",
                        "Replace worn washers",
                        "Test for leaks",
                        "Clean up work area",
                    ],
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Job updated successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Fix leaking kitchen faucet - URGENT",
                        "description": "Kitchen faucet has been leaking for a week now. Need someone to fix it ASAP.",
                        "estimated_budget": 75.00,
                        "category": {
                            "public_id": "123e4567-e89b-12d3-a456-426614174001",
                            "name": "Plumbing",
                            "slug": "plumbing",
                            "description": "Plumbing services",
                            "icon": "plumbing",
                        },
                        "city": {
                            "public_id": "123e4567-e89b-12d3-a456-426614174002",
                            "name": "Toronto",
                            "province": "Ontario",
                            "province_code": "ON",
                            "slug": "toronto-on",
                        },
                        "address": "456 Oak Ave, Toronto",
                        "postal_code": "M5H 2N2",
                        "latitude": 43.651070,
                        "longitude": -79.347015,
                        "status": "open",
                        "status_at": "2024-01-16T14:30:00Z",
                        "job_items": [
                            "Inspect faucet and pipes",
                            "Replace worn washers",
                            "Test for leaks",
                            "Clean up work area",
                        ],
                        "images": [],
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-16T14:30:00Z",
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def put(self, request, public_id):
        """Update job."""
        # Verify job belongs to authenticated homeowner
        job = get_object_or_404(
            Job.objects.select_related("category", "city").prefetch_related("images"),
            public_id=public_id,
            homeowner=request.user,
        )

        # Return 404 for deleted jobs
        if job.status == "deleted":
            return not_found_response("Job not found")

        # Return 403 for completed/cancelled jobs
        if job.status in ["completed", "cancelled"]:
            return forbidden_response(
                errors={"status": f"Cannot update a {job.status} job."},
                message=f"Cannot update a {job.status} job",
            )

        serializer = JobUpdateSerializer(
            job, data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            job = serializer.save()
            # Refresh to get updated related objects
            job = (
                Job.objects.select_related("category", "city")
                .prefetch_related("images")
                .get(pk=job.pk)
            )
            response_serializer = JobDetailSerializer(job)
            return success_response(
                response_serializer.data, message="Job updated successfully"
            )
        return validation_error_response(serializer.errors)

    @extend_schema(
        operation_id="mobile_homeowner_jobs_delete",
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Delete a job by public_id for mobile app (soft delete - sets status to 'deleted'). "
            "Only the job owner can delete. Returns 404 if job is already deleted or not found. "
            "The job data is preserved in the database but will no longer appear in listings. "
            "Requires verified email and phone verification."
        ),
        summary="Delete job",
        tags=["Mobile Homeowner Jobs"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Job deleted successfully",
                    "data": None,
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
    def delete(self, request, public_id):
        """Soft delete job by setting status to 'deleted'."""
        # Verify job belongs to authenticated homeowner
        job = get_object_or_404(
            Job,
            public_id=public_id,
            homeowner=request.user,
        )

        # Return 404 for already deleted jobs
        if job.status == "deleted":
            return not_found_response("Job not found")

        job.status = "deleted"
        job.save()

        return no_content_response(message="Job deleted successfully")


class ForYouJobListView(APIView):
    """
    View for listing open jobs for homeowner discovery/inspiration.
    Returns jobs from other homeowners, sorted by recency and optionally by distance.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_homeowner_jobs_for_you",
        responses={
            200: ForYouJobListResponseSerializer,
            401: OpenApiTypes.OBJECT,
        },
        parameters=[
            OpenApiParameter(
                name="latitude",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description="User's current latitude for distance calculation (e.g., 43.651070)",
                required=False,
                examples=[
                    OpenApiExample(
                        "Toronto",
                        value=43.651070,
                        description="Latitude of Toronto, ON",
                    ),
                ],
            ),
            OpenApiParameter(
                name="longitude",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description="User's current longitude for distance calculation (e.g., -79.347015)",
                required=False,
                examples=[
                    OpenApiExample(
                        "Toronto",
                        value=-79.347015,
                        description="Longitude of Toronto, ON",
                    ),
                ],
            ),
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number (default: 1)",
                required=False,
                examples=[
                    OpenApiExample("First page", value=1),
                ],
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Items per page, max 100 (default: 20)",
                required=False,
                examples=[
                    OpenApiExample("Default", value=20),
                    OpenApiExample("Large", value=50),
                ],
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
        ],
        description=(
            "List open jobs from other homeowners for discovery/inspiration. "
            "Jobs are sorted by recency (newest first). "
            "If latitude and longitude are provided, jobs are also sorted by distance (closest first). "
            "Jobs without coordinates will have distance_km as null and appear after jobs with coordinates. "
            "Requires authenticated homeowner with verified email."
        ),
        summary="For You - Discover jobs",
        tags=["Mobile Homeowner Jobs"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Jobs retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "Fix leaking kitchen faucet",
                            "description": "Kitchen faucet has been leaking for a few days. Need someone to fix it.",
                            "estimated_budget": 50.00,
                            "category": {
                                "public_id": "123e4567-e89b-12d3-a456-426614174001",
                                "name": "Plumbing",
                                "slug": "plumbing",
                                "description": "Plumbing services",
                                "icon": "plumbing",
                            },
                            "city": {
                                "public_id": "123e4567-e89b-12d3-a456-426614174002",
                                "name": "Toronto",
                                "province": "Ontario",
                                "province_code": "ON",
                                "slug": "toronto-on",
                            },
                            "address": "123 Main St, Toronto",
                            "postal_code": "M5H 2N2",
                            "latitude": 43.651070,
                            "longitude": -79.347015,
                            "status": "open",
                            "job_items": [
                                "Inspect faucet and pipes",
                                "Replace worn washers",
                                "Test for leaks",
                            ],
                            "images": [],
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z",
                            "distance_km": 2.5,
                        },
                    ],
                    "errors": None,
                    "meta": pagination_meta_example(
                        total_count=45, total_pages=3, has_next=True
                    ),
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
        ],
    )
    def get(self, request):
        """List open jobs for discovery, sorted by recency and distance."""
        # Get coordinates from query params (optional)
        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")

        # Base queryset: open jobs from other users
        jobs = Job.objects.filter(status="open").exclude(homeowner=request.user)

        # Apply filters
        category_id = request.query_params.get("category")
        city_id = request.query_params.get("city")

        if category_id:
            jobs = jobs.filter(category__public_id=category_id)
        if city_id:
            jobs = jobs.filter(city__public_id=city_id)

        # Calculate distance if coordinates provided
        has_coordinates = latitude is not None and longitude is not None
        if has_coordinates:
            try:
                user_lat = float(latitude)
                user_lng = float(longitude)

                # Validate coordinate ranges
                if not (-90 <= user_lat <= 90) or not (-180 <= user_lng <= 180):
                    has_coordinates = False
                else:
                    # Haversine formula for distance calculation in km
                    # distance = 6371 * acos(
                    #     cos(radians(lat1)) * cos(radians(lat2)) *
                    #     cos(radians(lng2) - radians(lng1)) +
                    #     sin(radians(lat1)) * sin(radians(lat2))
                    # )
                    jobs = jobs.annotate(
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
                        )
                    )
                    # Order by created_at DESC, then by distance ASC (nulls last)
                    jobs = jobs.order_by("-created_at", "distance_km")
            except (ValueError, TypeError):
                has_coordinates = False

        if not has_coordinates:
            # No coordinates or invalid - just annotate with null distance
            jobs = jobs.annotate(distance_km=Value(None, output_field=FloatField()))
            jobs = jobs.order_by("-created_at")

        # Count total before pagination
        total_count = jobs.count()

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 1
        )

        # Optimize queries
        jobs = jobs.select_related("category", "city").prefetch_related("images")

        # Slice queryset
        start = (page - 1) * page_size
        end = start + page_size
        jobs = jobs[start:end]

        # Serialize
        serializer = ForYouJobSerializer(jobs, many=True)

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


class GuestJobListView(APIView):
    """
    View for listing open jobs for guest users (no authentication required).
    Returns public jobs with optional distance calculation.
    """

    authentication_classes = []
    permission_classes = [
        GuestPlatformGuardPermission,
    ]

    @extend_schema(
        operation_id="mobile_guest_jobs_list",
        responses={200: GuestJobListResponseSerializer},
        parameters=[
            OpenApiParameter(
                name="latitude",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description="User's current latitude for distance calculation (e.g., 43.651070)",
                required=False,
                examples=[
                    OpenApiExample(
                        "Toronto",
                        value=43.651070,
                        description="Latitude of Toronto, ON",
                    ),
                ],
            ),
            OpenApiParameter(
                name="longitude",
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description="User's current longitude for distance calculation (e.g., -79.347015)",
                required=False,
                examples=[
                    OpenApiExample(
                        "Toronto",
                        value=-79.347015,
                        description="Longitude of Toronto, ON",
                    ),
                ],
            ),
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number (default: 1)",
                required=False,
                examples=[
                    OpenApiExample("First page", value=1),
                ],
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Items per page, max 100 (default: 20)",
                required=False,
                examples=[
                    OpenApiExample("Default", value=20),
                    OpenApiExample("Large", value=50),
                ],
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
        ],
        description=(
            "List open jobs for guest users (no authentication required). "
            "Jobs are sorted by recency (newest first). "
            "If latitude and longitude are provided, jobs include distance_km field. "
            "Jobs without coordinates will have distance_km as null."
        ),
        summary="Guest - List jobs",
        tags=["Mobile Guest Jobs"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Jobs retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "Fix leaking kitchen faucet",
                            "description": "Kitchen faucet has been leaking for a few days.",
                            "estimated_budget": 50.00,
                            "category": {
                                "public_id": "123e4567-e89b-12d3-a456-426614174001",
                                "name": "Plumbing",
                                "slug": "plumbing",
                                "description": "Plumbing services",
                                "icon": "plumbing",
                            },
                            "city": {
                                "public_id": "123e4567-e89b-12d3-a456-426614174002",
                                "name": "Toronto",
                                "province": "Ontario",
                                "province_code": "ON",
                                "slug": "toronto-on",
                            },
                            "address": "123 Main St, Toronto",
                            "postal_code": "M5H 2N2",
                            "latitude": 43.651070,
                            "longitude": -79.347015,
                            "status": "open",
                            "job_items": [
                                "Inspect faucet and pipes",
                                "Replace worn washers",
                            ],
                            "images": [],
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z",
                            "distance_km": 2.5,
                        },
                    ],
                    "errors": None,
                    "meta": {
                        "pagination": {
                            "page": 1,
                            "page_size": 20,
                            "total_pages": 3,
                            "total_count": 45,
                            "has_next": True,
                            "has_previous": False,
                        }
                    },
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def get(self, request):
        """List open jobs for guest users with optional distance calculation."""
        # Get coordinates from query params (optional)
        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")

        # Base queryset: only open jobs
        jobs = Job.objects.filter(status="open")

        # Apply filters
        category_id = request.query_params.get("category")
        city_id = request.query_params.get("city")

        if category_id:
            jobs = jobs.filter(category__public_id=category_id)
        if city_id:
            jobs = jobs.filter(city__public_id=city_id)

        # Calculate distance if coordinates provided
        has_coordinates = latitude is not None and longitude is not None
        if has_coordinates:
            try:
                user_lat = float(latitude)
                user_lng = float(longitude)

                # Validate coordinate ranges
                if not (-90 <= user_lat <= 90) or not (-180 <= user_lng <= 180):
                    has_coordinates = False
                else:
                    # Haversine formula for distance calculation in km
                    jobs = jobs.annotate(
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
                        )
                    )
                    # Order by created_at DESC, then by distance ASC (nulls last)
                    jobs = jobs.order_by("-created_at", "distance_km")
            except (ValueError, TypeError):
                has_coordinates = False

        if not has_coordinates:
            # No coordinates or invalid - just annotate with null distance
            jobs = jobs.annotate(distance_km=Value(None, output_field=FloatField()))
            jobs = jobs.order_by("-created_at")

        # Count total before pagination
        total_count = jobs.count()

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 1
        )

        # Optimize queries
        jobs = jobs.select_related("category", "city").prefetch_related("images")

        # Slice queryset
        start = (page - 1) * page_size
        end = start + page_size
        jobs = jobs[start:end]

        # Serialize
        serializer = GuestJobListSerializer(jobs, many=True)

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


class GuestJobDetailView(APIView):
    """
    View for getting job detail for guest users (no authentication required).
    Only returns open jobs.
    """

    authentication_classes = []
    permission_classes = [
        GuestPlatformGuardPermission,
    ]

    @extend_schema(
        operation_id="mobile_guest_jobs_retrieve",
        responses={
            200: GuestJobDetailResponseSerializer,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Get job detail by public_id for guest users (no authentication required). "
            "Only returns jobs with 'open' status. "
            "Returns 404 for non-open jobs or jobs not found."
        ),
        summary="Guest - Get job detail",
        tags=["Mobile Guest Jobs"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Job retrieved successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Fix leaking kitchen faucet",
                        "description": "Kitchen faucet has been leaking for a few days.",
                        "estimated_budget": 50.00,
                        "category": {
                            "public_id": "123e4567-e89b-12d3-a456-426614174001",
                            "name": "Plumbing",
                            "slug": "plumbing",
                            "description": "Plumbing services",
                            "icon": "plumbing",
                        },
                        "city": {
                            "public_id": "123e4567-e89b-12d3-a456-426614174002",
                            "name": "Toronto",
                            "province": "Ontario",
                            "province_code": "ON",
                            "slug": "toronto-on",
                        },
                        "address": "123 Main St, Toronto",
                        "postal_code": "M5H 2N2",
                        "latitude": 43.651070,
                        "longitude": -79.347015,
                        "status": "open",
                        "status_at": "2024-01-15T10:30:00Z",
                        "job_items": [
                            "Inspect faucet and pipes",
                            "Replace worn washers",
                        ],
                        "images": [],
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Not Found Response",
                value={
                    "message": "Job not found",
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
        """Get job detail for guest users (only open jobs)."""
        job = get_object_or_404(
            Job.objects.select_related("category", "city").prefetch_related("images"),
            public_id=public_id,
            status="open",
        )

        serializer = GuestJobDetailSerializer(job)
        return success_response(serializer.data, message="Job retrieved successfully")


# ========================
# Job Views - Handyman
# ========================


class HandymanForYouJobListView(APIView):
    """
    View for handymen to browse available open jobs.
    Jobs are sorted by distance (if coordinates provided) and recency.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_jobs_for_you",
        responses={
            200: HandymanForYouJobListResponseSerializer,
            401: OpenApiTypes.OBJECT,
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
        ],
        description="List open jobs for handymen to browse and apply to. Jobs are sorted by distance (if coordinates provided) and recency. Requires authenticated handyman with verified email.",
        summary="Browse available jobs",
        tags=["Mobile Handyman Jobs"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Jobs retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "Fix leaking kitchen faucet",
                            "description": "Kitchen faucet has been leaking for a few days.",
                            "estimated_budget": 50.00,
                            "category": {
                                "public_id": "123e4567-e89b-12d3-a456-426614174001",
                                "name": "Plumbing",
                                "slug": "plumbing",
                            },
                            "city": {
                                "public_id": "123e4567-e89b-12d3-a456-426614174002",
                                "name": "Toronto",
                                "province": "Ontario",
                                "province_code": "ON",
                            },
                            "status": "open",
                            "created_at": "2024-01-15T10:30:00Z",
                            "distance_km": 5.2,
                        }
                    ],
                    "errors": None,
                    "meta": pagination_meta_example(total_count=1),
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
        ],
    )
    def get(self, request):
        """List open jobs for handymen."""
        # Get all open jobs (exclude jobs created by this user if they're also a homeowner)
        jobs = (
            Job.objects.filter(status="open")
            .select_related("category", "city")
            .prefetch_related("images")
        )

        # Exclude own jobs if user is also a homeowner
        jobs = jobs.exclude(homeowner=request.user)

        # Filter by category if provided
        category_id = request.query_params.get("category")
        if category_id:
            jobs = jobs.filter(category__public_id=category_id)

        # Filter by city if provided
        city_id = request.query_params.get("city")
        if city_id:
            jobs = jobs.filter(city__public_id=city_id)

        # Get user's location for distance calculation
        user_lat = request.query_params.get("latitude")
        user_lon = request.query_params.get("longitude")

        if user_lat and user_lon:
            try:
                user_lat = float(user_lat)
                user_lon = float(user_lon)

                # Calculate distance using Haversine formula
                jobs = jobs.annotate(
                    distance_km=Case(
                        When(
                            latitude__isnull=False,
                            longitude__isnull=False,
                            then=6371
                            * ACos(
                                Cos(Radians(Value(user_lat)))
                                * Cos(Radians("latitude"))
                                * Cos(Radians("longitude") - Radians(Value(user_lon)))
                                + Sin(Radians(Value(user_lat)))
                                * Sin(Radians("latitude"))
                            ),
                        ),
                        default=Value(None),
                        output_field=FloatField(),
                    )
                ).order_by("distance_km", "-created_at")
            except (ValueError, TypeError):
                # Invalid coordinates, just order by created_at
                jobs = jobs.order_by("-created_at")
        else:
            # No coordinates provided, order by recency
            jobs = jobs.order_by("-created_at")

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        total_count = jobs.count()
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 1
        )

        start = (page - 1) * page_size
        end = start + page_size
        jobs = jobs[start:end]

        serializer = ForYouJobSerializer(jobs, many=True)

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
            message="Jobs retrieved successfully",
            meta=meta,
        )


class HandymanJobDetailView(APIView):
    """
    View for handymen to view job details, including whether they've applied.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_jobs_detail",
        responses={
            200: HandymanJobDetailResponseSerializer,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Get details of a specific job. Includes has_applied flag and application info if handyman has applied. Requires authenticated handyman with verified email.",
        summary="Get job detail",
        tags=["Mobile Handyman Jobs"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Job retrieved successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Fix leaking kitchen faucet",
                        "description": "Kitchen faucet has been leaking for a few days.",
                        "estimated_budget": 50.00,
                        "category": {
                            "public_id": "123e4567-e89b-12d3-a456-426614174001",
                            "name": "Plumbing",
                        },
                        "city": {
                            "public_id": "123e4567-e89b-12d3-a456-426614174002",
                            "name": "Toronto",
                        },
                        "status": "open",
                        "job_items": ["Inspect faucet", "Replace washers"],
                        "has_applied": True,
                        "my_application": {
                            "public_id": "423e4567-e89b-12d3-a456-426614174000",
                            "status": "pending",
                            "created_at": "2024-01-15T10:30:00Z",
                            "status_at": "2024-01-15T10:30:00Z",
                        },
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
        """Get job detail with application status."""
        job = get_object_or_404(
            Job.objects.select_related("category", "city")
            .prefetch_related("images", "applications")
            .filter(status="open"),
            public_id=public_id,
        )

        serializer = HandymanJobDetailSerializer(job, context={"request": request})
        return success_response(serializer.data, message="Job retrieved successfully")


# ========================
# Job Application Views - Handyman
# ========================


class HandymanJobApplicationListCreateView(APIView):
    """
    View for listing handyman's job applications and creating new applications.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
        PhoneVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_applications_list",
        responses={
            200: JobApplicationListResponseSerializer,
            401: OpenApiTypes.OBJECT,
        },
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
                description="Number of items per page (max 100)",
                required=False,
            ),
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by status (pending, approved, rejected, withdrawn)",
                required=False,
            ),
        ],
        description="List all job applications for the authenticated handyman with pagination and filtering. Requires authentication with verified email and phone number.",
        summary="List my applications",
        tags=["Mobile Handyman Applications"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Applications retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "job": {
                                "public_id": "223e4567-e89b-12d3-a456-426614174000",
                                "title": "Fix Kitchen Sink",
                                "description": "Need help fixing leaky kitchen sink",
                                "estimated_budget": 150.00,
                                "category": {
                                    "public_id": "323e4567-e89b-12d3-a456-426614174000",
                                    "name": "Plumbing",
                                    "slug": "plumbing",
                                },
                                "city": {
                                    "public_id": "423e4567-e89b-12d3-a456-426614174000",
                                    "name": "Toronto",
                                    "province": "Ontario",
                                    "province_code": "ON",
                                },
                                "status": "open",
                            },
                            "status": "pending",
                            "status_at": "2024-01-15T10:30:00Z",
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z",
                        }
                    ],
                    "errors": None,
                    "meta": pagination_meta_example(total_count=1),
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
        ],
    )
    def get(self, request):
        """List all job applications for the handyman."""
        applications = (
            JobApplication.objects.filter(handyman=request.user)
            .select_related("job__category", "job__city")
            .prefetch_related("job__images")
        )

        # Filter by status if provided
        status = request.query_params.get("status")
        if status:
            applications = applications.filter(status=status)

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        total_count = applications.count()
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 1
        )

        start = (page - 1) * page_size
        end = start + page_size
        applications = applications[start:end]

        serializer = JobApplicationListSerializer(applications, many=True)

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
            message="Applications retrieved successfully",
            meta=meta,
        )

    @extend_schema(
        operation_id="mobile_handyman_applications_create",
        request=JobApplicationCreateSerializer,
        responses={
            201: JobApplicationDetailResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Apply to a job. The job must be in 'open' status. Requires authentication with verified email and phone number.",
        summary="Apply to a job",
        tags=["Mobile Handyman Applications"],
        examples=[
            OpenApiExample(
                "Request Example",
                value={"job_id": "223e4567-e89b-12d3-a456-426614174000"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Application created successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "job": {
                            "public_id": "223e4567-e89b-12d3-a456-426614174000",
                            "title": "Fix Kitchen Sink",
                        },
                        "status": "pending",
                        "status_at": "2024-01-15T10:30:00Z",
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
            NOT_FOUND_EXAMPLE,
        ],
    )
    def post(self, request):
        """Create a new job application."""
        serializer = JobApplicationCreateSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            application = serializer.save()
            response_serializer = JobApplicationDetailSerializer(application)
            return created_response(
                response_serializer.data, message="Application created successfully"
            )
        except Exception as e:
            return validation_error_response({"detail": str(e)})


class HandymanJobApplicationDetailView(APIView):
    """
    View for retrieving and withdrawing a job application.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_applications_retrieve",
        responses={
            200: JobApplicationDetailResponseSerializer,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Get details of a specific job application. Requires authenticated handyman with verified email.",
        summary="Get application detail",
        tags=["Mobile Handyman Applications"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Application retrieved successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "pending",
                        "job": {"title": "Fix Kitchen Sink"},
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
        """Get application detail."""
        application = get_object_or_404(
            JobApplication.objects.select_related(
                "job__category", "job__city"
            ).prefetch_related("job__images"),
            public_id=public_id,
            handyman=request.user,
        )

        serializer = JobApplicationDetailSerializer(application)
        return success_response(
            serializer.data, message="Application retrieved successfully"
        )


class HandymanJobApplicationWithdrawView(APIView):
    """
    View for withdrawing a job application.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_applications_withdraw",
        request=None,
        responses={
            200: JobApplicationDetailResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Withdraw a pending job application. Only pending applications can be withdrawn. Requires authenticated handyman with verified email.",
        summary="Withdraw application",
        tags=["Mobile Handyman Applications"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Application withdrawn successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "withdrawn",
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
    def post(self, request, public_id):
        """Withdraw a job application."""
        application = get_object_or_404(
            JobApplication, public_id=public_id, handyman=request.user
        )

        try:
            from apps.jobs.services import job_application_service

            application = job_application_service.withdraw_application(
                handyman=request.user, application=application
            )

            serializer = JobApplicationDetailSerializer(application)
            return success_response(
                serializer.data, message="Application withdrawn successfully"
            )
        except Exception as e:
            return validation_error_response({"detail": str(e)})


# ========================
# Job Application Views - Homeowner
# ========================


class HomeownerApplicationListView(APIView):
    """
    View for listing ALL applications across all homeowner's jobs.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_homeowner_applications_list",
        responses={
            200: HomeownerJobApplicationListResponseSerializer,
            401: OpenApiTypes.OBJECT,
        },
        parameters=[
            OpenApiParameter(
                name="job_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description="Filter by job public_id",
                required=False,
            ),
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by status (pending, approved, rejected, withdrawn)",
                required=False,
            ),
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
        ],
        description="List ALL applications across all homeowner's jobs. Supports filtering by job and status. Requires authentication with verified email.",
        summary="List all applications",
        tags=["Mobile Homeowner Applications"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Applications retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "job": {
                                "public_id": "223e4567-e89b-12d3-a456-426614174000",
                                "title": "Fix Kitchen Sink",
                            },
                            "handyman_profile": {
                                "public_id": "323e4567-e89b-12d3-a456-426614174000",
                                "display_name": "John Handyman",
                                "avatar_url": None,
                                "rating": 4.5,
                                "hourly_rate": 75.0,
                            },
                            "status": "pending",
                            "created_at": "2024-01-15T10:30:00Z",
                        }
                    ],
                    "errors": None,
                    "meta": pagination_meta_example(total_count=1),
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
        ],
    )
    def get(self, request):
        """List all applications for homeowner."""
        # Get all applications for this homeowner's jobs
        applications = JobApplication.objects.filter(
            job__homeowner=request.user
        ).select_related("job__category", "job__city", "handyman__handyman_profile")

        # Filter by job if provided
        job_id = request.query_params.get("job_id")
        if job_id:
            applications = applications.filter(job__public_id=job_id)

        # Filter by status if provided
        status = request.query_params.get("status")
        if status:
            applications = applications.filter(status=status)

        # Order by created_at (newest first)
        applications = applications.order_by("-created_at")

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        total_count = applications.count()
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 1
        )

        start = (page - 1) * page_size
        end = start + page_size
        applications = applications[start:end]

        serializer = HomeownerJobApplicationListSerializer(applications, many=True)

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
            message="Applications retrieved successfully",
            meta=meta,
        )


class HomeownerApplicationDetailView(APIView):
    """
    View for retrieving a specific application.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_homeowner_applications_retrieve",
        responses={
            200: HomeownerJobApplicationDetailResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Get details of a specific application. Validates that application belongs to homeowner's job. Requires authentication with verified email.",
        summary="Get application detail",
        tags=["Mobile Homeowner Applications"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Application retrieved successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "job": {
                            "public_id": "223e4567-e89b-12d3-a456-426614174000",
                            "title": "Fix Kitchen Sink",
                        },
                        "handyman_profile": {
                            "public_id": "323e4567-e89b-12d3-a456-426614174000",
                            "display_name": "John Handyman",
                            "avatar_url": None,
                            "rating": 4.5,
                            "hourly_rate": 75.0,
                        },
                        "status": "pending",
                        "created_at": "2024-01-15T10:30:00Z",
                    },
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
    def get(self, request, public_id):
        """Get application detail."""
        application = get_object_or_404(
            JobApplication.objects.select_related(
                "job__category", "job__city", "handyman__handyman_profile"
            ),
            public_id=public_id,
            job__homeowner=request.user,
        )

        serializer = HomeownerJobApplicationDetailSerializer(application)
        return success_response(
            serializer.data, message="Application retrieved successfully"
        )


class HomeownerApplicationApproveView(APIView):
    """
    View for approving a job application.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_homeowner_applications_approve",
        request=None,
        responses={
            200: HomeownerJobApplicationDetailResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Approve a pending application. The job status will change to 'in_progress' and all other pending applications will be automatically rejected. Only pending applications can be approved. Requires authentication with verified email.",
        summary="Approve application",
        tags=["Mobile Homeowner Applications"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Application approved successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "approved",
                        "job": {
                            "public_id": "223e4567-e89b-12d3-a456-426614174000",
                            "status": "in_progress",
                        },
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def post(self, request, public_id):
        """Approve a job application."""
        application = get_object_or_404(
            JobApplication.objects.select_related("job"),
            public_id=public_id,
            job__homeowner=request.user,
        )

        try:
            from apps.jobs.services import job_application_service

            application = job_application_service.approve_application(
                homeowner=request.user, application=application
            )

            serializer = HomeownerJobApplicationDetailSerializer(application)
            return success_response(
                serializer.data, message="Application approved successfully"
            )
        except Exception as e:
            return validation_error_response({"detail": str(e)})


class HomeownerApplicationRejectView(APIView):
    """
    View for rejecting a job application.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_homeowner_applications_reject",
        request=None,
        responses={
            200: HomeownerJobApplicationDetailResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Reject a pending application. Only pending applications can be rejected. Requires authentication with verified email.",
        summary="Reject application",
        tags=["Mobile Homeowner Applications"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Application rejected successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "rejected",
                        "job": {
                            "public_id": "223e4567-e89b-12d3-a456-426614174000",
                            "status": "open",
                        },
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def post(self, request, public_id):
        """Reject a job application."""
        application = get_object_or_404(
            JobApplication.objects.select_related("job"),
            public_id=public_id,
            job__homeowner=request.user,
        )

        try:
            from apps.jobs.services import job_application_service

            application = job_application_service.reject_application(
                homeowner=request.user, application=application
            )

            serializer = HomeownerJobApplicationDetailSerializer(application)
            return success_response(
                serializer.data, message="Application rejected successfully"
            )
        except Exception as e:
            return validation_error_response({"detail": str(e)})
