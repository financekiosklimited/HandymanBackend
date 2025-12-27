"""Tests for job admin views and actions."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.jobs.admin import (
    DisputeDeadlineFilter,
    DisputeResolveForm,
    JobDisputeAdmin,
    get_dispute_dashboard_data,
)
from apps.jobs.models import City, Job, JobCategory, JobDispute
from apps.profiles.models import HandymanProfile, HomeownerProfile


class DisputeResolveFormTests(TestCase):
    """Test cases for DisputeResolveForm."""

    def test_valid_pay_handyman(self):
        """Test valid form for pay handyman resolution."""
        form = DisputeResolveForm(
            data={
                "status": "resolved_pay_handyman",
                "admin_notes": "Work was satisfactory.",
            }
        )
        self.assertTrue(form.is_valid())

    def test_valid_full_refund(self):
        """Test valid form for full refund resolution."""
        form = DisputeResolveForm(
            data={
                "status": "resolved_full_refund",
                "admin_notes": "Homeowner's complaint is valid.",
            }
        )
        self.assertTrue(form.is_valid())

    def test_valid_partial_refund(self):
        """Test valid form for partial refund resolution."""
        form = DisputeResolveForm(
            data={
                "status": "resolved_partial_refund",
                "refund_percentage": 50,
                "admin_notes": "Partial work completed.",
            }
        )
        self.assertTrue(form.is_valid())

    def test_partial_refund_requires_percentage(self):
        """Test that partial refund requires refund_percentage."""
        form = DisputeResolveForm(
            data={
                "status": "resolved_partial_refund",
                "admin_notes": "Test notes.",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("refund_percentage", form.errors)

    def test_refund_percentage_min_value(self):
        """Test refund_percentage minimum value validation."""
        form = DisputeResolveForm(
            data={
                "status": "resolved_partial_refund",
                "refund_percentage": 0,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("refund_percentage", form.errors)

    def test_refund_percentage_max_value(self):
        """Test refund_percentage maximum value validation."""
        form = DisputeResolveForm(
            data={
                "status": "resolved_partial_refund",
                "refund_percentage": 100,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("refund_percentage", form.errors)

    def test_admin_notes_optional(self):
        """Test that admin_notes is optional."""
        form = DisputeResolveForm(
            data={
                "status": "resolved_pay_handyman",
            }
        )
        self.assertTrue(form.is_valid())


class DisputeDeadlineFilterTests(TestCase):
    """Test cases for DisputeDeadlineFilter."""

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

        HomeownerProfile.objects.create(user=self.homeowner, display_name="Owner")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Handy",
            phone_verified_at=timezone.now(),
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
            title="Test Job",
            description="Test description",
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
            estimated_budget=100,
            assigned_handyman=self.handyman,
        )

        now = timezone.now()

        # Create overdue dispute
        self.overdue_dispute = JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Overdue dispute",
            status="pending",
            resolution_deadline=now - timedelta(hours=2),
        )

        # Create due soon dispute
        self.due_soon_dispute = JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Due soon dispute",
            status="pending",
            resolution_deadline=now + timedelta(hours=12),
        )

        # Create on track dispute
        self.on_track_dispute = JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="On track dispute",
            status="pending",
            resolution_deadline=now + timedelta(days=2),
        )

    def _get_filter_queryset(self, value):
        """Helper to get filtered queryset with a specific value."""
        from django.http import QueryDict
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/admin/jobs/jobdispute/", {"deadline_status": value})

        # Use QueryDict to properly format params as Django expects
        params = QueryDict(mutable=True)
        params["deadline_status"] = value

        filter_instance = DisputeDeadlineFilter(
            request=request,
            params=params,
            model=JobDispute,
            model_admin=None,
        )
        return filter_instance.queryset(request, JobDispute.objects.all())

    def test_filter_lookups(self):
        """Test filter provides correct lookup options."""
        filter_instance = DisputeDeadlineFilter(
            request=None, params={}, model=JobDispute, model_admin=None
        )
        lookups = filter_instance.lookups(None, None)

        self.assertEqual(len(lookups), 3)
        self.assertIn(("overdue", "Overdue"), lookups)
        self.assertIn(("due_soon", "Due Soon (24h)"), lookups)
        self.assertIn(("on_track", "On Track"), lookups)

    def test_filter_overdue(self):
        """Test filtering overdue disputes."""
        queryset = self._get_filter_queryset("overdue")
        dispute_ids = list(queryset.values_list("pk", flat=True))

        self.assertIn(self.overdue_dispute.pk, dispute_ids)
        self.assertNotIn(self.due_soon_dispute.pk, dispute_ids)
        self.assertNotIn(self.on_track_dispute.pk, dispute_ids)

    def test_filter_due_soon(self):
        """Test filtering due soon disputes."""
        queryset = self._get_filter_queryset("due_soon")
        dispute_ids = list(queryset.values_list("pk", flat=True))

        self.assertNotIn(self.overdue_dispute.pk, dispute_ids)
        self.assertIn(self.due_soon_dispute.pk, dispute_ids)
        self.assertNotIn(self.on_track_dispute.pk, dispute_ids)

    def test_filter_on_track(self):
        """Test filtering on track disputes."""
        queryset = self._get_filter_queryset("on_track")
        dispute_ids = list(queryset.values_list("pk", flat=True))

        self.assertNotIn(self.overdue_dispute.pk, dispute_ids)
        self.assertNotIn(self.due_soon_dispute.pk, dispute_ids)
        self.assertIn(self.on_track_dispute.pk, dispute_ids)

    def test_filter_no_value(self):
        """Test filter returns all when no value selected."""
        filter_instance = DisputeDeadlineFilter(
            request=None, params={}, model=JobDispute, model_admin=None
        )
        queryset = filter_instance.queryset(None, JobDispute.objects.all())

        self.assertEqual(queryset.count(), 3)


class GetDisputeDashboardDataTests(TestCase):
    """Test cases for get_dispute_dashboard_data function."""

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

        HomeownerProfile.objects.create(user=self.homeowner, display_name="Owner")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Handy",
            phone_verified_at=timezone.now(),
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
            title="Test Job",
            description="Test description",
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
            estimated_budget=100,
            assigned_handyman=self.handyman,
        )

    def test_empty_dashboard_data(self):
        """Test dashboard data with no disputes."""
        data = get_dispute_dashboard_data()

        self.assertEqual(data["kpis"]["pending_count"], 0)
        self.assertEqual(data["kpis"]["in_review_count"], 0)
        self.assertEqual(data["kpis"]["overdue_count"], 0)
        self.assertEqual(data["kpis"]["due_soon_count"], 0)
        self.assertEqual(data["kpis"]["resolved_this_week"], 0)
        self.assertEqual(data["disputes"].count(), 0)

    def test_dashboard_data_with_disputes(self):
        """Test dashboard data with various disputes."""
        now = timezone.now()

        # Create pending dispute (on track - more than 24h away)
        JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Pending dispute",
            status="pending",
            resolution_deadline=now + timedelta(days=2),
        )

        # Create in_review dispute (on track)
        JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="In review dispute",
            status="in_review",
            resolution_deadline=now + timedelta(days=1, hours=2),
        )

        # Create overdue dispute
        JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Overdue dispute",
            status="pending",
            resolution_deadline=now - timedelta(hours=1),
        )

        # Create due soon dispute (within 24h but not overdue)
        JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Due soon dispute",
            status="pending",
            resolution_deadline=now + timedelta(hours=12),
        )

        # Create resolved dispute (this week)
        JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Resolved dispute",
            status="resolved_pay_handyman",
            resolution_deadline=now + timedelta(days=3),
            resolved_at=now - timedelta(days=1),
        )

        data = get_dispute_dashboard_data()

        # Pending count: 3 (all pending status disputes)
        self.assertEqual(data["kpis"]["pending_count"], 3)
        # In review count: 1
        self.assertEqual(data["kpis"]["in_review_count"], 1)
        # Overdue count: 1 (only the overdue one)
        self.assertEqual(data["kpis"]["overdue_count"], 1)
        # Due soon count: 1 (only the due soon one, overdue is not due_soon)
        self.assertEqual(data["kpis"]["due_soon_count"], 1)
        # Resolved this week: 1
        self.assertEqual(data["kpis"]["resolved_this_week"], 1)

        # disputes queryset should only include pending/in_review
        self.assertEqual(data["disputes"].count(), 4)


class JobDisputeAdminViewTests(TestCase):
    """Test cases for JobDisputeAdmin views."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create admin user
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )

        # Create regular admin without dispute permission
        self.limited_admin = User.objects.create_user(
            email="limited@example.com", password="limitedpass123", is_staff=True
        )

        # Create admin with dispute permission
        self.dispute_admin = User.objects.create_user(
            email="dispute@example.com", password="disputepass123", is_staff=True
        )
        content_type = ContentType.objects.get_for_model(JobDispute)
        permission = Permission.objects.get(
            codename="can_manage_disputes", content_type=content_type
        )
        self.dispute_admin.user_permissions.add(permission)

        # Create test data
        self.homeowner = User.objects.create_user(
            email="owner@example.com", password="password123"
        )
        self.handyman = User.objects.create_user(
            email="handy@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        UserRole.objects.create(user=self.handyman, role="handyman")

        HomeownerProfile.objects.create(user=self.homeowner, display_name="Owner")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Handy",
            phone_verified_at=timezone.now(),
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
            title="Test Job",
            description="Test description",
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
            estimated_budget=100,
            assigned_handyman=self.handyman,
        )

        self.dispute = JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Test dispute reason",
            status="pending",
            resolution_deadline=timezone.now() + timedelta(days=3),
        )

    def test_dashboard_view_requires_login(self):
        """Test dashboard view requires authentication."""
        url = reverse("admin:jobs_jobdispute_dashboard")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_dashboard_view_accessible_by_admin(self):
        """Test dashboard view is accessible by admin users."""
        self.client.login(email="admin@example.com", password="adminpass123")
        url = reverse("admin:jobs_jobdispute_dashboard")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Disputes Dashboard")

    def test_dashboard_view_shows_disputes(self):
        """Test dashboard view displays pending disputes."""
        self.client.login(email="admin@example.com", password="adminpass123")
        url = reverse("admin:jobs_jobdispute_dashboard")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.dispute.job.title)
        self.assertContains(response, "Test dispute reason")

    def test_resolve_view_requires_login(self):
        """Test resolve view requires authentication."""
        url = reverse("admin:jobs_jobdispute_resolve", args=[self.dispute.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_resolve_view_accessible_by_admin(self):
        """Test resolve view is accessible by admin users."""
        self.client.login(email="admin@example.com", password="adminpass123")
        url = reverse("admin:jobs_jobdispute_resolve", args=[self.dispute.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resolve Dispute")
        self.assertContains(response, self.job.title)

    def test_resolve_view_shows_dispute_details(self):
        """Test resolve view shows dispute details."""
        self.client.login(email="admin@example.com", password="adminpass123")
        url = reverse("admin:jobs_jobdispute_resolve", args=[self.dispute.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.dispute.reason)
        self.assertContains(response, self.homeowner.email)
        self.assertContains(response, self.handyman.email)

    @patch("apps.jobs.services.dispute_service.resolve_dispute")
    def test_resolve_view_post_success(self, mock_resolve):
        """Test successful dispute resolution via POST."""
        self.client.login(email="admin@example.com", password="adminpass123")
        url = reverse("admin:jobs_jobdispute_resolve", args=[self.dispute.pk])

        response = self.client.post(
            url,
            {
                "status": "resolved_pay_handyman",
                "admin_notes": "Work was good.",
            },
        )

        self.assertRedirects(
            response,
            reverse("admin:jobs_jobdispute_dashboard"),
            fetch_redirect_response=False,
        )
        mock_resolve.assert_called_once()

    @patch("apps.jobs.services.dispute_service.resolve_dispute")
    def test_resolve_view_post_partial_refund(self, mock_resolve):
        """Test partial refund resolution via POST."""
        self.client.login(email="admin@example.com", password="adminpass123")
        url = reverse("admin:jobs_jobdispute_resolve", args=[self.dispute.pk])

        response = self.client.post(
            url,
            {
                "status": "resolved_partial_refund",
                "refund_percentage": 50,
                "admin_notes": "Half the work was done.",
            },
        )

        self.assertRedirects(
            response,
            reverse("admin:jobs_jobdispute_dashboard"),
            fetch_redirect_response=False,
        )
        mock_resolve.assert_called_once()
        call_kwargs = mock_resolve.call_args.kwargs
        self.assertEqual(call_kwargs["refund_percentage"], 50)

    def test_resolve_view_post_invalid_form(self):
        """Test resolve view with invalid form data."""
        self.client.login(email="admin@example.com", password="adminpass123")
        url = reverse("admin:jobs_jobdispute_resolve", args=[self.dispute.pk])

        response = self.client.post(
            url,
            {
                "status": "resolved_partial_refund",
                # Missing refund_percentage
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "refund_percentage")

    def test_resolve_view_already_resolved(self):
        """Test resolve view redirects for already resolved disputes."""
        self.dispute.status = "resolved_pay_handyman"
        self.dispute.save()

        self.client.login(email="admin@example.com", password="adminpass123")
        url = reverse("admin:jobs_jobdispute_resolve", args=[self.dispute.pk])
        response = self.client.get(url)

        self.assertRedirects(
            response,
            reverse("admin:jobs_jobdispute_dashboard"),
            fetch_redirect_response=False,
        )

    def test_resolve_view_without_permission(self):
        """Test resolve view shows permission message for limited admin."""
        self.client.login(email="limited@example.com", password="limitedpass123")
        url = reverse("admin:jobs_jobdispute_resolve", args=[self.dispute.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Permission Required")

    def test_resolve_view_post_without_permission(self):
        """Test POST to resolve view without permission redirects."""
        self.client.login(email="limited@example.com", password="limitedpass123")
        url = reverse("admin:jobs_jobdispute_resolve", args=[self.dispute.pk])

        response = self.client.post(
            url,
            {
                "status": "resolved_pay_handyman",
                "admin_notes": "Test.",
            },
        )

        self.assertRedirects(
            response,
            reverse("admin:jobs_jobdispute_dashboard"),
            fetch_redirect_response=False,
        )

    def test_resolve_view_with_dispute_permission(self):
        """Test resolve view works with can_manage_disputes permission."""
        self.client.login(email="dispute@example.com", password="disputepass123")
        url = reverse("admin:jobs_jobdispute_resolve", args=[self.dispute.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Permission Required")
        self.assertContains(response, "Resolve Dispute")


class JobDisputeAdminActionsTests(TestCase):
    """Test cases for JobDisputeAdmin bulk actions."""

    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = JobDisputeAdmin(JobDispute, self.site)

        self.admin_user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )

        self.homeowner = User.objects.create_user(
            email="owner@example.com", password="password123"
        )
        self.handyman = User.objects.create_user(
            email="handy@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        UserRole.objects.create(user=self.handyman, role="handyman")

        HomeownerProfile.objects.create(user=self.homeowner, display_name="Owner")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Handy",
            phone_verified_at=timezone.now(),
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
            title="Test Job",
            description="Test description",
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
            estimated_budget=100,
            assigned_handyman=self.handyman,
        )

        self.dispute1 = JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Dispute 1",
            status="pending",
            resolution_deadline=timezone.now() + timedelta(days=3),
        )

        self.dispute2 = JobDispute.objects.create(
            job=self.job,
            initiated_by=self.homeowner,
            reason="Dispute 2",
            status="pending",
            resolution_deadline=timezone.now() + timedelta(days=3),
        )

    def test_mark_in_review_action(self):
        """Test mark_in_review bulk action."""
        queryset = JobDispute.objects.filter(
            pk__in=[self.dispute1.pk, self.dispute2.pk]
        )

        # Create a mock request
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.post("/admin/jobs/jobdispute/")
        request.user = self.admin_user
        request._messages = []  # Mock messages

        # Mock message_user
        messages_list = []

        def mock_message_user(request, message, level=None):
            messages_list.append(message)

        self.admin.message_user = mock_message_user

        self.admin.mark_in_review(request, queryset)

        self.dispute1.refresh_from_db()
        self.dispute2.refresh_from_db()

        self.assertEqual(self.dispute1.status, "in_review")
        self.assertEqual(self.dispute2.status, "in_review")
        self.assertTrue(any("2 dispute(s)" in msg for msg in messages_list))

    @patch("apps.jobs.services.dispute_service.resolve_dispute")
    def test_resolve_pay_handyman_action(self, mock_resolve):
        """Test resolve_pay_handyman bulk action."""
        queryset = JobDispute.objects.filter(pk=self.dispute1.pk)

        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.post("/admin/jobs/jobdispute/")
        request.user = self.admin_user

        messages_list = []

        def mock_message_user(request, message, level=None):
            messages_list.append(message)

        self.admin.message_user = mock_message_user

        self.admin.resolve_pay_handyman(request, queryset)

        mock_resolve.assert_called_once()
        call_kwargs = mock_resolve.call_args.kwargs
        self.assertEqual(call_kwargs["status"], "resolved_pay_handyman")

    @patch("apps.jobs.services.dispute_service.resolve_dispute")
    def test_resolve_full_refund_action(self, mock_resolve):
        """Test resolve_full_refund bulk action."""
        queryset = JobDispute.objects.filter(pk=self.dispute1.pk)

        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.post("/admin/jobs/jobdispute/")
        request.user = self.admin_user

        messages_list = []

        def mock_message_user(request, message, level=None):
            messages_list.append(message)

        self.admin.message_user = mock_message_user

        self.admin.resolve_full_refund(request, queryset)

        mock_resolve.assert_called_once()
        call_kwargs = mock_resolve.call_args.kwargs
        self.assertEqual(call_kwargs["status"], "resolved_full_refund")

    def test_bulk_action_skips_resolved_disputes(self):
        """Test bulk actions skip already resolved disputes."""
        self.dispute1.status = "resolved_pay_handyman"
        self.dispute1.save()

        queryset = JobDispute.objects.filter(
            pk__in=[self.dispute1.pk, self.dispute2.pk]
        )

        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.post("/admin/jobs/jobdispute/")
        request.user = self.admin_user

        messages_list = []

        def mock_message_user(request, message, level=None):
            messages_list.append(message)

        self.admin.message_user = mock_message_user

        self.admin.mark_in_review(request, queryset)

        self.dispute1.refresh_from_db()
        self.dispute2.refresh_from_db()

        # dispute1 should remain resolved
        self.assertEqual(self.dispute1.status, "resolved_pay_handyman")
        # Only dispute2 should be marked as in_review
        self.assertEqual(self.dispute2.status, "in_review")
        self.assertTrue(any("1 dispute(s)" in msg for msg in messages_list))
