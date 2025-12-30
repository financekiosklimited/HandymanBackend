
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authn.tests.factories import UserFactory
from apps.jobs.models import JobTask
from apps.jobs.tests.factories import JobFactory, JobTaskFactory


class HandymanJobTaskStatusViewTests(APITestCase):
    def setUp(self):
        self.handyman = UserFactory(
            role="handyman", email_verified=True, phone_verified=True
        )
        self.homeowner = UserFactory(
            role="homeowner", email_verified=True, phone_verified=True
        )
        
        # Create a job assigned to the handyman and in progress
        self.job = JobFactory(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            status="in_progress"
        )
        
        # Create a task for the job
        self.task = JobTaskFactory(
            job=self.job,
            title="Test Task",
            is_completed=False,
            completed_at=None
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
        other_handyman = UserFactory(role="handyman", email_verified=True, phone_verified=True)
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
