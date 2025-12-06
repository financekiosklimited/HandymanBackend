"""
Serializers for profile endpoints.
"""

from rest_framework import serializers

from apps.common.serializers import create_response_serializer
from apps.profiles.models import HandymanProfile, HomeownerProfile


class HomeownerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for homeowner profile.
    """

    is_phone_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = HomeownerProfile
        fields = [
            "display_name",
            "phone_number",
            "phone_verified_at",
            "is_phone_verified",
            "address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
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
    Serializer for handyman profile.
    """

    is_phone_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = HandymanProfile
        fields = [
            "display_name",
            "rating",
            "phone_number",
            "phone_verified_at",
            "is_phone_verified",
            "address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "phone_verified_at",
            "is_phone_verified",
            "created_at",
            "updated_at",
        ]


class HandymanProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating handyman profile.
    Resets phone_verified_at when phone_number changes.
    """

    class Meta:
        model = HandymanProfile
        fields = ["display_name", "phone_number", "address"]

    def update(self, instance, validated_data):
        """Reset phone verification if phone number changes."""
        new_phone = validated_data.get("phone_number")
        if new_phone is not None and new_phone != instance.phone_number:
            # Phone number changed, reset verification
            instance.phone_verified_at = None
        return super().update(instance, validated_data)


# Response serializers with envelope format
HomeownerProfileResponseSerializer = create_response_serializer(
    HomeownerProfileSerializer, "HomeownerProfileResponse"
)

HandymanProfileResponseSerializer = create_response_serializer(
    HandymanProfileSerializer, "HandymanProfileResponse"
)
