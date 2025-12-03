"""
Twilio Verify service for phone number verification.
"""

import logging
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of a verification operation."""

    success: bool
    status: str | None = None
    error: str | None = None


class TwilioService:
    """
    Service for phone verification via Twilio Verify API.
    """

    def __init__(self):
        self._client = None

    @property
    def client(self):
        """Lazy load Twilio client."""
        if self._client is None:
            account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
            auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)

            if account_sid and auth_token:
                try:
                    from twilio.rest import Client

                    self._client = Client(account_sid, auth_token)
                except ImportError:
                    logger.warning("Twilio package not installed")
                    return None
            else:
                logger.debug("Twilio credentials not configured")
                return None

        return self._client

    @property
    def verify_service_sid(self):
        """Get the Twilio Verify Service SID."""
        return getattr(settings, "TWILIO_VERIFY_SERVICE_SID", None)

    @property
    def is_configured(self):
        """Check if Twilio Verify is properly configured."""
        return self.client is not None and self.verify_service_sid is not None

    def send_verification(
        self, to_number: str, channel: str = "sms"
    ) -> VerificationResult:
        """
        Send verification code to a phone number via Twilio Verify API.

        Args:
            to_number: Phone number in E.164 format (e.g., +6281234567890)
            channel: Verification channel ("sms" or "call")

        Returns:
            VerificationResult with success status
        """
        if not self.is_configured:
            logger.warning(
                "Twilio Verify not configured, skipping verification to %s***",
                to_number[:6] if to_number else "unknown",
            )
            # In development/test, return success for testing
            if getattr(settings, "DEBUG", False):
                logger.info("DEBUG MODE - Verification would be sent to %s", to_number)
                return VerificationResult(success=True, status="pending")
            return VerificationResult(success=False, error="Twilio not configured")

        try:
            from twilio.base.exceptions import TwilioRestException

            verification = self.client.verify.v2.services(
                self.verify_service_sid
            ).verifications.create(to=to_number, channel=channel)

            logger.info(
                "Verification sent to %s***: status=%s, sid=%s",
                to_number[:6],
                verification.status,
                verification.sid,
            )
            return VerificationResult(success=True, status=verification.status)

        except TwilioRestException as e:
            logger.error(
                "Twilio error sending verification to %s***: %s",
                to_number[:6] if to_number else "unknown",
                str(e),
            )
            return VerificationResult(success=False, error=str(e))
        except Exception as e:
            logger.exception(
                "Unexpected error sending verification to %s***: %s",
                to_number[:6] if to_number else "unknown",
                str(e),
            )
            return VerificationResult(success=False, error=str(e))

    def check_verification(self, to_number: str, code: str) -> VerificationResult:
        """
        Check a verification code via Twilio Verify API.

        Args:
            to_number: Phone number in E.164 format
            code: The verification code entered by the user

        Returns:
            VerificationResult with success status and verification status
        """
        if not self.is_configured:
            logger.warning(
                "Twilio Verify not configured, skipping check for %s***",
                to_number[:6] if to_number else "unknown",
            )
            # In development/test, accept code "123456" for testing
            if getattr(settings, "DEBUG", False):
                if code == "123456":
                    logger.info(
                        "DEBUG MODE - Verification check approved for %s", to_number
                    )
                    return VerificationResult(success=True, status="approved")
                return VerificationResult(
                    success=False, status="pending", error="Invalid code"
                )
            return VerificationResult(success=False, error="Twilio not configured")

        try:
            from twilio.base.exceptions import TwilioRestException

            verification_check = self.client.verify.v2.services(
                self.verify_service_sid
            ).verification_checks.create(to=to_number, code=code)

            logger.info(
                "Verification check for %s***: status=%s, valid=%s",
                to_number[:6],
                verification_check.status,
                verification_check.valid,
            )

            if verification_check.status == "approved":
                return VerificationResult(success=True, status="approved")
            else:
                return VerificationResult(
                    success=False,
                    status=verification_check.status,
                    error="Invalid or expired code",
                )

        except TwilioRestException as e:
            logger.error(
                "Twilio error checking verification for %s***: %s",
                to_number[:6] if to_number else "unknown",
                str(e),
            )
            return VerificationResult(success=False, error=str(e))
        except Exception as e:
            logger.exception(
                "Unexpected error checking verification for %s***: %s",
                to_number[:6] if to_number else "unknown",
                str(e),
            )
            return VerificationResult(success=False, error=str(e))

    def mask_phone_number(self, phone_number: str) -> str:
        """
        Mask a phone number for display.

        Args:
            phone_number: Phone number in E.164 format

        Returns:
            Masked phone number (e.g., +62812****7890)
        """
        if not phone_number or len(phone_number) < 8:
            return phone_number

        # Keep first 5 chars (e.g., +6281) and last 4 chars, mask the rest
        visible_prefix = phone_number[:5]
        visible_suffix = phone_number[-4:]
        masked_length = len(phone_number) - 9

        return f"{visible_prefix}{'*' * max(masked_length, 4)}{visible_suffix}"


# Global service instance
twilio_service = TwilioService()
