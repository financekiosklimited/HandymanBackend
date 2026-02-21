from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.jobs.models import City, DailyReport, Job, JobCategory, JobDispute


class ProcessOverdueReportsCommandTests(TestCase):
    def setUp(self):
        self.homeowner = User.objects.create_user(
            email="owner@example.com", password="pass"
        )
        self.handyman = User.objects.create_user(
            email="handy@example.com", password="pass"
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
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 St",
            status="in_progress",
            payment_mode="legacy_exempt",
        )

    def test_overdue_reports_are_auto_approved(self):
        now = timezone.now()
        overdue = DailyReport.objects.create(
            job=self.job,
            handyman=self.handyman,
            report_date=now.date(),
            summary="Work",
            total_work_duration=timedelta(hours=2),
            status="pending",
            review_deadline=now - timedelta(days=1),
        )
        future = DailyReport.objects.create(
            job=self.job,
            handyman=self.handyman,
            report_date=now.date() - timedelta(days=1),
            summary="Work 2",
            total_work_duration=timedelta(hours=1),
            status="pending",
            review_deadline=now + timedelta(days=1),
        )

        out = StringIO()
        call_command("process_overdue_reports", stdout=out)

        overdue.refresh_from_db()
        future.refresh_from_db()
        self.assertEqual(overdue.status, "approved")
        self.assertIsNotNone(overdue.reviewed_at)
        self.assertEqual(future.status, "pending")
        self.assertIn("Auto-approved 1 overdue reports", out.getvalue())


class ProcessOverdueDisputesCommandTests(TestCase):
    def setUp(self):
        self.homeowner = User.objects.create_user(
            email="owner@example.com", password="pass"
        )
        self.handyman = User.objects.create_user(
            email="handy@example.com", password="pass"
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
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 St",
            status="pending_completion",
            payment_mode="legacy_exempt",
        )

    def test_overdue_disputes_are_resolved(self):
        now = timezone.now()
        overdue = JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Issue",
            status="pending",
            resolution_deadline=now - timedelta(days=1),
        )
        future = JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Issue later",
            status="in_review",
            resolution_deadline=now + timedelta(days=1),
        )

        out = StringIO()
        call_command("process_overdue_disputes", stdout=out)

        overdue.refresh_from_db()
        future.refresh_from_db()
        self.assertEqual(overdue.status, "resolved_pay_handyman")
        self.assertIsNotNone(overdue.resolved_at)
        self.assertEqual(future.status, "in_review")
        self.assertIn("Auto-resolved 1 disputes", out.getvalue())

    @patch("apps.jobs.services.dispute_service.resolve_dispute")
    def test_overdue_disputes_with_errors(self, mock_resolve):
        """Test that errors during dispute resolution are handled and reported."""
        mock_resolve.side_effect = Exception("Resolution failed")

        now = timezone.now()
        JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Issue",
            status="pending",
            resolution_deadline=now - timedelta(days=1),
        )

        out = StringIO()
        err = StringIO()
        call_command("process_overdue_disputes", stdout=out, stderr=err)

        # Should report 0 resolved and 1 failure
        self.assertIn("Auto-resolved 0 disputes", out.getvalue())
        self.assertIn("Failed to resolve 1 disputes", out.getvalue())
        self.assertIn("Resolution failed", err.getvalue())
