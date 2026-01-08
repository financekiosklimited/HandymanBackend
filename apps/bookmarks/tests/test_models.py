"""Tests for bookmark models."""

from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.bookmarks.models import HandymanBookmark, JobBookmark
from apps.jobs.models import City, Job, JobCategory
from apps.profiles.models import HandymanProfile, HomeownerProfile


class JobBookmarkModelTests(TestCase):
    """Test cases for JobBookmark model."""

    def setUp(self):
        """Set up test data."""
        # Create handyman user
        self.handyman_user = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user, role="handyman")
        self.handyman_profile = HandymanProfile.objects.create(
            user=self.handyman_user,
            display_name="John Handyman",
            is_approved=True,
            is_active=True,
        )

        # Create homeowner user
        self.homeowner_user = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner_user, role="homeowner")
        HomeownerProfile.objects.create(user=self.homeowner_user)

        # Create test category and city
        self.category = JobCategory.objects.create(
            name="Plumbing", slug="plumbing", is_active=True
        )
        self.city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            is_active=True,
        )

        # Create job
        self.job = Job.objects.create(
            homeowner=self.homeowner_user,
            title="Fix leaking faucet",
            description="Kitchen faucet needs fixing",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )

    def test_create_job_bookmark(self):
        """Test creating a job bookmark."""
        bookmark = JobBookmark.objects.create(
            handyman=self.handyman_user,
            job=self.job,
        )
        self.assertIsNotNone(bookmark.public_id)
        self.assertEqual(bookmark.handyman, self.handyman_user)
        self.assertEqual(bookmark.job, self.job)
        self.assertIsNotNone(bookmark.created_at)
        self.assertIsNotNone(bookmark.updated_at)

    def test_job_bookmark_str(self):
        """Test string representation of job bookmark."""
        bookmark = JobBookmark.objects.create(
            handyman=self.handyman_user,
            job=self.job,
        )
        expected_str = f"{self.handyman_user.email} -> {self.job.title}"
        self.assertEqual(str(bookmark), expected_str)

    def test_job_bookmark_unique_together(self):
        """Test that a handyman cannot bookmark the same job twice."""
        JobBookmark.objects.create(
            handyman=self.handyman_user,
            job=self.job,
        )
        with self.assertRaises(IntegrityError):
            JobBookmark.objects.create(
                handyman=self.handyman_user,
                job=self.job,
            )

    def test_job_bookmark_ordering(self):
        """Test that job bookmarks are ordered by created_at descending."""
        # Create second job
        job2 = Job.objects.create(
            homeowner=self.homeowner_user,
            title="Second job",
            description="Another job",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="456 Oak Ave",
            status="open",
        )

        bookmark1 = JobBookmark.objects.create(
            handyman=self.handyman_user,
            job=self.job,
        )
        bookmark2 = JobBookmark.objects.create(
            handyman=self.handyman_user,
            job=job2,
        )

        bookmarks = JobBookmark.objects.all()
        # Most recent should be first
        self.assertEqual(bookmarks[0], bookmark2)
        self.assertEqual(bookmarks[1], bookmark1)

    def test_job_bookmark_cascade_delete_on_handyman(self):
        """Test that bookmarks are deleted when handyman is deleted."""
        JobBookmark.objects.create(
            handyman=self.handyman_user,
            job=self.job,
        )
        self.assertEqual(JobBookmark.objects.count(), 1)
        self.handyman_user.delete()
        self.assertEqual(JobBookmark.objects.count(), 0)

    def test_job_bookmark_cascade_delete_on_job(self):
        """Test that bookmarks are deleted when job is deleted."""
        JobBookmark.objects.create(
            handyman=self.handyman_user,
            job=self.job,
        )
        self.assertEqual(JobBookmark.objects.count(), 1)
        self.job.delete()
        self.assertEqual(JobBookmark.objects.count(), 0)

    def test_job_bookmark_related_name_on_handyman(self):
        """Test related_name on handyman user."""
        JobBookmark.objects.create(
            handyman=self.handyman_user,
            job=self.job,
        )
        self.assertEqual(self.handyman_user.job_bookmarks.count(), 1)

    def test_job_bookmark_related_name_on_job(self):
        """Test related_name on job."""
        JobBookmark.objects.create(
            handyman=self.handyman_user,
            job=self.job,
        )
        self.assertEqual(self.job.bookmarks.count(), 1)


class HandymanBookmarkModelTests(TestCase):
    """Test cases for HandymanBookmark model."""

    def setUp(self):
        """Set up test data."""
        # Create handyman user
        self.handyman_user = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user, role="handyman")
        self.handyman_profile = HandymanProfile.objects.create(
            user=self.handyman_user,
            display_name="John Handyman",
            is_approved=True,
            is_active=True,
        )

        # Create homeowner user
        self.homeowner_user = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner_user, role="homeowner")
        HomeownerProfile.objects.create(user=self.homeowner_user)

    def test_create_handyman_bookmark(self):
        """Test creating a handyman bookmark."""
        bookmark = HandymanBookmark.objects.create(
            homeowner=self.homeowner_user,
            handyman_profile=self.handyman_profile,
        )
        self.assertIsNotNone(bookmark.public_id)
        self.assertEqual(bookmark.homeowner, self.homeowner_user)
        self.assertEqual(bookmark.handyman_profile, self.handyman_profile)
        self.assertIsNotNone(bookmark.created_at)
        self.assertIsNotNone(bookmark.updated_at)

    def test_handyman_bookmark_str(self):
        """Test string representation of handyman bookmark."""
        bookmark = HandymanBookmark.objects.create(
            homeowner=self.homeowner_user,
            handyman_profile=self.handyman_profile,
        )
        expected_str = (
            f"{self.homeowner_user.email} -> {self.handyman_profile.display_name}"
        )
        self.assertEqual(str(bookmark), expected_str)

    def test_handyman_bookmark_unique_together(self):
        """Test that a homeowner cannot bookmark the same handyman twice."""
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user,
            handyman_profile=self.handyman_profile,
        )
        with self.assertRaises(IntegrityError):
            HandymanBookmark.objects.create(
                homeowner=self.homeowner_user,
                handyman_profile=self.handyman_profile,
            )

    def test_handyman_bookmark_ordering(self):
        """Test that handyman bookmarks are ordered by created_at descending."""
        # Create second handyman
        handyman_user2 = User.objects.create_user(
            email="handyman2@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=handyman_user2, role="handyman")
        handyman_profile2 = HandymanProfile.objects.create(
            user=handyman_user2,
            display_name="Jane Handyman",
            is_approved=True,
            is_active=True,
        )

        bookmark1 = HandymanBookmark.objects.create(
            homeowner=self.homeowner_user,
            handyman_profile=self.handyman_profile,
        )
        bookmark2 = HandymanBookmark.objects.create(
            homeowner=self.homeowner_user,
            handyman_profile=handyman_profile2,
        )

        bookmarks = HandymanBookmark.objects.all()
        # Most recent should be first
        self.assertEqual(bookmarks[0], bookmark2)
        self.assertEqual(bookmarks[1], bookmark1)

    def test_handyman_bookmark_cascade_delete_on_homeowner(self):
        """Test that bookmarks are deleted when homeowner is deleted."""
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user,
            handyman_profile=self.handyman_profile,
        )
        self.assertEqual(HandymanBookmark.objects.count(), 1)
        self.homeowner_user.delete()
        self.assertEqual(HandymanBookmark.objects.count(), 0)

    def test_handyman_bookmark_cascade_delete_on_handyman_profile(self):
        """Test that bookmarks are deleted when handyman profile is deleted."""
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user,
            handyman_profile=self.handyman_profile,
        )
        self.assertEqual(HandymanBookmark.objects.count(), 1)
        self.handyman_profile.delete()
        self.assertEqual(HandymanBookmark.objects.count(), 0)

    def test_handyman_bookmark_related_name_on_homeowner(self):
        """Test related_name on homeowner user."""
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user,
            handyman_profile=self.handyman_profile,
        )
        self.assertEqual(self.homeowner_user.handyman_bookmarks.count(), 1)

    def test_handyman_bookmark_related_name_on_handyman_profile(self):
        """Test related_name on handyman profile."""
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user,
            handyman_profile=self.handyman_profile,
        )
        self.assertEqual(self.handyman_profile.bookmarks.count(), 1)
