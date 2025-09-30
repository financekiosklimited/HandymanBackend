"""
Tests for custom exception handler.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.common.exceptions import (
    custom_exception_handler,
    get_error_details,
    get_error_message,
)


class TestExceptionHandler(TestCase):
    """Tests for custom exception handler."""

    def test_get_error_message_with_detail(self):
        """Test getting error message from response with detail field."""
        exc = ValidationError("Test error")
        response = Response({"detail": "Custom error message"}, status=400)

        message = get_error_message(exc, response)

        self.assertEqual(message, "Custom error message")

    def test_get_error_message_with_message_field(self):
        """Test getting error message from response with message field."""
        exc = ValidationError("Test error")
        response = Response({"message": "Custom message"}, status=400)

        message = get_error_message(exc, response)

        self.assertEqual(message, "Custom message")

    def test_get_error_message_default_400(self):
        """Test default error message for 400 status."""
        exc = ValidationError("Test error")
        response = Response({}, status=400)

        message = get_error_message(exc, response)

        self.assertEqual(message, "Bad request")

    def test_get_error_message_default_404(self):
        """Test default error message for 404 status."""
        exc = NotFound("Not found")
        response = Response({}, status=404)

        message = get_error_message(exc, response)

        self.assertEqual(message, "Not found")

    def test_get_error_details_validation_error(self):
        """Test getting error details from validation error."""
        exc = ValidationError({"field": ["Error message"]})
        response = Response({"field": ["Error message"]}, status=400)

        details = get_error_details(exc, response)

        self.assertEqual(details, {"field": ["Error message"]})

    def test_get_error_details_with_detail_field(self):
        """Test getting error details with detail field."""
        exc = NotFound("Not found")
        response = Response({"detail": "Not found"}, status=404)

        details = get_error_details(exc, response)

        self.assertEqual(details, {"detail": "Not found"})

    def test_get_error_details_returns_existing_errors(self):
        """Use provided errors when response already has errors key."""
        exc = ValidationError("Invalid")
        response = Response({"errors": {"field": ["issue"]}}, status=400)

        details = get_error_details(exc, response)

        self.assertEqual(details, {"field": ["issue"]})

    def test_get_error_details_handles_envelope_response(self):
        """Extract errors from responses already in envelope format."""
        exc = ValidationError("Invalid")
        response = Response(
            {"message": "Oops", "data": None, "errors": {"field": "bad"}, "meta": {}},
            status=400,
        )

        details = get_error_details(exc, response)

        self.assertEqual(details, {"field": "bad"})

    def test_get_error_details_falls_back_to_envelope_when_errors_key_skipped(self):
        """Exercise secondary envelope branch when errors lookup first fails."""

        class FlakyEnvelope(dict):
            def __contains__(self, key):
                if key == "errors":
                    seen = getattr(self, "_seen_errors", False)
                    if not seen:
                        self._seen_errors = True
                        return False
                return super().__contains__(key)

        payload = FlakyEnvelope(
            message="Oops", data=None, errors={"field": "bad"}, meta={}
        )
        exc = ValidationError("Invalid")
        response = SimpleNamespace(data=payload, status_code=400)

        details = get_error_details(exc, response)

        self.assertEqual(details, {"field": "bad"})

    def test_get_error_details_filters_message_and_detail(self):
        """Remove message/detail keys for validation errors."""
        exc = ValidationError("Invalid payload")
        response = Response(
            {"message": "Bad", "detail": "Nope", "field": ["error"]}, status=400
        )

        details = get_error_details(exc, response)

        self.assertEqual(details, {"field": ["error"]})

    def test_get_error_details_returns_detail_when_filtered_errors_empty(self):
        """Return detail when validation errors dict is emptied by filtering."""
        exc = ValidationError("Invalid payload")
        response = Response({"message": "Bad", "detail": "Nope"}, status=400)

        details = get_error_details(exc, response)

        self.assertEqual(details, {"detail": "Nope"})

    def test_get_error_details_returns_raw_data(self):
        """Return raw data for non-validation dict responses."""
        exc = Exception("Server boom")
        response = Response({"reason": "fail"}, status=500)

        details = get_error_details(exc, response)

        self.assertEqual(details, {"reason": "fail"})

    def test_get_error_details_defaults_to_exception_string(self):
        """Fallback to exception string when no response data provided."""
        exc = Exception("Total failure")
        response = Response(None, status=500)

        details = get_error_details(exc, response)

        self.assertEqual(details, {"detail": "Total failure"})

    def test_custom_exception_handler_wraps_response(self):
        """Test that exception handler wraps response in envelope format."""
        exc = ValidationError("Test error")
        context = {}

        response = custom_exception_handler(exc, context)

        self.assertIsNotNone(response)
        self.assertIn("message", response.data)
        self.assertIn("data", response.data)
        self.assertIn("errors", response.data)
        self.assertIn("meta", response.data)
        self.assertIsNone(response.data["data"])
        self.assertIsNone(response.data["meta"])

    def test_custom_exception_handler_skips_202_response(self):
        """Test that handler skips 202 responses."""
        exc = MagicMock()
        context = {}

        with patch("apps.common.exceptions.exception_handler") as mock_handler:
            mock_response = Response(status=202)
            mock_handler.return_value = mock_response

            response = custom_exception_handler(exc, context)

            self.assertEqual(response.status_code, 202)
            # Response should not be wrapped - 202 has no content
            # so data is None, not a dict
            self.assertIsNone(response.data)

    def test_custom_exception_handler_skips_204_response(self):
        """Test that handler skips 204 responses."""
        exc = MagicMock()
        context = {}

        with patch("apps.common.exceptions.exception_handler") as mock_handler:
            mock_response = Response(status=204)
            mock_handler.return_value = mock_response

            response = custom_exception_handler(exc, context)

            self.assertEqual(response.status_code, 204)

    def test_custom_exception_handler_returns_none_for_unhandled(self):
        """Test that handler returns None for unhandled exceptions."""
        exc = Exception("Unhandled")
        context = {}

        with patch("apps.common.exceptions.exception_handler") as mock_handler:
            mock_handler.return_value = None

            response = custom_exception_handler(exc, context)

            self.assertIsNone(response)
