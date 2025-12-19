from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.jobs.models import City, Job, JobApplication, JobCategory
from apps.profiles.models import HandymanProfile, HomeownerProfile

User = get_user_model()


class JobApplicationModelTest(TestCase):
    """
    Test cases for JobApplication model.
    """

    def setUp(self):
        """Set up test data."""
        # Create users
        self.homeowner_user = User.objects.create_user(
            email="homeowner@test.com", password="testpass123"
        )
        self.handyman_user = User.objects.create_user(
            email="handyman@test.com", password="testpass123"
        )

        # Create profiles
        self.homeowner_profile = HomeownerProfile.objects.create(
            user=self.homeowner_user,
            display_name="Test Homeowner",
            phone_number="+1234567890",
            phone_verified_at=timezone.now(),
            address="123 Test St",
        )

        self.handyman_profile = HandymanProfile.objects.create(
            user=self.handyman_user,
            display_name="Test Handyman",
            phone_number="+1234567891",
            phone_verified_at=timezone.now(),
            address="456 Test St",
            is_approved=True,
        )

        # Create category and city
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
            title="Fix Kitchen Sink",
            description="Need help fixing leaky kitchen sink",
            estimated_budget=Decimal("150.00"),
            category=self.category,
            city=self.city,
            address="123 Test St",
            status="open",
        )

    def test_create_job_application(self):
        """Test creating a job application."""
        application = JobApplication.objects.create(
            job=self.job, handyman=self.handyman_user, status="pending"
        )

        self.assertIsNotNone(application.public_id)
        self.assertEqual(application.job, self.job)
        self.assertEqual(application.handyman, self.handyman_user)
        self.assertEqual(application.status, "pending")
        self.assertIsNotNone(application.status_at)

    def test_unique_application_per_job(self):
        """Test that a handyman can only apply once to a job."""
        JobApplication.objects.create(
            job=self.job, handyman=self.handyman_user, status="pending"
        )

        # Try to create duplicate application
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            JobApplication.objects.create(
                job=self.job, handyman=self.handyman_user, status="pending"
            )

    def test_application_status_choices(self):
        """Test that application status choices are valid."""
        valid_statuses = ["pending", "approved", "rejected", "withdrawn"]

        for status in valid_statuses:
            application = JobApplication.objects.create(
                job=self.job,
                handyman=self.handyman_user,
                status=status,
            )
            # Delete to allow unique constraint for next iteration
            application.delete()

    def test_str_representation(self):
        """Test string representation of job application."""
        application = JobApplication.objects.create(
            job=self.job, handyman=self.handyman_user, status="pending"
        )

        expected = f"{self.handyman_user.email} → {self.job.title} (pending)"
        self.assertEqual(str(application), expected)
