"""Tests for profile services."""

from decimal import Decimal

from django.test import TestCase

from apps.jobs.models import City


class ProfileLocationServiceTests(TestCase):
    """Test cases for profile location services."""

    def setUp(self):
        """Set up city fixtures for nearest-city resolution tests."""
        self.toronto = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            latitude=Decimal("43.653226"),
            longitude=Decimal("-79.383184"),
            is_active=True,
        )
        self.inactive_city = City.objects.create(
            name="Inactive Toronto",
            province="Ontario",
            province_code="ON",
            slug="inactive-toronto-on",
            latitude=Decimal("43.651070"),
            longitude=Decimal("-79.347015"),
            is_active=False,
        )
        self.ottawa = City.objects.create(
            name="Ottawa",
            province="Ontario",
            province_code="ON",
            slug="ottawa-on",
            latitude=Decimal("45.421530"),
            longitude=Decimal("-75.697193"),
            is_active=True,
        )

    def test_resolve_nearest_city_returns_closest_active_city_for_coordinates(self):
        """Test nearest-city resolution prefers the closest active city."""
        try:
            from apps.profiles.services import ProfileLocationService
        except ImportError:
            self.fail("ProfileLocationService is missing")

        service = ProfileLocationService()

        resolved_city = service.resolve_nearest_city(
            latitude=Decimal("43.650000"),
            longitude=Decimal("-79.360000"),
        )

        self.assertEqual(resolved_city, self.toronto)

    def test_resolve_nearest_city_returns_none_when_coordinates_missing(self):
        """Test nearest-city resolution returns None when coordinates are missing."""
        from apps.profiles.services import ProfileLocationService

        service = ProfileLocationService()

        self.assertIsNone(
            service.resolve_nearest_city(latitude=None, longitude=Decimal("-79.360000"))
        )
        self.assertIsNone(
            service.resolve_nearest_city(latitude=Decimal("43.650000"), longitude=None)
        )

    def test_resolve_nearest_city_can_replace_initial_candidate_with_closer_city(self):
        """Test nearest-city resolution updates when a later city is closer."""
        from apps.profiles.services import ProfileLocationService

        self.toronto.delete()
        self.inactive_city.delete()
        self.ottawa.delete()

        farther_city = City.objects.create(
            name="Farther City",
            province="Ontario",
            province_code="ON",
            slug="farther-city-on",
            latitude=Decimal("45.421530"),
            longitude=Decimal("-75.697193"),
            is_active=True,
        )
        closer_city = City.objects.create(
            name="Closer City",
            province="Ontario",
            province_code="ON",
            slug="closer-city-on",
            latitude=Decimal("43.653226"),
            longitude=Decimal("-79.383184"),
            is_active=True,
        )

        service = ProfileLocationService()

        resolved_city = service.resolve_nearest_city(
            latitude=Decimal("43.650000"),
            longitude=Decimal("-79.360000"),
        )

        self.assertNotEqual(resolved_city, farther_city)
        self.assertEqual(resolved_city, closer_city)
