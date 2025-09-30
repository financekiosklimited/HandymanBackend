"""Tests for profile serializers."""

from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.profiles.models import CustomerProfile, HandymanProfile
from apps.profiles.serializers import (
    CustomerProfileSerializer,
    CustomerProfileUpdateSerializer,
    HandymanProfileSerializer,
    HandymanProfileUpdateSerializer,
)


class CustomerProfileSerializerTests(TestCase):
    """Test cases for CustomerProfileSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="customer@example.com", password="testpass123"
        )
        UserRole.objects.create(user=self.user, role="customer")
        self.profile = CustomerProfile.objects.create(
            user=self.user,
            display_name="Test Customer",
            phone_number="+1234567890",
            address="123 Main St",
        )

    def test_serializer_contains_expected_fields(self):
        """Test serializer contains expected fields."""
        serializer = CustomerProfileSerializer(self.profile)
        self.assertIn("display_name", serializer.data)
        self.assertIn("phone_number", serializer.data)
        self.assertIn("address", serializer.data)
        self.assertIn("created_at", serializer.data)
        self.assertIn("updated_at", serializer.data)

    def test_serializer_field_values(self):
        """Test serializer returns correct field values."""
        serializer = CustomerProfileSerializer(self.profile)
        self.assertEqual(serializer.data["display_name"], "Test Customer")
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
        serializer = CustomerProfileSerializer(self.profile, data=data)
        self.assertTrue(serializer.is_valid())


class CustomerProfileUpdateSerializerTests(TestCase):
    """Test cases for CustomerProfileUpdateSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="customer@example.com", password="testpass123"
        )
        UserRole.objects.create(user=self.user, role="customer")
        self.profile = CustomerProfile.objects.create(
            user=self.user,
            display_name="Test Customer",
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
        serializer = CustomerProfileUpdateSerializer(self.profile, data=data)
        self.assertTrue(serializer.is_valid())

    def test_update_serializer_partial_update(self):
        """Test update serializer with partial data."""
        data = {"display_name": "Partial Update"}
        serializer = CustomerProfileUpdateSerializer(
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
        serializer = CustomerProfileUpdateSerializer(self.profile, data=data)
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
        self.assertIn("phone_number", serializer.data)
        self.assertIn("address", serializer.data)
        self.assertIn("created_at", serializer.data)
        self.assertIn("updated_at", serializer.data)

    def test_serializer_field_values(self):
        """Test serializer returns correct field values."""
        serializer = HandymanProfileSerializer(self.profile)
        self.assertEqual(serializer.data["display_name"], "Test Handyman")
        self.assertEqual(serializer.data["rating"], "4.50")
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
