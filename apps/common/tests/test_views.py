"""
Tests for common views.
"""

from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.models import CountryPhoneCode


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


class TestCountryPhoneCodeListView(APITestCase):
    """Tests for country phone code list view."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/country-codes/"

        # Create test country codes
        CountryPhoneCode.objects.create(
            country_code="ID",
            country_name="Indonesia",
            dial_code="+62",
            flag_emoji="🇮🇩",
            is_active=True,
            display_order=1,
        )
        CountryPhoneCode.objects.create(
            country_code="CA",
            country_name="Canada",
            dial_code="+1",
            flag_emoji="🇨🇦",
            is_active=True,
            display_order=2,
        )
        CountryPhoneCode.objects.create(
            country_code="XX",
            country_name="Inactive Country",
            dial_code="+99",
            flag_emoji="",
            is_active=False,
            display_order=3,
        )

    def test_list_country_codes_success(self):
        """Test listing country codes returns only active ones."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Country codes retrieved successfully"
        )
        self.assertEqual(len(response.data["data"]), 2)  # Only active codes

    def test_list_country_codes_is_public(self):
        """Test that country codes list is accessible without authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_country_codes_returns_correct_fields(self):
        """Test that country codes return correct fields."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first_code = response.data["data"][0]
        self.assertIn("country_code", first_code)
        self.assertIn("country_name", first_code)
        self.assertIn("dial_code", first_code)
        self.assertIn("flag_emoji", first_code)

    def test_list_country_codes_ordered_by_display_order(self):
        """Test that country codes are ordered by display_order."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        codes = response.data["data"]
        self.assertEqual(codes[0]["country_code"], "ID")  # display_order=1
        self.assertEqual(codes[1]["country_code"], "CA")  # display_order=2
