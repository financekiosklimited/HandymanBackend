"""Tests for profile models."""

from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image as PILImage

from apps.accounts.models import User, UserRole
from apps.profiles.models import HandymanProfile, HomeownerProfile


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
        self.assertIn("avatar.jpg", profile.avatar_url)

    def test_handyman_avatar_url_when_no_avatar(self):
        """Test avatar_url property returns None when no avatar."""
        profile = HandymanProfile.objects.create(user=self.user, display_name="Test")
        self.assertIsNone(profile.avatar_url)


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
        self.assertIn("avatar.jpg", profile.avatar_url)

    def test_homeowner_avatar_url_when_no_avatar(self):
        """Test avatar_url property returns None when no avatar."""
        profile = HomeownerProfile.objects.create(user=self.user, display_name="Test")
        self.assertIsNone(profile.avatar_url)
