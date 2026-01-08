"""Tests for profile serializers."""

from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.profiles.models import HandymanCategory, HandymanProfile, HomeownerProfile
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
        self.assertIn("email", serializer.data)
        self.assertIn("phone_number", serializer.data)
        self.assertIn("address", serializer.data)
        self.assertIn("date_of_birth", serializer.data)
        self.assertIn("created_at", serializer.data)
        self.assertIn("updated_at", serializer.data)

    def test_serializer_field_values(self):
        """Test serializer returns correct field values."""
        serializer = HomeownerProfileSerializer(self.profile)
        self.assertEqual(serializer.data["display_name"], "Test Homeowner")
        self.assertEqual(serializer.data["email"], "homeowner@example.com")
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
            "address": "456 Oak Ave",
            "date_of_birth": "1990-01-01",
        }
        serializer = HomeownerProfileUpdateSerializer(self.profile, data=data)
        self.assertTrue(serializer.is_valid())

    def test_update_serializer_age_validation(self):
        """Test update serializer age validation."""
        from datetime import date

        today = date.today()
        under_18 = date(today.year - 17, today.month, today.day)
        data = {"date_of_birth": under_18.isoformat()}
        serializer = HomeownerProfileUpdateSerializer(
            self.profile, data=data, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("date_of_birth", serializer.errors)

        over_18 = date(today.year - 19, today.month, today.day)
        data = {"date_of_birth": over_18.isoformat()}
        serializer = HomeownerProfileUpdateSerializer(
            self.profile, data=data, partial=True
        )
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
        # phone_number should be read-only (not in fields)
        self.assertEqual(self.profile.phone_number, "+1234567890")

    def test_update_serializer_phone_number_is_ignored(self):
        """Test update serializer ignores phone_number if provided."""
        data = {"display_name": "New Name", "phone_number": "+9999999999"}
        serializer = HomeownerProfileUpdateSerializer(self.profile, data=data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.phone_number, "+1234567890")

    def test_update_serializer_empty_optional_fields(self):
        """Test update serializer allows empty optional fields."""
        data = {"display_name": "Name", "phone_number": "", "address": ""}
        serializer = HomeownerProfileUpdateSerializer(self.profile, data=data)
        self.assertTrue(serializer.is_valid())

    def test_update_serializer_null_date_of_birth(self):
        """Test update serializer allows null date_of_birth (covers else branch)."""
        data = {"display_name": "Name", "date_of_birth": None}
        serializer = HomeownerProfileUpdateSerializer(
            self.profile, data=data, partial=True
        )
        self.assertTrue(serializer.is_valid())


class HandymanProfileSerializerTests(TestCase):
    """Test cases for HandymanProfileSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )
        UserRole.objects.create(user=self.user, role="handyman")
        self.category = HandymanCategory.objects.create(name="Electrical")
        self.profile = HandymanProfile.objects.create(
            user=self.user,
            display_name="Test Handyman",
            rating=Decimal("4.50"),
            phone_number="+1234567890",
            address="789 Pine Rd",
            job_title="Electrician",
            category=self.category,
            id_number="ID123",
            date_of_birth="1990-01-01",
        )

    def test_serializer_contains_expected_fields(self):
        """Test serializer contains expected fields."""
        serializer = HandymanProfileSerializer(self.profile)
        self.assertIn("display_name", serializer.data)
        self.assertIn("email", serializer.data)
        self.assertIn("rating", serializer.data)
        self.assertIn("hourly_rate", serializer.data)
        self.assertIn("job_title", serializer.data)
        self.assertIn("category", serializer.data)
        self.assertIn("id_number", serializer.data)
        self.assertIn("date_of_birth", serializer.data)
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
        self.assertEqual(serializer.data["email"], "handyman@example.com")
        self.assertEqual(serializer.data["rating"], "4.50")
        self.assertEqual(serializer.data["hourly_rate"], "75.00")
        self.assertEqual(serializer.data["job_title"], "Electrician")
        self.assertEqual(serializer.data["category"]["name"], "Electrical")
        self.assertEqual(serializer.data["id_number"], "ID123")
        self.assertEqual(serializer.data["date_of_birth"], "1990-01-01")
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
        self.category = HandymanCategory.objects.create(name="Electrical")
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
            "address": "123 New St",
            "job_title": "Master Electrician",
            "category_id": str(self.category.public_id),
            "date_of_birth": "1990-01-01",
        }
        serializer = HandymanProfileUpdateSerializer(self.profile, data=data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.job_title, "Master Electrician")
        self.assertEqual(self.profile.category, self.category)

    def test_update_serializer_age_validation(self):
        """Test update serializer age validation."""
        from datetime import date

        today = date.today()
        under_18 = date(today.year - 17, today.month, today.day)
        data = {"date_of_birth": under_18.isoformat()}
        serializer = HandymanProfileUpdateSerializer(
            self.profile, data=data, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("date_of_birth", serializer.errors)

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
        # phone_number should be read-only (not in fields)
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
        data = {"display_name": "Name", "address": ""}
        serializer = HandymanProfileUpdateSerializer(self.profile, data=data)
        self.assertTrue(serializer.is_valid())

    def test_update_serializer_null_date_of_birth(self):
        """Test update serializer allows null date_of_birth (covers else branch)."""
        data = {"display_name": "Name", "date_of_birth": None}
        serializer = HandymanProfileUpdateSerializer(
            self.profile, data=data, partial=True
        )
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

    def test_homeowner_list_serializer_is_bookmarked_fallback(self):
        """Test is_bookmarked fallback database check when not annotated."""
        from unittest.mock import Mock

        from apps.bookmarks.models import HandymanBookmark

        # Create a homeowner user for the request context
        homeowner_user = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        UserRole.objects.create(user=homeowner_user, role="homeowner")
        HomeownerProfile.objects.create(user=homeowner_user)

        # Create a mock request with authenticated user
        mock_request = Mock()
        mock_request.user = homeowner_user

        # Test without bookmark - should return False via database check
        serializer = HomeownerHandymanListSerializer(
            self.profile, context={"request": mock_request}
        )
        # Profile doesn't have is_bookmarked annotation, so it falls back to DB
        self.assertFalse(serializer.data["is_bookmarked"])

        # Create bookmark
        HandymanBookmark.objects.create(
            homeowner=homeowner_user, handyman_profile=self.profile
        )

        # Test with bookmark - should return True via database check
        serializer = HomeownerHandymanListSerializer(
            self.profile, context={"request": mock_request}
        )
        self.assertTrue(serializer.data["is_bookmarked"])

    def test_homeowner_detail_serializer_is_bookmarked_fallback(self):
        """Test is_bookmarked fallback database check for detail serializer."""
        from unittest.mock import Mock

        from apps.bookmarks.models import HandymanBookmark

        # Create a homeowner user for the request context
        homeowner_user = User.objects.create_user(
            email="homeowner_detail@example.com", password="testpass123"
        )
        UserRole.objects.create(user=homeowner_user, role="homeowner")
        HomeownerProfile.objects.create(user=homeowner_user)

        # Create a mock request with authenticated user
        mock_request = Mock()
        mock_request.user = homeowner_user

        # Test without bookmark - should return False via database check
        serializer = HomeownerHandymanDetailSerializer(
            self.profile, context={"request": mock_request}
        )
        # Profile doesn't have is_bookmarked annotation, so it falls back to DB
        self.assertFalse(serializer.data["is_bookmarked"])

        # Create bookmark
        HandymanBookmark.objects.create(
            homeowner=homeowner_user, handyman_profile=self.profile
        )

        # Test with bookmark - should return True via database check
        serializer = HomeownerHandymanDetailSerializer(
            self.profile, context={"request": mock_request}
        )
        self.assertTrue(serializer.data["is_bookmarked"])


class HandymanProfileUpdateSerializerValidationTests(TestCase):
    """Test cases for HandymanProfileUpdateSerializer validation."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )
        UserRole.objects.create(user=self.user, role="handyman")
        self.profile = HandymanProfile.objects.create(
            user=self.user,
            display_name="Test Handyman",
            latitude=Decimal("43.651070"),
            longitude=Decimal("-79.347015"),
        )

    def test_latitude_out_of_range_fails(self):
        """Test that latitude out of range raises validation error."""
        from apps.profiles.serializers import HandymanProfileUpdateSerializer

        serializer = HandymanProfileUpdateSerializer(
            self.profile,
            data={"latitude": "91.0"},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("latitude", serializer.errors)

    def test_longitude_out_of_range_fails(self):
        """Test that longitude out of range raises validation error."""
        from apps.profiles.serializers import HandymanProfileUpdateSerializer

        serializer = HandymanProfileUpdateSerializer(
            self.profile,
            data={"longitude": "181.0"},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("longitude", serializer.errors)

    def test_negative_latitude_out_of_range_fails(self):
        """Test that negative latitude out of range fails."""
        from apps.profiles.serializers import HandymanProfileUpdateSerializer

        serializer = HandymanProfileUpdateSerializer(
            self.profile,
            data={"latitude": "-91.0"},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("latitude", serializer.errors)

    def test_negative_longitude_out_of_range_fails(self):
        """Test that negative longitude out of range fails."""
        from apps.profiles.serializers import HandymanProfileUpdateSerializer

        serializer = HandymanProfileUpdateSerializer(
            self.profile,
            data={"longitude": "-181.0"},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("longitude", serializer.errors)

    def test_update_serializer_cross_field_validation_with_existing_instance(self):
        """Test coordinate cross-field validation with existing instance data."""
        # Case: instance has lat/lng, update provides only lat as None
        self.profile.latitude = Decimal("43.65")
        self.profile.longitude = Decimal("-79.34")
        self.profile.save()

        # Try to set latitude to None without setting longitude to None
        serializer = HandymanProfileUpdateSerializer(
            self.profile, data={"latitude": None}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

        # Try to set longitude to None without setting latitude to None
        serializer = HandymanProfileUpdateSerializer(
            self.profile, data={"longitude": None}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

        # Setting both to None is valid
        serializer = HandymanProfileUpdateSerializer(
            self.profile, data={"latitude": None, "longitude": None}, partial=True
        )
        self.assertTrue(serializer.is_valid())

    def test_update_serializer_latitude_out_of_range_branch_coverage(self):
        """Specifically target the latitude branch coverage."""
        # This targets line 143->148 branch part (lat is None but lng is not None - should fail cross-field first though)
        # Wait, if lat is None, it should have failed cross-field validation if lng is not None.
        # If both are None, it skips these blocks.
        # The coverage tool says 149->154 branch is missing.
        # Line 148 is `if new_lng is not None:`
        # Line 149 is `if not (-180 <= new_lng <= 180):`
        # 149->154 missing means it never saw a case where new_lng is not None AND it's valid?
        # No, 149->154 means the "else" branch of the "if" at 149 (where it IS in range) was not taken?
        # Or that it didn't see it NOT taken?

        # Let's provide a valid lat and valid lng.
        serializer = HandymanProfileUpdateSerializer(
            self.profile,
            data={"latitude": Decimal("10"), "longitude": Decimal("10")},
            partial=True,
        )
        self.assertTrue(serializer.is_valid())
