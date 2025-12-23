"""Tests for job application service."""

from datetime import UTC, datetime
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.jobs.models import City, Job, JobCategory
from apps.jobs.services import JobApplicationService
from apps.profiles.models import HandymanProfile, HomeownerProfile


class JobApplicationServiceTests(TestCase):
    """Test cases for JobApplicationService."""

    def setUp(self):
        """Set up test data."""
        self.service = JobApplicationService()
        self.homeowner = User.objects.create_user(
            email="owner@example.com", password="password123"
        )
        self.handyman = User.objects.create_user(
            email="handy@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        UserRole.objects.create(user=self.handyman, role="handyman")

        self.owner_profile = HomeownerProfile.objects.create(
            user=self.homeowner, display_name="Owner"
        )
        self.handy_profile = HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Handy",
            phone_verified_at=datetime.now(UTC),
        )

        self.category = JobCategory.objects.create(
            name="Plumbing", slug="plumbing", is_active=True
        )
        self.city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto",
            is_active=True,
        )

        self.job = Job.objects.create(
            homeowner=self.homeowner,
            title="Fix leaky faucet",
            description="Leaky faucet in kitchen",
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
            estimated_budget=100,
        )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_apply_to_job_success(self, mock_notify):
        """Test successful job application."""
        application = self.service.apply_to_job(self.handyman, self.job)

        self.assertEqual(application.job, self.job)
        self.assertEqual(application.handyman, self.handyman)
        self.assertEqual(application.status, "pending")
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args.kwargs
        self.assertEqual(call_kwargs["triggered_by"], self.handyman)

    def test_apply_to_job_invalid_status(self):
        """Test applying to job with invalid status."""
        self.job.status = "cancelled"
        self.job.save()

        with self.assertRaisesRegex(ValidationError, "not accepting applications"):
            self.service.apply_to_job(self.handyman, self.job)

    def test_apply_to_job_no_handyman_role(self):
        """Test applying without handyman role."""
        other_user = User.objects.create_user(
            email="other@example.com", password="password123"
        )
        with self.assertRaisesRegex(ValidationError, "handyman role to apply"):
            self.service.apply_to_job(other_user, self.job)

    def test_apply_to_job_no_profile(self):
        """Test applying without handyman profile."""
        other_handy = User.objects.create_user(
            email="other_handy@example.com", password="password123"
        )
        UserRole.objects.create(user=other_handy, role="handyman")
        # No profile created

        with self.assertRaisesRegex(ValidationError, "complete your handyman profile"):
            self.service.apply_to_job(other_handy, self.job)

    def test_apply_to_job_phone_unverified(self):
        """Test applying with unverified phone."""
        self.handy_profile.phone_verified_at = None
        self.handy_profile.save()

        with self.assertRaisesRegex(ValidationError, "verify your phone number"):
            self.service.apply_to_job(self.handyman, self.job)

    def test_apply_to_job_already_applied(self):
        """Test applying twice to same job."""
        self.service.apply_to_job(self.handyman, self.job)

        with self.assertRaisesRegex(ValidationError, "already applied"):
            self.service.apply_to_job(self.handyman, self.job)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_approve_application_success(self, mock_notify):
        """Test successful application approval."""
        application = self.service.apply_to_job(self.handyman, self.job)

        # Create another application to test auto-rejection
        other_handy = User.objects.create_user(
            email="other_handy@example.com", password="password123"
        )
        UserRole.objects.create(user=other_handy, role="handyman")
        HandymanProfile.objects.create(
            user=other_handy, display_name="Other", phone_verified_at=datetime.now(UTC)
        )
        other_app = self.service.apply_to_job(other_handy, self.job)

        # Reset mock to clear calls from apply_to_job
        mock_notify.reset_mock()

        self.service.approve_application(self.homeowner, application)

        application.refresh_from_db()
        self.assertEqual(application.status, "approved")

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "in_progress")

        other_app.refresh_from_db()
        self.assertEqual(other_app.status, "rejected")

        self.assertEqual(mock_notify.call_count, 2)
        # Check both calls have triggered_by=homeowner
        for call in mock_notify.call_args_list:
            self.assertEqual(call.kwargs["triggered_by"], self.homeowner)

    def test_approve_application_wrong_owner(self):
        """Test approving someone else's job application."""
        application = self.service.apply_to_job(self.handyman, self.job)
        other_owner = User.objects.create_user(
            email="other_owner@example.com", password="password123"
        )

        with self.assertRaisesRegex(ValidationError, "own jobs"):
            self.service.approve_application(other_owner, application)

    def test_approve_application_not_pending(self):
        """Test approving non-pending application."""
        application = self.service.apply_to_job(self.handyman, self.job)
        application.status = "rejected"
        application.save()

        with self.assertRaisesRegex(ValidationError, "pending applications"):
            self.service.approve_application(self.homeowner, application)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_reject_application_success(self, mock_notify):
        """Test successful application rejection."""
        application = self.service.apply_to_job(self.handyman, self.job)

        # Reset mock to clear calls from apply_to_job
        mock_notify.reset_mock()

        self.service.reject_application(self.homeowner, application)

        application.refresh_from_db()
        self.assertEqual(application.status, "rejected")
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args.kwargs
        self.assertEqual(call_kwargs["triggered_by"], self.homeowner)

    def test_reject_application_wrong_owner(self):
        """Test rejecting someone else's job application."""
        application = self.service.apply_to_job(self.handyman, self.job)
        other_owner = User.objects.create_user(
            email="other_owner@example.com", password="password123"
        )

        with self.assertRaisesRegex(ValidationError, "own jobs"):
            self.service.reject_application(other_owner, application)

    def test_reject_application_not_pending(self):
        """Test rejecting non-pending application."""
        application = self.service.apply_to_job(self.handyman, self.job)
        application.status = "approved"
        application.save()

        with self.assertRaisesRegex(ValidationError, "pending applications"):
            self.service.reject_application(self.homeowner, application)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_withdraw_application_success(self, mock_notify):
        """Test successful application withdrawal."""
        application = self.service.apply_to_job(self.handyman, self.job)

        # Reset mock to clear calls from apply_to_job
        mock_notify.reset_mock()

        self.service.withdraw_application(self.handyman, application)

        application.refresh_from_db()
        self.assertEqual(application.status, "withdrawn")
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args.kwargs
        self.assertEqual(call_kwargs["triggered_by"], self.handyman)

    def test_withdraw_application_wrong_handyman(self):
        """Test withdrawing someone else's application."""
        application = self.service.apply_to_job(self.handyman, self.job)
        other_handy = User.objects.create_user(
            email="other_user@example.com", password="password123"
        )

        with self.assertRaisesRegex(ValidationError, "own applications"):
            self.service.withdraw_application(other_handy, application)

    def test_withdraw_application_not_pending(self):
        """Test withdrawing non-pending application."""
        application = self.service.apply_to_job(self.handyman, self.job)
        application.status = "approved"
        application.save()

        with self.assertRaisesRegex(ValidationError, "pending applications"):
            self.service.withdraw_application(self.handyman, application)
