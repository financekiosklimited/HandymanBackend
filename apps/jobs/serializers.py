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
    Job,
    JobCategory,
    JobImage,
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


class JobImageSerializer(serializers.ModelSerializer):
    """
    Serializer for job image (read-only).
    """

    image = serializers.ImageField(use_url=True)

    class Meta:
        model = JobImage
        fields = ["public_id", "image", "order"]
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
            "job_items",
            "images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class JobDetailSerializer(JobListSerializer):
    """
    Serializer for job detail (read-only).
    Same as JobListSerializer for now.
    """

    pass


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
    job_items = serializers.ListField(
        child=serializers.CharField(max_length=MAX_JOB_ITEM_LENGTH, allow_blank=True),
        required=False,
        allow_empty=True,
        max_length=MAX_JOB_ITEMS,
        help_text=f"List of tasks/items to be done (max {MAX_JOB_ITEMS} items, {MAX_JOB_ITEM_LENGTH} chars each)",
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

    def validate_job_items(self, value):
        """Validate and clean job items."""
        if not value:
            return []

        # Strip whitespace and filter out empty strings
        cleaned_items = [item.strip() for item in value if item and item.strip()]

        return cleaned_items

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
        """Create job with images."""
        # Extract category and city (already validated)
        category = validated_data.pop("category_id")
        city = validated_data.pop("city_id")
        images = validated_data.pop("images", [])

        # Get homeowner from context
        homeowner = self.context["request"].user

        # Create job and images in a transaction
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

        return job


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
