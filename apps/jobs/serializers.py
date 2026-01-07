import re
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.common.serializers import (
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
    JobCategory,
    JobDispute,
    JobImage,
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


class JobImageSerializer(serializers.ModelSerializer):
    """
    Serializer for job image (read-only).
    """

    image = serializers.ImageField(use_url=True)

    class Meta:
        model = JobImage
        fields = ["public_id", "image", "order"]
        read_only_fields = fields


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


class JobListSerializer(serializers.ModelSerializer):
    """
    Serializer for job listing (read-only).
    """

    category = JobCategorySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    images = JobImageSerializer(many=True, read_only=True)
    estimated_budget = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False
    )
    tasks = JobTaskListSerializer(many=True, read_only=True)
    applicant_count = serializers.SerializerMethodField(
        help_text="Total number of job applications for this job"
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
            "images",
            "applicant_count",
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

    class Meta(ForYouJobSerializer.Meta):
        fields = ForYouJobSerializer.Meta.fields + [
            "homeowner_rating",
            "homeowner_review_count",
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


class HandymanJobDetailSerializer(JobDetailSerializer):
    """
    Job detail serializer for handyman - includes application status and homeowner rating.
    """

    has_applied = serializers.SerializerMethodField()
    my_application = serializers.SerializerMethodField()
    homeowner_rating = serializers.SerializerMethodField()
    homeowner_review_count = serializers.SerializerMethodField()

    class Meta(JobDetailSerializer.Meta):
        fields = JobDetailSerializer.Meta.fields + [
            "has_applied",
            "my_application",
            "homeowner_rating",
            "homeowner_review_count",
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
        max_length=7,
        required=False,
        allow_blank=True,
        help_text="Postal code (e.g., A1A 1A1)",
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
    images = serializers.ListField(
        child=serializers.ImageField(use_url=True),
        required=False,
        allow_empty=True,
        max_length=10,
        help_text="Job images (max 10 files, each max 5MB, JPEG/PNG only)",
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

    def validate_images(self, value):
        """Validate images."""
        if value and len(value) > 10:
            raise serializers.ValidationError("Maximum 10 images allowed.")

        # Validate each image
        for image in value:
            # Check file size (max 5MB)
            if image.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    f"Image '{image.name}' exceeds maximum size of 5MB."
                )

            # Check file type
            allowed_types = ["image/jpeg", "image/jpg", "image/png"]
            if (
                hasattr(image, "content_type")
                and image.content_type not in allowed_types
            ):
                raise serializers.ValidationError(
                    f"Image '{image.name}' must be a JPEG or PNG file."
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
        """Validate Canadian postal code format."""
        if value:
            # Remove spaces and convert to uppercase
            cleaned = value.replace(" ", "").upper()
            # Canadian postal code format: A1A1A1 (letter-number-letter-number-letter-number)
            if len(cleaned) != 6:
                raise serializers.ValidationError(
                    "Postal code must be 6 characters (e.g., A1A 1A1)."
                )
            # Check format: letter-number-letter-number-letter-number
            pattern = r"^[A-Z]\d[A-Z]\d[A-Z]\d$"
            if not re.match(pattern, cleaned):
                raise serializers.ValidationError(
                    "Invalid postal code format. Must be like A1A 1A1."
                )
            # Return formatted value with space
            return f"{cleaned[:3]} {cleaned[3:]}"
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
        """Create job with images and tasks."""
        # Extract category and city (already validated)
        category = validated_data.pop("category_id")
        city = validated_data.pop("city_id")
        images = validated_data.pop("images", [])
        tasks = validated_data.pop("tasks", [])

        # Get homeowner from context
        homeowner = self.context["request"].user

        # Create job, images, and tasks in a transaction
        with transaction.atomic():
            job = Job.objects.create(
                homeowner=homeowner,
                category=category,
                city=city,
                **validated_data,
            )

            # Create job images
            for idx, image_file in enumerate(images):
                JobImage.objects.create(job=job, image=image_file, order=idx)

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
        max_length=7,
        required=False,
        allow_blank=True,
        help_text="Postal code (e.g., A1A 1A1)",
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

    images = serializers.ListField(
        child=serializers.ImageField(use_url=True),
        required=False,
        allow_empty=True,
        max_length=10,
        help_text="New images to add (max 10 total images allowed)",
    )
    images_to_remove = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        help_text="List of image public_ids to remove",
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
        """Validate Canadian postal code format."""
        if value:
            # Remove spaces and convert to uppercase
            cleaned = value.replace(" ", "").upper()
            # Canadian postal code format: A1A1A1
            if len(cleaned) != 6:
                raise serializers.ValidationError(
                    "Postal code must be 6 characters (e.g., A1A 1A1)."
                )
            # Check format: letter-number-letter-number-letter-number
            pattern = r"^[A-Z]\d[A-Z]\d[A-Z]\d$"
            if not re.match(pattern, cleaned):
                raise serializers.ValidationError(
                    "Invalid postal code format. Must be like A1A 1A1."
                )
            # Return formatted value with space
            return f"{cleaned[:3]} {cleaned[3:]}"
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

    def validate_images(self, value):
        """Validate images."""
        # Validate each image
        for image in value:
            # Check file size (max 5MB)
            if image.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    f"Image '{image.name}' exceeds maximum size of 5MB."
                )

            # Check file type
            allowed_types = ["image/jpeg", "image/jpg", "image/png"]
            if (
                hasattr(image, "content_type")
                and image.content_type not in allowed_types
            ):
                raise serializers.ValidationError(
                    f"Image '{image.name}' must be a JPEG or PNG file."
                )

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

        # Validate total image count after add/remove
        images = attrs.get("images", [])
        images_to_remove = attrs.get("images_to_remove", [])

        if images or images_to_remove:
            current_count = instance.images.count() if instance else 0
            removed_count = (
                instance.images.filter(public_id__in=images_to_remove).count()
                if instance and images_to_remove
                else 0
            )
            new_total = current_count - removed_count + len(images)

            if new_total > 10:
                raise serializers.ValidationError(
                    {
                        "images": f"Maximum 10 images allowed. You have {current_count} images, "
                        f"removing {removed_count}, adding {len(images)} would result in {new_total}."
                    }
                )

        return attrs

    def update(self, instance, validated_data):
        """Update job fields, images, and tasks."""
        # Handle category if provided
        if "category_id" in validated_data:
            instance.category = validated_data.pop("category_id")

        # Handle city if provided
        if "city_id" in validated_data:
            instance.city = validated_data.pop("city_id")

        # Handle images
        images = validated_data.pop("images", [])
        images_to_remove = validated_data.pop("images_to_remove", [])

        # Handle tasks (replace all if provided)
        tasks = validated_data.pop("tasks", None)

        # Wrap all operations in a transaction for data integrity
        with transaction.atomic():
            # Delete removed images
            if images_to_remove:
                JobImage.objects.filter(
                    job=instance, public_id__in=images_to_remove
                ).delete()

            # Add new images
            if images:
                from django.db.models import Max

                # Calculate start order
                current_max_order = (
                    instance.images.aggregate(Max("order"))["order__max"]
                    if instance.images.exists()
                    else -1
                )

                start_order = current_max_order + 1

                for idx, image_file in enumerate(images):
                    JobImage.objects.create(
                        job=instance, image=image_file, order=start_order + idx
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


class JobApplicationCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a job application.
    """

    job_id = serializers.UUIDField(required=True)

    def validate_job_id(self, value):
        """
        Validate that job exists and is open.
        """
        try:
            job = Job.objects.get(public_id=value)
            return job
        except Job.DoesNotExist:
            raise serializers.ValidationError("Invalid job.")

    def create(self, validated_data):
        """
        Create job application using the service.
        """
        from apps.jobs.services import job_application_service

        job = validated_data["job_id"]
        handyman = self.context["request"].user

        application = job_application_service.apply_to_job(handyman=handyman, job=job)
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

    class Meta:
        model = JobApplication
        fields = [
            "public_id",
            "job",
            "handyman_profile",
            "status",
            "status_at",
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
            return HandymanProfileSerializer(profile).data
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
        help_text="Photo taken at start of work",
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
        help_text="Photo taken at end of work",
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
    Serializer for basic job info in dashboard.
    """

    category = JobCategorySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    estimated_budget = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False
    )
    homeowner_display_name = serializers.SerializerMethodField()
    homeowner_avatar_url = serializers.SerializerMethodField()

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
            "homeowner_display_name",
            "homeowner_avatar_url",
            "created_at",
        ]
        read_only_fields = fields

    def get_homeowner_display_name(self, obj):
        """Get homeowner's display name."""
        if hasattr(obj.homeowner, "homeowner_profile"):
            return obj.homeowner.homeowner_profile.display_name
        return None

    def get_homeowner_avatar_url(self, obj):
        """Get homeowner's avatar URL."""
        if hasattr(obj.homeowner, "homeowner_profile"):
            return obj.homeowner.homeowner_profile.avatar_url
        return None


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
    Shows assigned handyman info instead of homeowner info.
    """

    category = JobCategorySerializer(read_only=True)
    city = CitySerializer(read_only=True)
    estimated_budget = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False
    )
    handyman_display_name = serializers.SerializerMethodField()
    handyman_avatar_url = serializers.SerializerMethodField()

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
            "handyman_display_name",
            "handyman_avatar_url",
            "created_at",
        ]
        read_only_fields = fields

    def get_handyman_display_name(self, obj):
        """Get assigned handyman's display name."""
        if obj.assigned_handyman and hasattr(obj.assigned_handyman, "handyman_profile"):
            return obj.assigned_handyman.handyman_profile.display_name
        return None

    def get_handyman_avatar_url(self, obj):
        """Get assigned handyman's avatar URL."""
        if obj.assigned_handyman and hasattr(obj.assigned_handyman, "handyman_profile"):
            return obj.assigned_handyman.handyman_profile.avatar_url
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
