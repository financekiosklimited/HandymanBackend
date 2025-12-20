"""
Service for managing in-app notifications and push notifications.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.notifications.firebase_service import firebase_service
from apps.notifications.models import BroadcastNotification, Notification, UserDevice

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for creating and sending notifications.
    """

    def get_target_users(
        self, target_audience: str, broadcast: BroadcastNotification | None = None
    ):
        """
        Get target users based on target audience.
        """
        from apps.accounts.models import User

        if target_audience == "handyman":
            return User.objects.filter(roles__role="handyman")
        if target_audience == "homeowner":
            return User.objects.filter(roles__role="homeowner")
        if target_audience == "specific" and broadcast is not None:
            return broadcast.target_users.all()
        return User.objects.all()

    def send_broadcast(self, broadcast: BroadcastNotification) -> BroadcastNotification:
        """
        Send broadcast notification to target audience.
        """
        users = self.get_target_users(broadcast.target_audience, broadcast).distinct()
        if broadcast.target_audience == "specific" and users.count() == 0:
            raise ValueError("No target users selected for specific broadcast.")

        broadcast.status = "processing"
        broadcast.sent_at = timezone.now()
        broadcast.save(update_fields=["status", "sent_at"])

        # Build notifications based on target_audience
        notifications = []

        if broadcast.target_audience in ("handyman", "homeowner"):
            # Single role broadcast
            target_role = broadcast.target_audience
            for user in users:
                notifications.append(
                    Notification(
                        user=user,
                        notification_type="admin_broadcast",
                        title=broadcast.title,
                        body=broadcast.body,
                        data=broadcast.data,
                        target_role=target_role,
                    )
                )
        else:
            # "all" or "specific" - create per user's roles
            from apps.accounts.models import UserRole

            for user in users:
                user_roles = list(
                    UserRole.objects.filter(
                        user=user, role__in=["handyman", "homeowner"]
                    ).values_list("role", flat=True)
                )
                for role in user_roles:
                    notifications.append(
                        Notification(
                            user=user,
                            notification_type="admin_broadcast",
                            title=broadcast.title,
                            body=broadcast.body,
                            data=broadcast.data,
                            target_role=role,
                        )
                    )

        # Update total_recipients to count notifications
        broadcast.total_recipients = len(notifications)
        broadcast.save(update_fields=["total_recipients"])

        # Use bulk_create in batches of 1000
        batch_size = 1000
        for i in range(0, len(notifications), batch_size):
            Notification.objects.bulk_create(notifications[i : i + batch_size])

        # 2. Send push notifications if enabled
        if broadcast.send_push:
            # Get all active device tokens for these users
            devices = UserDevice.objects.filter(user__in=users, is_active=True)
            device_tokens = list(devices.values_list("device_token", flat=True))

            if device_tokens:
                # Multicast send (Firebase has 500 limit per request)
                # But our firebase_service.send_multicast_notification already handles it?
                # Let's check firebase_service again.
                # Actually, I'll batch it here just to be safe if it doesn't.
                # Looking at firebase_service.py, it uses send_each_for_multicast
                # which has a limit of 500 tokens.

                success_count = 0
                failure_count = 0
                batch_size_fcm = 500

                for i in range(0, len(device_tokens), batch_size_fcm):
                    batch_tokens = device_tokens[i : i + batch_size_fcm]
                    result = firebase_service.send_multicast_notification(
                        device_tokens=batch_tokens,
                        title=broadcast.title,
                        body=broadcast.body,
                        data=broadcast.data,
                    )
                    success_count += result["success_count"]
                    failure_count += result["failure_count"]

                broadcast.push_success_count = success_count
                broadcast.push_failure_count = failure_count

                # Update last_used_at for all active devices of these users
                # This is a bit broad but consistent with send_push_notification
                devices.update(last_used_at=timezone.now())

        broadcast.status = "completed"
        broadcast.save(
            update_fields=[
                "status",
                "push_success_count",
                "push_failure_count",
                "updated_at",
            ]
        )

        return broadcast

    def create_notification(
        self,
        user,
        notification_type: str,
        title: str,
        body: str,
        target_role: str,
        data: dict | None = None,
    ) -> Notification:
        """
        Create an in-app notification.

        Args:
            user: User to notify
            notification_type: Type of notification
            title: Notification title
            body: Notification body
            target_role: Target role for the notification (handyman or homeowner)
            data: Optional data payload

        Returns:
            Notification: Created notification
        """
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            body=body,
            target_role=target_role,
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
        target_role: str,
        data: dict | None = None,
    ) -> Notification:
        """
        Create an in-app notification and send push notification.

        Args:
            user: User to notify
            notification_type: Type of notification
            title: Notification title
            body: Notification body
            target_role: Target role for the notification (handyman or homeowner)
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
            target_role=target_role,
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

    def mark_all_as_read(self, user, target_role: str | None = None) -> int:
        """
        Mark all unread notifications as read for a user.

        Args:
            user: User whose notifications to mark as read
            target_role: Optional role filter (handyman or homeowner)

        Returns:
            int: Number of notifications marked as read
        """
        unread_notifications = Notification.objects.filter(user=user, is_read=False)
        if target_role:
            unread_notifications = unread_notifications.filter(target_role=target_role)
        count = unread_notifications.update(
            is_read=True, read_at=timezone.now(), updated_at=timezone.now()
        )
        logger.info(f"Marked {count} notifications as read for user {user.email}")
        return count

    def get_unread_count(self, user, target_role: str | None = None) -> int:
        """
        Get count of unread notifications for a user.

        Args:
            user: User to count notifications for
            target_role: Optional role filter (handyman or homeowner)

        Returns:
            int: Number of unread notifications
        """
        queryset = Notification.objects.filter(user=user, is_read=False)
        if target_role:
            queryset = queryset.filter(target_role=target_role)
        return queryset.count()

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
