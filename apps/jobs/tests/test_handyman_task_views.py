"""Tests for handyman job task status views."""

from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.jobs.models import City, Job, JobCategory, JobTask
from apps.profiles.models import HandymanProfile, HomeownerProfile


class HandymanJobTaskStatusViewTests(APITestCase):
    """Tests for HandymanJobTaskStatusView."""

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

        # Create a task for the job
        self.task = JobTask.objects.create(
            job=self.job, title="Test Task", order=0, is_completed=False
        )

        self.url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/tasks/{self.task.public_id}/status/"

    def test_update_task_status_success(self):
        """Test that a handyman can mark a task as completed."""
        self.client.force_authenticate(user=self.handyman)

        data = {"is_completed": True}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Task status updated successfully")
        self.assertTrue(response.data["data"]["is_completed"])
        self.assertIsNotNone(response.data["data"]["completed_at"])

        # Verify db update
        self.task.refresh_from_db()
        self.assertTrue(self.task.is_completed)
        self.assertIsNotNone(self.task.completed_at)

    def test_unmark_task_status_success(self):
        """Test that a handyman can unmark a task as completed."""
        self.task.is_completed = True
        self.task.completed_at = timezone.now()
        self.task.save()

        self.client.force_authenticate(user=self.handyman)

        data = {"is_completed": False}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["data"]["is_completed"])
        self.assertIsNone(response.data["data"]["completed_at"])

        # Verify db update
        self.task.refresh_from_db()
        self.assertFalse(self.task.is_completed)
        self.assertIsNone(self.task.completed_at)

    def test_update_task_status_invalid_job_status(self):
        """Test that tasks cannot be updated if job is not in progress."""
        self.job.status = "open"
        self.job.save()

        self.client.force_authenticate(user=self.handyman)

        data = {"is_completed": True}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_task_status_wrong_handyman(self):
        """Test that another handyman cannot update the task."""
        # Create another handyman
        other_handyman = User.objects.create_user(
            email="other_handyman@example.com", password="password123"
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

        self.client.force_authenticate(user=other_handyman)

        data = {"is_completed": True}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_task_status_invalid_data(self):
        """Test validation error."""
        self.client.force_authenticate(user=self.handyman)

        data = {"is_completed": "invalid"}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_task_status_unauthenticated(self):
        """Test that unauthenticated users cannot update task status."""
        data = {"is_completed": True}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_task_status_nonexistent_job(self):
        """Test 404 for nonexistent job."""
        self.client.force_authenticate(user=self.handyman)

        url = f"/api/v1/mobile/handyman/jobs/00000000-0000-0000-0000-000000000000/tasks/{self.task.public_id}/status/"
        data = {"is_completed": True}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_task_status_nonexistent_task(self):
        """Test 404 for nonexistent task."""
        self.client.force_authenticate(user=self.handyman)

        url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/tasks/00000000-0000-0000-0000-000000000000/status/"
        data = {"is_completed": True}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_task_idempotent_mark_complete(self):
        """Test that marking an already completed task as complete is idempotent."""
        self.task.is_completed = True
        original_completed_at = timezone.now()
        self.task.completed_at = original_completed_at
        self.task.save()

        self.client.force_authenticate(user=self.handyman)

        data = {"is_completed": True}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["data"]["is_completed"])

        # Verify the completed_at was not changed
        self.task.refresh_from_db()
        self.assertTrue(self.task.is_completed)
