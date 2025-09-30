"""
Tests for common views.
"""

from rest_framework import status
from rest_framework.test import APITestCase


class TestHealthCheckView(APITestCase):
    """Tests for health check view."""

    def test_health_check_returns_ok(self):
        """Test that health check returns ok status."""
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "ok")

    def test_health_check_is_public(self):
        """Test that health check is accessible without authentication."""
        # No authentication headers
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health_check_envelope_format(self):
        """Test that health check uses envelope format."""
        response = self.client.get("/health/")

        self.assertIn("message", response.data)
        self.assertIn("data", response.data)
        self.assertIn("errors", response.data)
        self.assertIn("meta", response.data)
        self.assertIsNone(response.data["data"])
        self.assertIsNone(response.data["errors"])
        self.assertIsNone(response.data["meta"])
