"""Tests for profile serializers."""

from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.profiles.models import HandymanProfile, HomeownerProfile
from apps.profiles.serializers import (
    HandymanProfileSerializer,
    HandymanProfileUpdateSerializer,
    HomeownerHandymanDetailSerializer,
    HomeownerHandymanListSerializer,
    HomeownerProfileSerializer,
    HomeownerProfileUpdateSerializer,
)


class HomeownerProfileSerializerTests(TestCase):
    """Test cases for HomeownerProfileSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        UserRole.objects.create(user=self.user, role="homeowner")
        self.profile = HomeownerProfile.objects.create(
            user=self.user,
            display_name="Test Homeowner",
            phone_number="+1234567890",
            address="123 Main St",
        )

    def test_serializer_contains_expected_fields(self):
        """Test serializer contains expected fields."""
        serializer = HomeownerProfileSerializer(self.profile)
        self.assertIn("display_name", serializer.data)
        self.assertIn("phone_number", serializer.data)
        self.assertIn("address", serializer.data)
        self.assertIn("created_at", serializer.data)
        self.assertIn("updated_at", serializer.data)

    def test_serializer_field_values(self):
        """Test serializer returns correct field values."""
        serializer = HomeownerProfileSerializer(self.profile)
        self.assertEqual(serializer.data["display_name"], "Test Homeowner")
        self.assertEqual(serializer.data["phone_number"], "+1234567890")
        self.assertEqual(serializer.data["address"], "123 Main St")

    def test_serializer_read_only_fields(self):
        """Test that created_at and updated_at are read-only."""
        data = {
            "display_name": "New Name",
            "phone_number": "+9876543210",
            "address": "New Address",
            "created_at": "2020-01-01T00:00:00Z",
            "updated_at": "2020-01-01T00:00:00Z",
        }
        serializer = HomeownerProfileSerializer(self.profile, data=data)
        self.assertTrue(serializer.is_valid())


class HomeownerProfileUpdateSerializerTests(TestCase):
    """Test cases for HomeownerProfileUpdateSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        UserRole.objects.create(user=self.user, role="homeowner")
        self.profile = HomeownerProfile.objects.create(
            user=self.user,
            display_name="Test Homeowner",
            phone_number="+1234567890",
            address="123 Main St",
        )

    def test_update_serializer_valid_data(self):
        """Test update serializer with valid data."""
        data = {
            "display_name": "Updated Name",
            "phone_number": "+9876543210",
            "address": "456 Oak Ave",
        }
        serializer = HomeownerProfileUpdateSerializer(self.profile, data=data)
        self.assertTrue(serializer.is_valid())

    def test_update_serializer_partial_update(self):
        """Test update serializer with partial data."""
        data = {"display_name": "Partial Update"}
        serializer = HomeownerProfileUpdateSerializer(
            self.profile, data=data, partial=True
        )
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, "Partial Update")
        # Other fields should remain unchanged
        self.assertEqual(self.profile.phone_number, "+1234567890")

    def test_update_serializer_empty_optional_fields(self):
        """Test update serializer allows empty optional fields."""
        data = {"display_name": "Name", "phone_number": "", "address": ""}
        serializer = HomeownerProfileUpdateSerializer(self.profile, data=data)
        self.assertTrue(serializer.is_valid())


class HandymanProfileSerializerTests(TestCase):
    """Test cases for HandymanProfileSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )
        UserRole.objects.create(user=self.user, role="handyman")
        self.profile = HandymanProfile.objects.create(
            user=self.user,
            display_name="Test Handyman",
            rating=Decimal("4.50"),
            phone_number="+1234567890",
            address="789 Pine Rd",
        )

    def test_serializer_contains_expected_fields(self):
        """Test serializer contains expected fields."""
        serializer = HandymanProfileSerializer(self.profile)
        self.assertIn("display_name", serializer.data)
        self.assertIn("rating", serializer.data)
        self.assertIn("hourly_rate", serializer.data)
        self.assertIn("latitude", serializer.data)
        self.assertIn("longitude", serializer.data)
        self.assertIn("is_active", serializer.data)
        self.assertIn("is_available", serializer.data)
        self.assertIn("is_approved", serializer.data)
        self.assertIn("phone_number", serializer.data)
        self.assertIn("address", serializer.data)
        self.assertIn("created_at", serializer.data)
        self.assertIn("updated_at", serializer.data)

    def test_serializer_field_values(self):
        """Test serializer returns correct field values."""
        self.profile.hourly_rate = Decimal("75.00")
        self.profile.latitude = Decimal("43.651070")
        self.profile.longitude = Decimal("-79.347015")
        self.profile.is_active = True
        self.profile.is_available = True
        self.profile.is_approved = True
        self.profile.save()

        serializer = HandymanProfileSerializer(self.profile)
        self.assertEqual(serializer.data["display_name"], "Test Handyman")
        self.assertEqual(serializer.data["rating"], "4.50")
        self.assertEqual(serializer.data["hourly_rate"], "75.00")
        self.assertEqual(serializer.data["latitude"], "43.651070")
        self.assertEqual(serializer.data["longitude"], "-79.347015")
        self.assertTrue(serializer.data["is_active"])
        self.assertTrue(serializer.data["is_available"])
        self.assertTrue(serializer.data["is_approved"])
        self.assertEqual(serializer.data["phone_number"], "+1234567890")
        self.assertEqual(serializer.data["address"], "789 Pine Rd")

    def test_serializer_null_rating(self):
        """Test serializer handles null rating."""
        self.profile.rating = None
        self.profile.save()
        serializer = HandymanProfileSerializer(self.profile)
        self.assertIsNone(serializer.data["rating"])

    def test_serializer_read_only_fields(self):
        """Test that created_at and updated_at are read-only."""
        data = {
            "display_name": "New Name",
            "rating": "5.00",
            "phone_number": "+9876543210",
            "address": "New Address",
            "created_at": "2020-01-01T00:00:00Z",
            "updated_at": "2020-01-01T00:00:00Z",
        }
        serializer = HandymanProfileSerializer(self.profile, data=data)
        self.assertTrue(serializer.is_valid())


class HandymanProfileUpdateSerializerTests(TestCase):
    """Test cases for HandymanProfileUpdateSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )
        UserRole.objects.create(user=self.user, role="handyman")
        self.profile = HandymanProfile.objects.create(
            user=self.user,
            display_name="Test Handyman",
            rating=Decimal("4.50"),
            phone_number="+1234567890",
            address="789 Pine Rd",
        )

    def test_update_serializer_valid_data(self):
        """Test update serializer with valid data."""
        data = {
            "display_name": "Updated Handyman",
            "phone_number": "+9876543210",
            "address": "123 New St",
        }
        serializer = HandymanProfileUpdateSerializer(self.profile, data=data)
        self.assertTrue(serializer.is_valid())

    def test_update_serializer_partial_update(self):
        """Test update serializer with partial data."""
        data = {"display_name": "Partial Update"}
        serializer = HandymanProfileUpdateSerializer(
            self.profile, data=data, partial=True
        )
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, "Partial Update")
        # Other fields should remain unchanged
        self.assertEqual(self.profile.phone_number, "+1234567890")

    def test_update_serializer_does_not_include_rating(self):
        """Test update serializer doesn't allow updating rating."""
        data = {
            "display_name": "Test",
            "rating": "5.00",  # Should be ignored
        }
        serializer = HandymanProfileUpdateSerializer(
            self.profile, data=data, partial=True
        )
        # Rating should not be in the serializer fields
        self.assertNotIn("rating", serializer.fields)

    def test_update_serializer_empty_optional_fields(self):
        """Test update serializer allows empty optional fields."""
        data = {"display_name": "Name", "phone_number": "", "address": ""}
        serializer = HandymanProfileUpdateSerializer(self.profile, data=data)
        self.assertTrue(serializer.is_valid())

    def test_update_serializer_rejects_hourly_rate_lte_zero(self):
        """Test update serializer rejects non-positive hourly rate."""
        serializer = HandymanProfileUpdateSerializer(
            self.profile, data={"hourly_rate": Decimal("0.00")}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("hourly_rate", serializer.errors)

        serializer = HandymanProfileUpdateSerializer(
            self.profile, data={"hourly_rate": Decimal("-1.00")}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("hourly_rate", serializer.errors)

    def test_update_serializer_requires_lat_lng_together(self):
        """Test update serializer requires latitude/longitude together."""
        serializer = HandymanProfileUpdateSerializer(
            self.profile, data={"latitude": Decimal("43.651070")}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

        serializer = HandymanProfileUpdateSerializer(
            self.profile, data={"longitude": Decimal("-79.347015")}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_update_serializer_rejects_out_of_range_coordinates(self):
        """Test update serializer rejects invalid coordinate ranges."""
        serializer = HandymanProfileUpdateSerializer(
            self.profile,
            data={"latitude": Decimal("91"), "longitude": Decimal("0")},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("latitude", serializer.errors)

        serializer = HandymanProfileUpdateSerializer(
            self.profile,
            data={"latitude": Decimal("0"), "longitude": Decimal("181")},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("longitude", serializer.errors)


class HomeownerHandymanPublicSerializersTests(TestCase):
    """Test cases for homeowner-facing handymen serializers."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )
        UserRole.objects.create(user=self.user, role="handyman")
        self.profile = HandymanProfile.objects.create(
            user=self.user,
            display_name="Test Handyman",
            rating=Decimal("4.50"),
            hourly_rate=Decimal("75.00"),
            latitude=Decimal("43.651070"),
            longitude=Decimal("-79.347015"),
            phone_number="+1234567890",
            address="789 Pine Rd",
        )

    def test_homeowner_list_serializer_hides_sensitive_fields(self):
        """Homeowner list serializer must not expose phone/address/coordinates."""
        serializer = HomeownerHandymanListSerializer(self.profile)
        self.assertNotIn("phone_number", serializer.data)
        self.assertNotIn("address", serializer.data)
        self.assertNotIn("latitude", serializer.data)
        self.assertNotIn("longitude", serializer.data)

    def test_homeowner_detail_serializer_hides_sensitive_fields(self):
        """Homeowner detail serializer must not expose phone/address/coordinates."""
        serializer = HomeownerHandymanDetailSerializer(self.profile)
        self.assertNotIn("phone_number", serializer.data)
        self.assertNotIn("address", serializer.data)
        self.assertNotIn("latitude", serializer.data)
        self.assertNotIn("longitude", serializer.data)
