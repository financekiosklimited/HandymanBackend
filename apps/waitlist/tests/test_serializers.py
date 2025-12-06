"""Tests for WaitlistEntrySerializer."""

from django.test import TestCase

from apps.waitlist.models import WaitlistEntry
from apps.waitlist.serializers import WaitlistEntrySerializer


class WaitlistEntrySerializerTests(TestCase):
    """Test cases for WaitlistEntrySerializer."""

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        data = {
            "user_name": "John Doe",
            "email": "john@example.com",
            "user_type": WaitlistEntry.HOMEOWNER,
        }
        serializer = WaitlistEntrySerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_serializer_missing_required_fields(self):
        """Test serializer with missing required fields."""
        data = {"user_name": "John Doe"}
        serializer = WaitlistEntrySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
        self.assertIn("user_type", serializer.errors)

    def test_serializer_invalid_email(self):
        """Test serializer with invalid email format."""
        data = {
            "user_name": "John Doe",
            "email": "invalid-email",
            "user_type": WaitlistEntry.HOMEOWNER,
        }
        serializer = WaitlistEntrySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_serializer_invalid_user_type(self):
        """Test serializer with invalid user type."""
        data = {
            "user_name": "John Doe",
            "email": "john@example.com",
            "user_type": "invalid_type",
        }
        serializer = WaitlistEntrySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("user_type", serializer.errors)

    def test_serializer_create_new_entry(self):
        """Test serializer creates new entry."""
        data = {
            "user_name": "John Doe",
            "email": "john@example.com",
            "user_type": WaitlistEntry.HOMEOWNER,
        }
        serializer = WaitlistEntrySerializer(data=data)
        self.assertTrue(serializer.is_valid())
        entry = serializer.save()
        self.assertIsNotNone(entry.id)
        self.assertEqual(entry.user_name, "John Doe")
        self.assertTrue(serializer._created)

    def test_serializer_update_existing_entry(self):
        """Test serializer updates existing entry with same name, email, and user_type."""
        # Create initial entry
        initial_data = {
            "user_name": "John Doe",
            "email": "john@example.com",
            "user_type": WaitlistEntry.HOMEOWNER,
        }
        serializer1 = WaitlistEntrySerializer(data=initial_data)
        self.assertTrue(serializer1.is_valid())
        entry1 = serializer1.save()
        initial_updated_at = entry1.updated_at

        # Try to create same entry
        serializer2 = WaitlistEntrySerializer(data=initial_data)
        self.assertTrue(serializer2.is_valid())
        entry2 = serializer2.save()

        # Should be same entry
        self.assertEqual(entry1.id, entry2.id)
        self.assertFalse(serializer2._created)
        # updated_at should be refreshed
        self.assertGreaterEqual(entry2.updated_at, initial_updated_at)

    def test_serializer_read_only_fields(self):
        """Test that read-only fields cannot be set during creation."""
        data = {
            "id": 999,
            "user_name": "John Doe",
            "email": "john@example.com",
            "user_type": WaitlistEntry.HOMEOWNER,
            "created_at": "2020-01-01T00:00:00Z",
            "updated_at": "2020-01-01T00:00:00Z",
        }
        serializer = WaitlistEntrySerializer(data=data)
        self.assertTrue(serializer.is_valid())
        entry = serializer.save()
        # ID should be auto-generated, not 999
        self.assertNotEqual(entry.id, 999)
