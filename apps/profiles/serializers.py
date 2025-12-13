"""
Serializers for profile endpoints.
"""

from rest_framework import serializers

from apps.common.serializers import (
    create_list_response_serializer,
    create_response_serializer,
)
from apps.profiles.models import HandymanProfile, HomeownerProfile


class HomeownerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for homeowner profile.
    """

    is_phone_verified = serializers.BooleanField(read_only=True)
    avatar_url = serializers.URLField(read_only=True, allow_null=True)

    class Meta:
        model = HomeownerProfile
        fields = [
            "display_name",
            "avatar_url",
            "phone_number",
            "phone_verified_at",
            "is_phone_verified",
            "address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "avatar_url",
            "phone_verified_at",
            "is_phone_verified",
            "created_at",
            "updated_at",
        ]


class HomeownerProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating homeowner profile.
    Resets phone_verified_at when phone_number changes.
    """

    class Meta:
        model = HomeownerProfile
        fields = ["display_name", "phone_number", "address"]

    def update(self, instance, validated_data):
        """Reset phone verification if phone number changes."""
        new_phone = validated_data.get("phone_number")
        if new_phone is not None and new_phone != instance.phone_number:
            # Phone number changed, reset verification
            instance.phone_verified_at = None
        return super().update(instance, validated_data)


class HandymanProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for handyman profile (self view).

    This includes contact and location fields because the handyman is viewing their
    own profile.
    """

    is_phone_verified = serializers.BooleanField(read_only=True)
    avatar_url = serializers.URLField(read_only=True, allow_null=True)

    class Meta:
        model = HandymanProfile
        fields = [
            "display_name",
            "avatar_url",
            "rating",
            "hourly_rate",
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
            "rating",
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
    - Resets phone_verified_at when phone_number changes.
    - If updating latitude/longitude, both must be provided together.
    """

    class Meta:
        model = HandymanProfile
        fields = [
            "display_name",
            "hourly_rate",
            "latitude",
            "longitude",
            "is_active",
            "is_available",
            "phone_number",
            "address",
        ]

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

    def update(self, instance, validated_data):
        """Reset phone verification if phone number changes."""
        new_phone = validated_data.get("phone_number")
        if new_phone is not None and new_phone != instance.phone_number:
            instance.phone_verified_at = None
        return super().update(instance, validated_data)


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
