from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.jobs.models import (
    City,
    DailyReport,
    Job,
    JobCategory,
    JobDispute,
    WorkSession,
)
from apps.profiles.models import HandymanProfile, HomeownerProfile


class HomeownerOngoingReadViewsTests(APITestCase):
    """Test cases for homeowner reading ongoing job entities."""

    def setUp(self):
        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        self.homeowner.email_verified_at = timezone.now()
        self.homeowner.save()
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
        self.handyman.email_verified_at = timezone.now()
        self.handyman.save()
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

        # Create other homeowner (for forbidden tests)
        self.other_homeowner = User.objects.create_user(
            email="other@example.com", password="password123"
        )
        UserRole.objects.create(user=self.other_homeowner, role="homeowner")
        self.other_homeowner.email_verified_at = timezone.now()
        self.other_homeowner.save()
        HomeownerProfile.objects.create(
            user=self.other_homeowner,
            display_name="Other Homeowner",
            phone_verified_at=timezone.now(),
        )
        self.other_homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
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
            title="Ongoing Job",
            description="Ongoing description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Street",
            status="in_progress",
        )

        # Create Work Session
        self.session = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now() - timedelta(hours=2),
            ended_at=timezone.now() - timedelta(hours=1),
            start_latitude=Decimal("43.0"),
            start_longitude=Decimal("-79.0"),
            start_photo="path/to/photo.jpg",
            status="completed",
        )

        # Create Daily Report
        self.report = DailyReport.objects.create(
            job=self.job,
            handyman=self.handyman,
            report_date=timezone.now().date(),
            summary="Work done today",
            total_work_duration=timedelta(hours=1),
            status="pending",
            review_deadline=timezone.now() + timedelta(days=3),
        )

        # Create Dispute
        self.dispute = JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Work not good",
            status="pending",
            resolution_deadline=timezone.now() + timedelta(days=3),
        )

    def test_homeowner_list_work_sessions_success(self):
        """Test homeowner can list work sessions for their job."""
        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/sessions/"
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

    def test_homeowner_list_work_sessions_forbidden(self):
        """Test other homeowner cannot access job sessions."""
        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/sessions/"
        self.client.force_authenticate(user=self.other_homeowner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_homeowner_work_session_detail_success(self):
        """Test homeowner can get work session detail."""
        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/sessions/{self.session.public_id}/"
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["data"]["public_id"], str(self.session.public_id)
        )

    def test_homeowner_list_daily_reports_success(self):
        """Test homeowner can list daily reports for their job."""
        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/reports/"
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

    def test_homeowner_daily_report_detail_success(self):
        """Test homeowner can get daily report detail."""
        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/reports/{self.report.public_id}/"
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["public_id"], str(self.report.public_id))

    def test_homeowner_list_disputes_success(self):
        """Test homeowner can list disputes for their job."""
        url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/disputes/"
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)


class HandymanOngoingReadViewsTests(APITestCase):
    """Test cases for handyman reading ongoing job entities."""

    def setUp(self):
        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        self.homeowner.email_verified_at = timezone.now()
        self.homeowner.save()
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
        self.handyman.email_verified_at = timezone.now()
        self.handyman.save()
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

        # Create other handyman (for forbidden tests)
        self.other_handyman = User.objects.create_user(
            email="other@example.com", password="password123"
        )
        UserRole.objects.create(user=self.other_handyman, role="handyman")
        self.other_handyman.email_verified_at = timezone.now()
        self.other_handyman.save()
        HandymanProfile.objects.create(
            user=self.other_handyman,
            display_name="Other Handyman",
            phone_verified_at=timezone.now(),
        )
        self.other_handyman.token_payload = {
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
            title="Ongoing Job",
            description="Ongoing description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Street",
            status="in_progress",
        )

        # Create Work Session
        self.session = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now() - timedelta(hours=2),
            ended_at=timezone.now() - timedelta(hours=1),
            start_latitude=Decimal("43.0"),
            start_longitude=Decimal("-79.0"),
            start_photo="path/to/photo.jpg",
            status="completed",
        )

        # Create Daily Report
        self.report = DailyReport.objects.create(
            job=self.job,
            handyman=self.handyman,
            report_date=timezone.now().date(),
            summary="Work done today",
            total_work_duration=timedelta(hours=1),
            status="pending",
            review_deadline=timezone.now() + timedelta(days=3),
        )

        # Create Dispute
        self.dispute = JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Work not good",
            status="pending",
            resolution_deadline=timezone.now() + timedelta(days=3),
        )

    def test_handyman_list_work_sessions_success(self):
        """Test handyman can list work sessions for their assigned job."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

    def test_handyman_list_work_sessions_forbidden(self):
        """Test other handyman cannot access job sessions."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/"
        self.client.force_authenticate(user=self.other_handyman)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_handyman_work_session_detail_success(self):
        """Test handyman can get work session detail."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/sessions/{self.session.public_id}/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["data"]["public_id"], str(self.session.public_id)
        )

    def test_handyman_list_daily_reports_success(self):
        """Test handyman can list daily reports for their assigned job."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/reports/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

    def test_handyman_daily_report_detail_success(self):
        """Test handyman can get daily report detail."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/reports/{self.report.public_id}/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["public_id"], str(self.report.public_id))

    def test_handyman_list_disputes_success(self):
        """Test handyman can list disputes for their assigned job."""
        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/disputes/"
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)


class OngoingSerializerCoverageTests(APITestCase):
    """Additional tests for serializer coverage."""

    def setUp(self):
        # Create homeowner
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")

        # Create handyman
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        UserRole.objects.create(user=self.handyman, role="handyman")

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

        # Create Daily Report for serializer test
        self.report = DailyReport.objects.create(
            job=self.job,
            handyman=self.handyman,
            report_date=timezone.now().date(),
            summary="Work done today",
            total_work_duration=timedelta(hours=1),
            status="pending",
            review_deadline=timezone.now() + timedelta(days=3),
        )

    def test_dispute_resolve_with_valid_refund_percentage(self):
        """Test dispute resolve serializer with full refund (auto-sets 100%)."""
        from apps.jobs.serializers import DisputeResolveSerializer

        data = {
            "status": "resolved_full_refund",
            "admin_notes": "Full refund approved",
        }
        serializer = DisputeResolveSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # Full refund should auto-set refund_percentage to 100
        self.assertEqual(serializer.validated_data["refund_percentage"], 100)

    def test_dispute_resolve_partial_with_percentage(self):
        """Test dispute resolve with partial refund and percentage."""
        from apps.jobs.serializers import DisputeResolveSerializer

        data = {
            "status": "resolved_partial_refund",
            "refund_percentage": 50,
            "admin_notes": "Partial refund",
        }
        serializer = DisputeResolveSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_daily_report_with_null_work_duration(self):
        """Test daily report serializer when total_work_duration is None."""
        from apps.jobs.serializers import DailyReportSerializer

        # Since the DB field is NOT NULL, we test the serializer logic by mocking
        class MockReport:
            public_id = self.report.public_id
            report_date = self.report.report_date
            summary = self.report.summary
            status = self.report.status
            total_work_duration = None  # Test the None case
            homeowner_comment = ""
            reviewed_at = None
            review_deadline = self.report.review_deadline
            tasks_worked = []
            created_at = self.report.created_at

        serializer = DailyReportSerializer(MockReport())
        self.assertEqual(serializer.data["total_work_duration_seconds"], 0)


class OngoingServiceCoverageTests(APITestCase):
    """Tests for service layer coverage."""

    def setUp(self):
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")

        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        UserRole.objects.create(user=self.handyman, role="handyman")

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
    def test_work_session_media_upload(self, mock_notify):
        """Test uploading media to a work session."""
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.jobs.services import work_session_service

        session = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now(),
            start_latitude=Decimal("43.0"),
            start_longitude=Decimal("-79.0"),
            status="in_progress",
        )

        # Create a simple test image
        image_content = BytesIO()
        image_content.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        image_content.seek(0)
        test_file = SimpleUploadedFile(
            "test.png", image_content.read(), content_type="image/png"
        )

        media = work_session_service.add_media(
            work_session=session,
            media_type="photo",
            file=test_file,
            file_size=100,
            description="Test photo",
        )

        self.assertIsNotNone(media)
        self.assertEqual(media.media_type, "photo")
        self.assertEqual(media.description, "Test photo")
        mock_notify.assert_called_once()

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_job_completion_reject(self, mock_notify):
        """Test rejecting job completion."""
        from apps.jobs.services import job_completion_service

        # Set job to pending_completion status
        self.job.status = "pending_completion"
        self.job.completion_requested_at = timezone.now()
        self.job.save()

        result = job_completion_service.reject_completion(
            homeowner=self.homeowner, job=self.job, reason="Work not complete"
        )

        self.assertEqual(result.status, "in_progress")
        self.assertIsNone(result.completion_requested_at)
        mock_notify.assert_called_once()
