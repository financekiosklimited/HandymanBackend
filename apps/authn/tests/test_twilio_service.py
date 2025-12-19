"""Tests for Twilio service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.authn.twilio_service import TwilioService


class TwilioServiceTests(TestCase):
    """Test cases for TwilioService."""

    def setUp(self):
        """Set up test data."""
        self.service = TwilioService()

    def test_client_lazy_load_not_configured(self):
        """Test client lazy load when not configured."""
        with override_settings(TWILIO_ACCOUNT_SID=None, TWILIO_AUTH_TOKEN=None):
            service = TwilioService()
            self.assertIsNone(service.client)

    @patch("twilio.rest.Client")
    def test_client_lazy_load_success(self, mock_client):
        """Test client lazy load success."""
        with override_settings(
            TWILIO_ACCOUNT_SID="AC123", TWILIO_AUTH_TOKEN="token123"
        ):
            service = TwilioService()
            client = service.client
            self.assertIsNotNone(client)
            mock_client.assert_called_once_with("AC123", "token123")
            # Should be cached
            self.assertEqual(service.client, client)
            self.assertEqual(mock_client.call_count, 1)

    @patch("twilio.rest.Client")
    def test_client_lazy_load_import_error(self, mock_client):
        """Test client lazy load with import error."""
        with override_settings(
            TWILIO_ACCOUNT_SID="AC123", TWILIO_AUTH_TOKEN="token123"
        ):
            service = TwilioService()
            with patch("builtins.__import__", side_effect=ImportError):
                self.assertIsNone(service.client)

    def test_verify_service_sid(self):
        """Test getting verify service sid."""
        with override_settings(TWILIO_VERIFY_SERVICE_SID="VA123"):
            self.assertEqual(self.service.verify_service_sid, "VA123")

    def test_is_configured(self):
        """Test is_configured check."""
        with override_settings(
            TWILIO_ACCOUNT_SID="AC123",
            TWILIO_AUTH_TOKEN="token123",
            TWILIO_VERIFY_SERVICE_SID="VA123",
        ):
            with patch("twilio.rest.Client"):
                # Reset cached client
                self.service._client = None
                self.assertTrue(self.service.is_configured)

        with override_settings(TWILIO_ACCOUNT_SID=None):
            # Reset cached client
            self.service._client = None
            self.assertFalse(self.service.is_configured)

    def test_send_verification_not_configured(self):
        """Test sending verification when not configured."""
        with override_settings(TWILIO_ACCOUNT_SID=None):
            result = self.service.send_verification("+1234567890")
            self.assertFalse(result.success)
            self.assertEqual(result.error, "Twilio not configured")

    @patch("apps.authn.twilio_service.TwilioService.client", new_callable=MagicMock)
    def test_send_verification_success(self, mock_client_prop):
        """Test sending verification success."""
        mock_client = MagicMock()
        mock_client_prop.__get__ = MagicMock(return_value=mock_client)

        mock_verification = MagicMock()
        mock_verification.status = "pending"
        mock_verification.sid = "VE123"
        mock_client.verify.v2.services().verifications.create.return_value = (
            mock_verification
        )

        with override_settings(TWILIO_VERIFY_SERVICE_SID="VA123"):
            result = self.service.send_verification("+1234567890")

            self.assertTrue(result.success)
            self.assertEqual(result.status, "pending")
            mock_client.verify.v2.services.assert_called_with("VA123")

    @patch("apps.authn.twilio_service.TwilioService.client", new_callable=MagicMock)
    def test_send_verification_twilio_error(self, mock_client_prop):
        """Test sending verification with Twilio error."""
        from twilio.base.exceptions import TwilioRestException

        mock_client = MagicMock()
        mock_client_prop.__get__ = MagicMock(return_value=mock_client)

        mock_client.verify.v2.services().verifications.create.side_effect = (
            TwilioRestException(400, "uri", "Twilio Error")
        )

        with override_settings(TWILIO_VERIFY_SERVICE_SID="VA123"):
            result = self.service.send_verification("+1234567890")
            self.assertFalse(result.success)
            self.assertIn("Twilio Error", result.error)

    @patch("apps.authn.twilio_service.TwilioService.client", new_callable=MagicMock)
    def test_send_verification_general_error(self, mock_client_prop):
        """Test sending verification with general error."""
        mock_client = MagicMock()
        mock_client_prop.__get__ = MagicMock(return_value=mock_client)

        mock_client.verify.v2.services().verifications.create.side_effect = Exception(
            "General Error"
        )

        with override_settings(TWILIO_VERIFY_SERVICE_SID="VA123"):
            result = self.service.send_verification("+1234567890")
            self.assertFalse(result.success)
            self.assertEqual(result.error, "General Error")

    def test_check_verification_not_configured(self):
        """Test checking verification when not configured."""
        with override_settings(TWILIO_ACCOUNT_SID=None):
            result = self.service.check_verification("+1234567890", "123456")
            self.assertFalse(result.success)
            self.assertEqual(result.error, "Twilio not configured")

    @patch("apps.authn.twilio_service.TwilioService.client", new_callable=MagicMock)
    def test_check_verification_approved(self, mock_client_prop):
        """Test checking verification approved."""
        mock_client = MagicMock()
        mock_client_prop.__get__ = MagicMock(return_value=mock_client)

        mock_check = MagicMock()
        mock_check.status = "approved"
        mock_check.valid = True
        mock_client.verify.v2.services().verification_checks.create.return_value = (
            mock_check
        )

        with override_settings(TWILIO_VERIFY_SERVICE_SID="VA123"):
            result = self.service.check_verification("+1234567890", "123456")
            self.assertTrue(result.success)
            self.assertEqual(result.status, "approved")

    @patch("apps.authn.twilio_service.TwilioService.client", new_callable=MagicMock)
    def test_check_verification_pending(self, mock_client_prop):
        """Test checking verification still pending/invalid."""
        mock_client = MagicMock()
        mock_client_prop.__get__ = MagicMock(return_value=mock_client)

        mock_check = MagicMock()
        mock_check.status = "pending"
        mock_check.valid = False
        mock_client.verify.v2.services().verification_checks.create.return_value = (
            mock_check
        )

        with override_settings(TWILIO_VERIFY_SERVICE_SID="VA123"):
            result = self.service.check_verification("+1234567890", "123456")
            self.assertFalse(result.success)
            self.assertEqual(result.status, "pending")
            self.assertEqual(result.error, "Invalid or expired code")

    @patch("apps.authn.twilio_service.TwilioService.client", new_callable=MagicMock)
    def test_check_verification_twilio_error(self, mock_client_prop):
        """Test checking verification with Twilio error."""
        from twilio.base.exceptions import TwilioRestException

        mock_client = MagicMock()
        mock_client_prop.__get__ = MagicMock(return_value=mock_client)

        mock_client.verify.v2.services().verification_checks.create.side_effect = (
            TwilioRestException(400, "uri", "Twilio Error")
        )

        with override_settings(TWILIO_VERIFY_SERVICE_SID="VA123"):
            result = self.service.check_verification("+1234567890", "123456")
            self.assertFalse(result.success)
            self.assertIn("Twilio Error", result.error)

    @patch("apps.authn.twilio_service.TwilioService.client", new_callable=MagicMock)
    def test_check_verification_general_error(self, mock_client_prop):
        """Test checking verification with general error."""
        mock_client = MagicMock()
        mock_client_prop.__get__ = MagicMock(return_value=mock_client)

        mock_client.verify.v2.services().verification_checks.create.side_effect = (
            Exception("General Error")
        )

        with override_settings(TWILIO_VERIFY_SERVICE_SID="VA123"):
            result = self.service.check_verification("+1234567890", "123456")
            self.assertFalse(result.success)
            self.assertEqual(result.error, "General Error")

    def test_mask_phone_number(self):
        """Test masking phone number."""
        self.assertEqual(
            self.service.mask_phone_number("+6281234567890"), "+6281*****7890"
        )
        self.assertEqual(self.service.mask_phone_number("+1234"), "+1234")
        self.assertEqual(self.service.mask_phone_number(""), "")
        self.assertEqual(self.service.mask_phone_number(None), None)
        # 8 characters is minimum for masking logic in code (len < 8 returns as is)
        self.assertEqual(self.service.mask_phone_number("+123456"), "+123456")
        # 9 characters: prefix(5) + suffix(4) = 9. masked_length = 0, max(0, 4) = 4 stars.
        self.assertEqual(self.service.mask_phone_number("+62812345"), "+6281****2345")

    def test_client_lazy_load_import_error_real(self):
        """Test client lazy load with a real ImportError during twilio.rest import."""
        with override_settings(
            TWILIO_ACCOUNT_SID="AC123", TWILIO_AUTH_TOKEN="token123"
        ):
            service = TwilioService()
            with patch.dict("sys.modules", {"twilio.rest": None}):
                client = service.client
                self.assertIsNone(client)
