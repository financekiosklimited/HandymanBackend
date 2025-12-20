from rest_framework import serializers

from apps.common.serializers import (
    create_list_response_serializer,
    create_response_serializer,
)
from apps.notifications.models import Notification, UserDevice


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for notification (read-only).
    """

    class Meta:
        model = Notification
        fields = [
            "public_id",
            "notification_type",
            "title",
            "body",
            "data",
            "target_role",
            "is_read",
            "read_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UserDeviceSerializer(serializers.ModelSerializer):
    """
    Serializer for user device (read-only).
    """

    class Meta:
        model = UserDevice
        fields = [
            "public_id",
            "device_type",
            "is_active",
            "last_used_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DeviceRegisterSerializer(serializers.Serializer):
    """
    Serializer for registering a device.
    """

    device_token = serializers.CharField(max_length=512, required=True)
    device_type = serializers.ChoiceField(
        choices=["ios", "android", "web"], required=True
    )

    def create(self, validated_data):
        """
        Register device using the service.
        """
        from apps.notifications.services import notification_service

        user = self.context["request"].user
        device = notification_service.register_device(
            user=user,
            device_token=validated_data["device_token"],
            device_type=validated_data["device_type"],
        )
        return device


class UnreadCountSerializer(serializers.Serializer):
    """
    Serializer for unread notification count.
    """

    unread_count = serializers.IntegerField(read_only=True)


# Response envelope serializers

NotificationListResponseSerializer = create_list_response_serializer(
    NotificationSerializer, "NotificationListResponse"
)

NotificationDetailResponseSerializer = create_response_serializer(
    NotificationSerializer, "NotificationDetailResponse"
)

UserDeviceResponseSerializer = create_response_serializer(
    UserDeviceSerializer, "UserDeviceResponse"
)

UnreadCountResponseSerializer = create_response_serializer(
    UnreadCountSerializer, "UnreadCountResponse"
)
