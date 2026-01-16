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
    JobApplicationAttachment,
    JobApplicationMaterial,
    JobCategory,
    JobTask,
    Review,
)
from apps.jobs.services import (
    JobApplicationService,
    daily_report_service,
    dispute_service,
    job_completion_service,
    review_service,
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

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_apply_to_job_with_proposal_data(self, mock_notify):
        """Test job application with proposal data."""
        from decimal import Decimal

        from django.core.files.uploadedfile import SimpleUploadedFile

        materials_data = [
            {"name": "PVC Pipe", "price": Decimal("25.50"), "description": "2m"},
            {"name": "Fittings", "price": Decimal("15.00"), "description": "4 pieces"},
        ]
        attachments = [
            SimpleUploadedFile(
                "quote.pdf", b"file content", content_type="application/pdf"
            )
        ]

        application = self.service.apply_to_job(
            self.handyman,
            self.job,
            predicted_hours=Decimal("8.5"),
            estimated_total_price=Decimal("450.00"),
            negotiation_reasoning="Need additional materials",
            materials_data=materials_data,
            attachments=attachments,
        )

        self.assertEqual(application.predicted_hours, Decimal("8.5"))
        self.assertEqual(application.estimated_total_price, Decimal("450.00"))
        self.assertEqual(application.negotiation_reasoning, "Need additional materials")

        # Check materials were created
        materials = JobApplicationMaterial.objects.filter(application=application)
        self.assertEqual(materials.count(), 2)
        self.assertEqual(materials[0].name, "PVC Pipe")
        self.assertEqual(materials[1].name, "Fittings")

        # Check attachments were created
        attachments_created = JobApplicationAttachment.objects.filter(
            application=application
        )
        self.assertEqual(attachments_created.count(), 1)
        self.assertEqual(attachments_created[0].file_name, "quote.pdf")

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

    def test_update_application_wrong_handyman(self):
        """Test updating application by a different handyman."""
        application = self.service.apply_to_job(self.handyman, self.job)

        other_handy = User.objects.create_user(
            email="other_handy@example.com", password="password123"
        )
        UserRole.objects.create(user=other_handy, role="handyman")
        HandymanProfile.objects.create(
            user=other_handy, display_name="Other", phone_verified_at=datetime.now(UTC)
        )

        with self.assertRaisesRegex(ValidationError, "only update your own"):
            self.service.update_application(
                handyman=other_handy,
                application=application,
                predicted_hours=10,
            )

    def test_update_application_with_legacy_plain_file_attachment(self):
        """Test update_application handles legacy plain file attachments."""
        from decimal import Decimal

        from django.core.files.uploadedfile import SimpleUploadedFile

        application = self.service.apply_to_job(self.handyman, self.job)

        # Create a plain file (legacy format - not a dict)
        plain_file = SimpleUploadedFile(
            "quote.pdf", b"file content", content_type="application/pdf"
        )

        # This should handle the legacy format where attachment is just a file
        updated = self.service.update_application(
            handyman=self.handyman,
            application=application,
            predicted_hours=Decimal("10.0"),
            attachments=[plain_file],  # Legacy plain file format
        )

        # Check attachment was created
        attachments = updated.attachments.all()
        self.assertEqual(attachments.count(), 1)
        self.assertEqual(attachments[0].file_name, "quote.pdf")
        # Document type should be detected from mime
        self.assertEqual(attachments[0].file_type, "document")


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

        end_photo = SimpleUploadedFile("end.jpg", b"data", content_type="image/jpeg")
        work_session_service.stop_session(
            session=session,
            ended_at=timezone.now(),
            end_latitude=1,
            end_longitude=1,
            end_photo=end_photo,
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
        end_photo = SimpleUploadedFile("end.jpg", b"data", content_type="image/jpeg")
        with self.assertRaisesRegex(ValidationError, "Session is not active"):
            work_session_service.stop_session(
                session=session,
                ended_at=timezone.now(),
                end_latitude=1,
                end_longitude=1,
                end_photo=end_photo,
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
        end_photo = SimpleUploadedFile("end.jpg", b"data", content_type="image/jpeg")
        with self.assertRaisesRegex(ValidationError, "End time must be after start"):
            work_session_service.stop_session(
                session=session,
                ended_at=start_time - timedelta(hours=1),
                end_latitude=1,
                end_longitude=1,
                end_photo=end_photo,
            )
        # Try to stop with end time equal to start time
        end_photo2 = SimpleUploadedFile("end2.jpg", b"data", content_type="image/jpeg")
        with self.assertRaisesRegex(ValidationError, "End time must be after start"):
            work_session_service.stop_session(
                session=session,
                ended_at=start_time,
                end_latitude=1,
                end_longitude=1,
                end_photo=end_photo2,
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


class ReviewServiceTests(TestCase):
    """Test cases for ReviewService."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        UserRole.objects.create(user=self.handyman, role="handyman")

        self.homeowner_profile = HomeownerProfile.objects.create(
            user=self.homeowner, display_name="Test Owner"
        )
        self.handyman_profile = HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
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
            address="123 Main St",
            status="completed",
            completed_at=timezone.now(),
        )

    def test_can_review_success(self):
        """Test can_review returns True for valid review."""
        can_review, error = review_service.can_review(
            self.homeowner, self.job, "homeowner"
        )
        self.assertTrue(can_review)
        self.assertEqual(error, "")

    def test_can_review_job_not_completed(self):
        """Test can_review fails if job is not completed."""
        self.job.status = "in_progress"
        self.job.save()

        can_review, error = review_service.can_review(
            self.homeowner, self.job, "homeowner"
        )
        self.assertFalse(can_review)
        self.assertIn("completed jobs", error)

    def test_can_review_wrong_homeowner(self):
        """Test can_review fails if wrong homeowner."""
        other_user = User.objects.create_user(
            email="other@example.com", password="password123"
        )
        can_review, error = review_service.can_review(other_user, self.job, "homeowner")
        self.assertFalse(can_review)
        self.assertIn("only review jobs you posted", error)

    def test_can_review_wrong_handyman(self):
        """Test can_review fails if wrong handyman."""
        other_user = User.objects.create_user(
            email="other@example.com", password="password123"
        )
        can_review, error = review_service.can_review(other_user, self.job, "handyman")
        self.assertFalse(can_review)
        self.assertIn("only review jobs you were assigned to", error)

    def test_can_review_invalid_reviewer_type(self):
        """Test can_review fails for invalid reviewer type."""
        can_review, error = review_service.can_review(
            self.homeowner, self.job, "invalid"
        )
        self.assertFalse(can_review)
        self.assertIn("Invalid reviewer type", error)

    def test_can_review_outside_review_window(self):
        """Test can_review fails if outside 14-day window."""
        self.job.completed_at = timezone.now() - timedelta(days=15)
        self.job.save()

        can_review, error = review_service.can_review(
            self.homeowner, self.job, "homeowner"
        )
        self.assertFalse(can_review)
        self.assertIn("review window has expired", error)

    def test_can_review_already_reviewed(self):
        """Test can_review fails if already reviewed."""
        Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
        )

        can_review, error = review_service.can_review(
            self.homeowner, self.job, "homeowner"
        )
        self.assertFalse(can_review)
        self.assertIn("already reviewed", error)

    def test_is_within_review_window_no_completed_at(self):
        """Test is_within_review_window returns False if completed_at is None."""
        self.job.completed_at = None
        self.job.save()

        result = review_service.is_within_review_window(self.job)
        self.assertFalse(result)

    def test_is_within_review_window_within_window(self):
        """Test is_within_review_window returns True if within 14 days."""
        self.job.completed_at = timezone.now() - timedelta(days=10)
        self.job.save()

        result = review_service.is_within_review_window(self.job)
        self.assertTrue(result)

    def test_is_within_review_window_exactly_at_deadline(self):
        """Test is_within_review_window just before 14 days."""
        # Set to just under 14 days to ensure we're within the window
        self.job.completed_at = timezone.now() - timedelta(
            days=13, hours=23, minutes=59
        )
        self.job.save()

        result = review_service.is_within_review_window(self.job)
        self.assertTrue(result)

    def test_can_edit_review_success(self):
        """Test can_edit_review returns True for valid edit."""
        review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
        )

        can_edit, error = review_service.can_edit_review(self.homeowner, review)
        self.assertTrue(can_edit)
        self.assertEqual(error, "")

    def test_can_edit_review_wrong_user(self):
        """Test can_edit_review fails for wrong user."""
        review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
        )

        can_edit, error = review_service.can_edit_review(self.handyman, review)
        self.assertFalse(can_edit)
        self.assertIn("only edit your own reviews", error)

    def test_can_edit_review_outside_window(self):
        """Test can_edit_review fails outside review window."""
        self.job.completed_at = timezone.now() - timedelta(days=15)
        self.job.save()

        review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
        )

        can_edit, error = review_service.can_edit_review(self.homeowner, review)
        self.assertFalse(can_edit)
        self.assertIn("edit window has expired", error)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_review_homeowner_success(self, mock_notify):
        """Test homeowner creating a review for handyman."""
        review = review_service.create_review(
            user=self.homeowner,
            job=self.job,
            reviewer_type="homeowner",
            rating=5,
            comment="Great work!",
        )

        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, "Great work!")
        self.assertEqual(review.reviewer, self.homeowner)
        self.assertEqual(review.reviewee, self.handyman)

        # Check profile rating updated
        self.handyman_profile.refresh_from_db()
        self.assertEqual(self.handyman_profile.rating, 5)
        self.assertEqual(self.handyman_profile.review_count, 1)

        # Check notification sent
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args.kwargs
        self.assertEqual(call_kwargs["user"], self.handyman)
        self.assertEqual(call_kwargs["notification_type"], "review_received")

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_review_handyman_success(self, mock_notify):
        """Test handyman creating a review for homeowner (no notification)."""
        review = review_service.create_review(
            user=self.handyman,
            job=self.job,
            reviewer_type="handyman",
            rating=4,
            comment="Good homeowner!",
        )

        self.assertEqual(review.rating, 4)
        self.assertEqual(review.reviewer, self.handyman)
        self.assertEqual(review.reviewee, self.homeowner)

        # Check profile rating updated
        self.homeowner_profile.refresh_from_db()
        self.assertEqual(self.homeowner_profile.rating, 4)
        self.assertEqual(self.homeowner_profile.review_count, 1)

        # Check NO notification sent for handyman reviewing homeowner
        mock_notify.assert_not_called()

    def test_create_review_validation_error(self):
        """Test create_review raises ValidationError for invalid review."""
        self.job.status = "in_progress"
        self.job.save()

        with self.assertRaises(ValidationError):
            review_service.create_review(
                user=self.homeowner,
                job=self.job,
                reviewer_type="homeowner",
                rating=5,
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_update_review_success(self, mock_notify):
        """Test updating an existing review."""
        review = review_service.create_review(
            user=self.homeowner,
            job=self.job,
            reviewer_type="homeowner",
            rating=3,
        )
        mock_notify.reset_mock()

        updated_review = review_service.update_review(
            user=self.homeowner,
            review=review,
            rating=5,
            comment="Updated comment",
        )

        self.assertEqual(updated_review.rating, 5)
        self.assertEqual(updated_review.comment, "Updated comment")

        # Check profile rating updated
        self.handyman_profile.refresh_from_db()
        self.assertEqual(self.handyman_profile.rating, 5)

    def test_update_review_validation_error(self):
        """Test update_review raises ValidationError for invalid edit."""
        review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
        )

        # Try to edit as wrong user
        with self.assertRaises(ValidationError):
            review_service.update_review(
                user=self.handyman,
                review=review,
                rating=4,
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_update_profile_rating_multiple_reviews(self, mock_notify):
        """Test profile rating is average of all reviews."""
        # Create first job with review
        review_service.create_review(
            user=self.homeowner,
            job=self.job,
            reviewer_type="homeowner",
            rating=4,
        )

        # Create second job with review
        job2 = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Fix door",
            description="Broken door",
            estimated_budget=50,
            category=self.category,
            city=self.city,
            address="456 Main St",
            status="completed",
            completed_at=timezone.now(),
        )
        review_service.create_review(
            user=self.homeowner,
            job=job2,
            reviewer_type="homeowner",
            rating=2,
        )

        # Average should be 3.0
        self.handyman_profile.refresh_from_db()
        self.assertEqual(self.handyman_profile.rating, 3)
        self.assertEqual(self.handyman_profile.review_count, 2)

    def test_update_profile_rating_no_profile(self):
        """Test update_profile_rating handles missing profile gracefully."""
        # Create user without profile
        user_no_profile = User.objects.create_user(
            email="noprofile@example.com", password="password123"
        )

        # Should not raise error
        review_service.update_profile_rating(user_no_profile, "homeowner")
        review_service.update_profile_rating(user_no_profile, "handyman")

    def test_get_review_for_job_exists(self):
        """Test get_review_for_job returns review when it exists."""
        review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
        )

        result = review_service.get_review_for_job(self.job, "homeowner")
        self.assertEqual(result, review)

    def test_get_review_for_job_not_exists(self):
        """Test get_review_for_job returns None when no review exists."""
        result = review_service.get_review_for_job(self.job, "homeowner")
        self.assertIsNone(result)

    def test_get_reviews_received(self):
        """Test get_reviews_received returns all reviews for a user."""
        # Create multiple jobs with reviews
        Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
        )

        job2 = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Fix door",
            description="Broken door",
            estimated_budget=50,
            category=self.category,
            city=self.city,
            address="456 Main St",
            status="completed",
            completed_at=timezone.now(),
        )
        Review.objects.create(
            job=job2,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=4,
        )

        reviews = review_service.get_reviews_received(self.handyman, "homeowner")
        self.assertEqual(reviews.count(), 2)


class ReimbursementServiceTests(TestCase):
    """Test cases for ReimbursementService."""

    def setUp(self):
        """Set up test data."""
        from apps.jobs.models import JobReimbursementCategory
        from apps.jobs.services import ReimbursementService

        self.service = ReimbursementService()
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

        # Use get_or_create for categories that may already exist from migration
        self.reimbursement_category, _ = JobReimbursementCategory.objects.get_or_create(
            slug="materials",
            defaults={
                "name": "Materials",
                "description": "Material expenses",
                "is_active": True,
            },
        )
        self.tools_category, _ = JobReimbursementCategory.objects.get_or_create(
            slug="tools",
            defaults={
                "name": "Tools",
                "description": "Tool expenses",
                "is_active": True,
            },
        )

        self.job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Leaky faucet in kitchen",
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
            estimated_budget=100,
        )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_submit_reimbursement_success(self, mock_notify):
        """Test successful reimbursement submission."""
        from decimal import Decimal

        attachments = [
            SimpleUploadedFile(
                "receipt.jpg", b"file content", content_type="image/jpeg"
            )
        ]

        reimbursement = self.service.submit_reimbursement(
            handyman=self.handyman,
            job=self.job,
            name="Plumbing materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
            attachments=attachments,
            notes="Required for repair",
        )

        self.assertEqual(reimbursement.job, self.job)
        self.assertEqual(reimbursement.handyman, self.handyman)
        self.assertEqual(reimbursement.name, "Plumbing materials")
        self.assertEqual(reimbursement.category, self.reimbursement_category)
        self.assertEqual(reimbursement.amount, Decimal("50.00"))
        self.assertEqual(reimbursement.status, "pending")
        self.assertEqual(reimbursement.attachments.count(), 1)
        mock_notify.assert_called_once()

    def test_submit_reimbursement_not_assigned(self):
        """Test submitting reimbursement when not assigned to job."""
        other_handyman = User.objects.create_user(
            email="other@example.com", password="password123"
        )
        UserRole.objects.create(user=other_handyman, role="handyman")
        HandymanProfile.objects.create(
            user=other_handyman,
            display_name="Other",
            phone_verified_at=datetime.now(UTC),
        )

        attachments = [
            SimpleUploadedFile(
                "receipt.jpg", b"file content", content_type="image/jpeg"
            )
        ]

        with self.assertRaisesRegex(ValidationError, "not assigned"):
            self.service.submit_reimbursement(
                handyman=other_handyman,
                job=self.job,
                name="Materials",
                category=self.reimbursement_category,
                amount=50,
                attachments=attachments,
            )

    def test_submit_reimbursement_job_not_active(self):
        """Test submitting reimbursement for non-active job."""
        self.job.status = "completed"
        self.job.save()

        attachments = [
            SimpleUploadedFile(
                "receipt.jpg", b"file content", content_type="image/jpeg"
            )
        ]

        with self.assertRaisesRegex(ValidationError, "not active"):
            self.service.submit_reimbursement(
                handyman=self.handyman,
                job=self.job,
                name="Materials",
                category=self.reimbursement_category,
                amount=50,
                attachments=attachments,
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_submit_reimbursement_pending_completion(self, mock_notify):
        """Test submitting reimbursement for job pending completion."""
        from decimal import Decimal

        self.job.status = "pending_completion"
        self.job.save()

        attachments = [
            SimpleUploadedFile(
                "receipt.jpg", b"file content", content_type="image/jpeg"
            )
        ]

        reimbursement = self.service.submit_reimbursement(
            handyman=self.handyman,
            job=self.job,
            name="Materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
            attachments=attachments,
        )

        self.assertEqual(reimbursement.status, "pending")

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_review_reimbursement_approve(self, mock_notify):
        """Test approving a reimbursement."""
        from decimal import Decimal

        from apps.jobs.models import JobReimbursement

        reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
            status="pending",
        )

        result = self.service.review_reimbursement(
            homeowner=self.homeowner,
            reimbursement=reimbursement,
            decision="approved",
            comment="Looks good",
        )

        self.assertEqual(result.status, "approved")
        self.assertEqual(result.homeowner_comment, "Looks good")
        self.assertEqual(result.reviewed_by, self.homeowner)
        self.assertIsNotNone(result.reviewed_at)
        mock_notify.assert_called_once()

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_review_reimbursement_reject(self, mock_notify):
        """Test rejecting a reimbursement."""
        from decimal import Decimal

        from apps.jobs.models import JobReimbursement

        reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
            status="pending",
        )

        result = self.service.review_reimbursement(
            homeowner=self.homeowner,
            reimbursement=reimbursement,
            decision="rejected",
            comment="Receipt not clear",
        )

        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.homeowner_comment, "Receipt not clear")
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args.kwargs
        self.assertEqual(call_kwargs["notification_type"], "reimbursement_rejected")

    def test_review_reimbursement_not_owner(self):
        """Test reviewing reimbursement when not the job owner."""
        from decimal import Decimal

        from apps.jobs.models import JobReimbursement

        other_homeowner = User.objects.create_user(
            email="other_owner@example.com", password="password123"
        )

        reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
            status="pending",
        )

        with self.assertRaisesRegex(ValidationError, "your own jobs"):
            self.service.review_reimbursement(
                homeowner=other_homeowner,
                reimbursement=reimbursement,
                decision="approved",
            )

    def test_review_reimbursement_already_reviewed(self):
        """Test reviewing already reviewed reimbursement."""
        from decimal import Decimal

        from apps.jobs.models import JobReimbursement

        reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
            status="approved",
            reviewed_by=self.homeowner,
            reviewed_at=timezone.now(),
        )

        with self.assertRaisesRegex(ValidationError, "pending"):
            self.service.review_reimbursement(
                homeowner=self.homeowner,
                reimbursement=reimbursement,
                decision="rejected",
            )

    def test_review_reimbursement_invalid_decision(self):
        """Test reviewing reimbursement with invalid decision."""
        from decimal import Decimal

        from apps.jobs.models import JobReimbursement

        reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
            status="pending",
        )

        with self.assertRaisesRegex(ValidationError, "Invalid decision"):
            self.service.review_reimbursement(
                homeowner=self.homeowner,
                reimbursement=reimbursement,
                decision="pending",  # Invalid decision
            )

    def test_update_reimbursement_success(self):
        """Test successful reimbursement update."""
        from decimal import Decimal

        from apps.jobs.models import JobReimbursement, JobReimbursementAttachment

        reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
            status="pending",
        )
        # Add initial attachment
        JobReimbursementAttachment.objects.create(
            reimbursement=reimbursement,
            file=SimpleUploadedFile("receipt.jpg", b"file", content_type="image/jpeg"),
            file_name="receipt.jpg",
        )

        result = self.service.update_reimbursement(
            handyman=self.handyman,
            reimbursement=reimbursement,
            name="Updated Materials",
            category=self.tools_category,
            amount=Decimal("75.00"),
            notes="Updated notes",
        )

        self.assertEqual(result.name, "Updated Materials")
        self.assertEqual(result.category, self.tools_category)
        self.assertEqual(result.amount, Decimal("75.00"))
        self.assertEqual(result.notes, "Updated notes")

    def test_update_reimbursement_not_owner(self):
        """Test updating reimbursement when not the owner."""
        from decimal import Decimal

        from apps.jobs.models import JobReimbursement, JobReimbursementAttachment

        other_handyman = User.objects.create_user(
            email="other@example.com", password="password123"
        )

        reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
            status="pending",
        )
        JobReimbursementAttachment.objects.create(
            reimbursement=reimbursement,
            file=SimpleUploadedFile("receipt.jpg", b"file", content_type="image/jpeg"),
            file_name="receipt.jpg",
        )

        with self.assertRaisesRegex(ValidationError, "your own"):
            self.service.update_reimbursement(
                handyman=other_handyman,
                reimbursement=reimbursement,
                name="Updated",
            )

    def test_update_reimbursement_not_pending(self):
        """Test updating non-pending reimbursement."""
        from decimal import Decimal

        from apps.jobs.models import JobReimbursement, JobReimbursementAttachment

        reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
            status="approved",
        )
        JobReimbursementAttachment.objects.create(
            reimbursement=reimbursement,
            file=SimpleUploadedFile("receipt.jpg", b"file", content_type="image/jpeg"),
            file_name="receipt.jpg",
        )

        with self.assertRaisesRegex(ValidationError, "pending"):
            self.service.update_reimbursement(
                handyman=self.handyman,
                reimbursement=reimbursement,
                name="Updated",
            )

    def test_update_reimbursement_add_attachments(self):
        """Test adding attachments to reimbursement."""
        from decimal import Decimal

        from apps.jobs.models import JobReimbursement, JobReimbursementAttachment

        reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
            status="pending",
        )
        JobReimbursementAttachment.objects.create(
            reimbursement=reimbursement,
            file=SimpleUploadedFile("receipt.jpg", b"file", content_type="image/jpeg"),
            file_name="receipt.jpg",
        )

        new_attachment = SimpleUploadedFile(
            "receipt2.jpg", b"file2", content_type="image/jpeg"
        )
        result = self.service.update_reimbursement(
            handyman=self.handyman,
            reimbursement=reimbursement,
            attachments=[new_attachment],
        )

        self.assertEqual(result.attachments.count(), 2)

    def test_update_reimbursement_remove_attachments(self):
        """Test removing attachments from reimbursement."""
        from decimal import Decimal

        from apps.jobs.models import JobReimbursement, JobReimbursementAttachment

        reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
            status="pending",
        )
        att1 = JobReimbursementAttachment.objects.create(
            reimbursement=reimbursement,
            file=SimpleUploadedFile(
                "receipt1.jpg", b"file1", content_type="image/jpeg"
            ),
            file_name="receipt1.jpg",
        )
        JobReimbursementAttachment.objects.create(
            reimbursement=reimbursement,
            file=SimpleUploadedFile(
                "receipt2.jpg", b"file2", content_type="image/jpeg"
            ),
            file_name="receipt2.jpg",
        )

        result = self.service.update_reimbursement(
            handyman=self.handyman,
            reimbursement=reimbursement,
            attachments_to_remove=[att1.public_id],
        )

        self.assertEqual(result.attachments.count(), 1)

    def test_update_reimbursement_no_attachments_left(self):
        """Test error when removing all attachments."""
        from decimal import Decimal

        from apps.jobs.models import JobReimbursement, JobReimbursementAttachment

        reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
            status="pending",
        )
        att = JobReimbursementAttachment.objects.create(
            reimbursement=reimbursement,
            file=SimpleUploadedFile("receipt.jpg", b"file", content_type="image/jpeg"),
            file_name="receipt.jpg",
        )

        with self.assertRaisesRegex(ValidationError, "At least one attachment"):
            self.service.update_reimbursement(
                handyman=self.handyman,
                reimbursement=reimbursement,
                attachments_to_remove=[att.public_id],
            )


class DirectOfferServiceTests(TestCase):
    """Test cases for DirectOfferService."""

    def setUp(self):
        """Set up test data."""
        from datetime import UTC, datetime

        from apps.jobs.services import DirectOfferService

        self.service = DirectOfferService()

        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        self.homeowner_profile = HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Homeowner",
            phone_verified_at=datetime.now(UTC),
        )

        # Create target handyman
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        UserRole.objects.create(user=self.handyman, role="handyman")
        self.handyman_profile = HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Handyman",
            phone_verified_at=datetime.now(UTC),
        )

        # Create category and city
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

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_direct_offer_success(self, mock_notify):
        """Test successful direct offer creation."""
        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Need to fix a leaky faucet in kitchen",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        self.assertEqual(job.homeowner, self.homeowner)
        self.assertEqual(job.target_handyman, self.handyman)
        self.assertEqual(job.title, "Fix leaky faucet")
        self.assertTrue(job.is_direct_offer)
        self.assertEqual(job.offer_status, "pending")
        self.assertEqual(job.status, "draft")
        self.assertIsNotNone(job.offer_expires_at)

        # Verify notification was sent
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args.kwargs
        self.assertEqual(call_kwargs["user"], self.handyman)
        self.assertEqual(call_kwargs["notification_type"], "direct_offer_received")

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_direct_offer_with_custom_expiry(self, mock_notify):
        """Test direct offer creation with custom expiry days."""
        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Need to fix a leaky faucet",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
            offer_expires_in_days=14,
        )

        # Check expiry is approximately 14 days from now
        expected_expiry = timezone.now() + timedelta(days=14)
        self.assertAlmostEqual(
            job.offer_expires_at.timestamp(),
            expected_expiry.timestamp(),
            delta=60,  # Allow 60 seconds difference
        )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_direct_offer_with_tasks(self, mock_notify):
        """Test direct offer creation with tasks."""
        tasks_data = [
            {"title": "Turn off water", "description": "Turn off the main valve"},
            {"title": "Replace faucet", "description": "Install new faucet"},
        ]

        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Need to fix a leaky faucet",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
            tasks_data=tasks_data,
        )

        self.assertEqual(job.tasks.count(), 2)
        self.assertEqual(job.tasks.first().title, "Turn off water")

    def test_create_direct_offer_no_homeowner_role(self):
        """Test direct offer creation without homeowner role."""
        user = User.objects.create_user(
            email="notrole@example.com", password="password123"
        )

        with self.assertRaisesRegex(ValidationError, "homeowner role"):
            self.service.create_direct_offer(
                homeowner=user,
                target_handyman=self.handyman,
                title="Fix faucet",
                description="Test",
                estimated_budget=100,
                category=self.category,
                city=self.city,
                address="123 Main St",
            )

    def test_create_direct_offer_no_homeowner_profile(self):
        """Test direct offer creation without homeowner profile."""
        user = User.objects.create_user(
            email="noprofile@example.com", password="password123"
        )
        UserRole.objects.create(user=user, role="homeowner")
        # No profile created

        with self.assertRaisesRegex(ValidationError, "complete your homeowner profile"):
            self.service.create_direct_offer(
                homeowner=user,
                target_handyman=self.handyman,
                title="Fix faucet",
                description="Test",
                estimated_budget=100,
                category=self.category,
                city=self.city,
                address="123 Main St",
            )

    def test_create_direct_offer_unverified_phone(self):
        """Test direct offer creation with unverified phone."""
        self.homeowner_profile.phone_verified_at = None
        self.homeowner_profile.save()

        with self.assertRaisesRegex(ValidationError, "verify your phone number"):
            self.service.create_direct_offer(
                homeowner=self.homeowner,
                target_handyman=self.handyman,
                title="Fix faucet",
                description="Test",
                estimated_budget=100,
                category=self.category,
                city=self.city,
                address="123 Main St",
            )

    def test_create_direct_offer_target_not_handyman(self):
        """Test direct offer to non-handyman user."""
        other_user = User.objects.create_user(
            email="other@example.com", password="password123"
        )

        with self.assertRaisesRegex(ValidationError, "handyman role"):
            self.service.create_direct_offer(
                homeowner=self.homeowner,
                target_handyman=other_user,
                title="Fix faucet",
                description="Test",
                estimated_budget=100,
                category=self.category,
                city=self.city,
                address="123 Main St",
            )

    def test_create_direct_offer_target_no_profile(self):
        """Test direct offer to handyman without profile."""
        other_handy = User.objects.create_user(
            email="otherhandy@example.com", password="password123"
        )
        UserRole.objects.create(user=other_handy, role="handyman")
        # No profile created

        with self.assertRaisesRegex(ValidationError, "not completed their profile"):
            self.service.create_direct_offer(
                homeowner=self.homeowner,
                target_handyman=other_handy,
                title="Fix faucet",
                description="Test",
                estimated_budget=100,
                category=self.category,
                city=self.city,
                address="123 Main St",
            )

    def test_create_direct_offer_to_self(self):
        """Test direct offer to self."""
        # Add handyman role to homeowner
        UserRole.objects.create(user=self.homeowner, role="handyman")
        HandymanProfile.objects.create(
            user=self.homeowner,
            display_name="Self",
            phone_verified_at=timezone.now(),
        )

        with self.assertRaisesRegex(ValidationError, "cannot send.*yourself"):
            self.service.create_direct_offer(
                homeowner=self.homeowner,
                target_handyman=self.homeowner,
                title="Fix faucet",
                description="Test",
                estimated_budget=100,
                category=self.category,
                city=self.city,
                address="123 Main St",
            )

    def test_create_direct_offer_invalid_expiry_days(self):
        """Test direct offer with invalid expiry days."""
        with self.assertRaisesRegex(ValidationError, "between 1 and 30"):
            self.service.create_direct_offer(
                homeowner=self.homeowner,
                target_handyman=self.handyman,
                title="Fix faucet",
                description="Test",
                estimated_budget=100,
                category=self.category,
                city=self.city,
                address="123 Main St",
                offer_expires_in_days=0,
            )

        with self.assertRaisesRegex(ValidationError, "between 1 and 30"):
            self.service.create_direct_offer(
                homeowner=self.homeowner,
                target_handyman=self.handyman,
                title="Fix faucet",
                description="Test",
                estimated_budget=100,
                category=self.category,
                city=self.city,
                address="123 Main St",
                offer_expires_in_days=31,
            )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_accept_offer_success(self, mock_notify):
        """Test successful offer acceptance."""
        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        mock_notify.reset_mock()

        updated_job = self.service.accept_offer(self.handyman, job)

        self.assertEqual(updated_job.offer_status, "accepted")
        self.assertEqual(updated_job.status, "in_progress")
        self.assertEqual(updated_job.assigned_handyman, self.handyman)
        self.assertIsNotNone(updated_job.offer_responded_at)

        # Verify notification was sent to homeowner
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args.kwargs
        self.assertEqual(call_kwargs["user"], self.homeowner)
        self.assertEqual(call_kwargs["notification_type"], "direct_offer_accepted")

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_accept_offer_not_direct_offer(self, mock_notify):
        """Test accepting non-direct offer job."""
        job = Job.objects.create(
            homeowner=self.homeowner,
            title="Regular job",
            description="Test",
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
            estimated_budget=100,
            is_direct_offer=False,
        )

        with self.assertRaisesRegex(ValidationError, "not a direct offer"):
            self.service.accept_offer(self.handyman, job)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_accept_offer_wrong_handyman(self, mock_notify):
        """Test accepting offer by wrong handyman."""
        from datetime import UTC, datetime

        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        other_handy = User.objects.create_user(
            email="other_handy@example.com", password="password123"
        )
        UserRole.objects.create(user=other_handy, role="handyman")
        HandymanProfile.objects.create(
            user=other_handy,
            display_name="Other Handy",
            phone_verified_at=datetime.now(UTC),
        )

        with self.assertRaisesRegex(ValidationError, "not the target"):
            self.service.accept_offer(other_handy, job)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_accept_offer_not_pending(self, mock_notify):
        """Test accepting already accepted offer."""
        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        # Accept first time
        self.service.accept_offer(self.handyman, job)

        # Try to accept again
        job.refresh_from_db()
        with self.assertRaisesRegex(ValidationError, "cannot be accepted"):
            self.service.accept_offer(self.handyman, job)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_accept_offer_expired(self, mock_notify):
        """Test accepting expired offer."""
        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        # Set offer to expired
        job.offer_expires_at = timezone.now() - timedelta(days=1)
        job.save()

        with self.assertRaisesRegex(ValidationError, "expired"):
            self.service.accept_offer(self.handyman, job)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_reject_offer_success(self, mock_notify):
        """Test successful offer rejection."""
        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        mock_notify.reset_mock()

        updated_job = self.service.reject_offer(
            self.handyman, job, rejection_reason="Too busy right now"
        )

        self.assertEqual(updated_job.offer_status, "rejected")
        self.assertEqual(updated_job.offer_rejection_reason, "Too busy right now")
        self.assertIsNotNone(updated_job.offer_responded_at)

        # Verify notification was sent to homeowner
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args.kwargs
        self.assertEqual(call_kwargs["user"], self.homeowner)
        self.assertEqual(call_kwargs["notification_type"], "direct_offer_rejected")

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_reject_offer_not_direct_offer(self, mock_notify):
        """Test rejecting non-direct offer job."""
        job = Job.objects.create(
            homeowner=self.homeowner,
            title="Regular job",
            description="Test",
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
            estimated_budget=100,
            is_direct_offer=False,
        )

        with self.assertRaisesRegex(ValidationError, "not a direct offer"):
            self.service.reject_offer(self.handyman, job)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_reject_offer_wrong_handyman(self, mock_notify):
        """Test rejecting offer by wrong handyman."""
        from datetime import UTC, datetime

        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        other_handy = User.objects.create_user(
            email="other_handy@example.com", password="password123"
        )
        UserRole.objects.create(user=other_handy, role="handyman")
        HandymanProfile.objects.create(
            user=other_handy,
            display_name="Other Handy",
            phone_verified_at=datetime.now(UTC),
        )

        with self.assertRaisesRegex(ValidationError, "not the target"):
            self.service.reject_offer(other_handy, job)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_reject_offer_not_pending(self, mock_notify):
        """Test rejecting already rejected offer."""
        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        # Reject first time
        self.service.reject_offer(self.handyman, job)

        # Try to reject again
        job.refresh_from_db()
        with self.assertRaisesRegex(ValidationError, "cannot be rejected"):
            self.service.reject_offer(self.handyman, job)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_cancel_offer_success(self, mock_notify):
        """Test successful offer cancellation by homeowner."""
        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        mock_notify.reset_mock()

        updated_job = self.service.cancel_offer(self.homeowner, job)

        self.assertEqual(updated_job.offer_status, "expired")
        self.assertEqual(updated_job.status, "cancelled")

        # Verify notification was sent to handyman
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args.kwargs
        self.assertEqual(call_kwargs["user"], self.handyman)
        self.assertEqual(call_kwargs["notification_type"], "direct_offer_cancelled")

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_cancel_offer_not_direct_offer(self, mock_notify):
        """Test cancelling non-direct offer job."""
        job = Job.objects.create(
            homeowner=self.homeowner,
            title="Regular job",
            description="Test",
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
            estimated_budget=100,
            is_direct_offer=False,
        )

        with self.assertRaisesRegex(ValidationError, "not a direct offer"):
            self.service.cancel_offer(self.homeowner, job)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_cancel_offer_wrong_homeowner(self, mock_notify):
        """Test cancelling offer by wrong homeowner."""
        from datetime import UTC, datetime

        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        other_homeowner = User.objects.create_user(
            email="other_homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=other_homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=other_homeowner,
            display_name="Other Owner",
            phone_verified_at=datetime.now(UTC),
        )

        with self.assertRaisesRegex(ValidationError, "only cancel your own"):
            self.service.cancel_offer(other_homeowner, job)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_cancel_offer_not_pending(self, mock_notify):
        """Test cancelling already accepted offer."""
        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        # Accept the offer first
        self.service.accept_offer(self.handyman, job)

        # Try to cancel
        job.refresh_from_db()
        with self.assertRaisesRegex(ValidationError, "cannot be cancelled"):
            self.service.cancel_offer(self.homeowner, job)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_convert_to_public_from_rejected(self, mock_notify):
        """Test converting rejected offer to public listing."""
        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        # Reject the offer
        self.service.reject_offer(self.handyman, job)

        # Convert to public
        job.refresh_from_db()
        updated_job = self.service.convert_to_public(self.homeowner, job)

        self.assertFalse(updated_job.is_direct_offer)
        self.assertEqual(updated_job.offer_status, "converted")
        self.assertEqual(updated_job.status, "open")
        self.assertIsNone(updated_job.assigned_handyman)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_convert_to_public_from_expired(self, mock_notify):
        """Test converting expired offer to public listing."""
        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        # Set to expired status
        job.offer_status = "expired"
        job.save()

        updated_job = self.service.convert_to_public(self.homeowner, job)

        self.assertFalse(updated_job.is_direct_offer)
        self.assertEqual(updated_job.offer_status, "converted")
        self.assertEqual(updated_job.status, "open")

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_convert_to_public_not_direct_offer(self, mock_notify):
        """Test converting non-direct offer job."""
        job = Job.objects.create(
            homeowner=self.homeowner,
            title="Regular job",
            description="Test",
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
            estimated_budget=100,
            is_direct_offer=False,
        )

        with self.assertRaisesRegex(ValidationError, "not a direct offer"):
            self.service.convert_to_public(self.homeowner, job)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_convert_to_public_wrong_homeowner(self, mock_notify):
        """Test converting offer by wrong homeowner."""
        from datetime import UTC, datetime

        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        # Reject the offer
        self.service.reject_offer(self.handyman, job)
        job.refresh_from_db()

        other_homeowner = User.objects.create_user(
            email="other_homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=other_homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=other_homeowner,
            display_name="Other Owner",
            phone_verified_at=datetime.now(UTC),
        )

        with self.assertRaisesRegex(ValidationError, "only convert your own"):
            self.service.convert_to_public(other_homeowner, job)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_convert_to_public_pending_status(self, mock_notify):
        """Test converting pending offer fails."""
        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        with self.assertRaisesRegex(
            ValidationError, "rejected or expired offers can be converted"
        ):
            self.service.convert_to_public(self.homeowner, job)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_convert_to_public_accepted_status(self, mock_notify):
        """Test converting accepted offer fails."""
        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        # Accept the offer
        self.service.accept_offer(self.handyman, job)
        job.refresh_from_db()

        with self.assertRaisesRegex(
            ValidationError, "rejected or expired offers can be converted"
        ):
            self.service.convert_to_public(self.homeowner, job)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_expire_pending_offers(self, mock_notify):
        """Test expiring pending offers."""
        # Create an expired offer
        job1 = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Expired offer",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        job1.offer_expires_at = timezone.now() - timedelta(days=1)
        job1.save()

        # Create a non-expired offer
        job2 = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Valid offer",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
            offer_expires_in_days=7,
        )

        mock_notify.reset_mock()

        count = self.service.expire_pending_offers()

        self.assertEqual(count, 1)

        job1.refresh_from_db()
        job2.refresh_from_db()

        self.assertEqual(job1.offer_status, "expired")
        self.assertEqual(job2.offer_status, "pending")

        # Verify notifications were sent for expired offer
        self.assertEqual(mock_notify.call_count, 2)  # One for homeowner, one for handy

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_direct_offer_with_attachment_dict(self, mock_notify):
        """Test creating direct offer with attachment as dict (with metadata)."""
        from io import BytesIO

        from PIL import Image

        # Create a test image
        img = Image.new("RGB", (100, 100), color="red")
        img_io = BytesIO()
        img.save(img_io, format="JPEG")
        img_io.seek(0)

        attachment_file = SimpleUploadedFile(
            "test.jpg", img_io.read(), content_type="image/jpeg"
        )

        # Attachment as dict with metadata
        attachments = [
            {
                "file": attachment_file,
                "file_type": "image",
                "thumbnail": None,
                "duration_seconds": None,
            }
        ]

        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
            attachments=attachments,
        )

        self.assertEqual(job.attachments.count(), 1)
        attachment = job.attachments.first()
        self.assertEqual(attachment.file_type, "image")

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_direct_offer_with_attachment_file_directly(self, mock_notify):
        """Test creating direct offer with attachment as file directly."""
        from io import BytesIO

        from PIL import Image

        # Create a test image
        img = Image.new("RGB", (100, 100), color="blue")
        img_io = BytesIO()
        img.save(img_io, format="JPEG")
        img_io.seek(0)

        attachment_file = SimpleUploadedFile(
            "test_direct.jpg", img_io.read(), content_type="image/jpeg"
        )

        # Attachment as file directly (not dict)
        attachments = [attachment_file]

        job = self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
            attachments=attachments,
        )

        self.assertEqual(job.attachments.count(), 1)
        attachment = job.attachments.first()
        self.assertEqual(attachment.file_type, "image")

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_expire_pending_offers_no_expired(self, mock_notify):
        """Test expire_pending_offers returns 0 when no offers need expiring."""
        # Create only non-expired offers
        self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Valid offer 1",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Main St",
            offer_expires_in_days=7,
        )

        self.service.create_direct_offer(
            homeowner=self.homeowner,
            target_handyman=self.handyman,
            title="Valid offer 2",
            description="Test",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="456 Main St",
            offer_expires_in_days=14,
        )

        mock_notify.reset_mock()

        # Run expire - should return 0
        count = self.service.expire_pending_offers()

        self.assertEqual(count, 0)
        # No notifications should be sent
        mock_notify.assert_not_called()
