"""Tests for profiles management commands."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.profiles.models import HandymanCategory


class SeedHandymanCategoriesTests(TestCase):
    """Test cases for seed_handyman_categories command."""

    def test_seed_handyman_categories(self):
        """Test seed_handyman_categories command creates categories."""
        out = StringIO()
        call_command("seed_handyman_categories", stdout=out)
        output = out.getvalue()

        self.assertIn("Created category:", output)
        self.assertTrue(HandymanCategory.objects.exists())

        # Verify expected categories were created
        expected_categories = [
            "Plumbing",
            "Electrical",
            "Carpentry",
            "Painting",
            "Cleaning",
            "Gardening",
            "Masonry",
            "General Repairs",
        ]
        for category_name in expected_categories:
            self.assertTrue(
                HandymanCategory.objects.filter(name=category_name).exists(),
                f"Category '{category_name}' was not created",
            )

    def test_seed_handyman_categories_idempotency(self):
        """Test command is idempotent (skips existing categories)."""
        # Run command first time
        out1 = StringIO()
        call_command("seed_handyman_categories", stdout=out1)

        initial_count = HandymanCategory.objects.count()

        # Run command second time
        out2 = StringIO()
        call_command("seed_handyman_categories", stdout=out2)

        # Should not create duplicates
        self.assertEqual(HandymanCategory.objects.count(), initial_count)
        self.assertIn("Category already exists:", out2.getvalue())

    def test_seed_handyman_categories_with_existing_partial(self):
        """Test command when some categories already exist."""
        # Create one category manually
        HandymanCategory.objects.create(name="Plumbing", description="Existing")

        out = StringIO()
        call_command("seed_handyman_categories", stdout=out)
        output = out.getvalue()

        # Should show existing for Plumbing
        self.assertIn("Category already exists: Plumbing", output)
        # Should create others
        self.assertIn("Created category:", output)

        # Verify all categories exist
        self.assertEqual(HandymanCategory.objects.count(), 8)
