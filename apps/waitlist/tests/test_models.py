"""Tests for WaitlistEntry model."""

from django.test import TestCase

from apps.waitlist.models import WaitlistEntry


class WaitlistEntryModelTests(TestCase):
    """Test cases for WaitlistEntry model."""

    def test_create_homeowner_entry(self):
        """Test creating a homeowner waitlist entry."""
        entry = WaitlistEntry.objects.create(
            user_name="John Doe",
            email="john@example.com",
            user_type=WaitlistEntry.HOMEOWNER,
        )
        self.assertEqual(entry.user_name, "John Doe")
        self.assertEqual(entry.email, "john@example.com")
        self.assertEqual(entry.user_type, WaitlistEntry.HOMEOWNER)
        self.assertIsNotNone(entry.created_at)
        self.assertIsNotNone(entry.updated_at)

    def test_create_handyman_entry(self):
        """Test creating a handyman waitlist entry."""
        entry = WaitlistEntry.objects.create(
            user_name="Jane Smith",
            email="jane@example.com",
            user_type=WaitlistEntry.HANDYMAN,
        )
        self.assertEqual(entry.user_name, "Jane Smith")
        self.assertEqual(entry.email, "jane@example.com")
        self.assertEqual(entry.user_type, WaitlistEntry.HANDYMAN)

    def test_str_representation(self):
        """Test string representation of waitlist entry."""
        entry = WaitlistEntry.objects.create(
            user_name="Test User",
            email="test@example.com",
            user_type=WaitlistEntry.HOMEOWNER,
        )
        expected = "test@example.com (homeowner)"
        self.assertEqual(str(entry), expected)

    def test_ordering(self):
        """Test entries are ordered by created_at descending."""
        entry1 = WaitlistEntry.objects.create(
            user_name="User 1",
            email="user1@example.com",
            user_type=WaitlistEntry.HOMEOWNER,
        )
        entry2 = WaitlistEntry.objects.create(
            user_name="User 2",
            email="user2@example.com",
            user_type=WaitlistEntry.HANDYMAN,
        )
        entries = WaitlistEntry.objects.all()
        self.assertEqual(entries[0], entry2)
        self.assertEqual(entries[1], entry1)
