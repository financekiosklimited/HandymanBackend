"""Tests for profile models."""

from decimal import Decimal
from io import BytesIO

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image as PILImage

from apps.accounts.models import User, UserRole
from apps.jobs.models import City
from apps.profiles.models import HandymanCategory, HandymanProfile, HomeownerProfile


class HandymanCategoryModelTests(TestCase):
    """Test cases for HandymanCategory model."""

    def test_create_handyman_category(self):
        """Test creating a handyman category."""
        category = HandymanCategory.objects.create(
            name="Electrical", description="Electrical services"
        )
        self.assertEqual(category.name, "Electrical")
        self.assertEqual(category.description, "Electrical services")
        self.assertTrue(category.is_active)
        self.assertIsNotNone(category.public_id)
        self.assertIsNotNone(category.created_at)
        self.assertIsNotNone(category.updated_at)

    def test_handyman_category_str_representation(self):
        """Test string representation of handyman category."""
        category = HandymanCategory.objects.create(name="Plumbing")
        self.assertEqual(str(category), "Plumbing")

    def test_handyman_category_ordering(self):
        """Test categories are ordered by name."""
        HandymanCategory.objects.create(name="Plumbing")
        HandymanCategory.objects.create(name="Electrical")
        HandymanCategory.objects.create(name="Carpentry")

        categories = HandymanCategory.objects.all()
        self.assertEqual(categories[0].name, "Carpentry")
        self.assertEqual(categories[1].name, "Electrical")
        self.assertEqual(categories[2].name, "Plumbing")

    def test_handyman_category_unique_name(self):
        """Test category name must be unique."""
        from django.db import IntegrityError

        HandymanCategory.objects.create(name="Plumbing")
        with self.assertRaises(IntegrityError):
            HandymanCategory.objects.create(name="Plumbing")

    def test_handyman_category_is_active_default(self):
        """Test is_active defaults to True."""
        category = HandymanCategory.objects.create(name="Painting")
        self.assertTrue(category.is_active)

    def test_handyman_category_blank_description(self):
        """Test category can have blank description."""
        category = HandymanCategory.objects.create(name="Cleaning")
        self.assertEqual(category.description, "")


class HandymanProfileModelTests(TestCase):
    """Test cases for HandymanProfile model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="handyman")

    def test_create_handyman_profile(self):
        """Test creating a handyman profile."""
        profile = HandymanProfile.objects.create(
            user=self.user,
            display_name="John the Handyman",
            phone_number="+1234567890",
            address="123 Main St",
        )
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.display_name, "John the Handyman")
        self.assertEqual(profile.phone_number, "+1234567890")
        self.assertEqual(profile.address, "123 Main St")
        self.assertIsNone(profile.rating)
        self.assertIsNotNone(profile.created_at)
        self.assertIsNotNone(profile.updated_at)
        self.assertIsNotNone(profile.public_id)

    def test_handyman_profile_with_rating(self):
        """Test handyman profile with rating."""
        profile = HandymanProfile.objects.create(
            user=self.user,
            display_name="Jane Smith",
            rating=Decimal("4.75"),
        )
        self.assertEqual(profile.rating, Decimal("4.75"))

    def test_handyman_profile_str_representation(self):
        """Test string representation of handyman profile."""
        profile = HandymanProfile.objects.create(
            user=self.user, display_name="Test Handyman"
        )
        self.assertEqual(str(profile), "Handyman: Test Handyman")

    def test_handyman_profile_optional_fields(self):
        """Test handyman profile with optional fields blank."""
        profile = HandymanProfile.objects.create(
            user=self.user, display_name="Minimal Profile"
        )
        self.assertEqual(profile.phone_number, "")
        self.assertEqual(profile.address, "")
        self.assertIsNone(profile.rating)

    def test_handyman_profile_ordering(self):
        """Test profiles are ordered by created_at descending."""
        user2 = User.objects.create_user(
            email="handyman2@example.com", password="testpass123"
        )
        UserRole.objects.create(user=user2, role="handyman")
        profile1 = HandymanProfile.objects.create(user=self.user, display_name="First")
        profile2 = HandymanProfile.objects.create(user=user2, display_name="Second")

        profiles = HandymanProfile.objects.all()
        self.assertEqual(profiles[0], profile2)
        self.assertEqual(profiles[1], profile1)

    def test_handyman_profile_cascade_delete(self):
        """Test profile is deleted when user is deleted."""
        profile = HandymanProfile.objects.create(
            user=self.user, display_name="Delete Test"
        )
        profile_id = profile.id
        self.user.delete()
        self.assertFalse(HandymanProfile.objects.filter(id=profile_id).exists())

    def test_handyman_profile_one_to_one_relationship(self):
        """Test one-to-one relationship with user."""
        profile = HandymanProfile.objects.create(user=self.user, display_name="Test")
        self.assertEqual(self.user.handyman_profile, profile)

    def test_handyman_avatar_url_when_avatar_exists(self):
        """Test avatar_url property returns URL when avatar is set."""
        # Create a simple image
        image = PILImage.new("RGB", (100, 100), color="red")
        image_file = BytesIO()
        image.save(image_file, format="JPEG")
        image_file.seek(0)

        avatar = SimpleUploadedFile(
            "avatar.jpg", image_file.read(), content_type="image/jpeg"
        )

        profile = HandymanProfile.objects.create(
            user=self.user, display_name="Test", avatar=avatar
        )

        self.assertIsNotNone(profile.avatar_url)
        self.assertIn("/handyman/avatars/", profile.avatar_url)
        self.assertTrue(profile.avatar_url.endswith(".jpg"))

    def test_handyman_avatar_url_when_no_avatar(self):
        """Test avatar_url property returns None when no avatar."""
        profile = HandymanProfile.objects.create(user=self.user, display_name="Test")
        self.assertIsNone(profile.avatar_url)

    def test_handyman_profile_with_category(self):
        """Test handyman profile with category relationship."""
        category = HandymanCategory.objects.create(name="Electrical")
        profile = HandymanProfile.objects.create(
            user=self.user,
            display_name="Electrician",
            category=category,
            job_title="Senior Electrician",
        )
        self.assertEqual(profile.category, category)
        self.assertEqual(profile.job_title, "Senior Electrician")
        # Test reverse relationship
        self.assertIn(profile, category.handymen.all())

    def test_handyman_profile_category_set_null_on_delete(self):
        """Test category is set to null when deleted (SET_NULL)."""
        category = HandymanCategory.objects.create(name="Plumbing")
        profile = HandymanProfile.objects.create(
            user=self.user, display_name="Plumber", category=category
        )
        category.delete()
        profile.refresh_from_db()
        self.assertIsNone(profile.category)
        # Profile should still exist
        self.assertTrue(HandymanProfile.objects.filter(id=profile.id).exists())

    def test_handyman_profile_new_fields(self):
        """Test new fields on handyman profile."""
        from datetime import date

        category = HandymanCategory.objects.create(name="Carpentry")
        profile = HandymanProfile.objects.create(
            user=self.user,
            display_name="Carpenter",
            job_title="Master Carpenter",
            category=category,
            id_number="ID123456",
            date_of_birth=date(1990, 5, 15),
        )
        self.assertEqual(profile.job_title, "Master Carpenter")
        self.assertEqual(profile.category.name, "Carpentry")
        self.assertEqual(profile.id_number, "ID123456")
        self.assertEqual(profile.date_of_birth, date(1990, 5, 15))

    def test_handyman_profile_invalid_latitude_validation(self):
        """Test handyman profile latitude must be between -90 and 90."""
        profile = HandymanProfile(
            user=self.user,
            display_name="Invalid Latitude",
            latitude=Decimal("91.0"),
            longitude=Decimal("-79.347015"),
        )

        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_handyman_profile_latitude_without_longitude_validation(self):
        """Test handyman profile cannot have latitude without longitude."""
        profile = HandymanProfile(
            user=self.user,
            display_name="Missing Longitude",
            latitude=Decimal("43.651070"),
        )

        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_handyman_profile_invalid_longitude_validation(self):
        """Test handyman profile longitude must be between -180 and 180."""
        profile = HandymanProfile(
            user=self.user,
            display_name="Invalid Longitude",
            latitude=Decimal("43.651070"),
            longitude=Decimal("181.0"),
        )

        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_handyman_profile_valid_coordinates_pass_model_validation(self):
        """Test handyman profile accepts valid latitude and longitude values."""
        profile = HandymanProfile(
            user=self.user,
            display_name="Valid Coordinates",
            latitude=Decimal("43.651070"),
            longitude=Decimal("-79.347015"),
        )

        profile.full_clean()

    def test_handyman_profile_can_store_canonical_city_and_refresh_timestamp(self):
        """Test handyman profile stores canonical city metadata for refresh flows."""
        city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            latitude=Decimal("43.653226"),
            longitude=Decimal("-79.383184"),
        )
        last_location_updated_at = timezone.now()

        profile = HandymanProfile.objects.create(
            user=self.user,
            display_name="Located Handyman",
            latitude=Decimal("43.651070"),
            longitude=Decimal("-79.347015"),
            current_city=city,
            last_location_updated_at=last_location_updated_at,
        )

        self.assertEqual(profile.current_city, city)
        self.assertEqual(
            profile.last_location_updated_at,
            last_location_updated_at,
        )


class HomeownerProfileModelTests(TestCase):
    """Test cases for HomeownerProfile model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="homeowner")

    def test_create_homeowner_profile(self):
        """Test creating a homeowner profile."""
        profile = HomeownerProfile.objects.create(
            user=self.user,
            display_name="Jane Homeowner",
            phone_number="+1234567890",
            address="456 Oak Ave",
        )
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.display_name, "Jane Homeowner")
        self.assertEqual(profile.phone_number, "+1234567890")
        self.assertEqual(profile.address, "456 Oak Ave")
        self.assertIsNotNone(profile.created_at)
        self.assertIsNotNone(profile.updated_at)
        self.assertIsNotNone(profile.public_id)

    def test_homeowner_profile_str_representation(self):
        """Test string representation of homeowner profile."""
        profile = HomeownerProfile.objects.create(
            user=self.user, display_name="Test Homeowner"
        )
        self.assertEqual(str(profile), "Homeowner: Test Homeowner")

    def test_homeowner_profile_optional_fields(self):
        """Test homeowner profile with optional fields blank."""
        profile = HomeownerProfile.objects.create(
            user=self.user, display_name="Minimal Profile"
        )
        self.assertEqual(profile.phone_number, "")
        self.assertEqual(profile.address, "")

    def test_homeowner_profile_ordering(self):
        """Test profiles are ordered by created_at descending."""
        user2 = User.objects.create_user(
            email="homeowner2@example.com", password="testpass123"
        )
        UserRole.objects.create(user=user2, role="homeowner")
        profile1 = HomeownerProfile.objects.create(user=self.user, display_name="First")
        profile2 = HomeownerProfile.objects.create(user=user2, display_name="Second")

        profiles = HomeownerProfile.objects.all()
        self.assertEqual(profiles[0], profile2)
        self.assertEqual(profiles[1], profile1)

    def test_homeowner_profile_cascade_delete(self):
        """Test profile is deleted when user is deleted."""
        profile = HomeownerProfile.objects.create(
            user=self.user, display_name="Delete Test"
        )
        profile_id = profile.id
        self.user.delete()
        self.assertFalse(HomeownerProfile.objects.filter(id=profile_id).exists())

    def test_homeowner_profile_one_to_one_relationship(self):
        """Test one-to-one relationship with user."""
        profile = HomeownerProfile.objects.create(user=self.user, display_name="Test")
        self.assertEqual(self.user.homeowner_profile, profile)

    def test_homeowner_avatar_url_when_avatar_exists(self):
        """Test avatar_url property returns URL when avatar is set."""
        # Create a simple image
        image = PILImage.new("RGB", (100, 100), color="blue")
        image_file = BytesIO()
        image.save(image_file, format="JPEG")
        image_file.seek(0)

        avatar = SimpleUploadedFile(
            "avatar.jpg", image_file.read(), content_type="image/jpeg"
        )

        profile = HomeownerProfile.objects.create(
            user=self.user, display_name="Test", avatar=avatar
        )

        self.assertIsNotNone(profile.avatar_url)
        self.assertIn("/homeowner/avatars/", profile.avatar_url)
        self.assertTrue(profile.avatar_url.endswith(".jpg"))

    def test_homeowner_avatar_url_when_no_avatar(self):
        """Test avatar_url property returns None when no avatar."""
        profile = HomeownerProfile.objects.create(user=self.user, display_name="Test")
        self.assertIsNone(profile.avatar_url)

    def test_homeowner_profile_date_of_birth(self):
        """Test homeowner profile with date_of_birth field."""
        from datetime import date

        profile = HomeownerProfile.objects.create(
            user=self.user,
            display_name="Test Homeowner",
            date_of_birth=date(1985, 3, 20),
        )
        self.assertEqual(profile.date_of_birth, date(1985, 3, 20))

    def test_homeowner_profile_can_store_persisted_location_fields(self):
        """Test homeowner profile stores persisted coordinates and canonical city."""
        city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            latitude=Decimal("43.653226"),
            longitude=Decimal("-79.383184"),
        )
        last_location_updated_at = timezone.now()

        profile = HomeownerProfile.objects.create(
            user=self.user,
            display_name="Located Homeowner",
            latitude=Decimal("43.651070"),
            longitude=Decimal("-79.347015"),
            current_city=city,
            last_location_updated_at=last_location_updated_at,
        )

        self.assertEqual(profile.latitude, Decimal("43.651070"))
        self.assertEqual(profile.longitude, Decimal("-79.347015"))
        self.assertEqual(profile.current_city, city)
        self.assertEqual(
            profile.last_location_updated_at,
            last_location_updated_at,
        )


class GuestLocationSnapshotModelTests(TestCase):
    """Test cases for GuestLocationSnapshot model."""

    def test_guest_location_snapshot_can_store_coordinates_and_city(self):
        """Test guest location snapshot stores coordinates and canonical city."""
        city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            latitude=Decimal("43.653226"),
            longitude=Decimal("-79.383184"),
        )

        try:
            guest_location_snapshot_model = apps.get_model(
                "profiles", "GuestLocationSnapshot"
            )
        except LookupError:
            self.fail("GuestLocationSnapshot model is missing")

        snapshot = guest_location_snapshot_model.objects.create(
            device_token="device-token-123",
            latitude=Decimal("43.651070"),
            longitude=Decimal("-79.347015"),
            current_city=city,
        )

        self.assertEqual(snapshot.device_token, "device-token-123")
        self.assertEqual(snapshot.current_city, city)
        self.assertEqual(snapshot.latitude, Decimal("43.651070"))
        self.assertEqual(snapshot.longitude, Decimal("-79.347015"))

    def test_guest_location_snapshot_can_store_refresh_timestamp(self):
        """Test guest location snapshot stores the latest refresh timestamp."""
        last_location_updated_at = timezone.now()

        try:
            guest_location_snapshot_model = apps.get_model(
                "profiles", "GuestLocationSnapshot"
            )
        except LookupError:
            self.fail("GuestLocationSnapshot model is missing")

        snapshot = guest_location_snapshot_model.objects.create(
            device_token="device-token-456",
            last_location_updated_at=last_location_updated_at,
        )

        self.assertEqual(
            snapshot.last_location_updated_at,
            last_location_updated_at,
        )
