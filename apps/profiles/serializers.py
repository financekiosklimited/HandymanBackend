"""
Serializers for profile endpoints.
"""

from rest_framework import serializers

from apps.common.serializers import (
    create_list_response_serializer,
    create_response_serializer,
)
from apps.profiles.models import HandymanCategory, HandymanProfile, HomeownerProfile


class HandymanCategorySerializer(serializers.ModelSerializer):
    """Serializer for handyman categories."""

    class Meta:
        model = HandymanCategory
        fields = ["public_id", "name"]


class HomeownerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for homeowner profile.
    """

    is_phone_verified = serializers.BooleanField(read_only=True)
    avatar_url = serializers.URLField(read_only=True, allow_null=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = HomeownerProfile
        fields = [
            "display_name",
            "avatar_url",
            "email",
            "phone_number",
            "phone_verified_at",
            "is_phone_verified",
            "address",
            "date_of_birth",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "avatar_url",
            "email",
            "phone_verified_at",
            "is_phone_verified",
            "created_at",
            "updated_at",
        ]


class HomeownerProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating homeowner profile.
    """

    class Meta:
        model = HomeownerProfile
        fields = ["display_name", "address", "date_of_birth"]

    def validate_date_of_birth(self, value):
        """Must be at least 18 years old."""
        if value:
            from datetime import date

            today = date.today()
            age = (
                today.year
                - value.year
                - ((today.month, today.day) < (value.month, value.day))
            )
            if age < 18:
                raise serializers.ValidationError("Must be at least 18 years old.")
        return value


class HandymanProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for handyman profile (self view).

    This includes contact and location fields because the handyman is viewing their
    own profile.
    """

    is_phone_verified = serializers.BooleanField(read_only=True)
    avatar_url = serializers.URLField(read_only=True, allow_null=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    category = HandymanCategorySerializer(read_only=True)

    class Meta:
        model = HandymanProfile
        fields = [
            "display_name",
            "avatar_url",
            "email",
            "rating",
            "hourly_rate",
            "job_title",
            "category",
            "id_number",
            "date_of_birth",
            "latitude",
            "longitude",
            "is_active",
            "is_available",
            "is_approved",
            "phone_number",
            "phone_verified_at",
            "is_phone_verified",
            "address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "avatar_url",
            "email",
            "rating",
            "id_number",
            "is_approved",
            "phone_verified_at",
            "is_phone_verified",
            "created_at",
            "updated_at",
        ]


class HandymanProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating handyman profile.

    Notes:
    - If updating latitude/longitude, both must be provided together.
    """

    category_id = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=HandymanCategory.objects.all(),
        source="category",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = HandymanProfile
        fields = [
            "display_name",
            "hourly_rate",
            "job_title",
            "category_id",
            "date_of_birth",
            "latitude",
            "longitude",
            "is_active",
            "is_available",
            "address",
        ]

    def validate_date_of_birth(self, value):
        """Must be at least 18 years old."""
        if value:
            from datetime import date

            today = date.today()
            age = (
                today.year
                - value.year
                - ((today.month, today.day) < (value.month, value.day))
            )
            if age < 18:
                raise serializers.ValidationError("Must be at least 18 years old.")
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        instance = getattr(self, "instance", None)

        if "latitude" in attrs or "longitude" in attrs:
            new_lat = attrs.get("latitude")
            new_lng = attrs.get("longitude")

            if "latitude" in attrs and "longitude" not in attrs:
                new_lng = getattr(instance, "longitude", None) if instance else None
            if "longitude" in attrs and "latitude" not in attrs:
                new_lat = getattr(instance, "latitude", None) if instance else None

            if (new_lat is None) != (new_lng is None):
                raise serializers.ValidationError(
                    "Both latitude and longitude must be provided together."
                )

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

        hourly_rate = attrs.get("hourly_rate")
        if hourly_rate is not None and hourly_rate <= 0:
            raise serializers.ValidationError(
                {"hourly_rate": "Hourly rate must be greater than 0."}
            )

        return attrs


# Response serializers with envelope format
HomeownerProfileResponseSerializer = create_response_serializer(
    HomeownerProfileSerializer, "HomeownerProfileResponse"
)

HandymanProfileResponseSerializer = create_response_serializer(
    HandymanProfileSerializer, "HandymanProfileResponse"
)


class HomeownerHandymanListSerializer(serializers.ModelSerializer):
    """Serializer for homeowners browsing nearby handymen (public fields only)."""

    avatar_url = serializers.URLField(read_only=True, allow_null=True)
    rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        read_only=True,
        allow_null=True,
        coerce_to_string=False,
    )
    hourly_rate = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        allow_null=True,
        coerce_to_string=False,
    )
    distance_km = serializers.FloatField(
        read_only=True,
        allow_null=True,
        help_text="Distance from user location in kilometers.",
    )

    class Meta:
        model = HandymanProfile
        fields = [
            "public_id",
            "display_name",
            "avatar_url",
            "rating",
            "hourly_rate",
            "distance_km",
        ]
        read_only_fields = fields


class HomeownerHandymanDetailSerializer(serializers.ModelSerializer):
    """Serializer for homeowner viewing a handyman profile detail (public fields only)."""

    avatar_url = serializers.URLField(read_only=True, allow_null=True)
    rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        read_only=True,
        allow_null=True,
        coerce_to_string=False,
    )
    hourly_rate = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        allow_null=True,
        coerce_to_string=False,
    )

    class Meta:
        model = HandymanProfile
        fields = [
            "public_id",
            "display_name",
            "avatar_url",
            "rating",
            "hourly_rate",
        ]
        read_only_fields = fields


HomeownerHandymanListResponseSerializer = create_list_response_serializer(
    HomeownerHandymanListSerializer, "HomeownerHandymanListResponse"
)

HomeownerHandymanDetailResponseSerializer = create_response_serializer(
    HomeownerHandymanDetailSerializer, "HomeownerHandymanDetailResponse"
)


# Guest serializers (reuse HomeownerHandyman serializers)
GuestHandymanListSerializer = HomeownerHandymanListSerializer
GuestHandymanDetailSerializer = HomeownerHandymanDetailSerializer

GuestHandymanListResponseSerializer = create_list_response_serializer(
    GuestHandymanListSerializer, "GuestHandymanListResponse"
)

GuestHandymanDetailResponseSerializer = create_response_serializer(
    GuestHandymanDetailSerializer, "GuestHandymanDetailResponse"
)
