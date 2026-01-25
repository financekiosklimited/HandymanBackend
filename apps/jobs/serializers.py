import re
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.common.constants import (
    MAX_JOB_APPLICATION_ATTACHMENTS,
    MAX_JOB_ATTACHMENTS,
    MAX_REIMBURSEMENT_ATTACHMENTS,
)
from apps.common.serializers import (
    AttachmentInputSerializer,
    create_list_response_serializer,
    create_response_serializer,
)
from apps.jobs.models import (
    MAX_JOB_ITEM_LENGTH,
    MAX_JOB_ITEMS,
    City,
    DailyReport,
    DailyReportTask,
    Job,
    JobApplication,
    JobApplicationAttachment,
    JobApplicationMaterial,
    JobAttachment,
    JobCategory,
    JobDispute,
    JobTask,
    Review,
    WorkSession,
    WorkSessionMedia,
)


class JobCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for job category (read-only).
    """

    class Meta:
        model = JobCategory
        fields = ["public_id", "name", "slug", "description", "icon"]
        read_only_fields = fields


class CitySerializer(serializers.ModelSerializer):
    """
    Serializer for city (read-only).
    """

    class Meta:
        model = City
        fields = ["public_id", "name", "province", "province_code", "slug"]
        read_only_fields = fields


class JobTaskSerializer(serializers.ModelSerializer):
    """
    Serializer for job tasks (read-only).
    """

    class Meta:
        model = JobTask
        fields = [
            "public_id",
            "title",
            "description",
            "order",
            "is_completed",
            "completed_at",
        ]
        read_only_fields = fields


class JobAttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer for job attachments (images/videos) - read-only.
    """

    file_url = serializers.SerializerMethodField(help_text="Full URL of the file")
    thumbnail_url = serializers.SerializerMethodField(
        help_text="Thumbnail URL (video thumbnail or image itself)"
    )

    class Meta:
        model = JobAttachment
        fields = [
            "public_id",
            "file_url",
            "file_type",
            "file_name",
            "file_size",
            "thumbnail_url",
            "duration_seconds",
            "order",
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        """Get the full file URL."""
        return obj.file_url

    def get_thumbnail_url(self, obj):
        """Get the thumbnail URL."""
        return obj.thumbnail_url


class JobTaskListSerializer(serializers.ModelSerializer):
    """
    Serializer for job task in list/detail views (read-only).
    """

    class Meta:
        model = JobTask
        fields = [
            "public_id",
            "title",
            "description",
            "order",
            "is_completed",
            "completed_at",
        ]
        read_only_fields = fields


# ========================
# Nested Info Serializers for Job Listings and Dashboards
# ========================


class HomeownerInfoSerializer(serializers.Serializer):
    """
    Nested serializer for homeowner info in job listings (without rating).
    Used in job list APIs where rating is not needed.
    """

    public_id = serializers.UUIDField(help_text="Homeowner's public ID")
    display_name = serializers.CharField(
        allow_null=True, help_text="Homeowner's display name"
    )
    avatar_url = serializers.URLField(
        allow_null=True, help_text="Homeowner's avatar URL"
    )


class HomeownerInfoWithRatingSerializer(HomeownerInfoSerializer):
    """
    Nested serializer for homeowner info with rating (for dashboards).
    Extends HomeownerInfoSerializer with rating field.
    """

    rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        allow_null=True,
        coerce_to_string=False,
        help_text="Homeowner's rating (1-5)",
    )


class HandymanInfoWithRatingSerializer(serializers.Serializer):
    """
    Nested serializer for handyman info with rating (for dashboards).
    Used in homeowner job dashboard to show assigned handyman details.
    """

    public_id = serializers.UUIDField(help_text="Handyman's public ID")
    display_name = serializers.CharField(
        allow_null=True, help_text="Handyman's display name"
    )
    avatar_url = serializers.URLField(
        allow_null=True, help_text="Handyman's avatar URL"
    )
    rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        allow_null=True,
        coerce_to_string=False,
        help_text="Handyman's rating (1-5)",
    )


class JobListSerializer(serializers.ModelSerializer):
    """
    Serializer for job listing (read-only).
    """

    category = JobCategorySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    attachments = JobAttachmentSerializer(many=True, read_only=True)
    estimated_budget = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False
    )
    tasks = JobTaskListSerializer(many=True, read_only=True)
    applicant_count = serializers.SerializerMethodField(
        help_text="Total number of job applications for this job"
    )
    homeowner = serializers.SerializerMethodField(
        help_text="Homeowner information (public_id, display_name, avatar_url)"
    )

    class Meta:
        model = Job
        fields = [
            "public_id",
            "title",
            "description",
            "estimated_budget",
            "category",
            "city",
            "address",
            "postal_code",
            "latitude",
            "longitude",
            "status",
            "status_at",
            "tasks",
            "attachments",
            "applicant_count",
            "homeowner",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_applicant_count(self, obj):
        """Get the total count of job applications for this job."""
        # Use annotation if available (for optimized queries)
        if hasattr(obj, "applicant_count"):
            return obj.applicant_count
        # Fall back to counting the queryset
        return obj.applications.count()

    def get_homeowner(self, obj):
        """Get homeowner info (without rating for job listings)."""
        if hasattr(obj.homeowner, "homeowner_profile"):
            profile = obj.homeowner.homeowner_profile
            return {
                "public_id": obj.homeowner.public_id,
                "display_name": profile.display_name,
                "avatar_url": profile.avatar_url,
            }
        return {
            "public_id": obj.homeowner.public_id,
            "display_name": None,
            "avatar_url": None,
        }


class JobDetailSerializer(JobListSerializer):
    """
    Serializer for job detail (read-only).
    Same as JobListSerializer for now.
    """

    tasks = JobTaskSerializer(many=True, read_only=True)

    class Meta(JobListSerializer.Meta):
        fields = JobListSerializer.Meta.fields + ["tasks"]


class ForYouJobSerializer(JobListSerializer):
    """
    Serializer for ForYou job listing with optional distance.
    Used for homeowner job discovery/inspiration.
    """

    distance_km = serializers.FloatField(
        read_only=True,
        allow_null=True,
        help_text="Distance from user's location in kilometers. Null if coordinates not provided.",
    )

    class Meta(JobListSerializer.Meta):
        fields = JobListSerializer.Meta.fields + ["distance_km"]


class HandymanForYouJobSerializer(ForYouJobSerializer):
    """
    Serializer for handyman job browsing - includes homeowner rating.
    Handymen can see the homeowner's rating before applying.
    """

    homeowner_rating = serializers.SerializerMethodField()
    homeowner_review_count = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField(
        help_text="Whether this job is bookmarked by the current handyman"
    )

    class Meta(ForYouJobSerializer.Meta):
        fields = ForYouJobSerializer.Meta.fields + [
            "homeowner_rating",
            "homeowner_review_count",
            "is_bookmarked",
        ]

    def get_homeowner_rating(self, obj):
        """Get homeowner's rating (visible only to handymen)."""
        if hasattr(obj.homeowner, "homeowner_profile"):
            return obj.homeowner.homeowner_profile.rating
        return None

    def get_homeowner_review_count(self, obj):
        """Get homeowner's review count (visible only to handymen)."""
        if hasattr(obj.homeowner, "homeowner_profile"):
            return obj.homeowner.homeowner_profile.review_count
        return 0

    def get_is_bookmarked(self, obj):
        """Check if the job is bookmarked by the current handyman."""
        # Use annotated value if available (for optimized queries)
        if hasattr(obj, "is_bookmarked"):
            return obj.is_bookmarked
        # Fall back to checking the database
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.bookmarks.filter(handyman=request.user).exists()
        return False


class HandymanJobDetailSerializer(JobDetailSerializer):
    """
    Job detail serializer for handyman - includes application status and homeowner rating.
    """

    has_applied = serializers.SerializerMethodField()
    my_application = serializers.SerializerMethodField()
    homeowner_rating = serializers.SerializerMethodField()
    homeowner_review_count = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField(
        help_text="Whether this job is bookmarked by the current handyman"
    )

    class Meta(JobDetailSerializer.Meta):
        fields = JobDetailSerializer.Meta.fields + [
            "has_applied",
            "my_application",
            "homeowner_rating",
            "homeowner_review_count",
            "is_bookmarked",
        ]

    def get_has_applied(self, obj):
        """Check if the current user (handyman) has applied to this job."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.applications.filter(handyman=request.user).exists()
        return False

    def get_my_application(self, obj):
        """Get the current user's application if exists."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            application = obj.applications.filter(handyman=request.user).first()
            if application:
                return {
                    "public_id": str(application.public_id),
                    "status": application.status,
                    "created_at": application.created_at,
                    "status_at": application.status_at,
                }
        return None

    def get_homeowner_rating(self, obj):
        """Get homeowner's rating (visible only to handymen)."""
        if hasattr(obj.homeowner, "homeowner_profile"):
            return obj.homeowner.homeowner_profile.rating
        return None

    def get_homeowner_review_count(self, obj):
        """Get homeowner's review count (visible only to handymen)."""
        if hasattr(obj.homeowner, "homeowner_profile"):
            return obj.homeowner.homeowner_profile.review_count
        return 0

    def get_is_bookmarked(self, obj):
        """Check if the job is bookmarked by the current handyman."""
        # Use annotated value if available (for optimized queries)
        if hasattr(obj, "is_bookmarked"):
            return obj.is_bookmarked
        # Fall back to checking the database
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.bookmarks.filter(handyman=request.user).exists()
        return False


class JobTaskInputSerializer(serializers.Serializer):
    """
    Serializer for task input (create/update/delete).

    Usage:
    - To CREATE a new task: {"title": "Task title", "description": "optional"}
    - To UPDATE an existing task: {"public_id": "uuid", "title": "New title"}
    - To DELETE an existing task: {"public_id": "uuid", "_delete": true}

    Notes:
    - Tasks not included in the array are preserved (no implicit delete)
    - Array index determines task order for tasks in the array
    - Empty titles are filtered out
    """

    public_id = serializers.UUIDField(
        required=False,
        help_text="Task public_id (required for update/delete, omit for create)",
    )
    title = serializers.CharField(
        max_length=MAX_JOB_ITEM_LENGTH,
        required=False,
        allow_blank=True,  # Allow blank so validate_tasks can filter them out
        help_text="Task title (required for create, optional for update)",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Task description (optional)",
    )
    _delete = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Set to true to delete this task (requires public_id)",
    )


class JobCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a job (write-only).
    """

    title = serializers.CharField(
        max_length=200,
        required=True,
        help_text="Job title",
    )
    description = serializers.CharField(
        required=True,
        help_text="Job description",
    )
    estimated_budget = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        coerce_to_string=False,
        help_text="Budget homeowner is willing to pay",
    )
    category_id = serializers.UUIDField(
        required=True,
        help_text="Category public_id",
    )
    city_id = serializers.UUIDField(
        required=True,
        help_text="City public_id",
    )
    address = serializers.CharField(
        required=True,
        help_text="Street address",
    )
    postal_code = serializers.CharField(
        max_length=12,
        required=False,
        allow_blank=True,
        help_text="Postal code (international formats supported, e.g., A1A 1A1, 12345, SW1A 1AA)",
    )
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        coerce_to_string=False,
        help_text="Latitude coordinate (optional, must provide both lat/lng)",
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        coerce_to_string=False,
        help_text="Longitude coordinate (optional, must provide both lat/lng)",
    )
    status = serializers.ChoiceField(
        choices=Job.STATUS_CHOICES,
        default="draft",
        required=False,
        help_text="Job status (default: draft)",
    )
    attachments = AttachmentInputSerializer(
        many=True,
        required=False,
        help_text=f"Job attachments (max {MAX_JOB_ATTACHMENTS} files). "
        "Use indexed format: attachments[0].file, attachments[0].thumbnail, "
        "attachments[0].duration_seconds. For videos, thumbnail and duration_seconds are required.",
    )
    tasks = serializers.ListField(
        child=JobTaskInputSerializer(),
        required=False,
        allow_empty=True,
        max_length=MAX_JOB_ITEMS,
        help_text=f"List of tasks to be done (max {MAX_JOB_ITEMS} tasks)",
    )

    def validate_estimated_budget(self, value):
        """Validate budget is positive."""
        if value <= Decimal("0"):
            raise serializers.ValidationError("Budget must be greater than 0.")
        return value

    def validate_category_id(self, value):
        """Validate category exists and is active."""
        try:
            category = JobCategory.objects.get(public_id=value)
            if not category.is_active:
                raise serializers.ValidationError("Selected category is not active.")
            return category
        except JobCategory.DoesNotExist:
            raise serializers.ValidationError("Invalid category.")

    def validate_city_id(self, value):
        """Validate city exists and is active."""
        try:
            city = City.objects.get(public_id=value)
            if not city.is_active:
                raise serializers.ValidationError("Selected city is not active.")
            return city
        except City.DoesNotExist:
            raise serializers.ValidationError("Invalid city.")

    def validate_attachments(self, value):
        """Validate attachments list count."""
        if not value:
            return []

        if len(value) > MAX_JOB_ATTACHMENTS:
            raise serializers.ValidationError(
                f"Maximum {MAX_JOB_ATTACHMENTS} attachments allowed."
            )

        return value

    def validate_tasks(self, value):
        """Validate and clean tasks."""
        if not value:
            return []

        # Filter out tasks with empty titles after stripping whitespace
        cleaned_tasks = []
        for task in value:
            title = task.get("title", "").strip()
            if title:
                cleaned_tasks.append({"title": title})

        return cleaned_tasks

    def validate_postal_code(self, value):
        """Validate international postal code format.

        Supports various international formats including:
        - Canada: A1A 1A1
        - USA: 12345 or 12345-6789
        - UK: SW1A 1AA
        - Indonesia: 12345
        - Germany: 10115
        - Japan: 100-0001
        - And many more
        """
        if value:
            # Strip leading/trailing whitespace and convert to uppercase
            cleaned = value.strip().upper()

            # Check minimum and maximum length (3-12 characters)
            if len(cleaned) < 3 or len(cleaned) > 12:
                raise serializers.ValidationError(
                    "Postal code must be between 3 and 12 characters."
                )

            # International postal code pattern:
            # - Must start and end with alphanumeric
            # - Can contain letters, numbers, spaces, and hyphens
            pattern = r"^[A-Z0-9][A-Z0-9\s\-]*[A-Z0-9]$|^[A-Z0-9]{1,2}$"
            if not re.match(pattern, cleaned):
                raise serializers.ValidationError(
                    "Invalid postal code format. Only letters, numbers, spaces, "
                    "and hyphens are allowed."
                )

            # Normalize: collapse multiple spaces into single space
            cleaned = " ".join(cleaned.split())

            return cleaned
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        latitude = attrs.get("latitude")
        longitude = attrs.get("longitude")

        # If one coordinate is provided, both must be provided
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                "Both latitude and longitude must be provided together."
            )

        # Validate coordinate ranges
        if latitude is not None:
            if not (-90 <= latitude <= 90):
                raise serializers.ValidationError(
                    {"latitude": "Latitude must be between -90 and 90."}
                )
        if longitude is not None:
            if not (-180 <= longitude <= 180):
                raise serializers.ValidationError(
                    {"longitude": "Longitude must be between -180 and 180."}
                )

        return attrs

    def create(self, validated_data):
        """Create job with attachments and tasks."""
        # Extract category and city (already validated)
        category = validated_data.pop("category_id")
        city = validated_data.pop("city_id")
        attachments = validated_data.pop("attachments", [])
        tasks = validated_data.pop("tasks", [])

        # Get homeowner from context
        homeowner = self.context["request"].user

        # Create job, attachments, and tasks in a transaction
        with transaction.atomic():
            job = Job.objects.create(
                homeowner=homeowner,
                category=category,
                city=city,
                **validated_data,
            )

            # Create job attachments with new indexed format
            for idx, attachment_data in enumerate(attachments):
                file = attachment_data["file"]
                JobAttachment.objects.create(
                    job=job,
                    file=file,
                    file_type=attachment_data["file_type"],
                    file_name=getattr(file, "name", ""),
                    file_size=getattr(file, "size", 0),
                    thumbnail=attachment_data.get("thumbnail"),
                    duration_seconds=attachment_data.get("duration_seconds"),
                    order=idx,
                )

            # Create job tasks
            for idx, task_data in enumerate(tasks):
                JobTask.objects.create(
                    job=job,
                    title=task_data["title"],
                    order=idx,
                )

        return job


class JobUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating a job (write-only).
    All fields are optional for partial updates.
    Cannot update completed, cancelled, or deleted jobs.
    """

    title = serializers.CharField(
        max_length=200,
        required=False,
        help_text="Job title",
    )
    description = serializers.CharField(
        required=False,
        help_text="Job description",
    )
    estimated_budget = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        coerce_to_string=False,
        help_text="Budget homeowner is willing to pay",
    )
    category_id = serializers.UUIDField(
        required=False,
        help_text="Category public_id",
    )
    city_id = serializers.UUIDField(
        required=False,
        help_text="City public_id",
    )
    address = serializers.CharField(
        required=False,
        help_text="Street address",
    )
    postal_code = serializers.CharField(
        max_length=12,
        required=False,
        allow_blank=True,
        help_text="Postal code (international formats supported, e.g., A1A 1A1, 12345, SW1A 1AA)",
    )
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        coerce_to_string=False,
        help_text="Latitude coordinate (optional, must provide both lat/lng)",
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        coerce_to_string=False,
        help_text="Longitude coordinate (optional, must provide both lat/lng)",
    )
    status = serializers.ChoiceField(
        choices=[
            ("draft", "Draft"),
            ("open", "Open"),
            ("in_progress", "In Progress"),
        ],
        required=False,
        help_text="Job status (only draft, open, in_progress allowed)",
    )
    tasks = serializers.ListField(
        child=JobTaskInputSerializer(),
        required=False,
        allow_empty=True,
        max_length=MAX_JOB_ITEMS,
        help_text=f"List of tasks (max {MAX_JOB_ITEMS}). Supports create/update/delete operations.",
    )

    attachments = AttachmentInputSerializer(
        many=True,
        required=False,
        help_text=f"New attachments to add (max {MAX_JOB_ATTACHMENTS} total). "
        "Use indexed format: attachments[0].file, attachments[0].thumbnail, "
        "attachments[0].duration_seconds. For videos, thumbnail and duration_seconds are required.",
    )
    attachments_to_remove = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        help_text="List of attachment public_ids to remove",
    )

    def validate_estimated_budget(self, value):
        """Validate budget is positive."""
        if value is not None and value <= Decimal("0"):
            raise serializers.ValidationError("Budget must be greater than 0.")
        return value

    def validate_category_id(self, value):
        """Validate category exists and is active."""
        try:
            category = JobCategory.objects.get(public_id=value)
            if not category.is_active:
                raise serializers.ValidationError("Selected category is not active.")
            return category
        except JobCategory.DoesNotExist:
            raise serializers.ValidationError("Invalid category.")

    def validate_city_id(self, value):
        """Validate city exists and is active."""
        try:
            city = City.objects.get(public_id=value)
            if not city.is_active:
                raise serializers.ValidationError("Selected city is not active.")
            return city
        except City.DoesNotExist:
            raise serializers.ValidationError("Invalid city.")

    def validate_postal_code(self, value):
        """Validate international postal code format.

        Supports various international formats including:
        - Canada: A1A 1A1
        - USA: 12345 or 12345-6789
        - UK: SW1A 1AA
        - Indonesia: 12345
        - Germany: 10115
        - Japan: 100-0001
        - And many more
        """
        if value:
            # Strip leading/trailing whitespace and convert to uppercase
            cleaned = value.strip().upper()

            # Check minimum and maximum length (3-12 characters)
            if len(cleaned) < 3 or len(cleaned) > 12:
                raise serializers.ValidationError(
                    "Postal code must be between 3 and 12 characters."
                )

            # International postal code pattern:
            # - Must start and end with alphanumeric
            # - Can contain letters, numbers, spaces, and hyphens
            pattern = r"^[A-Z0-9][A-Z0-9\s\-]*[A-Z0-9]$|^[A-Z0-9]{1,2}$"
            if not re.match(pattern, cleaned):
                raise serializers.ValidationError(
                    "Invalid postal code format. Only letters, numbers, spaces, "
                    "and hyphens are allowed."
                )

            # Normalize: collapse multiple spaces into single space
            cleaned = " ".join(cleaned.split())

            return cleaned
        return value

    def validate_tasks(self, value):
        """
        Validate and clean tasks for update operations.

        Validates:
        - public_id must belong to the job instance if provided
        - _delete requires public_id
        - New tasks (no public_id) require a non-empty title
        - Filters out tasks with empty titles (except deletes)
        """
        if not value:
            return []

        instance = self.instance
        if not instance:
            return value

        # Get existing task public_ids for this job
        existing_task_ids = {str(t.public_id) for t in instance.tasks.all()}

        cleaned_tasks = []
        for task in value:
            public_id = task.get("public_id")
            delete = task.get("_delete", False)
            title = task.get("title", "").strip() if task.get("title") else ""
            description = (
                task.get("description", "").strip() if task.get("description") else ""
            )

            # Validate _delete requires public_id
            if delete and not public_id:
                raise serializers.ValidationError(
                    "Cannot delete a task without public_id."
                )

            # Validate public_id belongs to this job
            if public_id and str(public_id) not in existing_task_ids:
                raise serializers.ValidationError(
                    f"Task with public_id '{public_id}' does not belong to this job."
                )

            # For delete operations, just pass through
            if delete:
                cleaned_tasks.append(
                    {
                        "public_id": public_id,
                        "_delete": True,
                    }
                )
                continue

            # For new tasks (no public_id), require non-empty title
            if not public_id and not title:
                # Skip empty new tasks (filter them out)
                continue

            # For updates with public_id but no title change, still include
            if public_id:
                cleaned_tasks.append(
                    {
                        "public_id": public_id,
                        "title": title
                        if title
                        else None,  # None means don't update title
                        "description": description if description else None,
                    }
                )
            else:
                # New task with valid title
                cleaned_tasks.append(
                    {
                        "title": title,
                        "description": description,
                    }
                )

        return cleaned_tasks

    def validate_attachments(self, value):
        """Validate attachments list count."""
        if not value:
            return []

        return value

    def validate(self, attrs):
        """Cross-field validation."""
        # Get current instance values for lat/lng if not provided in update
        instance = self.instance

        # Check if one is being set to None while the other exists
        if "latitude" in attrs or "longitude" in attrs:
            new_lat = attrs.get("latitude")
            new_lng = attrs.get("longitude")

            # If updating one, need to consider the other
            if "latitude" in attrs and "longitude" not in attrs:
                new_lng = getattr(instance, "longitude", None) if instance else None
            if "longitude" in attrs and "latitude" not in attrs:
                new_lat = getattr(instance, "latitude", None) if instance else None

            # If one coordinate is provided/exists, both must be provided/exist
            if (new_lat is None) != (new_lng is None):
                raise serializers.ValidationError(
                    "Both latitude and longitude must be provided together."
                )

            # Validate coordinate ranges
            if new_lat is not None:
                if not (-90 <= new_lat <= 90):
                    raise serializers.ValidationError(
                        {"latitude": "Latitude must be between -90 and 90."}
                    )
            if new_lng is not None:
                if not (-180 <= new_lng <= 180):
                    raise serializers.ValidationError(
                        {"longitude": "Longitude must be between -180 and 180."}
                    )

        # Validate total attachment count after add/remove
        attachments = attrs.get("attachments", [])
        attachments_to_remove = attrs.get("attachments_to_remove", [])

        if attachments or attachments_to_remove:
            current_count = instance.attachments.count() if instance else 0
            removed_count = (
                instance.attachments.filter(public_id__in=attachments_to_remove).count()
                if instance and attachments_to_remove
                else 0
            )
            new_total = current_count - removed_count + len(attachments)

            if new_total > MAX_JOB_ATTACHMENTS:
                raise serializers.ValidationError(
                    {
                        "attachments": f"Maximum {MAX_JOB_ATTACHMENTS} attachments allowed. "
                        f"You have {current_count} attachments, "
                        f"removing {removed_count}, adding {len(attachments)} would result in {new_total}."
                    }
                )

        return attrs

    def update(self, instance, validated_data):
        """Update job fields, attachments, and tasks."""
        # Handle category if provided
        if "category_id" in validated_data:
            instance.category = validated_data.pop("category_id")

        # Handle city if provided
        if "city_id" in validated_data:
            instance.city = validated_data.pop("city_id")

        # Handle attachments
        attachments = validated_data.pop("attachments", [])
        attachments_to_remove = validated_data.pop("attachments_to_remove", [])

        # Handle tasks (replace all if provided)
        tasks = validated_data.pop("tasks", None)

        # Wrap all operations in a transaction for data integrity
        with transaction.atomic():
            # Delete removed attachments
            if attachments_to_remove:
                JobAttachment.objects.filter(
                    job=instance, public_id__in=attachments_to_remove
                ).delete()

            # Add new attachments with new indexed format
            if attachments:
                from django.db.models import Max

                # Calculate start order
                current_max_order = (
                    instance.attachments.aggregate(Max("order"))["order__max"]
                    if instance.attachments.exists()
                    else -1
                )

                start_order = current_max_order + 1

                for idx, attachment_data in enumerate(attachments):
                    file = attachment_data["file"]
                    JobAttachment.objects.create(
                        job=instance,
                        file=file,
                        file_type=attachment_data["file_type"],
                        file_name=getattr(file, "name", ""),
                        file_size=getattr(file, "size", 0),
                        thumbnail=attachment_data.get("thumbnail"),
                        duration_seconds=attachment_data.get("duration_seconds"),
                        order=start_order + idx,
                    )

            # Handle tasks with proper CRUD operations
            if tasks is not None:
                # Build map of existing tasks by public_id
                existing_tasks = {str(t.public_id): t for t in instance.tasks.all()}
                processed_task_ids = set()

                # Calculate starting order for new tasks
                # Tasks in the array get order based on their index
                # Tasks not in the array keep their existing order
                for idx, task_data in enumerate(tasks):
                    public_id = task_data.get("public_id")
                    delete = task_data.get("_delete", False)
                    if public_id:
                        public_id_str = str(public_id)
                        task = existing_tasks.get(public_id_str)

                        # Task existence is validated in validate_tasks
                        if delete:
                            # DELETE: Remove the task
                            task.delete()
                            processed_task_ids.add(public_id_str)  # Track as processed
                        else:
                            # UPDATE: Update task fields
                            if task_data.get("title") is not None:
                                task.title = task_data["title"]
                            if task_data.get("description") is not None:
                                task.description = task_data["description"]
                            task.order = idx
                            task.save()
                            processed_task_ids.add(public_id_str)
                    else:
                        # CREATE: New task (no public_id)
                        # Empty titles are already filtered in validate_tasks
                        JobTask.objects.create(
                            job=instance,
                            title=task_data["title"],
                            description=task_data.get("description", ""),
                            order=idx,
                        )

                # Tasks not in the request are preserved (no implicit delete)
                # But we need to adjust their order to come after processed tasks
                max_order = len(tasks)
                for public_id_str, task in existing_tasks.items():
                    if public_id_str not in processed_task_ids:
                        # Task was not in the request, keep it but adjust order
                        task.order = max_order
                        task.save()
                        max_order += 1

            # Update remaining fields
            for field, value in validated_data.items():
                setattr(instance, field, value)

            instance.save()

        return instance


# Response envelope serializers
JobCategoryListResponseSerializer = create_list_response_serializer(
    JobCategorySerializer, "JobCategoryListResponse"
)

CityListResponseSerializer = create_list_response_serializer(
    CitySerializer, "CityListResponse"
)

JobListResponseSerializer = create_list_response_serializer(
    JobListSerializer, "JobListResponse"
)

JobDetailResponseSerializer = create_response_serializer(
    JobDetailSerializer, "JobDetailResponse"
)

JobCreateResponseSerializer = create_response_serializer(
    JobDetailSerializer, "JobCreateResponse"
)

JobUpdateResponseSerializer = create_response_serializer(
    JobDetailSerializer, "JobUpdateResponse"
)

ForYouJobListResponseSerializer = create_list_response_serializer(
    ForYouJobSerializer, "ForYouJobListResponse"
)


# Guest serializers (reuse ForYouJobSerializer for list with distance_km)
GuestJobListSerializer = ForYouJobSerializer
GuestJobDetailSerializer = JobDetailSerializer

GuestJobListResponseSerializer = create_list_response_serializer(
    GuestJobListSerializer, "GuestJobListResponse"
)

GuestJobDetailResponseSerializer = create_response_serializer(
    GuestJobDetailSerializer, "GuestJobDetailResponse"
)


# ========================
# Job Application Serializers
# ========================


class JobApplicationMaterialSerializer(serializers.ModelSerializer):
    """
    Serializer for job application material (read-only).
    """

    class Meta:
        model = JobApplicationMaterial
        fields = [
            "public_id",
            "name",
            "price",
            "description",
            "created_at",
        ]
        read_only_fields = fields


class JobApplicationAttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer for job application attachment (read-only).
    """

    file_url = serializers.SerializerMethodField(help_text="Full URL of the file")
    thumbnail_url = serializers.SerializerMethodField(
        help_text="Thumbnail URL (video thumbnail or image itself)"
    )

    class Meta:
        model = JobApplicationAttachment
        fields = [
            "public_id",
            "file_url",
            "file_type",
            "file_name",
            "file_size",
            "thumbnail_url",
            "duration_seconds",
            "created_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        """Get the full file URL."""
        return obj.file_url

    def get_thumbnail_url(self, obj):
        """Get the thumbnail URL."""
        return obj.thumbnail_url


class JobApplicationMaterialInputSerializer(serializers.Serializer):
    """
    Serializer for inputting job application material.
    """

    name = serializers.CharField(max_length=255)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )


class JobApplicationListSerializer(serializers.ModelSerializer):
    """
    Serializer for job application listing (read-only).
    """

    job = JobListSerializer(read_only=True)

    class Meta:
        model = JobApplication
        fields = [
            "public_id",
            "job",
            "status",
            "status_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class JobApplicationDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for job application detail (read-only).
    """

    job = JobDetailSerializer(read_only=True)
    materials = JobApplicationMaterialSerializer(many=True, read_only=True)
    attachments = JobApplicationAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = JobApplication
        fields = [
            "public_id",
            "job",
            "status",
            "status_at",
            "predicted_hours",
            "estimated_total_price",
            "negotiation_reasoning",
            "materials",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class JobApplicationCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a job application.
    """

    job_id = serializers.UUIDField(required=True)
    predicted_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=True
    )
    estimated_total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=True
    )
    negotiation_reasoning = serializers.CharField(required=False, allow_blank=True)
    materials = JobApplicationMaterialInputSerializer(many=True, required=False)
    attachments = AttachmentInputSerializer(
        many=True,
        required=False,
        help_text="Attachments for the application. "
        "Use indexed format: attachments[0].file, attachments[0].thumbnail, "
        "attachments[0].duration_seconds. For videos, thumbnail and duration_seconds are required.",
    )

    def validate_job_id(self, value):
        """
        Validate that job exists and is open.
        """
        try:
            job = Job.objects.get(public_id=value)
            return job
        except Job.DoesNotExist:
            raise serializers.ValidationError("Invalid job.")

    def validate_predicted_hours(self, value):
        """
        Validate predicted hours is positive.
        """
        if value <= 0:
            raise serializers.ValidationError("Predicted hours must be greater than 0.")
        return value

    def validate_estimated_total_price(self, value):
        """
        Validate estimated total price is positive.
        """
        if value <= 0:
            raise serializers.ValidationError(
                "Estimated total price must be greater than 0."
            )
        return value

    def validate_attachments(self, value):
        """
        Validate attachment count does not exceed the limit.
        """
        if value and len(value) > MAX_JOB_APPLICATION_ATTACHMENTS:
            raise serializers.ValidationError(
                f"Cannot upload more than {MAX_JOB_APPLICATION_ATTACHMENTS} attachments."
            )
        return value

    def create(self, validated_data):
        """
        Create job application using the service.
        """
        from apps.jobs.services import job_application_service

        job = validated_data["job_id"]
        handyman = self.context["request"].user
        predicted_hours = validated_data["predicted_hours"]
        estimated_total_price = validated_data["estimated_total_price"]
        negotiation_reasoning = validated_data.get("negotiation_reasoning", "")
        materials_data = validated_data.get("materials", [])
        attachments = validated_data.get("attachments", [])

        application = job_application_service.apply_to_job(
            handyman=handyman,
            job=job,
            predicted_hours=predicted_hours,
            estimated_total_price=estimated_total_price,
            negotiation_reasoning=negotiation_reasoning,
            materials_data=materials_data,
            attachments=attachments,
        )
        return application


class JobApplicationUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating a job application.
    Only pending applications can be updated.
    All fields are optional for partial updates.
    """

    predicted_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    estimated_total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    negotiation_reasoning = serializers.CharField(required=False, allow_blank=True)
    materials = JobApplicationMaterialInputSerializer(many=True, required=False)
    attachments = AttachmentInputSerializer(
        many=True,
        required=False,
        help_text="New attachments to add to the application. "
        "Use indexed format: attachments[0].file, attachments[0].thumbnail, "
        "attachments[0].duration_seconds. For videos, thumbnail and duration_seconds are required.",
    )
    attachments_to_remove = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        help_text="List of attachment public_ids to remove",
    )

    def validate_predicted_hours(self, value):
        """
        Validate predicted hours is positive.
        """
        if value <= 0:
            raise serializers.ValidationError("Predicted hours must be greater than 0.")
        return value

    def validate_estimated_total_price(self, value):
        """
        Validate estimated total price is positive.
        """
        if value <= 0:
            raise serializers.ValidationError(
                "Estimated total price must be greater than 0."
            )
        return value

    def validate(self, data):
        """
        Validate total attachment count after add/remove operations.
        """
        instance = self.instance
        if instance:
            # Calculate final attachment count
            current_count = instance.attachments.count()
            to_remove = data.get("attachments_to_remove", [])
            to_add = data.get("attachments", [])

            # Only count valid removals (attachments that actually belong to this app)
            valid_removals = instance.attachments.filter(
                public_id__in=to_remove
            ).count()

            final_count = current_count - valid_removals + len(to_add)
            if final_count > MAX_JOB_APPLICATION_ATTACHMENTS:
                raise serializers.ValidationError(
                    {
                        "attachments": (
                            f"Total attachments would exceed the limit of "
                            f"{MAX_JOB_APPLICATION_ATTACHMENTS}. "
                            f"Current: {current_count}, "
                            f"removing: {valid_removals}, "
                            f"adding: {len(to_add)}."
                        )
                    }
                )
        return data

    def update(self, instance, validated_data):
        """
        Update job application using the service.
        """
        from apps.jobs.services import job_application_service

        handyman = self.context["request"].user
        predicted_hours = validated_data.get("predicted_hours")
        estimated_total_price = validated_data.get("estimated_total_price")
        negotiation_reasoning = validated_data.get("negotiation_reasoning")
        materials_data = validated_data.get("materials")
        attachments = validated_data.get("attachments")
        attachments_to_remove = validated_data.get("attachments_to_remove")

        application = job_application_service.update_application(
            handyman=handyman,
            application=instance,
            predicted_hours=predicted_hours,
            estimated_total_price=estimated_total_price,
            negotiation_reasoning=negotiation_reasoning,
            materials_data=materials_data,
            attachments=attachments,
            attachments_to_remove=attachments_to_remove,
        )
        return application


# Homeowner-specific serializers for viewing applications


class HandymanProfileSerializer(serializers.Serializer):
    """
    Serializer for handyman profile in application (read-only).
    """

    public_id = serializers.UUIDField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    avatar_url = serializers.CharField(read_only=True)
    rating = serializers.DecimalField(
        max_digits=3, decimal_places=2, coerce_to_string=False, read_only=True
    )
    review_count = serializers.IntegerField(read_only=True)
    hourly_rate = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False, read_only=True
    )


class HomeownerJobApplicationListSerializer(serializers.ModelSerializer):
    """
    Serializer for job applications seen by homeowner (read-only).
    Includes handyman profile information.
    """

    job = JobListSerializer(read_only=True)
    handyman_profile = serializers.SerializerMethodField()
    materials = JobApplicationMaterialSerializer(many=True, read_only=True)
    attachments = JobApplicationAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = JobApplication
        fields = [
            "public_id",
            "job",
            "handyman_profile",
            "status",
            "status_at",
            "predicted_hours",
            "estimated_total_price",
            "negotiation_reasoning",
            "materials",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_handyman_profile(self, obj):
        """
        Get handyman profile information.
        """
        if hasattr(obj.handyman, "handyman_profile"):
            profile = obj.handyman.handyman_profile
            return {
                "public_id": obj.handyman.public_id,
                "display_name": profile.display_name,
                "avatar_url": profile.avatar_url,
                "rating": profile.rating,
                "review_count": profile.review_count,
                "hourly_rate": profile.hourly_rate,
            }
        return None


class HomeownerJobApplicationDetailSerializer(HomeownerJobApplicationListSerializer):
    """
    Serializer for job application detail seen by homeowner (read-only).
    Same as list for now.
    """

    pass


# Response envelope serializers

JobApplicationListResponseSerializer = create_list_response_serializer(
    JobApplicationListSerializer, "JobApplicationListResponse"
)

JobApplicationDetailResponseSerializer = create_response_serializer(
    JobApplicationDetailSerializer, "JobApplicationDetailResponse"
)

HomeownerJobApplicationListResponseSerializer = create_list_response_serializer(
    HomeownerJobApplicationListSerializer, "HomeownerJobApplicationListResponse"
)

HomeownerJobApplicationDetailResponseSerializer = create_response_serializer(
    HomeownerJobApplicationDetailSerializer, "HomeownerJobApplicationDetailResponse"
)

HandymanJobDetailResponseSerializer = create_response_serializer(
    HandymanJobDetailSerializer, "HandymanJobDetailResponse"
)

HandymanForYouJobListResponseSerializer = create_list_response_serializer(
    HandymanForYouJobSerializer, "HandymanForYouJobListResponse"
)


# ========================
# Ongoing Job Serializers
# ========================


class WorkSessionMediaSerializer(serializers.ModelSerializer):
    """
    Serializer for work session media (read-only).
    """

    file = serializers.FileField(use_url=True)
    thumbnail = serializers.ImageField(use_url=True)

    class Meta:
        model = WorkSessionMedia
        fields = [
            "public_id",
            "media_type",
            "file",
            "thumbnail",
            "description",
            "created_at",
        ]
        read_only_fields = fields


class WorkSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for work sessions (read-only).
    """

    start_photo = serializers.ImageField(use_url=True)
    end_photo = serializers.ImageField(use_url=True, allow_null=True)
    media = WorkSessionMediaSerializer(many=True, read_only=True)
    duration_seconds = serializers.IntegerField(read_only=True)

    class Meta:
        model = WorkSession
        fields = [
            "public_id",
            "status",
            "started_at",
            "ended_at",
            "duration_seconds",
            "start_latitude",
            "start_longitude",
            "start_photo",
            "end_latitude",
            "end_longitude",
            "end_photo",
            "media",
        ]
        read_only_fields = fields


class JobDashboardActiveSessionSerializer(serializers.Serializer):
    """
    Serializer for active work session data in job dashboard.
    """

    public_id = serializers.UUIDField(help_text="Public ID of the active work session")
    started_at = serializers.DateTimeField(help_text="When the session was started")
    start_latitude = serializers.DecimalField(
        max_digits=12, decimal_places=9, help_text="Starting latitude"
    )
    start_longitude = serializers.DecimalField(
        max_digits=12, decimal_places=9, help_text="Starting longitude"
    )
    start_photo = serializers.ImageField(
        use_url=True, allow_null=True, help_text="Starting location photo URL"
    )
    start_accuracy = serializers.FloatField(
        allow_null=True, help_text="GPS accuracy at start location in meters"
    )
    current_duration_seconds = serializers.IntegerField(
        help_text="Current session duration in seconds"
    )
    current_duration_formatted = serializers.CharField(
        help_text="Current session duration formatted as HH:MM:SS"
    )
    media_count = serializers.IntegerField(
        help_text="Number of media files uploaded for this session"
    )
    media = WorkSessionMediaSerializer(
        many=True, help_text="List of media files uploaded for this session"
    )


class DailyReportTaskSerializer(serializers.ModelSerializer):
    """
    Serializer for tasks in a daily report (read-only).
    """

    task = JobTaskSerializer(read_only=True)

    class Meta:
        model = DailyReportTask
        fields = ["public_id", "task", "notes", "marked_complete"]
        read_only_fields = fields


class DailyReportSerializer(serializers.ModelSerializer):
    """
    Serializer for daily reports (read-only).
    """

    tasks_worked = DailyReportTaskSerializer(many=True, read_only=True)
    total_work_duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = DailyReport
        fields = [
            "public_id",
            "report_date",
            "summary",
            "status",
            "total_work_duration_seconds",
            "homeowner_comment",
            "reviewed_at",
            "review_deadline",
            "tasks_worked",
            "created_at",
        ]
        read_only_fields = fields

    def get_total_work_duration_seconds(self, obj):
        """Get total work duration in seconds."""
        if obj.total_work_duration:
            return int(obj.total_work_duration.total_seconds())
        return 0


class JobDisputeSerializer(serializers.ModelSerializer):
    """
    Serializer for job disputes (read-only).
    """

    disputed_reports = DailyReportSerializer(many=True, read_only=True)

    class Meta:
        model = JobDispute
        fields = [
            "public_id",
            "reason",
            "status",
            "admin_notes",
            "resolved_at",
            "refund_percentage",
            "resolution_deadline",
            "disputed_reports",
            "created_at",
        ]
        read_only_fields = fields


# ========================
# Ongoing Job Write Serializers
# ========================


class WorkSessionMediaCreateSerializer(serializers.Serializer):
    """
    Serializer for uploading media to a work session.
    """

    media_type = serializers.ChoiceField(
        choices=[("photo", "Photo"), ("video", "Video")],
        help_text="Type of media",
    )
    file = serializers.FileField(
        help_text="Media file (photo or video)",
    )
    file_size = serializers.IntegerField(
        help_text="File size in bytes",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional description of the media",
    )
    task_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Optional task this media is associated with",
    )
    duration_seconds = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Duration in seconds (required for video)",
    )

    def validate_task_id(self, value):
        """Validate task exists if provided."""
        if value is None:
            return None
        try:
            task = JobTask.objects.get(public_id=value)
            return task
        except JobTask.DoesNotExist:
            raise serializers.ValidationError("Invalid task.")

    def validate(self, attrs):
        """Cross-field validation."""
        media_type = attrs.get("media_type")
        duration_seconds = attrs.get("duration_seconds")

        if media_type == "video" and not duration_seconds:
            raise serializers.ValidationError(
                {"duration_seconds": "Duration is required for video uploads."}
            )

        return attrs


class DisputeCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a dispute.
    """

    reason = serializers.CharField(
        help_text="Reason for the dispute",
    )
    disputed_report_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        help_text="List of daily report public_ids to dispute",
    )

    def validate_disputed_report_ids(self, value):
        """Validate that all report IDs exist."""
        if not value:
            return []

        reports = []
        for report_id in value:
            try:
                report = DailyReport.objects.get(public_id=report_id)
                reports.append(report)
            except DailyReport.DoesNotExist:
                raise serializers.ValidationError(
                    f"Daily report with ID {report_id} not found."
                )
        return reports


class DisputeResolveSerializer(serializers.Serializer):
    """
    Serializer for resolving a dispute (admin only).
    """

    RESOLUTION_CHOICES = [
        ("resolved_full_refund", "Full Refund"),
        ("resolved_partial_refund", "Partial Refund"),
        ("resolved_pay_handyman", "Pay Handyman"),
    ]

    status = serializers.ChoiceField(
        choices=RESOLUTION_CHOICES,
        help_text="Resolution status",
    )
    admin_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Admin notes about the resolution",
    )
    refund_percentage = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=99,
        help_text="Refund percentage (required for partial refund, 1-99%)",
    )

    def validate(self, attrs):
        """Cross-field validation."""
        status = attrs.get("status")
        refund_percentage = attrs.get("refund_percentage")

        if status == "resolved_partial_refund":
            if refund_percentage is None:
                raise serializers.ValidationError(
                    {
                        "refund_percentage": "Refund percentage is required for partial refund resolution."
                    }
                )
        elif status == "resolved_full_refund":
            # Full refund is implicitly 100%
            attrs["refund_percentage"] = 100

        return attrs


# Response envelope serializers for ongoing job entities

WorkSessionListResponseSerializer = create_list_response_serializer(
    WorkSessionSerializer, "WorkSessionListResponse"
)

WorkSessionDetailResponseSerializer = create_response_serializer(
    WorkSessionSerializer, "WorkSessionDetailResponse"
)

DailyReportListResponseSerializer = create_list_response_serializer(
    DailyReportSerializer, "DailyReportListResponse"
)

DailyReportDetailResponseSerializer = create_response_serializer(
    DailyReportSerializer, "DailyReportDetailResponse"
)

JobDisputeListResponseSerializer = create_list_response_serializer(
    JobDisputeSerializer, "JobDisputeListResponse"
)

JobDisputeDetailResponseSerializer = create_response_serializer(
    JobDisputeSerializer, "JobDisputeDetailResponse"
)


# ========================
# Write Operation Serializers
# ========================


class WorkSessionStartSerializer(serializers.Serializer):
    """
    Serializer for starting a work session.
    """

    started_at = serializers.DateTimeField(
        help_text="Timestamp when work started",
    )
    start_latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        coerce_to_string=False,
        help_text="Latitude coordinate at start",
    )
    start_longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        coerce_to_string=False,
        help_text="Longitude coordinate at start",
    )
    start_accuracy = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        coerce_to_string=False,
        help_text="GPS accuracy in meters (optional)",
    )
    start_photo = serializers.ImageField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Photo taken at start of work (optional)",
    )

    def validate_start_latitude(self, value):
        """Validate latitude range."""
        if not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_start_longitude(self, value):
        """Validate longitude range."""
        if not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value


class WorkSessionStopSerializer(serializers.Serializer):
    """
    Serializer for stopping a work session.
    """

    ended_at = serializers.DateTimeField(
        help_text="Timestamp when work ended",
    )
    end_latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        coerce_to_string=False,
        help_text="Latitude coordinate at end",
    )
    end_longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        coerce_to_string=False,
        help_text="Longitude coordinate at end",
    )
    end_accuracy = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        coerce_to_string=False,
        help_text="GPS accuracy in meters (optional)",
    )
    end_photo = serializers.ImageField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Photo taken at end of work (optional)",
    )

    def validate_end_latitude(self, value):
        """Validate latitude range."""
        if not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_end_longitude(self, value):
        """Validate longitude range."""
        if not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value


class DailyReportTaskEntrySerializer(serializers.Serializer):
    """
    Serializer for a task entry in a daily report.
    """

    task_id = serializers.UUIDField(
        help_text="Public ID of the task",
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Notes about work done on this task",
    )
    marked_complete = serializers.BooleanField(
        default=False,
        help_text="Whether to mark the task as complete",
    )

    def validate_task_id(self, value):
        """Validate task exists."""
        try:
            task = JobTask.objects.get(public_id=value)
            return task
        except JobTask.DoesNotExist:
            raise serializers.ValidationError("Invalid task.")


class DailyReportCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a daily report.
    """

    report_date = serializers.DateField(
        help_text="Date of the report (YYYY-MM-DD)",
    )
    summary = serializers.CharField(
        help_text="Summary of work done today",
    )
    total_work_duration_seconds = serializers.IntegerField(
        min_value=0,
        help_text="Total work duration in seconds",
    )
    tasks = DailyReportTaskEntrySerializer(
        many=True,
        required=False,
        help_text="List of tasks worked on today",
    )


class DailyReportUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating a daily report.
    All fields are optional for partial updates.
    """

    summary = serializers.CharField(
        required=False,
        allow_blank=False,
        help_text="Summary of work done today",
    )
    total_work_duration_seconds = serializers.IntegerField(
        min_value=0,
        required=False,
        help_text="Total work duration in seconds",
    )
    tasks = DailyReportTaskEntrySerializer(
        many=True,
        required=False,
        help_text="List of tasks worked on today",
    )


class DailyReportReviewSerializer(serializers.Serializer):
    """
    Serializer for reviewing (accepting/rejecting) a daily report.
    """

    decision = serializers.ChoiceField(
        choices=[("approved", "Approved"), ("rejected", "Rejected")],
        help_text="Decision on the report",
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional comment from homeowner",
    )


class CompletionRejectSerializer(serializers.Serializer):
    """
    Serializer for rejecting job completion.
    """

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Reason for rejection",
    )


class JobTaskStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for updating job task status (handyman only).
    """

    is_completed = serializers.BooleanField(
        required=True,
        help_text="Set to true to mark task as completed, false to unmark.",
    )

    class Meta:
        model = JobTask
        fields = ["is_completed"]


# ========================
# Review Serializers
# ========================


class ReviewCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a review.
    """

    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        help_text="Rating from 1 to 5 stars",
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        default="",
        help_text="Optional review comment",
    )


class ReviewUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating a review.
    """

    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        help_text="Rating from 1 to 5 stars",
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        default="",
        help_text="Optional review comment",
    )


class ReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for the reviewer's own review.
    """

    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "public_id",
            "rating",
            "comment",
            "reviewer_type",
            "created_at",
            "updated_at",
            "can_edit",
        ]
        read_only_fields = fields

    def get_can_edit(self, obj):
        """Check if the review can still be edited (within 14-day window)."""
        from datetime import timedelta

        from django.utils import timezone

        if obj.job.completed_at is None:
            return False
        review_deadline = obj.job.completed_at + timedelta(days=14)
        return timezone.now() <= review_deadline


class ReviewDetailSerializer(serializers.ModelSerializer):
    """
    Review with reviewer info (for handyman viewing their received reviews).
    """

    reviewer_display_name = serializers.SerializerMethodField()
    reviewer_avatar_url = serializers.SerializerMethodField()
    job_title = serializers.CharField(source="job.title", read_only=True)
    job_public_id = serializers.UUIDField(source="job.public_id", read_only=True)

    class Meta:
        model = Review
        fields = [
            "public_id",
            "rating",
            "comment",
            "reviewer_display_name",
            "reviewer_avatar_url",
            "job_title",
            "job_public_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_reviewer_display_name(self, obj):
        """Get reviewer's display name."""
        if obj.reviewer_type == "homeowner":
            if hasattr(obj.reviewer, "homeowner_profile"):
                return obj.reviewer.homeowner_profile.display_name
        elif obj.reviewer_type == "handyman":
            if hasattr(obj.reviewer, "handyman_profile"):
                return obj.reviewer.handyman_profile.display_name
        return None

    def get_reviewer_avatar_url(self, obj):
        """Get reviewer's avatar URL."""
        if obj.reviewer_type == "homeowner":
            if hasattr(obj.reviewer, "homeowner_profile"):
                return obj.reviewer.homeowner_profile.avatar_url
        elif obj.reviewer_type == "handyman":
            if hasattr(obj.reviewer, "handyman_profile"):
                return obj.reviewer.handyman_profile.avatar_url
        return None


class HomeownerRatingSummarySerializer(serializers.Serializer):
    """
    For handyman to see homeowner's rating summary.
    """

    rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        allow_null=True,
        read_only=True,
    )
    review_count = serializers.IntegerField(read_only=True)


# Response serializers for reviews
ReviewResponseSerializer = create_response_serializer(
    ReviewSerializer, "ReviewResponse"
)
ReviewDetailResponseSerializer = create_response_serializer(
    ReviewDetailSerializer, "ReviewDetailResponse"
)
ReviewListResponseSerializer = create_list_response_serializer(
    ReviewDetailSerializer, "ReviewListResponse"
)


# ============================================================================
# Handyman Job Dashboard Serializers
# ============================================================================


class JobDashboardTaskSerializer(serializers.ModelSerializer):
    """
    Serializer for job task in dashboard with completion status.
    """

    class Meta:
        model = JobTask
        fields = [
            "public_id",
            "title",
            "description",
            "order",
            "is_completed",
            "completed_at",
        ]
        read_only_fields = fields


class JobDashboardTasksProgressSerializer(serializers.Serializer):
    """
    Serializer for task completion progress in job dashboard.
    """

    total_tasks = serializers.IntegerField(help_text="Total number of tasks in the job")
    completed_tasks = serializers.IntegerField(help_text="Number of completed tasks")
    pending_tasks = serializers.IntegerField(help_text="Number of pending tasks")
    completion_percentage = serializers.FloatField(
        help_text="Percentage of tasks completed (0-100)"
    )
    tasks = JobDashboardTaskSerializer(
        many=True, help_text="List of all tasks with their status"
    )


class JobDashboardTimeStatsSerializer(serializers.Serializer):
    """
    Serializer for time-related statistics in job dashboard.
    """

    total_time_seconds = serializers.IntegerField(
        help_text="Total time worked in seconds across all sessions"
    )
    total_time_formatted = serializers.CharField(
        help_text="Total time worked formatted as HH:MM:SS"
    )
    average_session_duration_seconds = serializers.IntegerField(
        allow_null=True,
        help_text="Average duration of work sessions in seconds",
    )
    average_session_duration_formatted = serializers.CharField(
        allow_null=True,
        help_text="Average session duration formatted as HH:MM:SS",
    )
    longest_session_seconds = serializers.IntegerField(
        allow_null=True,
        help_text="Duration of the longest session in seconds",
    )
    longest_session_formatted = serializers.CharField(
        allow_null=True,
        help_text="Longest session duration formatted as HH:MM:SS",
    )


class JobDashboardSessionStatsSerializer(serializers.Serializer):
    """
    Serializer for work session statistics in job dashboard.
    """

    total_sessions = serializers.IntegerField(help_text="Total number of work sessions")
    completed_sessions = serializers.IntegerField(
        help_text="Number of completed sessions"
    )
    in_progress_sessions = serializers.IntegerField(
        help_text="Number of sessions currently in progress (should be 0 or 1)"
    )
    has_active_session = serializers.BooleanField(
        help_text="Whether there is an active work session"
    )
    active_session_id = serializers.UUIDField(
        allow_null=True,
        help_text="Public ID of the active session if any",
    )


class JobDashboardReportStatsSerializer(serializers.Serializer):
    """
    Serializer for daily report statistics in job dashboard.
    """

    total_reports = serializers.IntegerField(
        help_text="Total number of daily reports submitted"
    )
    pending_reports = serializers.IntegerField(
        help_text="Number of reports pending review"
    )
    approved_reports = serializers.IntegerField(help_text="Number of approved reports")
    rejected_reports = serializers.IntegerField(help_text="Number of rejected reports")
    latest_report_date = serializers.DateField(
        allow_null=True,
        help_text="Date of the most recent report",
    )


class JobDashboardJobInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for basic job info in handyman dashboard.
    Includes nested homeowner info with rating.
    """

    category = JobCategorySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    estimated_budget = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False
    )
    homeowner = serializers.SerializerMethodField(
        help_text="Homeowner information including rating"
    )
    source = serializers.CharField(
        read_only=True,
        help_text="Source of the job: 'direct_offer' or 'application'",
    )
    source_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
        help_text="UUID of the job application if source is 'application', null if 'direct_offer'",
    )

    class Meta:
        model = Job
        fields = [
            "public_id",
            "title",
            "description",
            "status",
            "status_at",
            "estimated_budget",
            "category",
            "city",
            "address",
            "postal_code",
            "latitude",
            "longitude",
            "completion_requested_at",
            "completed_at",
            "homeowner",
            "source",
            "source_id",
            "created_at",
        ]
        read_only_fields = fields

    def get_homeowner(self, obj):
        """Get homeowner info with rating for dashboard."""
        if hasattr(obj.homeowner, "homeowner_profile"):
            profile = obj.homeowner.homeowner_profile
            return {
                "public_id": obj.homeowner.public_id,
                "display_name": profile.display_name,
                "avatar_url": profile.avatar_url,
                "rating": profile.rating,
            }
        return {
            "public_id": obj.homeowner.public_id,
            "display_name": None,
            "avatar_url": None,
            "rating": None,
        }


class JobDashboardReviewSerializer(serializers.Serializer):
    """
    Serializer for review data in job dashboard.
    Generic review serializer used for both homeowner and handyman reviews.
    """

    public_id = serializers.UUIDField(help_text="Public ID of the review")
    rating = serializers.IntegerField(help_text="Rating from 1 to 5 stars")
    comment = serializers.CharField(allow_blank=True, help_text="Review comment")
    created_at = serializers.DateTimeField(help_text="When the review was created")
    updated_at = serializers.DateTimeField(help_text="When the review was last updated")


class HandymanJobDashboardSerializer(serializers.Serializer):
    """
    Comprehensive serializer for handyman job dashboard.
    Aggregates job details, task progress, time stats, session info, and report stats.
    """

    job = JobDashboardJobInfoSerializer(help_text="Basic job information")
    tasks_progress = JobDashboardTasksProgressSerializer(
        help_text="Task completion progress"
    )
    time_stats = JobDashboardTimeStatsSerializer(help_text="Time-related statistics")
    session_stats = JobDashboardSessionStatsSerializer(
        help_text="Work session statistics"
    )
    active_session = JobDashboardActiveSessionSerializer(
        allow_null=True, help_text="Current active work session data"
    )
    report_stats = JobDashboardReportStatsSerializer(
        help_text="Daily report statistics"
    )
    homeowner_review = JobDashboardReviewSerializer(
        allow_null=True, help_text="Review from homeowner for handyman's work"
    )
    my_review = JobDashboardReviewSerializer(
        allow_null=True, help_text="Handyman's own review for the homeowner"
    )


# Response serializer for handyman job dashboard
HandymanJobDashboardResponseSerializer = create_response_serializer(
    HandymanJobDashboardSerializer, "HandymanJobDashboardResponse"
)


# ============================================================================
# Homeowner Job Dashboard Serializers
# ============================================================================


class HomeownerJobDashboardJobInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for basic job info in homeowner dashboard.
    Shows assigned handyman info with rating.
    """

    category = JobCategorySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    estimated_budget = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False
    )
    handyman = serializers.SerializerMethodField(
        help_text="Assigned handyman information including rating"
    )
    source = serializers.CharField(
        read_only=True,
        help_text="Source of the job: 'direct_offer' or 'application'",
    )
    source_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
        help_text="UUID of the job application if source is 'application', null if 'direct_offer'",
    )

    class Meta:
        model = Job
        fields = [
            "public_id",
            "title",
            "description",
            "status",
            "status_at",
            "estimated_budget",
            "category",
            "city",
            "address",
            "postal_code",
            "latitude",
            "longitude",
            "completion_requested_at",
            "completed_at",
            "handyman",
            "source",
            "source_id",
            "created_at",
        ]
        read_only_fields = fields

    def get_handyman(self, obj):
        """Get assigned handyman info with rating for dashboard."""
        if obj.assigned_handyman and hasattr(obj.assigned_handyman, "handyman_profile"):
            profile = obj.assigned_handyman.handyman_profile
            return {
                "public_id": obj.assigned_handyman.public_id,
                "display_name": profile.display_name,
                "avatar_url": profile.avatar_url,
                "rating": profile.rating,
            }
        return None


class HomeownerJobDashboardSerializer(serializers.Serializer):
    """
    Comprehensive serializer for homeowner job dashboard.
    Aggregates job details, task progress, time stats, session info, and report stats.
    """

    job = HomeownerJobDashboardJobInfoSerializer(help_text="Basic job information")
    tasks_progress = JobDashboardTasksProgressSerializer(
        help_text="Task completion progress"
    )
    time_stats = JobDashboardTimeStatsSerializer(help_text="Time-related statistics")
    session_stats = JobDashboardSessionStatsSerializer(
        help_text="Work session statistics"
    )
    active_session = JobDashboardActiveSessionSerializer(
        allow_null=True, help_text="Current active work session data"
    )
    report_stats = JobDashboardReportStatsSerializer(
        help_text="Daily report statistics"
    )
    my_review = JobDashboardReviewSerializer(
        allow_null=True, help_text="Homeowner's own review for the handyman"
    )


# Response serializer for homeowner job dashboard
HomeownerJobDashboardResponseSerializer = create_response_serializer(
    HomeownerJobDashboardSerializer, "HomeownerJobDashboardResponse"
)


# ========================
# Job Reimbursement Serializers
# ========================


class JobReimbursementCategorySerializer(serializers.ModelSerializer):
    """Serializer for job reimbursement category (read-only)."""

    class Meta:
        from apps.jobs.models import JobReimbursementCategory

        model = JobReimbursementCategory
        fields = ["public_id", "name", "slug", "description", "icon"]
        read_only_fields = fields


class JobReimbursementAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for reimbursement attachment (read-only)."""

    file_url = serializers.SerializerMethodField(help_text="Full URL of the file")
    thumbnail_url = serializers.SerializerMethodField(
        help_text="Thumbnail URL (video thumbnail or image itself)"
    )

    class Meta:
        from apps.jobs.models import JobReimbursementAttachment

        model = JobReimbursementAttachment
        fields = [
            "public_id",
            "file_url",
            "file_type",
            "file_name",
            "file_size",
            "thumbnail_url",
            "duration_seconds",
            "created_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        """Get the full file URL."""
        return obj.file_url

    def get_thumbnail_url(self, obj):
        """Get the thumbnail URL."""
        return obj.thumbnail_url


class JobReimbursementSerializer(serializers.ModelSerializer):
    """Serializer for job reimbursement (read-only)."""

    from apps.jobs.models import JobReimbursement

    category = JobReimbursementCategorySerializer(read_only=True)
    attachments = JobReimbursementAttachmentSerializer(many=True, read_only=True)

    class Meta:
        from apps.jobs.models import JobReimbursement

        model = JobReimbursement
        fields = [
            "public_id",
            "name",
            "category",
            "amount",
            "notes",
            "status",
            "homeowner_comment",
            "reviewed_at",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class JobReimbursementCreateSerializer(serializers.Serializer):
    """Serializer for creating a reimbursement (handyman)."""

    name = serializers.CharField(max_length=255)
    category_id = serializers.UUIDField(help_text="Category public_id")
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    attachments = AttachmentInputSerializer(
        many=True,
        help_text="At least one attachment required. "
        "Use indexed format: attachments[0].file, attachments[0].thumbnail, "
        "attachments[0].duration_seconds. For videos, thumbnail and duration_seconds are required.",
    )

    def validate_attachments(self, value):
        """Ensure at least one attachment is provided and doesn't exceed limit."""
        if not value or len(value) == 0:
            raise serializers.ValidationError("At least one attachment is required.")
        if len(value) > MAX_REIMBURSEMENT_ATTACHMENTS:
            raise serializers.ValidationError(
                f"Cannot upload more than {MAX_REIMBURSEMENT_ATTACHMENTS} attachments."
            )
        return value

    def validate_category_id(self, value):
        """Validate category exists and is active."""
        from apps.jobs.models import JobReimbursementCategory

        try:
            category = JobReimbursementCategory.objects.get(public_id=value)
            if not category.is_active:
                raise serializers.ValidationError("Selected category is not active.")
            return category
        except JobReimbursementCategory.DoesNotExist:
            raise serializers.ValidationError("Invalid category.")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value


class JobReimbursementUpdateSerializer(serializers.Serializer):
    """Serializer for updating a reimbursement (handyman). All fields optional."""

    name = serializers.CharField(max_length=255, required=False)
    category_id = serializers.UUIDField(required=False, help_text="Category public_id")
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    attachments = AttachmentInputSerializer(
        many=True,
        required=False,
        help_text="New attachments to add (existing ones are preserved). "
        "Use indexed format: attachments[0].file, attachments[0].thumbnail, "
        "attachments[0].duration_seconds. For videos, thumbnail and duration_seconds are required.",
    )
    attachments_to_remove = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of attachment public_ids to remove",
    )

    def validate_category_id(self, value):
        """Validate category exists and is active."""
        from apps.jobs.models import JobReimbursementCategory

        try:
            category = JobReimbursementCategory.objects.get(public_id=value)
            if not category.is_active:
                raise serializers.ValidationError("Selected category is not active.")
            return category
        except JobReimbursementCategory.DoesNotExist:
            raise serializers.ValidationError("Invalid category.")

    def validate_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value

    def validate(self, data):
        """
        Validate total attachment count after add/remove operations.
        Also ensure at least one attachment remains.
        """
        instance = self.instance
        if instance:
            # Calculate final attachment count
            current_count = instance.attachments.count()
            to_remove = data.get("attachments_to_remove", [])
            to_add = data.get("attachments", [])

            # Only count valid removals (attachments that actually belong to this reimbursement)
            valid_removals = instance.attachments.filter(
                public_id__in=to_remove
            ).count()

            final_count = current_count - valid_removals + len(to_add)

            # Check minimum (at least one attachment required)
            if final_count < 1:
                raise serializers.ValidationError(
                    {"attachments": "At least one attachment is required."}
                )

            # Check maximum
            if final_count > MAX_REIMBURSEMENT_ATTACHMENTS:
                raise serializers.ValidationError(
                    {
                        "attachments": (
                            f"Total attachments would exceed the limit of "
                            f"{MAX_REIMBURSEMENT_ATTACHMENTS}. "
                            f"Current: {current_count}, "
                            f"removing: {valid_removals}, "
                            f"adding: {len(to_add)}."
                        )
                    }
                )
        return data


class JobReimbursementReviewSerializer(serializers.Serializer):
    """Serializer for reviewing (approve/reject) a reimbursement (homeowner)."""

    decision = serializers.ChoiceField(
        choices=[("approved", "Approved"), ("rejected", "Rejected")],
    )
    comment = serializers.CharField(required=False, allow_blank=True, default="")


# Response serializers for reimbursement category
JobReimbursementCategoryListResponseSerializer = create_list_response_serializer(
    JobReimbursementCategorySerializer, "JobReimbursementCategoryListResponse"
)

# Response serializers for reimbursement
JobReimbursementListResponseSerializer = create_list_response_serializer(
    JobReimbursementSerializer, "JobReimbursementListResponse"
)

JobReimbursementDetailResponseSerializer = create_response_serializer(
    JobReimbursementSerializer, "JobReimbursementDetailResponse"
)


# ========================
# Direct Offer Serializers
# ========================


class TargetHandymanInfoSerializer(serializers.Serializer):
    """
    Nested serializer for target handyman info in direct offers.
    """

    public_id = serializers.UUIDField(help_text="Handyman's public ID")
    display_name = serializers.CharField(
        allow_null=True, help_text="Handyman's display name"
    )
    avatar_url = serializers.URLField(
        allow_null=True, help_text="Handyman's avatar URL"
    )
    rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        allow_null=True,
        coerce_to_string=False,
        help_text="Handyman's rating (1-5)",
    )
    review_count = serializers.IntegerField(help_text="Number of reviews received")
    job_title = serializers.CharField(allow_null=True, help_text="Handyman's job title")


class DirectOfferCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a direct job offer (write-only).
    Similar to JobCreateSerializer but with target_handyman field.
    """

    target_handyman_id = serializers.UUIDField(
        required=True,
        help_text="Target handyman's public_id to send the offer to",
    )
    title = serializers.CharField(
        max_length=200,
        required=True,
        help_text="Job title",
    )
    description = serializers.CharField(
        required=True,
        help_text="Job description",
    )
    estimated_budget = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        coerce_to_string=False,
        help_text="Budget homeowner is willing to pay",
    )
    category_id = serializers.UUIDField(
        required=True,
        help_text="Category public_id",
    )
    city_id = serializers.UUIDField(
        required=True,
        help_text="City public_id",
    )
    address = serializers.CharField(
        required=True,
        help_text="Street address",
    )
    postal_code = serializers.CharField(
        max_length=12,
        required=False,
        allow_blank=True,
        help_text="Postal code (international formats supported, e.g., A1A 1A1, 12345, SW1A 1AA)",
    )
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        coerce_to_string=False,
        help_text="Latitude coordinate (optional, must provide both lat/lng)",
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        coerce_to_string=False,
        help_text="Longitude coordinate (optional, must provide both lat/lng)",
    )
    offer_expires_in_days = serializers.IntegerField(
        required=False,
        default=7,
        min_value=1,
        max_value=30,
        help_text="Days until offer expires (default: 7, min: 1, max: 30)",
    )
    attachments = AttachmentInputSerializer(
        many=True,
        required=False,
        help_text=f"Job attachments (max {MAX_JOB_ATTACHMENTS} files). "
        "Use indexed format: attachments[0].file, attachments[0].thumbnail, "
        "attachments[0].duration_seconds. For videos, thumbnail and duration_seconds are required.",
    )
    tasks = serializers.ListField(
        child=JobTaskInputSerializer(),
        required=False,
        allow_empty=True,
        max_length=MAX_JOB_ITEMS,
        help_text=f"List of tasks to be done (max {MAX_JOB_ITEMS} tasks)",
    )

    def validate_estimated_budget(self, value):
        """Validate budget is positive."""
        if value <= Decimal("0"):
            raise serializers.ValidationError("Budget must be greater than 0.")
        return value

    def validate_target_handyman_id(self, value):
        """Validate target handyman exists and has handyman role."""
        from apps.accounts.models import User

        try:
            user = User.objects.get(public_id=value)
            if not user.has_role("handyman"):
                raise serializers.ValidationError("Target user is not a handyman.")
            if not hasattr(user, "handyman_profile"):
                raise serializers.ValidationError(
                    "Target handyman has not completed their profile."
                )
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError("Target handyman not found.")

    def validate_category_id(self, value):
        """Validate category exists and is active."""
        try:
            category = JobCategory.objects.get(public_id=value)
            if not category.is_active:
                raise serializers.ValidationError("Selected category is not active.")
            return category
        except JobCategory.DoesNotExist:
            raise serializers.ValidationError("Invalid category.")

    def validate_city_id(self, value):
        """Validate city exists and is active."""
        try:
            city = City.objects.get(public_id=value)
            if not city.is_active:
                raise serializers.ValidationError("Selected city is not active.")
            return city
        except City.DoesNotExist:
            raise serializers.ValidationError("Invalid city.")

    def validate_attachments(self, value):
        """Validate attachments list count."""
        if not value:
            return []

        if len(value) > MAX_JOB_ATTACHMENTS:
            raise serializers.ValidationError(
                f"Maximum {MAX_JOB_ATTACHMENTS} attachments allowed."
            )

        return value

    def validate_tasks(self, value):
        """Validate and clean tasks."""
        if not value:
            return []

        # Filter out tasks with empty titles after stripping whitespace
        cleaned_tasks = []
        for task in value:
            title = task.get("title", "").strip()
            if title:
                cleaned_tasks.append(
                    {"title": title, "description": task.get("description", "")}
                )

        return cleaned_tasks

    def validate_postal_code(self, value):
        """Validate international postal code format.

        Supports various international formats including:
        - Canada: A1A 1A1
        - USA: 12345 or 12345-6789
        - UK: SW1A 1AA
        - Indonesia: 12345
        - Germany: 10115
        - Japan: 100-0001
        - And many more
        """
        if value:
            import re

            # Strip leading/trailing whitespace and convert to uppercase
            cleaned = value.strip().upper()

            # Check minimum and maximum length (3-12 characters)
            if len(cleaned) < 3 or len(cleaned) > 12:
                raise serializers.ValidationError(
                    "Postal code must be between 3 and 12 characters."
                )

            # International postal code pattern:
            # - Must start and end with alphanumeric
            # - Can contain letters, numbers, spaces, and hyphens
            pattern = r"^[A-Z0-9][A-Z0-9\s\-]*[A-Z0-9]$|^[A-Z0-9]{1,2}$"
            if not re.match(pattern, cleaned):
                raise serializers.ValidationError(
                    "Invalid postal code format. Only letters, numbers, spaces, "
                    "and hyphens are allowed."
                )

            # Normalize: collapse multiple spaces into single space
            cleaned = " ".join(cleaned.split())

            return cleaned
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        latitude = attrs.get("latitude")
        longitude = attrs.get("longitude")

        # If one coordinate is provided, both must be provided
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                "Both latitude and longitude must be provided together."
            )

        # Validate coordinate ranges
        if latitude is not None:
            if not (-90 <= latitude <= 90):
                raise serializers.ValidationError(
                    {"latitude": "Latitude must be between -90 and 90."}
                )
        if longitude is not None:
            if not (-180 <= longitude <= 180):
                raise serializers.ValidationError(
                    {"longitude": "Longitude must be between -180 and 180."}
                )

        # Validate homeowner cannot send offer to themselves
        request = self.context.get("request")
        target_handyman = attrs.get("target_handyman_id")
        if request and target_handyman and request.user == target_handyman:
            raise serializers.ValidationError(
                {"target_handyman_id": "You cannot send a direct offer to yourself."}
            )

        return attrs


class DirectOfferListSerializer(serializers.ModelSerializer):
    """
    Serializer for direct offer listing (read-only).
    Used for homeowner's list of sent offers.
    """

    category = JobCategorySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    estimated_budget = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False
    )
    target_handyman = serializers.SerializerMethodField(
        help_text="Target handyman information"
    )
    time_remaining = serializers.SerializerMethodField(
        help_text="Time remaining until offer expires (in seconds, null if expired/responded)"
    )

    class Meta:
        model = Job
        fields = [
            "public_id",
            "title",
            "description",
            "estimated_budget",
            "category",
            "city",
            "address",
            "offer_status",
            "offer_expires_at",
            "offer_responded_at",
            "time_remaining",
            "target_handyman",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_target_handyman(self, obj):
        """Get target handyman info."""
        if obj.target_handyman and hasattr(obj.target_handyman, "handyman_profile"):
            profile = obj.target_handyman.handyman_profile
            return {
                "public_id": obj.target_handyman.public_id,
                "display_name": profile.display_name,
                "avatar_url": profile.avatar_url,
                "rating": profile.rating,
                "review_count": profile.review_count,
                "job_title": profile.job_title,
            }
        return None

    def get_time_remaining(self, obj):
        """Get time remaining in seconds until offer expires."""
        from django.utils import timezone

        if obj.offer_status != "pending" or not obj.offer_expires_at:
            return None

        remaining = obj.offer_expires_at - timezone.now()
        if remaining.total_seconds() <= 0:
            return 0

        return int(remaining.total_seconds())


class DirectOfferDetailSerializer(DirectOfferListSerializer):
    """
    Serializer for direct offer detail (read-only).
    Includes tasks and attachments.
    """

    attachments = JobAttachmentSerializer(many=True, read_only=True)
    tasks = JobTaskListSerializer(many=True, read_only=True)

    class Meta(DirectOfferListSerializer.Meta):
        fields = DirectOfferListSerializer.Meta.fields + [
            "postal_code",
            "latitude",
            "longitude",
            "tasks",
            "attachments",
            "offer_rejection_reason",
        ]


class HandymanDirectOfferListSerializer(serializers.ModelSerializer):
    """
    Serializer for direct offers received by handyman (read-only).
    """

    category = JobCategorySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    estimated_budget = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False
    )
    homeowner = serializers.SerializerMethodField(help_text="Homeowner information")
    time_remaining = serializers.SerializerMethodField(
        help_text="Time remaining until offer expires (in seconds, null if expired/responded)"
    )

    class Meta:
        model = Job
        fields = [
            "public_id",
            "title",
            "description",
            "estimated_budget",
            "category",
            "city",
            "address",
            "offer_status",
            "offer_expires_at",
            "time_remaining",
            "homeowner",
            "created_at",
        ]
        read_only_fields = fields

    def get_homeowner(self, obj):
        """Get homeowner info with rating."""
        if hasattr(obj.homeowner, "homeowner_profile"):
            profile = obj.homeowner.homeowner_profile
            return {
                "public_id": obj.homeowner.public_id,
                "display_name": profile.display_name,
                "avatar_url": profile.avatar_url,
                "rating": profile.rating,
                "review_count": profile.review_count,
            }
        return {
            "public_id": obj.homeowner.public_id,
            "display_name": None,
            "avatar_url": None,
            "rating": None,
            "review_count": 0,
        }

    def get_time_remaining(self, obj):
        """Get time remaining in seconds until offer expires."""
        from django.utils import timezone

        if obj.offer_status != "pending" or not obj.offer_expires_at:
            return None

        remaining = obj.offer_expires_at - timezone.now()
        if remaining.total_seconds() <= 0:
            return 0

        return int(remaining.total_seconds())


class HandymanDirectOfferDetailSerializer(HandymanDirectOfferListSerializer):
    """
    Serializer for direct offer detail for handyman (read-only).
    Includes tasks and attachments.
    """

    attachments = JobAttachmentSerializer(many=True, read_only=True)
    tasks = JobTaskListSerializer(many=True, read_only=True)

    class Meta(HandymanDirectOfferListSerializer.Meta):
        fields = HandymanDirectOfferListSerializer.Meta.fields + [
            "postal_code",
            "latitude",
            "longitude",
            "tasks",
            "attachments",
        ]


class DirectOfferRejectSerializer(serializers.Serializer):
    """
    Serializer for rejecting a direct offer (handyman).
    """

    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Optional reason for declining the offer",
    )


# Response serializers for direct offers
DirectOfferListResponseSerializer = create_list_response_serializer(
    DirectOfferListSerializer, "DirectOfferListResponse"
)

DirectOfferDetailResponseSerializer = create_response_serializer(
    DirectOfferDetailSerializer, "DirectOfferDetailResponse"
)

HandymanDirectOfferListResponseSerializer = create_list_response_serializer(
    HandymanDirectOfferListSerializer, "HandymanDirectOfferListResponse"
)

HandymanDirectOfferDetailResponseSerializer = create_response_serializer(
    HandymanDirectOfferDetailSerializer, "HandymanDirectOfferDetailResponse"
)


# ========================
# Handyman Assigned Jobs Serializers
# ========================


class HandymanAssignedJobListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing jobs assigned to a handyman.
    Shows jobs that the handyman has been approved to work on.
    """

    category = JobCategorySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    attachments = JobAttachmentSerializer(many=True, read_only=True)
    estimated_budget = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False
    )
    tasks = JobTaskListSerializer(many=True, read_only=True)
    homeowner = serializers.SerializerMethodField(
        help_text="Homeowner information with rating"
    )
    task_progress = serializers.SerializerMethodField(
        help_text="Task completion progress summary"
    )

    class Meta:
        model = Job
        fields = [
            "public_id",
            "title",
            "description",
            "estimated_budget",
            "category",
            "city",
            "address",
            "postal_code",
            "latitude",
            "longitude",
            "status",
            "status_at",
            "tasks",
            "attachments",
            "homeowner",
            "task_progress",
            "completion_requested_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_homeowner(self, obj):
        """Get homeowner info with rating."""
        if hasattr(obj.homeowner, "homeowner_profile"):
            profile = obj.homeowner.homeowner_profile
            return {
                "public_id": obj.homeowner.public_id,
                "display_name": profile.display_name,
                "avatar_url": profile.avatar_url,
                "rating": profile.rating,
                "review_count": profile.review_count,
            }
        return {
            "public_id": obj.homeowner.public_id,
            "display_name": None,
            "avatar_url": None,
            "rating": None,
            "review_count": 0,
        }

    def get_task_progress(self, obj):
        """Get task completion progress."""
        # Use prefetched tasks if available
        tasks = obj.tasks.all()
        total = len(tasks)
        completed = sum(1 for t in tasks if t.is_completed)
        return {
            "total": total,
            "completed": completed,
            "percentage": round((completed / total * 100), 1) if total > 0 else 0,
        }


# Response serializer for handyman assigned jobs
HandymanAssignedJobListResponseSerializer = create_list_response_serializer(
    HandymanAssignedJobListSerializer, "HandymanAssignedJobListResponse"
)
