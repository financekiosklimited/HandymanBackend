"""Tests for Firebase service."""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.notifications.firebase_service import FirebaseService


class FirebaseServiceTests(TestCase):
    """Test cases for FirebaseService."""

    def test_initialize_firebase_already_initialized(self):
        """Test initialization when already initialized."""
        with patch("firebase_admin._apps", ["default"]):
            with patch("firebase_admin.get_app") as mock_get_app:
                service = FirebaseService()
                mock_get_app.assert_called_once()
                self.assertEqual(service._app, mock_get_app.return_value)

    @patch("firebase_admin.initialize_app")
    @patch("firebase_admin.credentials.Certificate")
    def test_initialize_firebase_path(self, mock_cert, mock_init):
        """Test initialization with credentials path."""
        with patch("firebase_admin._apps", []):
            with override_settings(FIREBASE_CREDENTIALS_PATH="/path/to/json"):
                FirebaseService()
                mock_cert.assert_called_once_with("/path/to/json")
                mock_init.assert_called_once()

    @patch("firebase_admin.initialize_app")
    @patch("firebase_admin.credentials.Certificate")
    def test_initialize_firebase_json(self, mock_cert, mock_init):
        """Test initialization with credentials JSON."""
        cred_json = json.dumps({"project_id": "test"})
        with patch("firebase_admin._apps", []):
            with override_settings(
                FIREBASE_CREDENTIALS_PATH=None, FIREBASE_CREDENTIALS_JSON=cred_json
            ):
                FirebaseService()
                mock_cert.assert_called_once_with({"project_id": "test"})
                mock_init.assert_called_once()

    def test_initialize_firebase_not_configured(self):
        """Test initialization when not configured."""
        with patch("firebase_admin._apps", []):
            with override_settings(
                FIREBASE_CREDENTIALS_PATH=None, FIREBASE_CREDENTIALS_JSON=None
            ):
                service = FirebaseService()
                self.assertIsNone(service._app)

    @patch("firebase_admin.messaging.send")
    @patch("firebase_admin.messaging.Message")
    @patch("firebase_admin.messaging.Notification")
    def test_send_notification_success(self, mock_notif, mock_msg, mock_send):
        """Test sending single notification success."""
        service = FirebaseService()
        service._app = MagicMock()
        mock_send.return_value = "msg_id"

        result = service.send_notification("token", "Title", "Body", {"key": "val"})

        self.assertTrue(result)
        mock_notif.assert_called_once_with(title="Title", body="Body")
        mock_msg.assert_called_once()
        mock_send.assert_called_once()

    def test_send_notification_no_app(self):
        """Test sending single notification when app not initialized."""
        service = FirebaseService()
        service._app = None
        result = service.send_notification("token", "Title", "Body")
        self.assertFalse(result)

    @patch("firebase_admin.messaging.send")
    def test_send_notification_failure(self, mock_send):
        """Test sending single notification failure."""
        service = FirebaseService()
        service._app = MagicMock()
        mock_send.side_effect = Exception("error")

        result = service.send_notification("token", "Title", "Body")
        self.assertFalse(result)

    @patch("firebase_admin.messaging.send_each_for_multicast")
    @patch("firebase_admin.messaging.MulticastMessage")
    def test_send_multicast_notification_success(self, mock_msg, mock_send):
        """Test sending multicast notification success."""
        service = FirebaseService()
        service._app = MagicMock()
        mock_resp = MagicMock()
        mock_resp.success_count = 2
        mock_resp.failure_count = 1
        mock_send.return_value = mock_resp

        result = service.send_multicast_notification(
            ["t1", "t2", "t3"], "Title", "Body"
        )

        self.assertEqual(result["success_count"], 2)
        self.assertEqual(result["failure_count"], 1)

    def test_send_multicast_notification_no_app(self):
        """Test sending multicast notification when app not initialized."""
        service = FirebaseService()
        service._app = None
        result = service.send_multicast_notification(["t1"], "Title", "Body")
        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["failure_count"], 1)

    @patch("firebase_admin.messaging.send_each_for_multicast")
    def test_send_multicast_notification_failure(self, mock_send):
        """Test sending multicast notification failure."""
        service = FirebaseService()
        service._app = MagicMock()
        mock_send.side_effect = Exception("error")

        result = service.send_multicast_notification(["t1"], "Title", "Body")
        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["failure_count"], 1)

    def test_initialize_firebase_import_error(self):
        """Test initialization with ImportError."""
        with patch("firebase_admin._apps", []):
            with patch.dict("sys.modules", {"firebase_admin": None}):
                service = FirebaseService()
                self.assertIsNone(service._app)

    def test_initialize_firebase_general_exception(self):
        """Test initialization with general Exception."""
        with patch("firebase_admin._apps", []):
            # We need to trigger an exception during initialization
            # For example, by mocking settings to return something that breaks json.loads
            with override_settings(FIREBASE_CREDENTIALS_JSON="invalid-json"):
                service = FirebaseService()
                self.assertIsNone(service._app)
