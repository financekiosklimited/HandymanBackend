"""
Service for managing in-app notifications and push notifications.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.notifications.firebase_service import firebase_service
from apps.notifications.models import Notification, UserDevice

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for creating and sending notifications.
    """

    def create_notification(
        self,
        user,
        notification_type: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> Notification:
        """
        Create an in-app notification.

        Args:
            user: User to notify
            notification_type: Type of notification
            title: Notification title
            body: Notification body
            data: Optional data payload

        Returns:
            Notification: Created notification
        """
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data,
        )
        logger.info(
            f"Created notification {notification.public_id} for user {user.email}"
        )
        return notification

    def send_push_notification(
        self,
        user,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> bool:
        """
        Send push notification to all active devices of a user.

        Args:
            user: User to notify
            title: Notification title
            body: Notification body
            data: Optional data payload

        Returns:
            bool: True if at least one notification was sent successfully
        """
        # Get all active devices for the user
        devices = UserDevice.objects.filter(user=user, is_active=True)

        if not devices.exists():
            logger.debug(f"No active devices found for user {user.email}")
            return False

        device_tokens = list(devices.values_list("device_token", flat=True))

        # Send multicast notification
        result = firebase_service.send_multicast_notification(
            device_tokens=device_tokens,
            title=title,
            body=body,
            data=data,
        )

        # Update last_used_at for successful devices
        if result["success_count"] > 0:
            devices.update(last_used_at=timezone.now())

        return result["success_count"] > 0

    @transaction.atomic
    def create_and_send_notification(
        self,
        user,
        notification_type: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> Notification:
        """
        Create an in-app notification and send push notification.

        Args:
            user: User to notify
            notification_type: Type of notification
            title: Notification title
            body: Notification body
            data: Optional data payload

        Returns:
            Notification: Created notification
        """
        # Create in-app notification
        notification = self.create_notification(
            user=user,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data,
        )

        # Send push notification
        self.send_push_notification(
            user=user,
            title=title,
            body=body,
            data=data,
        )

        return notification

    def mark_as_read(self, notification: Notification) -> Notification:
        """
        Mark a notification as read.

        Args:
            notification: Notification to mark as read

        Returns:
            Notification: Updated notification
        """
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at", "updated_at"])
            logger.info(f"Marked notification {notification.public_id} as read")

        return notification

    def mark_all_as_read(self, user) -> int:
        """
        Mark all unread notifications as read for a user.

        Args:
            user: User whose notifications to mark as read

        Returns:
            int: Number of notifications marked as read
        """
        unread_notifications = Notification.objects.filter(user=user, is_read=False)
        count = unread_notifications.update(
            is_read=True, read_at=timezone.now(), updated_at=timezone.now()
        )
        logger.info(f"Marked {count} notifications as read for user {user.email}")
        return count

    def get_unread_count(self, user) -> int:
        """
        Get count of unread notifications for a user.

        Args:
            user: User to count notifications for

        Returns:
            int: Number of unread notifications
        """
        return Notification.objects.filter(user=user, is_read=False).count()

    def register_device(self, user, device_token: str, device_type: str) -> UserDevice:
        """
        Register a device for push notifications.

        Args:
            user: User to register device for
            device_token: FCM device token
            device_type: Type of device (ios, android, web)

        Returns:
            UserDevice: Registered device
        """
        # Check if device already exists
        device, created = UserDevice.objects.update_or_create(
            device_token=device_token,
            defaults={
                "user": user,
                "device_type": device_type,
                "is_active": True,
                "last_used_at": timezone.now(),
            },
        )

        action = "Registered" if created else "Updated"
        logger.info(f"{action} device {device.public_id} for user {user.email}")

        return device

    def unregister_device(self, device: UserDevice) -> None:
        """
        Unregister a device (soft delete by setting is_active=False).

        Args:
            device: Device to unregister
        """
        device.is_active = False
        device.save(update_fields=["is_active", "updated_at"])
        logger.info(f"Unregistered device {device.public_id}")


# Global notification service instance
notification_service = NotificationService()
