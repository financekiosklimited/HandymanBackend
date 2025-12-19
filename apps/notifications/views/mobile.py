from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.authn.permissions import (
    EmailVerifiedPermission,
    PlatformGuardPermission,
    RoleGuardPermission,
)
from apps.common.responses import (
    created_response,
    success_response,
    validation_error_response,
)
from apps.notifications.models import Notification, UserDevice
from apps.notifications.serializers import (
    DeviceRegisterSerializer,
    NotificationDetailResponseSerializer,
    NotificationListResponseSerializer,
    NotificationSerializer,
    UnreadCountResponseSerializer,
    UserDeviceResponseSerializer,
)


class NotificationListView(APIView):
    """
    View for listing user notifications.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_notifications_list",
        responses={200: NotificationListResponseSerializer},
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
                name="is_read",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter by read status",
                required=False,
            ),
        ],
        description="List all notifications for the authenticated user with pagination and filtering.",
        summary="List notifications",
        tags=["Mobile Notifications"],
    )
    def get(self, request):
        """List all notifications for the user."""
        notifications = Notification.objects.filter(user=request.user)

        # Filter by read status if provided
        is_read = request.query_params.get("is_read")
        if is_read is not None:
            is_read_bool = is_read.lower() in ["true", "1"]
            notifications = notifications.filter(is_read=is_read_bool)

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        total_count = notifications.count()
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 1
        )

        start = (page - 1) * page_size
        end = start + page_size
        notifications = notifications[start:end]

        serializer = NotificationSerializer(notifications, many=True)

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
            message="Notifications retrieved successfully",
            meta=meta,
        )


class NotificationMarkAsReadView(APIView):
    """
    View for marking a notification as read.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_notifications_mark_as_read",
        request=None,
        responses={
            200: NotificationDetailResponseSerializer,
            404: OpenApiTypes.OBJECT,
        },
        description="Mark a specific notification as read.",
        summary="Mark as read",
        tags=["Mobile Notifications"],
    )
    def post(self, request, public_id):
        """Mark a notification as read."""
        notification = get_object_or_404(
            Notification, public_id=public_id, user=request.user
        )

        from apps.notifications.services import notification_service

        notification = notification_service.mark_as_read(notification)

        serializer = NotificationSerializer(notification)
        return success_response(serializer.data, message="Notification marked as read")


class NotificationMarkAllAsReadView(APIView):
    """
    View for marking all notifications as read.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_notifications_mark_all_as_read",
        request=None,
        responses={200: OpenApiTypes.OBJECT},
        description="Mark all unread notifications as read for the authenticated user.",
        summary="Mark all as read",
        tags=["Mobile Notifications"],
    )
    def post(self, request):
        """Mark all notifications as read."""
        from apps.notifications.services import notification_service

        count = notification_service.mark_all_as_read(request.user)

        return success_response(
            {"count": count}, message=f"{count} notifications marked as read"
        )


class NotificationUnreadCountView(APIView):
    """
    View for getting unread notification count.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_notifications_unread_count",
        responses={200: UnreadCountResponseSerializer},
        description="Get the count of unread notifications for the authenticated user.",
        summary="Get unread count",
        tags=["Mobile Notifications"],
    )
    def get(self, request):
        """Get unread notification count."""
        from apps.notifications.services import notification_service

        count = notification_service.get_unread_count(request.user)

        return success_response(
            {"unread_count": count}, message="Unread count retrieved successfully"
        )


class DeviceRegisterView(APIView):
    """
    View for registering a device for push notifications.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_devices_register",
        request=DeviceRegisterSerializer,
        responses={
            201: UserDeviceResponseSerializer,
            400: OpenApiTypes.OBJECT,
        },
        description="Register a device for push notifications. If the device token already exists, it will be updated.",
        summary="Register device",
        tags=["Mobile Devices"],
        examples=[
            OpenApiExample(
                "Request Example",
                value={
                    "device_token": "fK9xZ3tY2pQ:APA91bF...",
                    "device_type": "ios",
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        """Register a device for push notifications."""
        serializer = DeviceRegisterSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        device = serializer.save()

        from apps.notifications.serializers import UserDeviceSerializer

        response_serializer = UserDeviceSerializer(device)
        return created_response(
            response_serializer.data, message="Device registered successfully"
        )


class DeviceUnregisterView(APIView):
    """
    View for unregistering a device.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_devices_unregister",
        request=None,
        responses={
            200: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Unregister a device from receiving push notifications.",
        summary="Unregister device",
        tags=["Mobile Devices"],
    )
    def delete(self, request, public_id):
        """Unregister a device."""
        device = get_object_or_404(UserDevice, public_id=public_id, user=request.user)

        from apps.notifications.services import notification_service

        notification_service.unregister_device(device)

        return success_response(None, message="Device unregistered successfully")
