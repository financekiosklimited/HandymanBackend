"""Serializers for waitlist API."""

from rest_framework import serializers

from apps.common.serializers import create_response_serializer

from .models import WaitlistEntry


class WaitlistEntrySerializer(serializers.ModelSerializer):
    """Serializer for creating and returning waitlist entries."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._created = False

    class Meta:
        model = WaitlistEntry
        fields = [
            "public_id",
            "user_name",
            "email",
            "user_type",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["public_id", "created_at", "updated_at"]
        extra_kwargs = {
            "user_name": {"max_length": 255},
        }

    def create(self, validated_data):
        entry, created = WaitlistEntry.objects.update_or_create(
            user_name=validated_data["user_name"],
            email=validated_data["email"],
            user_type=validated_data["user_type"],
            defaults={"email": validated_data["email"]},
        )
        self._created = created
        return entry


# Response wrapper
WaitlistEntryResponseSerializer = create_response_serializer(
    WaitlistEntrySerializer, "WaitlistEntryResponse"
)
