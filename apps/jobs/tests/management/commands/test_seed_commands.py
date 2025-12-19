"""Tests for jobs management commands."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.jobs.models import City, JobCategory


class SeedCommandsTests(TestCase):
    """Test cases for seeding commands in jobs app."""

    def test_seed_categories(self):
        """Test seed_categories command."""
        out = StringIO()
        call_command("seed_categories", stdout=out)
        self.assertIn("Successfully seeded categories", out.getvalue())
        self.assertTrue(JobCategory.objects.exists())

        # Test idempotency (updating)
        call_command("seed_categories", stdout=out)
        self.assertIn("0 created", out.getvalue())

    def test_seed_cities(self):
        """Test seed_cities command."""
        out = StringIO()
        call_command("seed_cities", stdout=out)
        self.assertIn("Successfully seeded cities", out.getvalue())
        self.assertTrue(City.objects.exists())

        # Test idempotency
        call_command("seed_cities", stdout=out)
        self.assertIn("0 created", out.getvalue())
