from django.db.models import Case, FloatField, Q, Value, When
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
from apps.jobs.models import (
    City,
    DailyReport,
    Job,
    JobApplication,
    JobCategory,
    Review,
    WorkSession,
)
from apps.jobs.serializers import (
    CityListResponseSerializer,
    CitySerializer,
    CompletionRejectSerializer,
    DailyReportCreateSerializer,
    DailyReportDetailResponseSerializer,
    DailyReportListResponseSerializer,
    DailyReportReviewSerializer,
    DailyReportSerializer,
    DailyReportUpdateSerializer,
    DisputeCreateSerializer,
    ForYouJobListResponseSerializer,
    ForYouJobSerializer,
    GuestJobDetailResponseSerializer,
    GuestJobDetailSerializer,
    GuestJobListResponseSerializer,
    GuestJobListSerializer,
    HandymanForYouJobListResponseSerializer,
    HandymanForYouJobSerializer,
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
    JobDisputeDetailResponseSerializer,
    JobDisputeListResponseSerializer,
    JobDisputeSerializer,
    JobListResponseSerializer,
    JobListSerializer,
    JobTaskSerializer,
    JobTaskStatusSerializer,
    JobUpdateResponseSerializer,
    JobUpdateSerializer,
    ReviewCreateSerializer,
    ReviewDetailSerializer,
    ReviewListResponseSerializer,
    ReviewResponseSerializer,
    ReviewSerializer,
    ReviewUpdateSerializer,
    WorkSessionDetailResponseSerializer,
    WorkSessionListResponseSerializer,
    WorkSessionMediaCreateSerializer,
    WorkSessionMediaSerializer,
    WorkSessionSerializer,
    WorkSessionStartSerializer,
    WorkSessionStopSerializer,
)
from apps.jobs.services import (
    daily_report_service,
    dispute_service,
    job_completion_service,
    review_service,
    work_session_service,
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
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search by title or description",
                required=False,
            ),
        ],
        description="List all jobs for authenticated homeowner with pagination and filtering. Returns only jobs created by the homeowner. Optional text search available. Requires homeowner role and verified email.",
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

        # Search filter
        search_query = request.query_params.get("search")
        if search_query:
            from django.db.models import Q

            jobs = jobs.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
            )

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
                    "tasks": [
                        {"title": "Inspect faucet and pipes"},
                        {"title": "Replace worn washers"},
                        {"title": "Test for leaks"},
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
                        "tasks": [
                            {
                                "public_id": "123e4567-e89b-12d3-a456-426614174020",
                                "title": "Inspect faucet and pipes",
                                "description": "",
                                "order": 0,
                                "is_completed": False,
                                "completed_at": None,
                            },
                            {
                                "public_id": "123e4567-e89b-12d3-a456-426614174021",
                                "title": "Replace worn washers",
                                "description": "",
                                "order": 1,
                                "is_completed": False,
                                "completed_at": None,
                            },
                            {
                                "public_id": "123e4567-e89b-12d3-a456-426614174022",
                                "title": "Test for leaks",
                                "description": "",
                                "order": 2,
                                "is_completed": False,
                                "completed_at": None,
                            },
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
                "Update Tasks - Mixed Operations",
                value={
                    "tasks": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174030",
                            "title": "Inspect faucet and pipes (updated)",
                        },
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174031",
                            "_delete": True,
                        },
                        {"title": "New task - Test for leaks"},
                        {"title": "New task - Clean up work area"},
                    ],
                },
                description=(
                    "Update tasks with CRUD operations. "
                    "Use public_id to update existing tasks, "
                    "_delete: true to delete tasks, "
                    "or omit public_id to create new tasks. "
                    "Tasks not included are preserved."
                ),
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
                        "tasks": [
                            {
                                "public_id": "123e4567-e89b-12d3-a456-426614174030",
                                "title": "Inspect faucet and pipes",
                                "description": "",
                                "order": 0,
                                "is_completed": False,
                                "completed_at": None,
                            },
                            {
                                "public_id": "123e4567-e89b-12d3-a456-426614174031",
                                "title": "Replace worn washers",
                                "description": "",
                                "order": 1,
                                "is_completed": False,
                                "completed_at": None,
                            },
                            {
                                "public_id": "123e4567-e89b-12d3-a456-426614174032",
                                "title": "Test for leaks",
                                "description": "",
                                "order": 2,
                                "is_completed": False,
                                "completed_at": None,
                            },
                            {
                                "public_id": "123e4567-e89b-12d3-a456-426614174033",
                                "title": "Clean up work area",
                                "description": "",
                                "order": 3,
                                "is_completed": False,
                                "completed_at": None,
                            },
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
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search by title or description",
                required=False,
            ),
        ],
        description=(
            "List open jobs from other homeowners for discovery/inspiration. "
            "Jobs are sorted by recency (newest first). "
            "If latitude and longitude are provided, jobs are also sorted by distance (closest first). "
            "Jobs without coordinates will have distance_km as null and appear after jobs with coordinates. "
            "Optional text search available via 'search' parameter. "
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
                            "tasks": [
                                {
                                    "public_id": "123e4567-e89b-12d3-a456-426614174040",
                                    "title": "Inspect faucet and pipes",
                                    "description": "",
                                    "order": 0,
                                    "is_completed": False,
                                    "completed_at": None,
                                },
                                {
                                    "public_id": "123e4567-e89b-12d3-a456-426614174041",
                                    "title": "Replace worn washers",
                                    "description": "",
                                    "order": 1,
                                    "is_completed": False,
                                    "completed_at": None,
                                },
                                {
                                    "public_id": "123e4567-e89b-12d3-a456-426614174042",
                                    "title": "Test for leaks",
                                    "description": "",
                                    "order": 2,
                                    "is_completed": False,
                                    "completed_at": None,
                                },
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

        # Search filter
        search_query = request.query_params.get("search")
        if search_query:
            from django.db.models import Q

            jobs = jobs.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
            )

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
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search by title or description",
                required=False,
            ),
        ],
        description=(
            "List open jobs for guest users (no authentication required). "
            "Jobs are sorted by recency (newest first). "
            "If latitude and longitude are provided, jobs include distance_km field. "
            "Jobs without coordinates will have distance_km as null. "
            "Optional text search available via 'search' parameter."
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
                            "tasks": [
                                {
                                    "public_id": "123e4567-e89b-12d3-a456-426614174050",
                                    "title": "Inspect faucet and pipes",
                                    "description": "",
                                    "order": 0,
                                    "is_completed": False,
                                    "completed_at": None,
                                },
                                {
                                    "public_id": "123e4567-e89b-12d3-a456-426614174051",
                                    "title": "Replace worn washers",
                                    "description": "",
                                    "order": 1,
                                    "is_completed": False,
                                    "completed_at": None,
                                },
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

        # Search filter
        search_query = request.query_params.get("search")
        if search_query:
            from django.db.models import Q

            jobs = jobs.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
            )

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
                        "tasks": [
                            {
                                "public_id": "123e4567-e89b-12d3-a456-426614174060",
                                "title": "Inspect faucet and pipes",
                                "description": "",
                                "order": 0,
                                "is_completed": False,
                                "completed_at": None,
                            },
                            {
                                "public_id": "123e4567-e89b-12d3-a456-426614174061",
                                "title": "Replace worn washers",
                                "description": "",
                                "order": 1,
                                "is_completed": False,
                                "completed_at": None,
                            },
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
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search by title or description",
                required=False,
            ),
        ],
        description="List open jobs for handymen to browse and apply to. Jobs are sorted by distance (if coordinates provided) and recency. Optional text search available. Requires authenticated handyman with verified email.",
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

        # Search filter
        search_query = request.query_params.get("search")
        if search_query:
            from django.db.models import Q

            jobs = jobs.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
            )

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

        serializer = HandymanForYouJobSerializer(jobs, many=True)

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
                        "tasks": [
                            {
                                "public_id": "123e4567-e89b-12d3-a456-426614174070",
                                "title": "Inspect faucet",
                                "description": "",
                                "order": 0,
                                "is_completed": False,
                                "completed_at": None,
                            },
                            {
                                "public_id": "123e4567-e89b-12d3-a456-426614174071",
                                "title": "Replace washers",
                                "description": "",
                                "order": 1,
                                "is_completed": False,
                                "completed_at": None,
                            },
                        ],
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
            .filter(Q(status="open") | Q(applications__handyman=request.user))
            .distinct(),
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


# ========================
# Ongoing Job Views
# ========================


class BaseHomeownerOngoingView(APIView):
    """
    Base view for homeowner ongoing job endpoints.
    Ensures user is the homeowner of the job.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
        PhoneVerifiedPermission,
    ]

    def get_job(self, public_id):
        """Get job and validate homeowner access."""
        job = get_object_or_404(
            Job.objects.filter(homeowner=self.request.user),
            public_id=public_id,
        )
        return job


class BaseHandymanOngoingView(APIView):
    """
    Base view for handyman ongoing job endpoints.
    Ensures user is the assigned handyman of the job.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
        PhoneVerifiedPermission,
    ]

    def get_job(self, public_id):
        """Get job and validate handyman access."""
        job = get_object_or_404(
            Job.objects.filter(assigned_handyman=self.request.user),
            public_id=public_id,
        )
        return job


# Homeowner Ongoing Job Views


class HomeownerWorkSessionListView(BaseHomeownerOngoingView):
    """
    View for homeowner to list work sessions for a specific job.
    """

    @extend_schema(
        operation_id="mobile_homeowner_jobs_sessions_list",
        responses={
            200: WorkSessionListResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="List all work sessions for a specific job. Accessible by the homeowner.",
        summary="List work sessions",
        tags=["Mobile Homeowner Ongoing Jobs"],
    )
    def get(self, request, public_id):
        job = self.get_job(public_id)
        sessions = job.work_sessions.all()
        serializer = WorkSessionSerializer(sessions, many=True)
        return success_response(
            serializer.data, message="Work sessions retrieved successfully"
        )


class HomeownerWorkSessionDetailView(BaseHomeownerOngoingView):
    """
    View for homeowner to get details of a specific work session.
    """

    @extend_schema(
        operation_id="mobile_homeowner_jobs_sessions_retrieve",
        responses={
            200: WorkSessionDetailResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Get details of a specific work session. Accessible by the homeowner.",
        summary="Get work session detail",
        tags=["Mobile Homeowner Ongoing Jobs"],
    )
    def get(self, request, public_id, session_id):
        job = self.get_job(public_id)
        session = get_object_or_404(job.work_sessions.all(), public_id=session_id)
        serializer = WorkSessionSerializer(session)
        return success_response(
            serializer.data, message="Work session retrieved successfully"
        )


class HomeownerDailyReportListView(BaseHomeownerOngoingView):
    """
    View for homeowner to list daily reports for a specific job.
    """

    @extend_schema(
        operation_id="mobile_homeowner_jobs_reports_list",
        responses={
            200: DailyReportListResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="List all daily reports for a specific job. Accessible by the homeowner.",
        summary="List daily reports",
        tags=["Mobile Homeowner Ongoing Jobs"],
    )
    def get(self, request, public_id):
        job = self.get_job(public_id)
        reports = job.daily_reports.all()
        serializer = DailyReportSerializer(reports, many=True)
        return success_response(
            serializer.data, message="Daily reports retrieved successfully"
        )


class HomeownerDailyReportDetailView(BaseHomeownerOngoingView):
    """
    View for homeowner to get details of a specific daily report.
    """

    @extend_schema(
        operation_id="mobile_homeowner_jobs_reports_retrieve",
        responses={
            200: DailyReportDetailResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Get details of a specific daily report. Accessible by the homeowner.",
        summary="Get daily report detail",
        tags=["Mobile Homeowner Ongoing Jobs"],
    )
    def get(self, request, public_id, report_id):
        job = self.get_job(public_id)
        report = get_object_or_404(job.daily_reports.all(), public_id=report_id)
        serializer = DailyReportSerializer(report)
        return success_response(
            serializer.data, message="Daily report retrieved successfully"
        )


class HomeownerJobDisputeListView(BaseHomeownerOngoingView):
    """
    View for homeowner to list disputes for a specific job.
    """

    @extend_schema(
        operation_id="mobile_homeowner_jobs_disputes_list",
        responses={
            200: JobDisputeListResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="List all disputes for a specific job. Accessible by the homeowner.",
        summary="List job disputes",
        tags=["Mobile Homeowner Ongoing Jobs"],
    )
    def get(self, request, public_id):
        job = self.get_job(public_id)
        disputes = job.disputes.all()
        serializer = JobDisputeSerializer(disputes, many=True)
        return success_response(
            serializer.data, message="Job disputes retrieved successfully"
        )


# Handyman Ongoing Job Views


class HandymanWorkSessionListView(BaseHandymanOngoingView):
    """
    View for handyman to list work sessions for a specific job.
    """

    @extend_schema(
        operation_id="mobile_handyman_jobs_sessions_list",
        responses={
            200: WorkSessionListResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="List all work sessions for a specific job. Accessible by the assigned handyman.",
        summary="List work sessions",
        tags=["Mobile Handyman Ongoing Jobs"],
    )
    def get(self, request, public_id):
        job = self.get_job(public_id)
        sessions = job.work_sessions.all()
        serializer = WorkSessionSerializer(sessions, many=True)
        return success_response(
            serializer.data, message="Work sessions retrieved successfully"
        )


class HandymanWorkSessionDetailView(BaseHandymanOngoingView):
    """
    View for handyman to get details of a specific work session.
    """

    @extend_schema(
        operation_id="mobile_handyman_jobs_sessions_retrieve",
        responses={
            200: WorkSessionDetailResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Get details of a specific work session. Accessible by the assigned handyman.",
        summary="Get work session detail",
        tags=["Mobile Handyman Ongoing Jobs"],
    )
    def get(self, request, public_id, session_id):
        job = self.get_job(public_id)
        session = get_object_or_404(job.work_sessions.all(), public_id=session_id)
        serializer = WorkSessionSerializer(session)
        return success_response(
            serializer.data, message="Work session retrieved successfully"
        )


class HandymanDailyReportListView(BaseHandymanOngoingView):
    """
    View for handyman to list daily reports for a specific job.
    """

    @extend_schema(
        operation_id="mobile_handyman_jobs_reports_list",
        responses={
            200: DailyReportListResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="List all daily reports for a specific job. Accessible by the assigned handyman.",
        summary="List daily reports",
        tags=["Mobile Handyman Ongoing Jobs"],
    )
    def get(self, request, public_id):
        job = self.get_job(public_id)
        reports = job.daily_reports.all()
        serializer = DailyReportSerializer(reports, many=True)
        return success_response(
            serializer.data, message="Daily reports retrieved successfully"
        )


class HandymanDailyReportDetailView(BaseHandymanOngoingView):
    """
    View for handyman to get details of a specific daily report.
    """

    @extend_schema(
        operation_id="mobile_handyman_jobs_reports_retrieve",
        responses={
            200: DailyReportDetailResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Get details of a specific daily report. Accessible by the assigned handyman.",
        summary="Get daily report detail",
        tags=["Mobile Handyman Ongoing Jobs"],
    )
    def get(self, request, public_id, report_id):
        job = self.get_job(public_id)
        report = get_object_or_404(job.daily_reports.all(), public_id=report_id)
        serializer = DailyReportSerializer(report)
        return success_response(
            serializer.data, message="Daily report retrieved successfully"
        )


class HandymanJobDisputeListView(BaseHandymanOngoingView):
    """
    View for handyman to list disputes for a specific job.
    """

    @extend_schema(
        operation_id="mobile_handyman_jobs_disputes_list",
        responses={
            200: JobDisputeListResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="List all disputes for a specific job. Accessible by the assigned handyman.",
        summary="List job disputes",
        tags=["Mobile Handyman Ongoing Jobs"],
    )
    def get(self, request, public_id):
        job = self.get_job(public_id)
        disputes = job.disputes.all()
        serializer = JobDisputeSerializer(disputes, many=True)
        return success_response(
            serializer.data, message="Job disputes retrieved successfully"
        )


# ========================
# Handyman Write Endpoints
# ========================


class HandymanWorkSessionStartView(BaseHandymanOngoingView):
    """
    View for handyman to start a work session.
    """

    @extend_schema(
        operation_id="mobile_handyman_jobs_sessions_start",
        request=WorkSessionStartSerializer,
        responses={
            201: WorkSessionDetailResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Start a new work session for a job. "
            "Requires location coordinates and a photo. "
            "Only one active session per job is allowed."
        ),
        summary="Start work session",
        tags=["Mobile Handyman Ongoing Jobs"],
        examples=[
            OpenApiExample(
                "Start Session Request",
                value={
                    "started_at": "2024-01-15T09:00:00Z",
                    "start_latitude": 43.6532,
                    "start_longitude": -79.3832,
                    "start_accuracy": 10.5,
                },
                request_only=True,
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def post(self, request, public_id):
        from django.core.exceptions import ValidationError

        job = self.get_job(public_id)
        serializer = WorkSessionStartSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            session = work_session_service.start_session(
                handyman=request.user,
                job=job,
                started_at=serializer.validated_data["started_at"],
                start_latitude=serializer.validated_data["start_latitude"],
                start_longitude=serializer.validated_data["start_longitude"],
                start_photo=serializer.validated_data["start_photo"],
                start_accuracy=serializer.validated_data.get("start_accuracy"),
            )
            return created_response(
                WorkSessionSerializer(session).data,
                message="Work session started successfully",
            )
        except ValidationError as e:
            return validation_error_response({"detail": str(e.message)})


class HandymanWorkSessionStopView(BaseHandymanOngoingView):
    """
    View for handyman to stop a work session.
    """

    @extend_schema(
        operation_id="mobile_handyman_jobs_sessions_stop",
        request=WorkSessionStopSerializer,
        responses={
            200: WorkSessionDetailResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=("Stop an active work session. Requires end location coordinates."),
        summary="Stop work session",
        tags=["Mobile Handyman Ongoing Jobs"],
        examples=[
            OpenApiExample(
                "Stop Session Request",
                value={
                    "ended_at": "2024-01-15T17:00:00Z",
                    "end_latitude": 43.6532,
                    "end_longitude": -79.3832,
                    "end_accuracy": 8.0,
                },
                request_only=True,
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def post(self, request, public_id, session_id):
        from django.core.exceptions import ValidationError

        job = self.get_job(public_id)
        session = get_object_or_404(
            WorkSession.objects.filter(job=job, handyman=request.user),
            public_id=session_id,
        )

        serializer = WorkSessionStopSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            session = work_session_service.stop_session(
                session=session,
                ended_at=serializer.validated_data["ended_at"],
                end_latitude=serializer.validated_data["end_latitude"],
                end_longitude=serializer.validated_data["end_longitude"],
                end_accuracy=serializer.validated_data.get("end_accuracy"),
            )
            return success_response(
                WorkSessionSerializer(session).data,
                message="Work session stopped successfully",
            )
        except ValidationError as e:
            return validation_error_response({"detail": str(e.message)})


class HandymanWorkSessionMediaUploadView(BaseHandymanOngoingView):
    """
    View for handyman to upload media to a work session.
    """

    @extend_schema(
        operation_id="mobile_handyman_jobs_sessions_media_upload",
        request=WorkSessionMediaCreateSerializer,
        responses={
            201: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Upload a photo or video to an active work session. "
            "For videos, duration_seconds is required."
        ),
        summary="Upload session media",
        tags=["Mobile Handyman Ongoing Jobs"],
        examples=[
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def post(self, request, public_id, session_id):
        from django.core.exceptions import ValidationError

        job = self.get_job(public_id)
        session = get_object_or_404(
            WorkSession.objects.filter(job=job, handyman=request.user),
            public_id=session_id,
        )

        serializer = WorkSessionMediaCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            media = work_session_service.add_media(
                work_session=session,
                media_type=serializer.validated_data["media_type"],
                file=serializer.validated_data["file"],
                file_size=serializer.validated_data["file_size"],
                description=serializer.validated_data.get("description", ""),
                task=serializer.validated_data.get("task_id"),
                duration_seconds=serializer.validated_data.get("duration_seconds"),
            )
            return created_response(
                WorkSessionMediaSerializer(media).data,
                message="Media uploaded successfully",
            )
        except ValidationError as e:
            return validation_error_response({"detail": str(e.message)})


class HandymanDailyReportCreateView(BaseHandymanOngoingView):
    """
    View for handyman to create a daily report.
    """

    @extend_schema(
        operation_id="mobile_handyman_jobs_reports_create",
        request=DailyReportCreateSerializer,
        responses={
            201: DailyReportDetailResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Submit a daily work report for a job. Only one report per day is allowed."
        ),
        summary="Create daily report",
        tags=["Mobile Handyman Ongoing Jobs"],
        examples=[
            OpenApiExample(
                "Create Report Request",
                value={
                    "report_date": "2024-01-15",
                    "summary": "Completed tiling work in the bathroom.",
                    "total_work_duration_seconds": 28800,
                    "tasks": [
                        {
                            "task_id": "123e4567-e89b-12d3-a456-426614174000",
                            "notes": "Finished floor tiles",
                            "marked_complete": True,
                        }
                    ],
                },
                request_only=True,
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def post(self, request, public_id):
        from datetime import timedelta

        from django.core.exceptions import ValidationError

        job = self.get_job(public_id)
        serializer = DailyReportCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        # Convert seconds to timedelta
        duration = timedelta(
            seconds=serializer.validated_data["total_work_duration_seconds"]
        )

        # Process task entries - task_id is already validated to JobTask
        task_entries = []
        for task_data in serializer.validated_data.get("tasks", []):
            task_entries.append(
                {
                    "task": task_data["task_id"],  # Already a JobTask instance
                    "notes": task_data.get("notes", ""),
                    "marked_complete": task_data.get("marked_complete", False),
                }
            )

        try:
            report = daily_report_service.submit_report(
                handyman=request.user,
                job=job,
                report_date=serializer.validated_data["report_date"],
                summary=serializer.validated_data["summary"],
                total_work_duration=duration,
                task_entries=task_entries,
            )
            return created_response(
                DailyReportSerializer(report).data,
                message="Daily report submitted successfully",
            )
        except ValidationError as e:
            return validation_error_response({"detail": str(e.message)})


class HandymanDailyReportEditView(BaseHandymanOngoingView):
    """
    View for handyman to edit an existing daily report.
    Only pending or rejected reports can be edited.
    """

    @extend_schema(
        operation_id="mobile_handyman_jobs_reports_update",
        request=DailyReportUpdateSerializer,
        responses={
            200: DailyReportDetailResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Edit an existing daily report for a job. "
            "Only reports with 'pending' or 'rejected' status can be edited. "
            "If a rejected report is edited, its status will be reset to 'pending' for re-review."
        ),
        summary="Edit daily report",
        tags=["Mobile Handyman Ongoing Jobs"],
        examples=[
            OpenApiExample(
                "Edit Report Request",
                value={
                    "summary": "Updated summary of work done today.",
                    "total_work_duration_seconds": 32400,
                    "tasks": [
                        {
                            "task_id": "123e4567-e89b-12d3-a456-426614174000",
                            "notes": "Finished remaining tiles",
                            "marked_complete": True,
                        }
                    ],
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Daily report updated successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "report_date": "2024-01-15",
                        "summary": "Updated summary of work done today.",
                        "total_work_duration_seconds": 32400,
                        "status": "pending",
                        "homeowner_comment": "",
                        "reviewed_at": None,
                        "review_deadline": "2024-01-18T12:00:00Z",
                        "tasks_worked": [
                            {
                                "public_id": "234e5678-e89b-12d3-a456-426614174001",
                                "task": {
                                    "public_id": "123e4567-e89b-12d3-a456-426614174000",
                                    "title": "Tile bathroom floor",
                                    "description": "Install new tiles",
                                    "is_completed": True,
                                },
                                "notes": "Finished remaining tiles",
                                "marked_complete": True,
                            }
                        ],
                        "created_at": "2024-01-15T10:00:00Z",
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
    def put(self, request, public_id, report_id):
        from datetime import timedelta

        from django.core.exceptions import ValidationError

        job = self.get_job(public_id)
        report = get_object_or_404(job.daily_reports.all(), public_id=report_id)

        serializer = DailyReportUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        duration = None
        if serializer.validated_data.get("total_work_duration_seconds") is not None:
            duration = timedelta(
                seconds=serializer.validated_data["total_work_duration_seconds"]
            )

        task_entries = None
        if serializer.validated_data.get("tasks") is not None:
            task_entries = []
            for task_data in serializer.validated_data["tasks"]:
                task_entries.append(
                    {
                        "task": task_data["task_id"],
                        "notes": task_data.get("notes", ""),
                        "marked_complete": task_data.get("marked_complete", False),
                    }
                )

        try:
            report = daily_report_service.update_report(
                handyman=request.user,
                report=report,
                summary=serializer.validated_data.get("summary"),
                total_work_duration=duration,
                task_entries=task_entries,
            )
            return success_response(
                DailyReportSerializer(report).data,
                message="Daily report updated successfully",
            )
        except ValidationError as e:
            return validation_error_response({"detail": str(e.message)})


class HandymanCompletionRequestView(BaseHandymanOngoingView):
    """
    View for handyman to request job completion.
    """

    @extend_schema(
        operation_id="mobile_handyman_jobs_completion_request",
        request=None,
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=("Request job completion. Job must be in 'in_progress' status."),
        summary="Request job completion",
        tags=["Mobile Handyman Ongoing Jobs"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Completion requested successfully",
                    "data": {"status": "pending_completion"},
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
        from django.core.exceptions import ValidationError

        job = self.get_job(public_id)

        try:
            job = job_completion_service.request_completion(
                handyman=request.user,
                job=job,
            )
            return success_response(
                {"status": job.status},
                message="Completion requested successfully",
            )
        except ValidationError as e:
            return validation_error_response({"detail": str(e.message)})


# ========================
# Homeowner Write Endpoints
# ========================


class HomeownerDailyReportReviewView(BaseHomeownerOngoingView):
    """
    View for homeowner to review (approve/reject) a daily report.
    """

    @extend_schema(
        operation_id="mobile_homeowner_jobs_reports_review",
        request=DailyReportReviewSerializer,
        responses={
            200: DailyReportDetailResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Review a daily report by approving or rejecting it. "
            "Only pending reports can be reviewed."
        ),
        summary="Review daily report",
        tags=["Mobile Homeowner Ongoing Jobs"],
        examples=[
            OpenApiExample(
                "Approve Report",
                value={
                    "decision": "approved",
                    "comment": "Great work today!",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Reject Report",
                value={
                    "decision": "rejected",
                    "comment": "Missing details about the electrical work.",
                },
                request_only=True,
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def post(self, request, public_id, report_id):
        from django.core.exceptions import ValidationError

        job = self.get_job(public_id)
        report = get_object_or_404(
            DailyReport.objects.filter(job=job),
            public_id=report_id,
        )

        serializer = DailyReportReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            report = daily_report_service.review_report(
                homeowner=request.user,
                report=report,
                decision=serializer.validated_data["decision"],
                comment=serializer.validated_data.get("comment", ""),
            )
            return success_response(
                DailyReportSerializer(report).data,
                message=f"Report {serializer.validated_data['decision']} successfully",
            )
        except ValidationError as e:
            return validation_error_response({"detail": str(e.message)})


class HomeownerCompletionApproveView(BaseHomeownerOngoingView):
    """
    View for homeowner to approve job completion.
    """

    @extend_schema(
        operation_id="mobile_homeowner_jobs_completion_approve",
        request=None,
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Approve job completion and mark job as completed. "
            "Job must be in 'pending_completion' status."
        ),
        summary="Approve job completion",
        tags=["Mobile Homeowner Ongoing Jobs"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Job completed successfully",
                    "data": {"status": "completed"},
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
        from django.core.exceptions import ValidationError

        job = self.get_job(public_id)

        try:
            job = job_completion_service.approve_completion(
                homeowner=request.user,
                job=job,
            )
            return success_response(
                {"status": job.status},
                message="Job completed successfully",
            )
        except ValidationError as e:
            return validation_error_response({"detail": str(e.message)})


class HomeownerCompletionRejectView(BaseHomeownerOngoingView):
    """
    View for homeowner to reject job completion.
    """

    @extend_schema(
        operation_id="mobile_homeowner_jobs_completion_reject",
        request=CompletionRejectSerializer,
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Reject job completion and return job to 'in_progress' status. "
            "Job must be in 'pending_completion' status."
        ),
        summary="Reject job completion",
        tags=["Mobile Homeowner Ongoing Jobs"],
        examples=[
            OpenApiExample(
                "Reject Completion",
                value={
                    "reason": "The bathroom tile grouting is incomplete.",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Completion rejected",
                    "data": {"status": "in_progress"},
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
        from django.core.exceptions import ValidationError

        job = self.get_job(public_id)

        serializer = CompletionRejectSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            job = job_completion_service.reject_completion(
                homeowner=request.user,
                job=job,
                reason=serializer.validated_data.get("reason", ""),
            )
            return success_response(
                {"status": job.status},
                message="Completion rejected",
            )
        except ValidationError as e:
            return validation_error_response({"detail": str(e.message)})


class HomeownerDisputeCreateView(BaseHomeownerOngoingView):
    """
    View for homeowner to create a dispute.
    """

    @extend_schema(
        operation_id="mobile_homeowner_jobs_disputes_create",
        request=DisputeCreateSerializer,
        responses={
            201: JobDisputeDetailResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Open a dispute for a job. "
            "Job must be in 'in_progress', 'pending_completion', or 'completed' status."
        ),
        summary="Create dispute",
        tags=["Mobile Homeowner Ongoing Jobs"],
        examples=[
            OpenApiExample(
                "Create Dispute Request",
                value={
                    "reason": "Work quality does not match what was agreed upon.",
                    "disputed_report_ids": [
                        "123e4567-e89b-12d3-a456-426614174000",
                    ],
                },
                request_only=True,
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def post(self, request, public_id):
        from django.core.exceptions import ValidationError

        job = self.get_job(public_id)

        serializer = DisputeCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            dispute = dispute_service.open_dispute(
                homeowner=request.user,
                job=job,
                reason=serializer.validated_data["reason"],
                disputed_reports=serializer.validated_data.get(
                    "disputed_report_ids", []
                ),
            )
            return created_response(
                JobDisputeSerializer(dispute).data,
                message="Dispute created successfully",
            )
        except ValidationError as e:
            return validation_error_response({"detail": str(e.message)})


class HandymanJobTaskStatusView(APIView):
    """
    View for handymen to update task completion status.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_jobs_tasks_status_update",
        request=JobTaskStatusSerializer,
        responses={
            200: JobTaskSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Update the completion status of a specific job task. "
            "Only the assigned handyman can update tasks. "
            "Requires authenticated handyman with verified email."
        ),
        summary="Update task status",
        tags=["Mobile Handyman Jobs"],
        examples=[
            OpenApiExample(
                "Mark Complete Request",
                value={"is_completed": True},
                request_only=True,
            ),
            OpenApiExample(
                "Unmark Complete Request",
                value={"is_completed": False},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Task status updated successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174020",
                        "title": "Inspect faucet and pipes",
                        "description": "",
                        "order": 0,
                        "is_completed": True,
                        "completed_at": "2024-01-15T11:00:00Z",
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
    def patch(self, request, public_id, task_id):
        """Update task status."""
        # Verify job exists and user is the assigned handyman
        job = get_object_or_404(
            Job.objects.filter(status="in_progress"),
            public_id=public_id,
            assigned_handyman=request.user,
        )

        task = get_object_or_404(job.tasks, public_id=task_id)

        serializer = JobTaskStatusSerializer(task, data=request.data)
        if serializer.is_valid():
            # Update status
            is_completed = serializer.validated_data["is_completed"]

            if is_completed and not task.is_completed:
                task.is_completed = True
                from django.utils import timezone

                task.completed_at = timezone.now()
            elif not is_completed and task.is_completed:
                task.is_completed = False
                task.completed_at = None

            task.save()

            response_serializer = JobTaskSerializer(task)
            return success_response(
                response_serializer.data, message="Task status updated successfully"
            )
        return validation_error_response(serializer.errors)


# ========================
# Review Views
# ========================


class HomeownerReviewView(APIView):
    """
    View for homeowners to create, view, and update their review for a completed job.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    def get_job(self, public_id, user):
        """Get job and verify ownership."""
        return get_object_or_404(
            Job.objects.select_related("assigned_handyman"),
            public_id=public_id,
            homeowner=user,
        )

    @extend_schema(
        operation_id="mobile_homeowner_job_review_get",
        responses={
            200: ReviewResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Get the homeowner's review for a completed job. Returns 404 if no review exists.",
        summary="Get my review for job",
        tags=["Mobile Homeowner Reviews"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Review retrieved successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "rating": 5,
                        "comment": "Great work, very professional!",
                        "reviewer_type": "homeowner",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                        "can_edit": True,
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
        """Get homeowner's review for a job."""
        job = self.get_job(public_id, request.user)

        review = review_service.get_review_for_job(job, "homeowner")
        if not review:
            return not_found_response("Review not found")

        serializer = ReviewSerializer(review)
        return success_response(
            serializer.data, message="Review retrieved successfully"
        )

    @extend_schema(
        operation_id="mobile_homeowner_job_review_create",
        request=ReviewCreateSerializer,
        responses={
            201: ReviewResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Create a review for the handyman after job completion. "
            "Reviews can only be submitted within 14 days of job completion. "
            "Rating is required (1-5 stars), comment is optional."
        ),
        summary="Create review for handyman",
        tags=["Mobile Homeowner Reviews"],
        examples=[
            OpenApiExample(
                "Review Request",
                value={"rating": 5, "comment": "Great work, very professional!"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Review submitted successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "rating": 5,
                        "comment": "Great work, very professional!",
                        "reviewer_type": "homeowner",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                        "can_edit": True,
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
    def post(self, request, public_id):
        """Create review for handyman."""
        from django.core.exceptions import ValidationError

        job = self.get_job(public_id, request.user)

        serializer = ReviewCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            review = review_service.create_review(
                user=request.user,
                job=job,
                reviewer_type="homeowner",
                rating=serializer.validated_data["rating"],
                comment=serializer.validated_data.get("comment", ""),
            )
            return created_response(
                ReviewSerializer(review).data,
                message="Review submitted successfully",
            )
        except ValidationError as e:
            return validation_error_response({"detail": str(e.message)})

    @extend_schema(
        operation_id="mobile_homeowner_job_review_update",
        request=ReviewUpdateSerializer,
        responses={
            200: ReviewResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Update the homeowner's review for a completed job. "
            "Reviews can only be edited within 14 days of job completion."
        ),
        summary="Update my review",
        tags=["Mobile Homeowner Reviews"],
        examples=[
            OpenApiExample(
                "Update Request",
                value={"rating": 4, "comment": "Updated review comment"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Review updated successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "rating": 4,
                        "comment": "Updated review comment",
                        "reviewer_type": "homeowner",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-16T10:30:00Z",
                        "can_edit": True,
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
        """Update homeowner's review."""
        from django.core.exceptions import ValidationError

        job = self.get_job(public_id, request.user)

        review = review_service.get_review_for_job(job, "homeowner")
        if not review:
            return not_found_response("Review not found")

        serializer = ReviewUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            review = review_service.update_review(
                user=request.user,
                review=review,
                rating=serializer.validated_data["rating"],
                comment=serializer.validated_data.get("comment", ""),
            )
            return success_response(
                ReviewSerializer(review).data,
                message="Review updated successfully",
            )
        except ValidationError as e:
            return validation_error_response({"detail": str(e.message)})


class HandymanReviewView(APIView):
    """
    View for handymen to create, view, and update their review for a completed job.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    def get_job(self, public_id, user):
        """Get job and verify handyman assignment."""
        return get_object_or_404(
            Job.objects.select_related("homeowner"),
            public_id=public_id,
            assigned_handyman=user,
        )

    @extend_schema(
        operation_id="mobile_handyman_job_review_get",
        responses={
            200: ReviewResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Get the handyman's review for a completed job. Returns 404 if no review exists.",
        summary="Get my review for job",
        tags=["Mobile Handyman Reviews"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Review retrieved successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "rating": 4,
                        "comment": "Good homeowner, clear communication.",
                        "reviewer_type": "handyman",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                        "can_edit": True,
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
        """Get handyman's review for a job."""
        job = self.get_job(public_id, request.user)

        review = review_service.get_review_for_job(job, "handyman")
        if not review:
            return not_found_response("Review not found")

        serializer = ReviewSerializer(review)
        return success_response(
            serializer.data, message="Review retrieved successfully"
        )

    @extend_schema(
        operation_id="mobile_handyman_job_review_create",
        request=ReviewCreateSerializer,
        responses={
            201: ReviewResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Create a review for the homeowner after job completion. "
            "Reviews can only be submitted within 14 days of job completion. "
            "Rating is required (1-5 stars), comment is optional. "
            "Note: Homeowner reviews are only visible to other handymen."
        ),
        summary="Create review for homeowner",
        tags=["Mobile Handyman Reviews"],
        examples=[
            OpenApiExample(
                "Review Request",
                value={"rating": 4, "comment": "Good homeowner, clear communication."},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Review submitted successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "rating": 4,
                        "comment": "Good homeowner, clear communication.",
                        "reviewer_type": "handyman",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                        "can_edit": True,
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
    def post(self, request, public_id):
        """Create review for homeowner."""
        from django.core.exceptions import ValidationError

        job = self.get_job(public_id, request.user)

        serializer = ReviewCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            review = review_service.create_review(
                user=request.user,
                job=job,
                reviewer_type="handyman",
                rating=serializer.validated_data["rating"],
                comment=serializer.validated_data.get("comment", ""),
            )
            return created_response(
                ReviewSerializer(review).data,
                message="Review submitted successfully",
            )
        except ValidationError as e:
            return validation_error_response({"detail": str(e.message)})

    @extend_schema(
        operation_id="mobile_handyman_job_review_update",
        request=ReviewUpdateSerializer,
        responses={
            200: ReviewResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Update the handyman's review for a completed job. "
            "Reviews can only be edited within 14 days of job completion."
        ),
        summary="Update my review",
        tags=["Mobile Handyman Reviews"],
        examples=[
            OpenApiExample(
                "Update Request",
                value={"rating": 5, "comment": "Updated: Excellent homeowner!"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Review updated successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "rating": 5,
                        "comment": "Updated: Excellent homeowner!",
                        "reviewer_type": "handyman",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-16T10:30:00Z",
                        "can_edit": True,
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
        """Update handyman's review."""
        from django.core.exceptions import ValidationError

        job = self.get_job(public_id, request.user)

        review = review_service.get_review_for_job(job, "handyman")
        if not review:
            return not_found_response("Review not found")

        serializer = ReviewUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            review = review_service.update_review(
                user=request.user,
                review=review,
                rating=serializer.validated_data["rating"],
                comment=serializer.validated_data.get("comment", ""),
            )
            return success_response(
                ReviewSerializer(review).data,
                message="Review updated successfully",
            )
        except ValidationError as e:
            return validation_error_response({"detail": str(e.message)})


class HandymanReceivedReviewsView(APIView):
    """
    View for handymen to list all reviews they have received from homeowners.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_reviews_received",
        responses={
            200: ReviewListResponseSerializer,
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
                description="Items per page (max 100)",
                required=False,
            ),
        ],
        description="List all reviews received by the handyman from homeowners. Reviews are sorted by most recent first.",
        summary="List my received reviews",
        tags=["Mobile Handyman Reviews"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Reviews retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "rating": 5,
                            "comment": "Great work, very professional!",
                            "reviewer_display_name": "John D.",
                            "reviewer_avatar_url": "https://cdn.example.com/avatars/...",
                            "job_title": "Fix kitchen sink",
                            "job_public_id": "123e4567-e89b-12d3-a456-426614174001",
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
        """List received reviews."""
        reviews = review_service.get_reviews_received(request.user, "homeowner")

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        total_count = reviews.count()
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 1
        )

        start = (page - 1) * page_size
        end = start + page_size
        reviews = reviews[start:end]

        serializer = ReviewDetailSerializer(reviews, many=True)

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
            message="Reviews retrieved successfully",
            meta=meta,
        )
