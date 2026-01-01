"""Tests for ongoing job write views."""

from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image as PILImage
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.jobs.models import (
    City,
    DailyReport,
    DailyReportTask,
    Job,
    JobCategory,
    JobTask,
    WorkSession,
)
from apps.profiles.models import HandymanProfile, HomeownerProfile


def create_test_image():
    """Create a test image file."""
    img = PILImage.new("RGB", (100, 100), color="red")
    img_io = BytesIO()
    img.save(img_io, format="JPEG")
    img_io.seek(0)
    return SimpleUploadedFile("test.jpg", img_io.read(), content_type="image/jpeg")


class HandymanWorkSessionStartViewTests(APITestCase):
    """Tests for starting work sessions."""

    def setUp(self):
        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
            phone_verified_at=timezone.now(),
        )

        # Create handyman
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="John Handyman",
            phone_verified_at=timezone.now(),
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Setup Job
        self.category = JobCategory.objects.create(name="Plumbing", slug="plumbing")
        self.city = City.objects.create(
            name="Toronto", province="Ontario", province_code="ON", slug="toronto"
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Test Job",
            description="Test description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Street",
            status="in_progress",
        )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_start_work_session_success(self, mock_notify):
        """Test successfully starting a work session."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/start/"
        self.client.force_authenticate(user=self.handyman)

        data = {
            "started_at": timezone.now().isoformat(),
            "start_latitude": "43.6532",
            "start_longitude": "-79.3832",
            "start_photo": create_test_image(),
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Work session started successfully")

    def test_start_work_session_validation_error(self):
        """Test starting session with missing fields."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/start/"
        self.client.force_authenticate(user=self.handyman)

        data = {"started_at": timezone.now().isoformat()}
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_start_work_session_already_active(self, mock_notify):
        """Test starting session when one is already active."""
        # Create an active session
        WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now(),
            start_latitude=Decimal("43.0"),
            start_longitude=Decimal("-79.0"),
            status="in_progress",
        )

        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/start/"
        self.client.force_authenticate(user=self.handyman)

        data = {
            "started_at": timezone.now().isoformat(),
            "start_latitude": "43.6532",
            "start_longitude": "-79.3832",
            "start_photo": create_test_image(),
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already have an active session", str(response.data))

    def test_start_work_session_invalid_latitude(self):
        """Test starting session with invalid latitude."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/start/"
        self.client.force_authenticate(user=self.handyman)

        data = {
            "started_at": timezone.now().isoformat(),
            "start_latitude": "100.0",  # Invalid: > 90
            "start_longitude": "-79.3832",
            "start_photo": create_test_image(),
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_work_session_invalid_longitude(self):
        """Test starting session with invalid longitude."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/start/"
        self.client.force_authenticate(user=self.handyman)

        data = {
            "started_at": timezone.now().isoformat(),
            "start_latitude": "43.6532",
            "start_longitude": "-200.0",  # Invalid: < -180
            "start_photo": create_test_image(),
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class HandymanWorkSessionStopViewTests(APITestCase):
    """Tests for stopping work sessions."""

    def setUp(self):
        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
            phone_verified_at=timezone.now(),
        )

        # Create handyman
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="John Handyman",
            phone_verified_at=timezone.now(),
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Setup Job
        self.category = JobCategory.objects.create(name="Plumbing", slug="plumbing")
        self.city = City.objects.create(
            name="Toronto", province="Ontario", province_code="ON", slug="toronto"
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Test Job",
            description="Test description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Street",
            status="in_progress",
        )

        # Create active session
        self.session = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now() - timedelta(hours=1),
            start_latitude=Decimal("43.0"),
            start_longitude=Decimal("-79.0"),
            status="in_progress",
        )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_stop_work_session_success(self, mock_notify):
        """Test successfully stopping a work session."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/{self.session.public_id}/stop/"
        self.client.force_authenticate(user=self.handyman)

        data = {
            "ended_at": timezone.now().isoformat(),
            "end_latitude": "43.6532",
            "end_longitude": "-79.3832",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Work session stopped successfully")

    def test_stop_work_session_validation_error(self):
        """Test stopping session with missing fields."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/{self.session.public_id}/stop/"
        self.client.force_authenticate(user=self.handyman)

        data = {}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_stop_work_session_already_stopped(self):
        """Test stopping an already completed session."""
        self.session.status = "completed"
        self.session.save()

        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/{self.session.public_id}/stop/"
        self.client.force_authenticate(user=self.handyman)

        data = {
            "ended_at": timezone.now().isoformat(),
            "end_latitude": "43.6532",
            "end_longitude": "-79.3832",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not active", str(response.data))

    def test_stop_work_session_invalid_latitude(self):
        """Test stopping session with invalid latitude."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/{self.session.public_id}/stop/"
        self.client.force_authenticate(user=self.handyman)

        data = {
            "ended_at": timezone.now().isoformat(),
            "end_latitude": "100.0",  # Invalid
            "end_longitude": "-79.3832",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class HandymanWorkSessionMediaUploadViewTests(APITestCase):
    """Tests for uploading media to work sessions."""

    def setUp(self):
        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
            phone_verified_at=timezone.now(),
        )

        # Create handyman
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="John Handyman",
            phone_verified_at=timezone.now(),
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Setup Job
        self.category = JobCategory.objects.create(name="Plumbing", slug="plumbing")
        self.city = City.objects.create(
            name="Toronto", province="Ontario", province_code="ON", slug="toronto"
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Test Job",
            description="Test description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Street",
            status="in_progress",
        )
        self.task = JobTask.objects.create(job=self.job, title="Task 1", order=0)

        # Create active session
        self.session = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now() - timedelta(hours=1),
            start_latitude=Decimal("43.0"),
            start_longitude=Decimal("-79.0"),
            status="in_progress",
        )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_upload_media_success(self, mock_notify):
        """Test successfully uploading media."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/{self.session.public_id}/media/"
        self.client.force_authenticate(user=self.handyman)

        data = {
            "media_type": "photo",
            "file": create_test_image(),
            "file_size": 1000,
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Media uploaded successfully")

    def test_upload_media_validation_error(self):
        """Test uploading with missing fields."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/{self.session.public_id}/media/"
        self.client.force_authenticate(user=self.handyman)

        data = {"media_type": "photo"}
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_video_without_duration(self):
        """Test uploading video without duration."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/{self.session.public_id}/media/"
        self.client.force_authenticate(user=self.handyman)

        data = {
            "media_type": "video",
            "file": create_test_image(),  # Not a real video, but testing validation
            "file_size": 1000,
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("duration", str(response.data).lower())

    def test_upload_media_with_invalid_task(self):
        """Test uploading media with invalid task ID."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/{self.session.public_id}/media/"
        self.client.force_authenticate(user=self.handyman)

        data = {
            "media_type": "photo",
            "file": create_test_image(),
            "file_size": 1000,
            "task_id": "00000000-0000-0000-0000-000000000000",
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class HandymanDailyReportCreateViewTests(APITestCase):
    """Tests for creating daily reports."""

    def setUp(self):
        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
            phone_verified_at=timezone.now(),
        )

        # Create handyman
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="John Handyman",
            phone_verified_at=timezone.now(),
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Setup Job
        self.category = JobCategory.objects.create(name="Plumbing", slug="plumbing")
        self.city = City.objects.create(
            name="Toronto", province="Ontario", province_code="ON", slug="toronto"
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Test Job",
            description="Test description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Street",
            status="in_progress",
        )
        self.task = JobTask.objects.create(job=self.job, title="Task 1", order=0)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_daily_report_success(self, mock_notify):
        """Test successfully creating a daily report."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/reports/create/"
        self.client.force_authenticate(user=self.handyman)

        data = {
            "report_date": timezone.now().date().isoformat(),
            "summary": "Completed bathroom tiling",
            "total_work_duration_seconds": 28800,
            "tasks": [],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["message"], "Daily report submitted successfully"
        )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_daily_report_with_tasks(self, mock_notify):
        """Test creating report with task entries."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/reports/create/"
        self.client.force_authenticate(user=self.handyman)

        data = {
            "report_date": timezone.now().date().isoformat(),
            "summary": "Completed Task 1",
            "total_work_duration_seconds": 28800,
            "tasks": [
                {
                    "task_id": str(self.task.public_id),
                    "notes": "Finished floor tiles",
                    "marked_complete": True,
                }
            ],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.task.refresh_from_db()
        self.assertTrue(self.task.is_completed)

    def test_create_daily_report_validation_error(self):
        """Test creating report with missing fields."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/reports/create/"
        self.client.force_authenticate(user=self.handyman)

        data = {"summary": "Work done"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_daily_report_duplicate(self, mock_notify):
        """Test creating duplicate report for same date."""
        # Create existing report
        DailyReport.objects.create(
            job=self.job,
            handyman=self.handyman,
            report_date=timezone.now().date(),
            summary="Existing report",
            total_work_duration=timedelta(hours=2),
            status="pending",
            review_deadline=timezone.now() + timedelta(days=3),
        )

        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/reports/create/"
        self.client.force_authenticate(user=self.handyman)

        data = {
            "report_date": timezone.now().date().isoformat(),
            "summary": "Another report",
            "total_work_duration_seconds": 28800,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", str(response.data))


class HandymanDailyReportEditViewTests(APITestCase):
    """Tests for editing daily reports."""

    def setUp(self):
        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
            phone_verified_at=timezone.now(),
        )

        # Create handyman
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="John Handyman",
            phone_verified_at=timezone.now(),
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Setup Job
        self.category = JobCategory.objects.create(name="Plumbing", slug="plumbing")
        self.city = City.objects.create(
            name="Toronto", province="Ontario", province_code="ON", slug="toronto"
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Test Job",
            description="Test description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Street",
            status="in_progress",
        )
        self.task1 = JobTask.objects.create(job=self.job, title="Task 1", order=0)
        self.task2 = JobTask.objects.create(job=self.job, title="Task 2", order=1)

        # Create pending report
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
            task=self.task1,
            notes="Original notes",
            marked_complete=False,
        )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_edit_report_summary_success(self, mock_notify):
        """Test successfully editing report summary."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/reports/{self.report.public_id}/edit/"
        self.client.force_authenticate(user=self.handyman)

        data = {"summary": "Updated summary"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Daily report updated successfully")
        self.report.refresh_from_db()
        self.assertEqual(self.report.summary, "Updated summary")

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_edit_report_duration_success(self, mock_notify):
        """Test successfully editing report duration."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/reports/{self.report.public_id}/edit/"
        self.client.force_authenticate(user=self.handyman)

        data = {"total_work_duration_seconds": 32400}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.report.refresh_from_db()
        self.assertEqual(self.report.total_work_duration, timedelta(seconds=32400))

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_edit_report_tasks_success(self, mock_notify):
        """Test successfully editing report tasks."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/reports/{self.report.public_id}/edit/"
        self.client.force_authenticate(user=self.handyman)

        data = {
            "tasks": [
                {
                    "task_id": str(self.task1.public_id),
                    "notes": "Updated task 1 notes",
                    "marked_complete": True,
                },
                {
                    "task_id": str(self.task2.public_id),
                    "notes": "New task 2 notes",
                    "marked_complete": False,
                },
            ]
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.report.refresh_from_db()
        self.assertEqual(self.report.tasks_worked.count(), 2)
        self.task1.refresh_from_db()
        self.assertTrue(self.task1.is_completed)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_edit_rejected_report_resets_status(self, mock_notify):
        """Test that editing rejected report resets status to pending."""
        self.report.status = "rejected"
        self.report.homeowner_comment = "Not detailed enough"
        self.report.save()

        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/reports/{self.report.public_id}/edit/"
        self.client.force_authenticate(user=self.handyman)

        data = {"summary": "More detailed summary"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "pending")
        self.assertIsNone(self.report.reviewed_by)
        self.assertIsNone(self.report.reviewed_at)
        self.assertEqual(self.report.homeowner_comment, "")

    def test_edit_approved_report_fails(self):
        """Test that editing approved report fails."""
        self.report.status = "approved"
        self.report.save()

        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/reports/{self.report.public_id}/edit/"
        self.client.force_authenticate(user=self.handyman)

        data = {"summary": "New summary"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Only pending or rejected", str(response.data))

    def test_edit_other_handyman_report_fails(self):
        """Test that editing another handyman's report fails."""
        other_handyman = User.objects.create_user(
            email="other@example.com", password="password123"
        )
        UserRole.objects.create(user=other_handyman, role="handyman")
        HandymanProfile.objects.create(
            user=other_handyman,
            display_name="Other Handyman",
            phone_verified_at=timezone.now(),
        )
        other_handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/reports/{self.report.public_id}/edit/"
        self.client.force_authenticate(user=other_handyman)

        data = {"summary": "Hacked summary"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_edit_report_remove_tasks(self, mock_notify):
        """Test successfully removing tasks from a report."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/reports/{self.report.public_id}/edit/"
        self.client.force_authenticate(user=self.handyman)

        data = {"tasks": []}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.report.refresh_from_db()
        self.assertEqual(self.report.tasks_worked.count(), 0)
        self.task1.refresh_from_db()
        self.assertFalse(self.task1.is_completed)

    def test_edit_report_validation_error(self):
        """Test editing report with invalid data."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/reports/{self.report.public_id}/edit/"
        self.client.force_authenticate(user=self.handyman)

        data = {"total_work_duration_seconds": -100}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_edit_report_with_same_task_values(self, mock_notify):
        """Test editing report with same task values doesn't recreate tasks."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/reports/{self.report.public_id}/edit/"
        self.client.force_authenticate(user=self.handyman)

        initial_task_count = DailyReportTask.objects.count()
        data = {
            "tasks": [
                {
                    "task_id": str(self.task1.public_id),
                    "notes": "Original notes",
                    "marked_complete": False,
                }
            ]
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(DailyReportTask.objects.count(), initial_task_count)


class HomeownerDailyReportReviewViewTests(APITestCase):
    """Tests for reviewing daily reports."""

    def setUp(self):
        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
            phone_verified_at=timezone.now(),
        )
        self.homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Create handyman
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="John Handyman",
            phone_verified_at=timezone.now(),
        )

        # Setup Job
        self.category = JobCategory.objects.create(name="Plumbing", slug="plumbing")
        self.city = City.objects.create(
            name="Toronto", province="Ontario", province_code="ON", slug="toronto"
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Test Job",
            description="Test description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Street",
            status="in_progress",
        )

        # Create pending report
        self.report = DailyReport.objects.create(
            job=self.job,
            handyman=self.handyman,
            report_date=timezone.now().date(),
            summary="Work done today",
            total_work_duration=timedelta(hours=2),
            status="pending",
            review_deadline=timezone.now() + timedelta(days=3),
        )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_approve_report_success(self, mock_notify):
        """Test successfully approving a report."""
        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/reports/{self.report.public_id}/review/"
        self.client.force_authenticate(user=self.homeowner)

        data = {"decision": "approved", "comment": "Great work!"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("approved", response.data["message"])

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_reject_report_success(self, mock_notify):
        """Test successfully rejecting a report."""
        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/reports/{self.report.public_id}/review/"
        self.client.force_authenticate(user=self.homeowner)

        data = {"decision": "rejected", "comment": "Missing details"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("rejected", response.data["message"])

    def test_review_report_validation_error(self):
        """Test reviewing with missing fields."""
        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/reports/{self.report.public_id}/review/"
        self.client.force_authenticate(user=self.homeowner)

        data = {}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_review_already_reviewed_report(self):
        """Test reviewing an already reviewed report."""
        self.report.status = "approved"
        self.report.save()

        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/reports/{self.report.public_id}/review/"
        self.client.force_authenticate(user=self.homeowner)

        data = {"decision": "approved"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Only pending", str(response.data))


class HandymanCompletionRequestViewTests(APITestCase):
    """Tests for requesting job completion."""

    def setUp(self):
        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
            phone_verified_at=timezone.now(),
        )

        # Create handyman
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="John Handyman",
            phone_verified_at=timezone.now(),
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Setup Job
        self.category = JobCategory.objects.create(name="Plumbing", slug="plumbing")
        self.city = City.objects.create(
            name="Toronto", province="Ontario", province_code="ON", slug="toronto"
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Test Job",
            description="Test description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Street",
            status="in_progress",
        )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_request_completion_success(self, mock_notify):
        """Test successfully requesting completion."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/completion/request/"
        self.client.force_authenticate(user=self.handyman)

        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["status"], "pending_completion")

    def test_request_completion_wrong_status(self):
        """Test requesting completion when job is not in progress."""
        self.job.status = "pending_completion"
        self.job.save()

        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/completion/request/"
        self.client.force_authenticate(user=self.handyman)

        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class HomeownerCompletionApproveRejectViewTests(APITestCase):
    """Tests for approving/rejecting job completion."""

    def setUp(self):
        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
            phone_verified_at=timezone.now(),
        )
        self.homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Create handyman
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="John Handyman",
            phone_verified_at=timezone.now(),
        )

        # Setup Job
        self.category = JobCategory.objects.create(name="Plumbing", slug="plumbing")
        self.city = City.objects.create(
            name="Toronto", province="Ontario", province_code="ON", slug="toronto"
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Test Job",
            description="Test description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Street",
            status="pending_completion",
        )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_approve_completion_success(self, mock_notify):
        """Test successfully approving completion."""
        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/completion/approve/"
        self.client.force_authenticate(user=self.homeowner)

        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["status"], "completed")

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_reject_completion_success(self, mock_notify):
        """Test successfully rejecting completion."""
        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/completion/reject/"
        self.client.force_authenticate(user=self.homeowner)

        data = {"reason": "Work incomplete"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["status"], "in_progress")

    def test_approve_completion_wrong_status(self):
        """Test approving when job is not pending completion."""
        self.job.status = "in_progress"
        self.job.save()

        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/completion/approve/"
        self.client.force_authenticate(user=self.homeowner)

        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class HomeownerDisputeCreateViewTests(APITestCase):
    """Tests for creating disputes."""

    def setUp(self):
        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
            phone_verified_at=timezone.now(),
        )
        self.homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Create handyman
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="John Handyman",
            phone_verified_at=timezone.now(),
        )

        # Setup Job
        self.category = JobCategory.objects.create(name="Plumbing", slug="plumbing")
        self.city = City.objects.create(
            name="Toronto", province="Ontario", province_code="ON", slug="toronto"
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Test Job",
            description="Test description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Street",
            status="pending_completion",
        )

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_dispute_success(self, mock_notify):
        """Test successfully creating a dispute."""
        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/disputes/create/"
        self.client.force_authenticate(user=self.homeowner)

        data = {"reason": "Work quality issues"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Dispute created successfully")

    def test_create_dispute_validation_error(self):
        """Test creating dispute with missing fields."""
        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/disputes/create/"
        self.client.force_authenticate(user=self.homeowner)

        data = {}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_dispute_wrong_status(self):
        """Test creating dispute when job status is not eligible."""
        self.job.status = "open"
        self.job.save()

        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/disputes/create/"
        self.client.force_authenticate(user=self.homeowner)

        data = {"reason": "Work quality issues"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not eligible", str(response.data))


class AdditionalSerializerValidationTests(APITestCase):
    """Additional tests for serializer validation coverage."""

    def test_stop_session_invalid_end_longitude(self):
        """Test stop session serializer with invalid end longitude."""
        from apps.jobs.serializers import WorkSessionStopSerializer

        data = {
            "ended_at": timezone.now().isoformat(),
            "end_latitude": "43.6532",
            "end_longitude": "-200.0",  # Invalid
        }
        serializer = WorkSessionStopSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("end_longitude", serializer.errors)

    def test_daily_report_task_entry_invalid_task(self):
        """Test DailyReportTaskEntrySerializer with invalid task_id."""
        from apps.jobs.serializers import DailyReportTaskEntrySerializer

        data = {
            "task_id": "00000000-0000-0000-0000-000000000000",
            "notes": "Some notes",
            "marked_complete": True,
        }
        serializer = DailyReportTaskEntrySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("task_id", serializer.errors)


class AdditionalViewValidationTests(APITestCase):
    """Additional tests for view validation error branches."""

    def setUp(self):
        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
            phone_verified_at=timezone.now(),
        )
        self.homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Create handyman
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="John Handyman",
            phone_verified_at=timezone.now(),
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Setup Job
        self.category = JobCategory.objects.create(name="Plumbing", slug="plumbing")
        self.city = City.objects.create(
            name="Toronto", province="Ontario", province_code="ON", slug="toronto"
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Test Job",
            description="Test description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Street",
            status="in_progress",
        )

        # Create active session
        self.session = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now() - timedelta(hours=1),
            start_latitude=Decimal("43.0"),
            start_longitude=Decimal("-79.0"),
            status="in_progress",
        )

    @patch("apps.jobs.views.mobile.work_session_service.add_media")
    def test_media_upload_service_validation_error(self, mock_add_media):
        """Test media upload when service raises ValidationError."""
        from django.core.exceptions import ValidationError

        mock_add_media.side_effect = ValidationError("Service validation error")

        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/{self.session.public_id}/media/"
        self.client.force_authenticate(user=self.handyman)

        data = {
            "media_type": "photo",
            "file": create_test_image(),
            "file_size": 1000,
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Service validation error", str(response.data))

    def test_completion_reject_serializer_validation_error(self):
        """Test completion reject with invalid serializer data type."""
        self.job.status = "pending_completion"
        self.job.save()

        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/completion/reject/"
        self.client.force_authenticate(user=self.homeowner)

        # Send data that will fail serializer validation - reason as dict instead of string
        response = self.client.post(
            url, {"reason": {"nested": "object"}}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", str(response.data))

    def test_completion_reject_service_validation_error(self):
        """Test completion reject when job is not awaiting completion."""
        # Job is in_progress, not pending_completion
        self.job.status = "in_progress"
        self.job.save()

        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/completion/reject/"
        self.client.force_authenticate(user=self.homeowner)

        response = self.client.post(url, {"reason": "test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not awaiting", str(response.data))
