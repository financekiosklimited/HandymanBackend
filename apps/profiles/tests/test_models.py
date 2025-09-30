"""Tests for profile models."""

from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.profiles.models import CustomerProfile, HandymanProfile


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


class CustomerProfileModelTests(TestCase):
    """Test cases for CustomerProfile model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="customer")

    def test_create_customer_profile(self):
        """Test creating a customer profile."""
        profile = CustomerProfile.objects.create(
            user=self.user,
            display_name="Jane Customer",
            phone_number="+1234567890",
            address="456 Oak Ave",
        )
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.display_name, "Jane Customer")
        self.assertEqual(profile.phone_number, "+1234567890")
        self.assertEqual(profile.address, "456 Oak Ave")
        self.assertIsNotNone(profile.created_at)
        self.assertIsNotNone(profile.updated_at)
        self.assertIsNotNone(profile.public_id)

    def test_customer_profile_str_representation(self):
        """Test string representation of customer profile."""
        profile = CustomerProfile.objects.create(
            user=self.user, display_name="Test Customer"
        )
        self.assertEqual(str(profile), "Customer: Test Customer")

    def test_customer_profile_optional_fields(self):
        """Test customer profile with optional fields blank."""
        profile = CustomerProfile.objects.create(
            user=self.user, display_name="Minimal Profile"
        )
        self.assertEqual(profile.phone_number, "")
        self.assertEqual(profile.address, "")

    def test_customer_profile_ordering(self):
        """Test profiles are ordered by created_at descending."""
        user2 = User.objects.create_user(
            email="customer2@example.com", password="testpass123"
        )
        UserRole.objects.create(user=user2, role="customer")
        profile1 = CustomerProfile.objects.create(user=self.user, display_name="First")
        profile2 = CustomerProfile.objects.create(user=user2, display_name="Second")

        profiles = CustomerProfile.objects.all()
        self.assertEqual(profiles[0], profile2)
        self.assertEqual(profiles[1], profile1)

    def test_customer_profile_cascade_delete(self):
        """Test profile is deleted when user is deleted."""
        profile = CustomerProfile.objects.create(
            user=self.user, display_name="Delete Test"
        )
        profile_id = profile.id
        self.user.delete()
        self.assertFalse(CustomerProfile.objects.filter(id=profile_id).exists())

    def test_customer_profile_one_to_one_relationship(self):
        """Test one-to-one relationship with user."""
        profile = CustomerProfile.objects.create(user=self.user, display_name="Test")
        self.assertEqual(self.user.customer_profile, profile)
