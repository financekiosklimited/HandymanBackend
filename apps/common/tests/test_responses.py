"""
Tests for response utilities.
"""

from django.test import TestCase
from rest_framework import status

from apps.common.responses import (
    accepted_response,
    conflict_response,
    created_response,
    error_response,
    forbidden_response,
    no_content_response,
    not_found_response,
    success_response,
    throttled_response,
    unauthorized_response,
    validation_error_response,
)


class TestResponseUtilities(TestCase):
    """Tests for response utility functions."""

    def test_success_response_default(self):
        """Test default success response."""
        response = success_response()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success")
        self.assertIsNone(response.data["data"])
        self.assertIsNone(response.data["errors"])
        self.assertIsNone(response.data["meta"])

    def test_success_response_with_data(self):
        """Test success response with data."""
        data = {"key": "value"}
        response = success_response(data=data, message="Operation successful")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Operation successful")
        self.assertEqual(response.data["data"], data)
        self.assertIsNone(response.data["errors"])

    def test_success_response_with_meta(self):
        """Test success response with metadata."""
        meta = {"page": 1, "total": 10}
        response = success_response(meta=meta)

        self.assertEqual(response.data["meta"], meta)

    def test_error_response_default(self):
        """Test default error response."""
        response = error_response()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Error")
        self.assertIsNone(response.data["data"])
        self.assertIsNone(response.data["errors"])

    def test_error_response_with_errors(self):
        """Test error response with error details."""
        errors = {"field": ["Required field"]}
        response = error_response(errors=errors, message="Validation failed")

        self.assertEqual(response.data["message"], "Validation failed")
        self.assertEqual(response.data["errors"], errors)

    def test_created_response(self):
        """Test created response."""
        data = {"id": 1, "name": "New Item"}
        response = created_response(data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Created")
        self.assertEqual(response.data["data"], data)

    def test_accepted_response(self):
        """Test accepted response has JSON body with message."""
        response = accepted_response()

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["message"], "Accepted")
        self.assertIsNone(response.data["data"])
        self.assertIsNone(response.data["errors"])

    def test_no_content_response(self):
        """Test no content response."""
        response = no_content_response()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success")
        self.assertIsNone(response.data["data"])
        self.assertIsNone(response.data["errors"])

    def test_validation_error_response(self):
        """Test validation error response."""
        errors = {"email": ["Invalid email format"]}
        response = validation_error_response(errors)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Validation failed")
        self.assertEqual(response.data["errors"], errors)

    def test_unauthorized_response(self):
        """Test unauthorized response."""
        response = unauthorized_response()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["message"], "Authentication required")
        self.assertIn("auth", response.data["errors"])

    def test_forbidden_response(self):
        """Test forbidden response."""
        response = forbidden_response(message="Access denied")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Access denied")

    def test_not_found_response(self):
        """Test not found response."""
        response = not_found_response()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Not found")
        self.assertIn("detail", response.data["errors"])

    def test_conflict_response(self):
        """Test conflict response."""
        errors = {"email": "Email already exists"}
        response = conflict_response(errors=errors)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["errors"], errors)

    def test_throttled_response(self):
        """Test throttled response."""
        response = throttled_response()

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data["message"], "Rate limit exceeded")
        self.assertIn("throttle", response.data["errors"])
