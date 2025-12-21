import json
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.common.dashboard import (
    dashboard_callback,
    get_jobs_by_status_chart_data,
    get_kpi_cards,
    get_user_signups_chart_data,
)
from apps.jobs.models import City, Job, JobApplication, JobCategory


class DashboardTests(TestCase):
    def setUp(self):
        # Create categories and cities for jobs
        self.category = JobCategory.objects.create(name="Test Category", slug="test")
        self.city = City.objects.create(name="Test City", slug="test")

        # Create a user
        self.user = User.objects.create_user(
            email="test@example.com", password="password"
        )

        # Create some jobs with different statuses
        Job.objects.create(
            homeowner=self.user,
            title="Job 1",
            description="Description 1",
            estimated_budget=100,
            address="Address 1",
            category=self.category,
            city=self.city,
            status="open",
        )
        Job.objects.create(
            homeowner=self.user,
            title="Job 2",
            description="Description 2",
            estimated_budget=200,
            address="Address 2",
            category=self.category,
            city=self.city,
            status="draft",
        )

        # Create a job application
        JobApplication.objects.create(
            job=Job.objects.first(), handyman=self.user, status="pending"
        )

    def test_get_kpi_cards(self):
        cards = get_kpi_cards()
        self.assertEqual(len(cards), 4)
        self.assertEqual(cards[0]["metric"], 1)  # 1 user
        self.assertEqual(cards[1]["metric"], 2)  # 2 jobs
        self.assertEqual(cards[2]["metric"], 1)  # 1 open job
        self.assertEqual(cards[3]["metric"], 1)  # 1 pending app

    def test_get_user_signups_chart_data(self):
        # Create a user 31 days ago (should not be in chart)
        old_user = User.objects.create_user(
            email="old@example.com", password="password"
        )
        User.objects.filter(id=old_user.id).update(
            created_at=timezone.now() - timedelta(days=31)
        )

        chart_json = get_user_signups_chart_data()
        chart_data = json.loads(chart_json)

        self.assertIn("labels", chart_data)
        self.assertEqual(len(chart_data["labels"]), 30)
        self.assertIn("datasets", chart_data)
        self.assertEqual(
            sum(chart_data["datasets"][0]["data"]), 1
        )  # Only 1 user from setUp

    def test_get_jobs_by_status_chart_data(self):
        chart_json = get_jobs_by_status_chart_data()
        chart_data = json.loads(chart_json)

        self.assertIn("labels", chart_data)
        # draft, open, in_progress, completed, cancelled
        self.assertEqual(chart_data["datasets"][0]["data"], [1, 1, 0, 0, 0])

    def test_dashboard_callback(self):
        context = {}
        updated_context = dashboard_callback(None, context)
        self.assertIn("kpi_cards", updated_context)
        self.assertIn("user_signups_chart", updated_context)
        self.assertIn("jobs_by_status_chart", updated_context)
