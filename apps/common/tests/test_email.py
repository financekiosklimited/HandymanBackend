"""
Tests for email service.
"""

from unittest.mock import MagicMock, patch

from django.core import mail
from django.test import TestCase, override_settings

from apps.common.email import EmailService


class TestEmailService(TestCase):
    """Tests for EmailService."""

    def setUp(self):
        """Set up test email service and mock user."""
        self.email_service = EmailService()
        self.mock_user = MagicMock()
        self.mock_user.email = "test@example.com"

    def test_email_service_initialization(self):
        """Test that EmailService initializes with default from_email."""
        self.assertIsNotNone(self.email_service.from_email)

    @override_settings(DEFAULT_FROM_EMAIL="custom@example.com")
    def test_email_service_uses_settings_from_email(self):
        """Test that EmailService uses DEFAULT_FROM_EMAIL from settings."""
        service = EmailService()
        self.assertEqual(service.from_email, "custom@example.com")

    def test_send_email_verification_success(self):
        """Test successful email verification send."""
        result = self.email_service.send_email_verification(self.mock_user, "123456")

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Verify Your Email Address")
        self.assertEqual(mail.outbox[0].to, ["test@example.com"])
        self.assertIn("123456", mail.outbox[0].body)

    def test_send_email_verification_contains_otp(self):
        """Test that verification email contains the OTP code."""
        otp_code = "987654"
        self.email_service.send_email_verification(self.mock_user, otp_code)

        self.assertIn(otp_code, mail.outbox[0].body)

    def test_send_password_reset_code_success(self):
        """Test successful password reset code send."""
        result = self.email_service.send_password_reset_code(self.mock_user, "654321")

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Password Reset Code")
        self.assertEqual(mail.outbox[0].to, ["test@example.com"])
        self.assertIn("654321", mail.outbox[0].body)

    def test_send_password_reset_contains_reset_code(self):
        """Test that password reset email contains the reset code."""
        reset_code = "111222"
        self.email_service.send_password_reset_code(self.mock_user, reset_code)

        self.assertIn(reset_code, mail.outbox[0].body)

    def test_send_welcome_email_success(self):
        """Test successful welcome email send."""
        result = self.email_service.send_welcome_email(self.mock_user)

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Welcome to SB!")
        self.assertEqual(mail.outbox[0].to, ["test@example.com"])

    @patch("apps.common.email.send_mail")
    def test_send_email_verification_failure(self, mock_send_mail):
        """Test email verification send failure handling."""
        mock_send_mail.side_effect = Exception("SMTP Error")

        result = self.email_service.send_email_verification(self.mock_user, "123456")

        self.assertFalse(result)

    @patch("apps.common.email.send_mail")
    def test_send_password_reset_failure(self, mock_send_mail):
        """Test password reset send failure handling."""
        mock_send_mail.side_effect = Exception("SMTP Error")

        result = self.email_service.send_password_reset_code(self.mock_user, "654321")

        self.assertFalse(result)

    @patch("apps.common.email.send_mail")
    def test_send_welcome_email_failure(self, mock_send_mail):
        """Test welcome email send failure handling."""
        mock_send_mail.side_effect = Exception("SMTP Error")

        result = self.email_service.send_welcome_email(self.mock_user)

        self.assertFalse(result)
