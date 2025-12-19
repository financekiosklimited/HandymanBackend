"""
Firebase Cloud Messaging service for sending push notifications.
"""

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class FirebaseService:
    """
    Service for sending push notifications via Firebase Cloud Messaging.
    """

    _app = None

    def __init__(self):
        """Initialize Firebase Admin SDK."""
        self._initialize_firebase()

    def _initialize_firebase(self):
        """
        Initialize Firebase Admin SDK if credentials are available.
        """
        try:
            import firebase_admin
            from firebase_admin import credentials

            # Skip if already initialized
            if firebase_admin._apps:
                self._app = firebase_admin.get_app()
                return

            # Try to load credentials from path or JSON
            cred = None

            # Option 1: Load from file path
            if (
                hasattr(settings, "FIREBASE_CREDENTIALS_PATH")
                and settings.FIREBASE_CREDENTIALS_PATH
            ):
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            # Option 2: Load from environment variable (JSON string)
            elif (
                hasattr(settings, "FIREBASE_CREDENTIALS_JSON")
                and settings.FIREBASE_CREDENTIALS_JSON
            ):
                cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                cred = credentials.Certificate(cred_dict)

            if cred:
                self._app = firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                logger.warning(
                    "Firebase credentials not configured. Push notifications will be skipped."
                )
        except ImportError:
            logger.warning(
                "firebase-admin not installed. Push notifications will be skipped."
            )
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

    def send_notification(
        self,
        device_token: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> bool:
        """
        Send a push notification to a single device.

        Args:
            device_token: FCM device token
            title: Notification title
            body: Notification body
            data: Optional data payload for deep linking

        Returns:
            bool: True if notification was sent successfully
        """
        if not self._app:
            logger.debug("Firebase not initialized. Skipping push notification.")
            return False

        try:
            from firebase_admin import messaging

            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
            )

            # Build message
            message = messaging.Message(
                notification=notification,
                data=data or {},
                token=device_token,
            )

            # Send message
            response = messaging.send(message)
            logger.info(f"Successfully sent message: {response}")
            return True

        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return False

    def send_multicast_notification(
        self,
        device_tokens: list[str],
        title: str,
        body: str,
        data: dict | None = None,
    ) -> dict:
        """
        Send a push notification to multiple devices.

        Args:
            device_tokens: List of FCM device tokens
            title: Notification title
            body: Notification body
            data: Optional data payload for deep linking

        Returns:
            dict: Response with success_count and failure_count
        """
        if not self._app:
            logger.debug("Firebase not initialized. Skipping push notifications.")
            return {"success_count": 0, "failure_count": len(device_tokens)}

        try:
            from firebase_admin import messaging

            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
            )

            # Build message
            message = messaging.MulticastMessage(
                notification=notification,
                data=data or {},
                tokens=device_tokens,
            )

            # Send message
            response = messaging.send_each_for_multicast(message)
            logger.info(
                f"Successfully sent {response.success_count} messages, "
                f"{response.failure_count} failures"
            )

            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count,
            }

        except Exception as e:
            logger.error(f"Failed to send multicast push notification: {e}")
            return {"success_count": 0, "failure_count": len(device_tokens)}


# Global Firebase service instance
firebase_service = FirebaseService()
