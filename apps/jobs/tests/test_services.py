"""Tests for job services."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.jobs.models import (
    City,
    DailyReport,
    DailyReportTask,
    Job,
    JobCategory,
    JobTask,
)
from apps.jobs.services import (
    JobApplicationService,
    daily_report_service,
    dispute_service,
    job_completion_service,
    work_session_service,
)
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

        self.assertEqual(mock_notify.call_count, 3)
        # Check all calls have triggered_by=homeowner
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


class OngoingServicesTests(TestCase):
    def setUp(self):
        self.homeowner = User.objects.create_user(
            email="owner@example.com", password="pass"
        )
        self.handyman = User.objects.create_user(
            email="handy@example.com", password="pass"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        UserRole.objects.create(user=self.handyman, role="handyman")
        self.home_profile = HomeownerProfile.objects.create(
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
            slug="toronto-on",
            is_active=True,
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Fix sink",
            description="Leaky sink",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 St",
            status="in_progress",
        )
        # Precreate tasks
        self.task1 = JobTask.objects.create(job=self.job, title="Task 1", order=0)
        self.task2 = JobTask.objects.create(job=self.job, title="Task 2", order=1)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_start_and_stop_session(self, mock_notify):
        photo = SimpleUploadedFile("start.jpg", b"data", content_type="image/jpeg")
        session = work_session_service.start_session(
            handyman=self.handyman,
            job=self.job,
            started_at=timezone.now(),
            start_latitude=1,
            start_longitude=1,
            start_photo=photo,
        )
        self.assertEqual(session.status, "in_progress")

        work_session_service.stop_session(
            session=session,
            ended_at=timezone.now(),
            end_latitude=1,
            end_longitude=1,
        )
        session.refresh_from_db()
        self.assertEqual(session.status, "completed")
        self.assertEqual(mock_notify.call_count, 2)

    def test_start_session_wrong_handyman(self):
        other = User.objects.create_user(email="other@example.com", password="pass")
        with self.assertRaises(ValidationError):
            work_session_service.start_session(
                handyman=other,
                job=self.job,
                started_at=timezone.now(),
                start_latitude=1,
                start_longitude=1,
                start_photo=SimpleUploadedFile(
                    "a.jpg", b"d", content_type="image/jpeg"
                ),
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_submit_and_review_report(self, mock_notify):
        report = daily_report_service.submit_report(
            handyman=self.handyman,
            job=self.job,
            report_date=timezone.now().date(),
            summary="Did work",
            total_work_duration=timedelta(hours=2),
            task_entries=[{"task": self.task1, "marked_complete": True}],
        )
        self.task1.refresh_from_db()
        self.assertTrue(self.task1.is_completed)

        daily_report_service.review_report(
            homeowner=self.homeowner,
            report=report,
            decision="approved",
            comment="good",
        )
        report.refresh_from_db()
        self.assertEqual(report.status, "approved")
        self.assertEqual(mock_notify.call_count, 2)

    def test_submit_report_wrong_handyman(self):
        other = User.objects.create_user(email="other2@example.com", password="pass")
        with self.assertRaises(ValidationError):
            daily_report_service.submit_report(
                handyman=other,
                job=self.job,
                report_date=timezone.now().date(),
                summary="x",
                total_work_duration=timedelta(hours=1),
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_completion_flow(self, mock_notify):
        job_completion_service.request_completion(self.handyman, self.job)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "pending_completion")

        job_completion_service.approve_completion(self.homeowner, self.job)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "completed")
        self.assertEqual(mock_notify.call_count, 2)

    def test_completion_wrong_owner(self):
        with self.assertRaises(ValidationError):
            job_completion_service.approve_completion(
                User.objects.create_user("o@x.com"), self.job
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_dispute_flow(self, mock_notify):
        self.job.status = "pending_completion"
        self.job.save()
        dispute = dispute_service.open_dispute(
            homeowner=self.homeowner,
            job=self.job,
            reason="Issue",
        )
        self.assertEqual(dispute.status, "pending")

        dispute_service.resolve_dispute(
            admin_user=self.homeowner,
            dispute=dispute,
            status="resolved_pay_handyman",
            admin_notes="ok",
        )
        dispute.refresh_from_db()
        self.assertEqual(dispute.status, "resolved_pay_handyman")
        self.assertGreaterEqual(mock_notify.call_count, 1)

    def test_dispute_wrong_homeowner(self):
        """Test that a homeowner cannot open dispute for another homeowner's job."""
        other_homeowner = User.objects.create_user(
            email="other_owner@example.com", password="pass"
        )
        with self.assertRaises(ValidationError):
            dispute_service.open_dispute(
                homeowner=other_homeowner,
                job=self.job,
                reason="r",
            )

    def test_start_session_job_not_active(self):
        """Test starting session for a job that is not in_progress/pending_completion."""
        self.job.status = "completed"
        self.job.save()
        with self.assertRaisesRegex(ValidationError, "not active for work sessions"):
            work_session_service.start_session(
                handyman=self.handyman,
                job=self.job,
                started_at=timezone.now(),
                start_latitude=1,
                start_longitude=1,
                start_photo=SimpleUploadedFile(
                    "a.jpg", b"d", content_type="image/jpeg"
                ),
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_start_session_already_active(self, mock_notify):
        """Test starting a session when one is already active."""
        photo = SimpleUploadedFile("start.jpg", b"data", content_type="image/jpeg")
        work_session_service.start_session(
            handyman=self.handyman,
            job=self.job,
            started_at=timezone.now(),
            start_latitude=1,
            start_longitude=1,
            start_photo=photo,
        )
        with self.assertRaisesRegex(ValidationError, "already have an active session"):
            work_session_service.start_session(
                handyman=self.handyman,
                job=self.job,
                started_at=timezone.now(),
                start_latitude=1,
                start_longitude=1,
                start_photo=SimpleUploadedFile(
                    "a.jpg", b"d", content_type="image/jpeg"
                ),
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_stop_session_not_active(self, mock_notify):
        """Test stopping a session that is not in_progress."""
        photo = SimpleUploadedFile("start.jpg", b"data", content_type="image/jpeg")
        session = work_session_service.start_session(
            handyman=self.handyman,
            job=self.job,
            started_at=timezone.now(),
            start_latitude=1,
            start_longitude=1,
            start_photo=photo,
        )
        session.status = "completed"
        session.save()
        with self.assertRaisesRegex(ValidationError, "Session is not active"):
            work_session_service.stop_session(
                session=session,
                ended_at=timezone.now(),
                end_latitude=1,
                end_longitude=1,
            )

    def test_submit_report_job_not_active(self):
        """Test submitting report for a job that is not in_progress/pending_completion."""
        self.job.status = "completed"
        self.job.save()
        with self.assertRaisesRegex(ValidationError, "not active for reporting"):
            daily_report_service.submit_report(
                handyman=self.handyman,
                job=self.job,
                report_date=timezone.now().date(),
                summary="summary",
                total_work_duration=timedelta(hours=1),
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_submit_report_duplicate_date(self, mock_notify):
        """Test submitting a report for a date that already has one."""
        report_date = timezone.now().date()
        daily_report_service.submit_report(
            handyman=self.handyman,
            job=self.job,
            report_date=report_date,
            summary="First report",
            total_work_duration=timedelta(hours=2),
        )
        with self.assertRaisesRegex(ValidationError, "report for this date already"):
            daily_report_service.submit_report(
                handyman=self.handyman,
                job=self.job,
                report_date=report_date,
                summary="Second report",
                total_work_duration=timedelta(hours=1),
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_submit_report_task_entry_not_job_task(self, mock_notify):
        """Test that non-JobTask entries in task_entries are skipped (continue branch)."""
        report = daily_report_service.submit_report(
            handyman=self.handyman,
            job=self.job,
            report_date=timezone.now().date(),
            summary="summary",
            total_work_duration=timedelta(hours=1),
            task_entries=[
                {"task": "not_a_task_object", "marked_complete": True},
                {"task": None, "marked_complete": False},
            ],
        )
        self.assertEqual(report.status, "pending")
        # No DailyReportTask created for invalid entries
        self.assertEqual(report.tasks_worked.count(), 0)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_review_report_wrong_homeowner(self, mock_notify):
        """Test reviewing a report by a different homeowner."""
        report = daily_report_service.submit_report(
            handyman=self.handyman,
            job=self.job,
            report_date=timezone.now().date(),
            summary="summary",
            total_work_duration=timedelta(hours=1),
        )
        other_homeowner = User.objects.create_user(
            email="other_home@example.com", password="pass"
        )
        with self.assertRaisesRegex(ValidationError, "only review your own"):
            daily_report_service.review_report(
                homeowner=other_homeowner,
                report=report,
                decision="approved",
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_review_report_not_pending(self, mock_notify):
        """Test reviewing a report that is not pending."""
        report = daily_report_service.submit_report(
            handyman=self.handyman,
            job=self.job,
            report_date=timezone.now().date(),
            summary="summary",
            total_work_duration=timedelta(hours=1),
        )
        report.status = "approved"
        report.save()
        with self.assertRaisesRegex(ValidationError, "Only pending reports"):
            daily_report_service.review_report(
                homeowner=self.homeowner,
                report=report,
                decision="approved",
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_review_report_invalid_decision(self, mock_notify):
        """Test reviewing a report with an invalid decision."""
        report = daily_report_service.submit_report(
            handyman=self.handyman,
            job=self.job,
            report_date=timezone.now().date(),
            summary="summary",
            total_work_duration=timedelta(hours=1),
        )
        with self.assertRaisesRegex(ValidationError, "Invalid decision"):
            daily_report_service.review_report(
                homeowner=self.homeowner,
                report=report,
                decision="invalid_decision",
            )

    def test_request_completion_wrong_handyman(self):
        """Test requesting completion by non-assigned handyman."""
        other_handy = User.objects.create_user(
            email="other_handy@example.com", password="pass"
        )
        with self.assertRaisesRegex(ValidationError, "not assigned to this job"):
            job_completion_service.request_completion(other_handy, self.job)

    def test_request_completion_not_in_progress(self):
        """Test requesting completion when job is not in_progress."""
        self.job.status = "pending_completion"
        self.job.save()
        with self.assertRaisesRegex(ValidationError, "only be requested in progress"):
            job_completion_service.request_completion(self.handyman, self.job)

    def test_approve_completion_job_not_pending(self):
        """Test approving completion when job is not pending_completion."""
        # Job is in_progress, not pending_completion
        with self.assertRaisesRegex(ValidationError, "not awaiting completion"):
            job_completion_service.approve_completion(self.homeowner, self.job)

    def test_reject_completion_wrong_owner(self):
        """Test rejecting completion by wrong owner."""
        self.job.status = "pending_completion"
        self.job.save()
        other_owner = User.objects.create_user(
            email="other_ow@example.com", password="pass"
        )
        with self.assertRaisesRegex(ValidationError, "only reject your own job"):
            job_completion_service.reject_completion(other_owner, self.job)

    def test_reject_completion_job_not_pending(self):
        """Test rejecting completion when job is not pending_completion."""
        with self.assertRaisesRegex(ValidationError, "not awaiting completion"):
            job_completion_service.reject_completion(self.homeowner, self.job)

    def test_open_dispute_job_not_eligible(self):
        """Test opening dispute for a job that is not eligible."""
        self.job.status = "open"
        self.job.save()
        with self.assertRaisesRegex(ValidationError, "not eligible for dispute"):
            dispute_service.open_dispute(
                homeowner=self.homeowner,
                job=self.job,
                reason="Issue",
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_open_dispute_with_disputed_reports(self, mock_notify):
        """Test opening dispute with disputed_reports list."""
        from apps.jobs.models import DailyReport

        self.job.status = "pending_completion"
        self.job.save()
        report = DailyReport.objects.create(
            job=self.job,
            handyman=self.handyman,
            report_date=timezone.now().date(),
            summary="summary",
            total_work_duration=timedelta(hours=2),
            review_deadline=timezone.now() + timedelta(days=3),
        )
        dispute = dispute_service.open_dispute(
            homeowner=self.homeowner,
            job=self.job,
            reason="Issue with reports",
            disputed_reports=[report],
        )
        self.assertEqual(dispute.disputed_reports.count(), 1)
        self.assertIn(report, dispute.disputed_reports.all())

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_resolve_dispute_invalid_status(self, mock_notify):
        """Test resolving dispute with an invalid resolution status."""
        self.job.status = "pending_completion"
        self.job.save()
        dispute = dispute_service.open_dispute(
            homeowner=self.homeowner,
            job=self.job,
            reason="Issue",
        )
        with self.assertRaisesRegex(ValidationError, "Invalid resolution status"):
            dispute_service.resolve_dispute(
                admin_user=self.homeowner,
                dispute=dispute,
                status="invalid_status",
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_resolve_dispute_notifies_handyman(self, mock_notify):
        """Test that resolving dispute notifies the assigned handyman."""
        self.job.status = "pending_completion"
        self.job.save()
        dispute = dispute_service.open_dispute(
            homeowner=self.homeowner,
            job=self.job,
            reason="Issue",
        )
        mock_notify.reset_mock()
        dispute_service.resolve_dispute(
            admin_user=self.homeowner,
            dispute=dispute,
            status="resolved_pay_handyman",
        )
        # Should have 2 notifications: one for homeowner, one for handyman
        self.assertEqual(mock_notify.call_count, 2)
        call_args_list = [call.kwargs for call in mock_notify.call_args_list]
        users_notified = [args["user"] for args in call_args_list]
        self.assertIn(self.homeowner, users_notified)
        self.assertIn(self.handyman, users_notified)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_resolve_dispute_without_assigned_handyman(self, mock_notify):
        """Test resolving dispute when job has no assigned handyman (branch 727->741)."""
        self.job.status = "pending_completion"
        self.job.assigned_handyman = None
        self.job.save()
        dispute = dispute_service.open_dispute(
            homeowner=self.homeowner,
            job=self.job,
            reason="Issue",
        )
        mock_notify.reset_mock()
        dispute_service.resolve_dispute(
            admin_user=self.homeowner,
            dispute=dispute,
            status="resolved_pay_handyman",
        )
        # Should only notify homeowner (no handyman assigned)
        self.assertEqual(mock_notify.call_count, 1)
        call_kwargs = mock_notify.call_args.kwargs
        self.assertEqual(call_kwargs["user"], self.homeowner)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_submit_report_with_task_not_marked_complete(self, mock_notify):
        """Test submitting report with task entry where marked_complete=False (branch 480->470)."""
        report = daily_report_service.submit_report(
            handyman=self.handyman,
            job=self.job,
            report_date=timezone.now().date(),
            summary="Did work",
            total_work_duration=timedelta(hours=2),
            task_entries=[
                {"task": self.task1, "marked_complete": False, "notes": "WIP"}
            ],
        )
        self.task1.refresh_from_db()
        self.assertFalse(self.task1.is_completed)
        self.assertEqual(report.tasks_worked.count(), 1)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_stop_session_end_time_before_start_time(self, mock_notify):
        """Test stopping a session with end time before or equal to start time."""
        photo = SimpleUploadedFile("start.jpg", b"data", content_type="image/jpeg")
        start_time = timezone.now()
        session = work_session_service.start_session(
            handyman=self.handyman,
            job=self.job,
            started_at=start_time,
            start_latitude=1,
            start_longitude=1,
            start_photo=photo,
        )
        # Try to stop with end time before start time
        with self.assertRaisesRegex(ValidationError, "End time must be after start"):
            work_session_service.stop_session(
                session=session,
                ended_at=start_time - timedelta(hours=1),
                end_latitude=1,
                end_longitude=1,
            )
        # Try to stop with end time equal to start time
        with self.assertRaisesRegex(ValidationError, "End time must be after start"):
            work_session_service.stop_session(
                session=session,
                ended_at=start_time,
                end_latitude=1,
                end_longitude=1,
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_add_media_task_not_belonging_to_job(self, mock_notify):
        """Test adding media with a task that doesn't belong to the job."""
        # Create a different job with its own task
        other_job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Other job",
            description="Different job",
            estimated_budget=200,
            category=self.category,
            city=self.city,
            address="456 St",
            status="in_progress",
        )
        other_task = JobTask.objects.create(job=other_job, title="Other Task", order=0)

        # Start a session for self.job
        photo = SimpleUploadedFile("start.jpg", b"data", content_type="image/jpeg")
        session = work_session_service.start_session(
            handyman=self.handyman,
            job=self.job,
            started_at=timezone.now(),
            start_latitude=1,
            start_longitude=1,
            start_photo=photo,
        )

        # Try to add media with task from other_job
        with self.assertRaisesRegex(
            ValidationError, "Task does not belong to this job"
        ):
            work_session_service.add_media(
                work_session=session,
                media_type="photo",
                file=SimpleUploadedFile(
                    "media.jpg", b"data", content_type="image/jpeg"
                ),
                file_size=1024,
                task=other_task,
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_submit_report_task_not_belonging_to_job(self, mock_notify):
        """Test submitting report with a task that doesn't belong to the job."""
        # Create a different job with its own task
        other_job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Other job",
            description="Different job",
            estimated_budget=200,
            category=self.category,
            city=self.city,
            address="456 St",
            status="in_progress",
        )
        other_task = JobTask.objects.create(job=other_job, title="Other Task", order=0)

        # Try to submit report with task from other_job
        with self.assertRaisesRegex(ValidationError, "does not belong to this job"):
            daily_report_service.submit_report(
                handyman=self.handyman,
                job=self.job,
                report_date=timezone.now().date(),
                summary="Did work",
                total_work_duration=timedelta(hours=2),
                task_entries=[{"task": other_task, "marked_complete": True}],
            )


class DailyReportServiceUpdateReportTests(TestCase):
    """Test cases for DailyReportService.update_report method."""

    def setUp(self):
        """Set up test data."""
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
            name="Toronto", province="Ontario", province_code="ON", slug="toronto"
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Test Job",
            description="Test description",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 St",
            status="in_progress",
        )
        self.task = JobTask.objects.create(job=self.job, title="Test Task", order=0)

        self.report = DailyReport.objects.create(
            job=self.job,
            handyman=self.handyman,
            report_date=timezone.now().date(),
            summary="Original summary",
            total_work_duration=timedelta(hours=2),
            status="pending",
            review_deadline=timezone.now() + timedelta(days=3),
        )
        DailyReportTask.objects.create(
            daily_report=self.report,
            task=self.task,
            notes="Original notes",
            marked_complete=False,
        )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_update_report_success(self, mock_notify):
        """Test successfully updating a report."""
        daily_report_service.update_report(
            handyman=self.handyman,
            report=self.report,
            summary="Updated summary",
        )
        self.report.refresh_from_db()
        self.assertEqual(self.report.summary, "Updated summary")

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_update_report_rejected_resets_status(self, mock_notify):
        """Test that editing rejected report resets status to pending."""
        self.report.status = "rejected"
        self.report.homeowner_comment = "Needs more detail"
        self.report.save()

        daily_report_service.update_report(
            handyman=self.handyman,
            report=self.report,
            summary="More detailed summary",
        )
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "pending")
        self.assertIsNone(self.report.reviewed_by)
        self.assertIsNone(self.report.reviewed_at)
        self.assertEqual(self.report.homeowner_comment, "")

    def test_update_report_wrong_handyman_fails(self):
        """Test that editing another handyman's report fails."""
        other_handyman = User.objects.create_user(
            email="other@example.com", password="password123"
        )
        UserRole.objects.create(user=other_handyman, role="handyman")
        HandymanProfile.objects.create(
            user=other_handyman,
            display_name="Other",
            phone_verified_at=datetime.now(UTC),
        )

        with self.assertRaisesRegex(ValidationError, "only edit your own reports"):
            daily_report_service.update_report(
                handyman=other_handyman,
                report=self.report,
                summary="Hacked summary",
            )

    def test_update_report_approved_fails(self):
        """Test that editing approved report fails."""
        self.report.status = "approved"
        self.report.save()

        with self.assertRaisesRegex(ValidationError, "pending or rejected"):
            daily_report_service.update_report(
                handyman=self.handyman,
                report=self.report,
                summary="New summary",
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_update_report_with_invalid_task(self, mock_notify):
        """Test updating report with an invalid task entry (not a JobTask instance)."""
        daily_report_service.update_report(
            handyman=self.handyman,
            report=self.report,
            task_entries=[
                {"task": "not-a-jobtask", "marked_complete": True},
                {"task": self.task, "marked_complete": True},
            ],
        )
        self.report.refresh_from_db()
        self.task.refresh_from_db()
        self.assertTrue(self.task.is_completed)
