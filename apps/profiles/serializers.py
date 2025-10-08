"""
Serializers for profile endpoints.
"""

from rest_framework import serializers

from apps.common.serializers import create_response_serializer
from apps.profiles.models import CustomerProfile, HandymanProfile


class CustomerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for customer profile.
    """

    class Meta:
        model = CustomerProfile
        fields = ["display_name", "phone_number", "address", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class CustomerProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating customer profile.
    """

    class Meta:
        model = CustomerProfile
        fields = ["display_name", "phone_number", "address"]


class HandymanProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for handyman profile.
    """

    class Meta:
        model = HandymanProfile
        fields = [
            "display_name",
            "rating",
            "phone_number",
            "address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class HandymanProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating handyman profile.
    """

    class Meta:
        model = HandymanProfile
        fields = ["display_name", "phone_number", "address"]


# Response serializers with envelope format
CustomerProfileResponseSerializer = create_response_serializer(
    CustomerProfileSerializer, "CustomerProfileResponse"
)

HandymanProfileResponseSerializer = create_response_serializer(
    HandymanProfileSerializer, "HandymanProfileResponse"
)
