"""Tests for common management commands."""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import User
from apps.common.models import CountryPhoneCode
from apps.jobs.models import Job


class SeedCountryCodesTests(TestCase):
    """Test cases for seed_country_codes command."""

    def test_seed_country_codes(self):
        """Test seed_country_codes command."""
        out = StringIO()
        call_command("seed_country_codes", stdout=out)
        self.assertIn("Seeding complete!", out.getvalue())
        self.assertTrue(CountryPhoneCode.objects.exists())

        # Test idempotency (skip existing)
        call_command("seed_country_codes", stdout=out)
        self.assertIn("Skipped (exists)", out.getvalue())

        # Test force update
        call_command("seed_country_codes", "--force", stdout=out)
        self.assertIn("Updated:", out.getvalue())


class DummyDataCommandsTests(TestCase):
    """Test cases for dummy data commands."""

    @patch("apps.common.management.commands.generate_dummy_data.NUM_HOMEOWNERS", 2)
    @patch("apps.common.management.commands.generate_dummy_data.NUM_HANDYMEN", 2)
    @patch("apps.common.management.commands.generate_dummy_data.NUM_JOBS", 5)
    def test_generate_and_delete_dummy_data(self):
        """Test generating and deleting dummy data."""
        # First, we need categories and cities for generate_dummy_data to work
        call_command("seed_categories", stdout=StringIO())
        call_command("seed_cities", stdout=StringIO())

        # Generate dummy data
        out_gen = StringIO()
        call_command("generate_dummy_data", stdout=out_gen)
        self.assertIn("Done! All dummy data has is_dummy=True.", out_gen.getvalue())

        # Check counts (based on patched constants)
        self.assertEqual(User.objects.filter(is_dummy=True).count(), 4)
        self.assertEqual(Job.objects.filter(is_dummy=True).count(), 5)

        # Delete dummy data (no confirmation)
        out_del = StringIO()
        call_command("delete_dummy_data", "--yes", stdout=out_del)
        self.assertIn("Done!", out_del.getvalue())

        # Check counts
        self.assertEqual(User.objects.filter(is_dummy=True).count(), 0)
        self.assertEqual(Job.objects.filter(is_dummy=True).count(), 0)

    def test_delete_dummy_data_none_found(self):
        """Test delete_dummy_data when no dummy data exists."""
        out = StringIO()
        call_command("delete_dummy_data", "--yes", stdout=out)
        self.assertIn("No dummy data found.", out.getvalue())

    @patch("builtins.input", return_value="n")
    def test_delete_dummy_data_aborted(self, mock_input):
        """Test delete_dummy_data when user aborts."""
        # Create some dummy data
        User.objects.create(email="dummy@example.com", is_dummy=True)

        out = StringIO()
        call_command("delete_dummy_data", stdout=out)
        self.assertIn("Aborted.", out.getvalue())
        self.assertTrue(User.objects.filter(is_dummy=True).exists())


class GenerateDummyDataEdgeCasesTests(TestCase):
    """Test edge cases for generate_dummy_data command."""

    def test_generate_dummy_data_seeds_automatically(self):
        """Test that categories and cities are seeded if they don't exist."""
        from apps.jobs.models import City, JobCategory

        JobCategory.objects.all().delete()
        City.objects.all().delete()

        out = StringIO()
        with patch(
            "apps.common.management.commands.generate_dummy_data.NUM_HOMEOWNERS", 1
        ):
            with patch(
                "apps.common.management.commands.generate_dummy_data.NUM_HANDYMEN", 1
            ):
                with patch(
                    "apps.common.management.commands.generate_dummy_data.NUM_JOBS", 1
                ):
                    call_command("generate_dummy_data", stdout=out)

        self.assertTrue(JobCategory.objects.filter(is_active=True).exists())
        self.assertTrue(City.objects.filter(is_active=True).exists())
        self.assertIn("Seeding job categories...", out.getvalue())
        self.assertIn("Seeding cities...", out.getvalue())

    @patch("apps.common.management.commands.generate_dummy_data.NUM_HOMEOWNERS", 1)
    @patch("apps.common.management.commands.generate_dummy_data.NUM_HANDYMEN", 1)
    @patch("apps.common.management.commands.generate_dummy_data.NUM_JOBS", 1)
    def test_generate_dummy_data_idempotency(self):
        """Test that running the command twice skips existing users."""
        call_command("seed_categories", stdout=StringIO())
        call_command("seed_cities", stdout=StringIO())

        out1 = StringIO()
        call_command("generate_dummy_data", stdout=out1)

        out2 = StringIO()
        call_command("generate_dummy_data", stdout=out2)

        # Should not create duplicate users with same email
        # Fixed: Changed 'role__role' to 'roles__role'
        self.assertEqual(
            User.objects.filter(is_dummy=True, roles__role="homeowner").count(), 1
        )
        self.assertEqual(
            User.objects.filter(is_dummy=True, roles__role="handyman").count(), 1
        )

    @patch("apps.common.management.commands.generate_dummy_data.NUM_HOMEOWNERS", 1)
    @patch("apps.common.management.commands.generate_dummy_data.NUM_HANDYMEN", 1)
    @patch("apps.common.management.commands.generate_dummy_data.NUM_JOBS", 1)
    def test_generate_dummy_data_font_oserror(self):
        """Test handling of OSError when loading fonts."""
        from PIL import ImageFont

        orig_truetype = ImageFont.truetype

        def mock_truetype(font=None, size=10, index=0, encoding="", layout_engine=None):
            if font and "/System/Library/Fonts" in str(font):
                raise OSError("Font not found")
            return orig_truetype(font, size, index, encoding, layout_engine)

        with patch("PIL.ImageFont.truetype", side_effect=mock_truetype):
            call_command("seed_categories", stdout=StringIO())
            call_command("seed_cities", stdout=StringIO())

            out = StringIO()
            call_command("generate_dummy_data", stdout=out)
            self.assertIn("Done!", out.getvalue())

    @patch("apps.common.management.commands.generate_dummy_data.NUM_HOMEOWNERS", 0)
    @patch("apps.common.management.commands.generate_dummy_data.NUM_HANDYMEN", 0)
    @patch("apps.common.management.commands.generate_dummy_data.NUM_JOBS", 1)
    def test_generate_dummy_data_no_coords(self):
        """Test _vary_coordinates with None values."""
        from apps.jobs.models import City, JobCategory

        call_command("seed_categories", stdout=StringIO())
        cat = JobCategory.objects.first()
        city = City.objects.create(
            name="NoCoordCity", province_code="ON", latitude=None, longitude=None
        )

        # We need at least one homeowner to create a job
        user = User.objects.create_user(
            email="h1@example.com", password="p", is_dummy=True
        )
        from apps.accounts.models import UserRole
        from apps.profiles.models import HomeownerProfile

        UserRole.objects.create(user=user, role="homeowner")
        HomeownerProfile.objects.create(user=user, display_name="H1")

        from apps.common.management.commands.generate_dummy_data import Command

        cmd = Command()
        lat, lng = cmd._vary_coordinates(None, None)
        self.assertIsNone(lat)
        self.assertIsNone(lng)

    @patch("apps.common.management.commands.generate_dummy_data.NUM_HOMEOWNERS", 1)
    @patch("apps.common.management.commands.generate_dummy_data.NUM_HANDYMEN", 1)
    @patch("apps.common.management.commands.generate_dummy_data.NUM_JOBS", 1)
    def test_generate_dummy_data_no_pillow(self):
        """Test handling when Pillow is not installed."""
        with patch(
            "apps.common.management.commands.generate_dummy_data.NUM_HOMEOWNERS", 1
        ):
            with patch(
                "apps.common.management.commands.generate_dummy_data.NUM_HANDYMEN", 1
            ):
                with patch(
                    "apps.common.management.commands.generate_dummy_data.NUM_JOBS", 1
                ):
                    with patch.dict("sys.modules", {"PIL": None}):
                        out = StringIO()
                        call_command("generate_dummy_data", stdout=out)
                        self.assertIn(
                            "Pillow not installed, skipping images", out.getvalue()
                        )
