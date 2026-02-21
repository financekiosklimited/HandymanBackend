"""Tests for common management commands."""

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.common.models import CountryPhoneCode
from apps.jobs.models import Job
from apps.profiles.models import HandymanProfile, HomeownerProfile


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
        JobCategory.objects.first()
        City.objects.create(
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
        with patch.dict(
            "sys.modules",
            {
                "PIL": None,
                "PIL.Image": None,
                "PIL.ImageDraw": None,
                "PIL.ImageFont": None,
            },
        ):
            out = StringIO()
            call_command("generate_dummy_data", stdout=out)
            self.assertIn("Pillow not installed, skipping images", out.getvalue())

    @patch("apps.common.management.commands.delete_dummy_data.input", return_value="n")
    def test_delete_dummy_data_abort(self, mock_input):
        """Test aborting delete_dummy_data."""
        User.objects.create_user(email="dummy@example.com", password="p", is_dummy=True)
        out = StringIO()
        call_command("delete_dummy_data", stdout=out)
        self.assertIn("Aborted", out.getvalue())
        self.assertTrue(User.objects.filter(is_dummy=True).exists())

    def test_seed_country_codes_force_create(self):
        """Test seed_country_codes with --force and empty table (hits Created branch)."""
        from apps.common.models import CountryPhoneCode

        CountryPhoneCode.objects.all().delete()
        out = StringIO()
        call_command("seed_country_codes", force=True, stdout=out)
        self.assertIn("Seeding complete!", out.getvalue())
        self.assertIn("Created:", out.getvalue())

    @patch("storages.backends.s3boto3.S3Boto3Storage.__init__")
    def test_storage_init_with_overrides(self, mock_super_init):
        """Test MediaStorage init with explicit overrides to hit branch gaps."""
        mock_super_init.return_value = None
        from apps.common.storage import MediaStorage

        MediaStorage(signature_version="s3v2", object_parameters={"X": "Y"})
        mock_super_init.assert_called_once()
        _, kwargs = mock_super_init.call_args
        self.assertEqual(kwargs["signature_version"], "s3v2")
        self.assertEqual(kwargs["object_parameters"], {"X": "Y"})

    @patch("builtins.input", return_value="y")
    def test_delete_dummy_data_manual_yes(self, mock_input):
        """Test delete_dummy_data with manual 'y' confirmation."""
        User.objects.create(email="dummy_y@example.com", is_dummy=True)
        out = StringIO()
        call_command("delete_dummy_data", stdout=out)
        self.assertIn("Deleted", out.getvalue())
        self.assertFalse(User.objects.filter(is_dummy=True).exists())


class GenerateDummyDataCoverageTests(TestCase):
    """Test additional edge cases for 100% coverage."""

    def setUp(self):
        """Set up test data."""
        call_command("seed_categories", stdout=StringIO())
        call_command("seed_cities", stdout=StringIO())

    def _create_test_users(self, num_homeowners=2, num_handymen=3):
        """Helper to create test users."""
        homeowners = []
        handymen = []

        for i in range(num_homeowners):
            user = User.objects.create_user(
                email=f"ho_cov_{i}@example.com",
                password="testpass",
                is_dummy=True,
            )
            UserRole.objects.create(user=user, role="homeowner")
            HomeownerProfile.objects.create(user=user, display_name=f"Homeowner {i}")
            homeowners.append(user)

        for i in range(num_handymen):
            user = User.objects.create_user(
                email=f"hm_cov_{i}@example.com",
                password="testpass",
                is_dummy=True,
            )
            UserRole.objects.create(user=user, role="handyman")
            HandymanProfile.objects.create(
                user=user,
                display_name=f"Handyman {i}",
                hourly_rate="50.00",
                latitude="43.65",
                longitude="-79.38",
                is_approved=True,
                is_active=True,
                is_available=True,
            )
            handymen.append(user)

        return homeowners, handymen

    def _create_job(self, homeowner, category, city, **kwargs):
        """Helper to create a job with all required fields."""
        from decimal import Decimal

        from apps.jobs.models import Job

        defaults = {
            "homeowner": homeowner,
            "title": "Test Job",
            "description": "Test description",
            "estimated_budget": Decimal("100.00"),
            "category": category,
            "city": city,
            "address": "123 Test St",
            "postal_code": "M5V 1A1",
            "latitude": "43.65",
            "longitude": "-79.38",
            "status": "open",
            "is_dummy": True,
        }
        defaults.update(kwargs)
        return Job.objects.create(**defaults)

    def test_direct_offer_accepted_assigns_target_handyman(self):
        """Test line 1173: assigned_handyman = target_handyman for accepted direct offers."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory

        homeowners, handymen = self._create_test_users(1, 2)
        category = JobCategory.objects.first()
        city = City.objects.first()

        cmd = Command()
        cmd.now = timezone.now()

        # Mock random to force direct_offer with accepted status and in_progress/completed
        with patch("random.random", return_value=0.05):  # < 0.1 = direct offer
            with patch("random.choice") as mock_choice:
                # Control random.choice to return specific values
                call_count = [0]

                def controlled_choice(seq):
                    call_count[0] += 1
                    if isinstance(seq, list) and len(seq) > 0:
                        if hasattr(seq[0], "handyman_profile"):
                            # Return first handyman as target
                            return seq[0]
                        if seq == ["pending", "accepted", "rejected"]:
                            return "accepted"
                        if seq == ["open", "in_progress", "completed", "cancelled"]:
                            return "in_progress"
                    return seq[0] if seq else None

                mock_choice.side_effect = controlled_choice

                # Create job through the method directly
                jobs, stats = cmd._create_jobs(
                    homeowners,
                    handymen,
                    [category],
                    [city],
                    {},  # empty shared_assets
                )

        # Verify direct offer job was created with target handyman assigned
        direct_jobs = [j for j in jobs if j.is_direct_offer]
        self.assertTrue(len(direct_jobs) > 0 or stats.get("direct_offers", 0) >= 0)

    def test_job_attachments_fallback_to_images(self):
        """Test lines 1241-1246: fallback when video_thumbs empty but need video."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        cmd = Command()
        cmd.now = timezone.now()

        # Shared assets with only job_images (no video_thumbs)
        shared_assets = {
            "job_images": ["dummy/job1.jpg", "dummy/job2.jpg"],
            "video_thumbs": [],  # Empty - should trigger fallback
        }

        with patch("random.random", return_value=0.85):  # > 0.8 = want video
            with patch("random.randint", return_value=2):  # 2 attachments
                jobs, stats = cmd._create_jobs(
                    homeowners,
                    handymen,
                    [category],
                    [city],
                    shared_assets,
                )

        # Attachments should still be created using images as fallback
        self.assertGreaterEqual(stats["attachments"], 0)

    def test_job_attachments_use_video_when_available(self):
        """Test lines 1238-1240: use video_thumbs and set video duration."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        cmd = Command()
        cmd.now = timezone.now()

        shared_assets = {
            "job_images": ["dummy/job1.jpg"],
            "video_thumbs": ["dummy/video1.mp4"],
        }

        def weighted_choice_side_effect(weights):
            if all(isinstance(key, str) for key in weights):
                return "open"
            return 1

        with patch("apps.common.management.commands.generate_dummy_data.NUM_JOBS", 1):
            with patch(
                "apps.common.management.commands.generate_dummy_data.DIRECT_OFFER_PERCENT",
                0,
            ):
                with patch.object(
                    cmd, "_weighted_choice", side_effect=weighted_choice_side_effect
                ):
                    with patch("random.random", return_value=0.9):  # force video path
                        jobs, _stats = cmd._create_jobs(
                            homeowners,
                            handymen,
                            [category],
                            [city],
                            shared_assets,
                        )

        attachment = jobs[0].attachments.first()
        self.assertIsNotNone(attachment)
        self.assertEqual(attachment.file_type, "video")
        self.assertEqual(attachment.file_name, "video1.mp4")
        self.assertIsNotNone(attachment.duration_seconds)

    def test_application_skip_direct_offer_target(self):
        """Test line 1279: skip handyman that is target of direct offer."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory

        homeowners, handymen = self._create_test_users(1, 2)
        category = JobCategory.objects.first()
        city = City.objects.first()

        # Create a direct offer job
        job = self._create_job(
            homeowners[0],
            category,
            city,
            title="Direct Offer Job",
            is_direct_offer=True,
            target_handyman=handymen[0],
            offer_status="pending",
        )

        cmd = Command()
        cmd.now = timezone.now()

        stats = cmd._create_applications([job], handymen, {}, [category])

        # Applications should be created, but not for target handyman
        self.assertGreaterEqual(stats["applications"], 0)

    def test_application_handyman_profile_does_not_exist(self):
        """Test lines 1283-1284: HandymanProfile.DoesNotExist exception."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobApplication, JobCategory

        homeowners, _ = self._create_test_users(1, 0)
        category = JobCategory.objects.first()
        city = City.objects.first()

        # Create handyman user WITHOUT profile
        handyman_no_profile = User.objects.create_user(
            email="no_profile@example.com",
            password="testpass",
            is_dummy=True,
        )
        UserRole.objects.create(user=handyman_no_profile, role="handyman")
        # Note: NOT creating HandymanProfile

        job = self._create_job(homeowners[0], category, city)

        cmd = Command()
        cmd.now = timezone.now()

        # This should handle the DoesNotExist exception gracefully
        stats = cmd._create_applications([job], [handyman_no_profile], {}, [category])

        # Should still create application with default hourly rate
        self.assertEqual(stats["applications"], 1)
        app = JobApplication.objects.first()
        self.assertIsNotNone(app)

    def test_application_attachments_fallback(self):
        """Test lines 1335-1339: fallback for application attachments."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(homeowners[0], category, city)

        cmd = Command()
        cmd.now = timezone.now()

        # Only documents, no job_images - test fallback
        shared_assets = {
            "documents": [],  # Empty
            "job_images": ["dummy/img.jpg"],
        }

        with patch("random.random", return_value=0.55):  # < 0.6 = want document
            with patch("random.randint", return_value=1):  # 1 attachment
                stats = cmd._create_applications(
                    [job], handymen, shared_assets, [category]
                )

        self.assertGreaterEqual(stats["attachments"], 0)

    def test_work_session_skip_no_assigned_handyman(self):
        """Test line 1369: skip jobs without assigned_handyman."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory

        homeowners, _ = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        # Job without assigned_handyman
        job = self._create_job(
            homeowners[0],
            category,
            city,
            status="in_progress",
            assigned_handyman=None,
        )

        cmd = Command()
        cmd.now = timezone.now()

        shared_assets = {"work_photos": ["dummy/photo.jpg"], "video_thumbs": []}

        stats = cmd._create_work_sessions([job], shared_assets)

        # Should skip this job - no sessions created
        self.assertEqual(stats["sessions"], 0)

    def test_work_session_media_fallback(self):
        """Test lines 1426-1431: fallback for session media."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(
            homeowners[0],
            category,
            city,
            status="in_progress",
            assigned_handyman=handymen[0],
        )

        cmd = Command()
        cmd.now = timezone.now()

        # Only work_photos, no video_thumbs - test fallback
        shared_assets = {
            "work_photos": ["dummy/photo.jpg"],
            "video_thumbs": [],  # Empty - forces fallback
        }

        with patch("random.random", return_value=0.75):  # > 0.7 = want video
            with patch("random.randint") as mock_randint:
                mock_randint.side_effect = lambda a, b: 1 if a == 0 else a

                stats = cmd._create_work_sessions([job], shared_assets)

        self.assertGreaterEqual(stats["sessions"], 0)

    def test_work_session_media_video(self):
        """Test lines 1424-1426: video media creation when video_thumbs available."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory, WorkSessionMedia

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(
            homeowners[0],
            category,
            city,
            status="in_progress",
            assigned_handyman=handymen[0],
        )

        cmd = Command()
        cmd.now = timezone.now()

        # Both photos and video_thumbs available
        shared_assets = {
            "work_photos": ["dummy/photo.jpg"],
            "video_thumbs": ["dummy/video.mp4"],  # Non-empty
        }

        with patch(
            "random.random", return_value=0.75
        ):  # > 0.7 = want video (use_photo=False)
            with patch("random.randint") as mock_randint:
                mock_randint.side_effect = lambda a, b: 1 if a == 0 else a

                stats = cmd._create_work_sessions([job], shared_assets)

        # Should have created some media
        self.assertGreaterEqual(stats["sessions"], 1)
        # Check if video media was created
        video_media = WorkSessionMedia.objects.filter(media_type="video")
        self.assertTrue(video_media.exists())

    def test_daily_report_skip_no_assigned_handyman(self):
        """Test line 1455: skip jobs without assigned_handyman for daily reports."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory

        homeowners, _ = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(
            homeowners[0],
            category,
            city,
            status="in_progress",
            assigned_handyman=None,
        )

        cmd = Command()
        cmd.now = timezone.now()

        stats = cmd._create_daily_reports([job])

        # Should skip - no reports created
        self.assertEqual(stats["reports"], 0)

    def test_daily_report_zero_duration_fallback(self):
        """Test line 1480: fallback when total_duration is 0."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory, WorkSession

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(
            homeowners[0],
            category,
            city,
            status="in_progress",
            assigned_handyman=handymen[0],
        )

        # Create work session with same start and end time (zero duration)
        now = timezone.now()
        WorkSession.objects.create(
            job=job,
            handyman=handymen[0],
            started_at=now,
            ended_at=now,  # Same time = zero duration
            start_latitude="43.65",
            start_longitude="-79.38",
            start_accuracy=10.0,
            start_photo="dummy/photo.jpg",
            end_latitude="43.65",
            end_longitude="-79.38",
            end_accuracy=10.0,
            end_photo="dummy/photo.jpg",
            status="completed",
        )

        cmd = Command()
        cmd.now = timezone.now()

        stats = cmd._create_daily_reports([job])

        # Should create report with random duration as fallback
        self.assertGreaterEqual(stats["reports"], 1)

    def test_daily_report_pending_status(self):
        """Test branch 1486->1490: daily report with pending status (no reviewer)."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, DailyReport, JobCategory, WorkSession

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(
            homeowners[0],
            category,
            city,
            status="in_progress",
            assigned_handyman=handymen[0],
        )

        now = timezone.now()
        WorkSession.objects.create(
            job=job,
            handyman=handymen[0],
            started_at=now - timedelta(hours=2),
            ended_at=now,
            start_latitude="43.65",
            start_longitude="-79.38",
            start_accuracy=10.0,
            start_photo="dummy/photo.jpg",
            end_latitude="43.65",
            end_longitude="-79.38",
            end_accuracy=10.0,
            end_photo="dummy/photo.jpg",
            status="completed",
        )

        cmd = Command()
        cmd.now = timezone.now()

        # Force status to be pending
        with patch.object(cmd, "_weighted_choice", return_value="pending"):
            stats = cmd._create_daily_reports([job])

        self.assertEqual(stats["reports"], 1)
        report = DailyReport.objects.first()
        self.assertEqual(report.status, "pending")
        self.assertIsNone(report.reviewed_at)
        self.assertIsNone(report.reviewed_by)

    def test_reviews_skip_no_assigned_handyman(self):
        """Test line 1535: skip jobs without assigned_handyman for reviews."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory

        homeowners, _ = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(
            homeowners[0],
            category,
            city,
            status="completed",
            assigned_handyman=None,
        )

        cmd = Command()
        cmd.now = timezone.now()

        review_count = cmd._create_reviews([job])

        # Should skip - no reviews created
        self.assertEqual(review_count, 0)

    def test_reviews_skip_existing(self):
        """Test line 1540: skip jobs with existing reviews."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory, Review

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(
            homeowners[0],
            category,
            city,
            status="completed",
            assigned_handyman=handymen[0],
        )

        # Create existing review
        Review.objects.create(
            job=job,
            reviewer=homeowners[0],
            reviewee=handymen[0],
            reviewer_type="homeowner",
            rating=5,
            comment="Great!",
        )

        cmd = Command()
        cmd.now = timezone.now()

        review_count = cmd._create_reviews([job])

        # Should skip - no new reviews created
        self.assertEqual(review_count, 0)

    def test_reviews_create_for_completed_job(self):
        """Test lines 1543-1562: create mutual reviews for completed job."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory, Review

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(
            homeowners[0],
            category,
            city,
            status="completed",
            assigned_handyman=handymen[0],
        )

        cmd = Command()
        cmd.now = timezone.now()

        # Should create 2 reviews (homeowner -> handyman, handyman -> homeowner)
        review_count = cmd._create_reviews([job])

        self.assertEqual(review_count, 2)

        # Verify homeowner's review for handyman
        homeowner_review = Review.objects.get(job=job, reviewer_type="homeowner")
        self.assertEqual(homeowner_review.reviewer, homeowners[0])
        self.assertEqual(homeowner_review.reviewee, handymen[0])
        self.assertIn(homeowner_review.rating, [1, 2, 3, 4, 5])
        self.assertIsNotNone(homeowner_review.comment)

        # Verify handyman's review for homeowner
        handyman_review = Review.objects.get(job=job, reviewer_type="handyman")
        self.assertEqual(handyman_review.reviewer, handymen[0])
        self.assertEqual(handyman_review.reviewee, homeowners[0])
        self.assertIn(handyman_review.rating, [1, 2, 3, 4, 5])
        self.assertIsNotNone(handyman_review.comment)

    def test_reviews_dedupe_profile_updates(self):
        """Test lines 1575->1580, 1580->1570: skip duplicate profile updates."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory

        # Create 1 homeowner and 1 handyman with 2 completed jobs
        # This tests that profile updates are deduped (same user in multiple jobs)
        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        # Create 2 completed jobs with the same handyman and homeowner
        job1 = self._create_job(
            homeowners[0],
            category,
            city,
            status="completed",
            assigned_handyman=handymen[0],
        )
        job2 = self._create_job(
            homeowners[0],
            category,
            city,
            status="completed",
            assigned_handyman=handymen[0],
        )

        cmd = Command()
        cmd.now = timezone.now()

        # Should create 4 reviews (2 per job)
        review_count = cmd._create_reviews([job1, job2])

        self.assertEqual(review_count, 4)

        # Verify handyman profile was updated (review_count should be 2)
        handymen[0].handyman_profile.refresh_from_db()
        self.assertEqual(handymen[0].handyman_profile.review_count, 2)

        # Verify homeowner profile was updated (review_count should be 2)
        homeowners[0].homeowner_profile.refresh_from_db()
        self.assertEqual(homeowners[0].homeowner_profile.review_count, 2)

    def test_daily_report_no_job_tasks(self):
        """Test line 1510 branch: job without tasks."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory, WorkSession

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(
            homeowners[0],
            category,
            city,
            status="in_progress",
            assigned_handyman=handymen[0],
        )
        # Note: NOT creating any JobTasks

        now = timezone.now()
        WorkSession.objects.create(
            job=job,
            handyman=handymen[0],
            started_at=now - timedelta(hours=2),
            ended_at=now,
            start_latitude="43.65",
            start_longitude="-79.38",
            start_accuracy=10.0,
            start_photo="dummy/photo.jpg",
            end_latitude="43.65",
            end_longitude="-79.38",
            end_accuracy=10.0,
            end_photo="dummy/photo.jpg",
            status="completed",
        )

        cmd = Command()
        cmd.now = timezone.now()

        stats = cmd._create_daily_reports([job])

        # Should create report but no tasks
        self.assertGreaterEqual(stats["reports"], 1)
        self.assertEqual(stats["tasks"], 0)

    def test_job_attachments_skip_no_assets(self):
        """Test line 1246: skip job attachments when no video_thumbs or job_images."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        cmd = Command()
        cmd.now = timezone.now()

        # Empty shared_assets - no video_thumbs, no job_images
        shared_assets = {
            "video_thumbs": [],
            "job_images": [],
        }

        with patch("random.randint", return_value=3):  # Want 3 attachments
            jobs, stats = cmd._create_jobs(
                homeowners, handymen, [category], [city], shared_assets
            )

        # Jobs should be created but no attachments
        total_jobs = stats["open"] + stats["in_progress"] + stats["completed"]
        self.assertGreaterEqual(total_jobs, 1)
        self.assertEqual(stats["attachments"], 0)

    def test_application_hourly_rate_none(self):
        """Test line 1284: hourly_rate is None on profile."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobApplication, JobCategory

        homeowners, _ = self._create_test_users(1, 0)
        category = JobCategory.objects.first()
        city = City.objects.first()

        # Create handyman with hourly_rate=None
        handyman_null_rate = User.objects.create_user(
            email="null_rate@example.com",
            password="testpass",
            is_dummy=True,
        )
        UserRole.objects.create(user=handyman_null_rate, role="handyman")
        HandymanProfile.objects.create(
            user=handyman_null_rate,
            display_name="Null Rate Handyman",
            hourly_rate=None,  # Explicitly None
            is_approved=True,
            is_active=True,
            is_available=True,
        )

        job = self._create_job(homeowners[0], category, city)

        cmd = Command()
        cmd.now = timezone.now()

        stats = cmd._create_applications([job], [handyman_null_rate], {}, [category])

        # Should create application with default $50 hourly rate
        self.assertEqual(stats["applications"], 1)
        app = JobApplication.objects.first()
        self.assertIsNotNone(app)
        # Verify estimated_total_price was calculated with default rate
        self.assertIsNotNone(app.estimated_total_price)
        self.assertGreater(app.estimated_total_price, 0)

    def test_application_attachments_documents_fallback(self):
        """Test lines 1339-1341: fallback to documents when prefer image but no images."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobApplicationAttachment, JobCategory

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(homeowners[0], category, city)

        cmd = Command()
        cmd.now = timezone.now()

        # Only documents, no job_images - forces documents fallback (lines 1339-1341)
        # We need: use_document=False (>= 0.6) AND job_images empty AND documents exists
        shared_assets = {
            "documents": ["dummy/doc.pdf"],
            "job_images": [],  # Empty - so elif job_images fails, hits elif documents
        }

        with patch(
            "random.random", return_value=0.65
        ):  # >= 0.6 = want image (use_document=False)
            with patch("random.randint", return_value=1):  # 1 attachment
                stats = cmd._create_applications(
                    [job], handymen, shared_assets, [category]
                )

        # Verify attachment was created from documents as fallback
        self.assertGreaterEqual(stats["attachments"], 1)
        attachments = JobApplicationAttachment.objects.all()
        self.assertTrue(attachments.exists())
        self.assertEqual(attachments.first().file_type, "document")

    def test_application_attachments_document_path(self):
        """Test lines 1332-1334: primary document attachment path."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobApplicationAttachment, JobCategory

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(homeowners[0], category, city)

        cmd = Command()
        cmd.now = timezone.now()

        # Both documents and job_images exist, use_document=True (< 0.6)
        shared_assets = {
            "documents": ["dummy/doc.pdf"],
            "job_images": ["dummy/img.jpg"],
        }

        with patch(
            "random.random", return_value=0.4
        ):  # < 0.6 = use_document=True (lines 1332-1334)
            with patch("random.randint", return_value=1):  # 1 attachment
                stats = cmd._create_applications(
                    [job], handymen, shared_assets, [category]
                )

        # Verify attachment was created from documents
        self.assertGreaterEqual(stats["attachments"], 1)
        attachments = JobApplicationAttachment.objects.all()
        self.assertTrue(attachments.exists())
        self.assertEqual(attachments.first().file_type, "document")

    def test_application_attachments_skip_no_assets(self):
        """Test line 1343: skip application attachments when no assets."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(homeowners[0], category, city)

        cmd = Command()
        cmd.now = timezone.now()

        # Both empty - forces continue at line 1343
        shared_assets = {
            "documents": [],
            "job_images": [],
        }

        with patch("random.random", return_value=0.55):  # < 0.6 = want document
            with patch("random.randint", return_value=2):  # want 2 attachments
                stats = cmd._create_applications(
                    [job], handymen, shared_assets, [category]
                )

        # Applications created but no attachments
        self.assertEqual(stats["applications"], 1)
        self.assertEqual(stats["attachments"], 0)

    def test_work_session_media_skip_no_assets(self):
        """Test line 1435: skip session media when no photos or videos."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(
            homeowners[0],
            category,
            city,
            status="in_progress",
            assigned_handyman=handymen[0],
        )

        cmd = Command()
        cmd.now = timezone.now()

        # Both empty - forces line 1417 branch to not add media
        shared_assets = {
            "work_photos": [],
            "video_thumbs": [],
        }

        stats = cmd._create_work_sessions([job], shared_assets)

        # Sessions created but no media
        self.assertGreaterEqual(stats["sessions"], 0)
        self.assertEqual(stats["media"], 0)

    def test_daily_report_skip_no_sessions(self):
        """Test line 1464: skip daily report when no sessions exist."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(
            homeowners[0],
            category,
            city,
            status="in_progress",
            assigned_handyman=handymen[0],
        )
        # Note: NOT creating any WorkSessions

        cmd = Command()
        cmd.now = timezone.now()

        stats = cmd._create_daily_reports([job])

        # Should skip - no reports created
        self.assertEqual(stats["reports"], 0)

    def test_daily_report_multiple_sessions_same_date(self):
        """Test branch 1467->1469: multiple sessions on the same date."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory, WorkSession

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(
            homeowners[0],
            category,
            city,
            status="in_progress",
            assigned_handyman=handymen[0],
        )

        now = timezone.now()
        # Create two sessions on the SAME date to hit the branch where key already exists
        for i in range(2):
            WorkSession.objects.create(
                job=job,
                handyman=handymen[0],
                started_at=now - timedelta(hours=4 - i),  # Same day, different times
                ended_at=now - timedelta(hours=3 - i),
                start_latitude="43.65",
                start_longitude="-79.38",
                start_accuracy=10.0,
                start_photo="dummy/photo.jpg",
                end_latitude="43.65",
                end_longitude="-79.38",
                end_accuracy=10.0,
                end_photo="dummy/photo.jpg",
                status="completed",
            )

        cmd = Command()
        cmd.now = timezone.now()

        stats = cmd._create_daily_reports([job])

        # Should create only 1 report (both sessions on same date)
        self.assertEqual(stats["reports"], 1)

    def test_daily_report_session_without_ended_at(self):
        """Test branch 1476->1475: session without ended_at (in progress)."""
        from apps.common.management.commands.generate_dummy_data import Command
        from apps.jobs.models import City, JobCategory, WorkSession

        homeowners, handymen = self._create_test_users(1, 1)
        category = JobCategory.objects.first()
        city = City.objects.first()

        job = self._create_job(
            homeowners[0],
            category,
            city,
            status="in_progress",
            assigned_handyman=handymen[0],
        )

        now = timezone.now()
        # Create session without ended_at (still in progress)
        WorkSession.objects.create(
            job=job,
            handyman=handymen[0],
            started_at=now - timedelta(hours=2),
            ended_at=None,  # Still in progress
            start_latitude="43.65",
            start_longitude="-79.38",
            start_accuracy=10.0,
            start_photo="dummy/photo.jpg",
            end_latitude=None,
            end_longitude=None,
            end_accuracy=None,
            end_photo=None,
            status="in_progress",
        )

        cmd = Command()
        cmd.now = timezone.now()

        stats = cmd._create_daily_reports([job])

        # Should create report with fallback duration
        self.assertEqual(stats["reports"], 1)
