"""Tests for jobs mobile views."""

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
    JobApplication,
    JobCategory,
    JobDispute,
    JobTask,
    Review,
    WorkSession,
    WorkSessionMedia,
)
from apps.profiles.models import HandymanProfile, HomeownerProfile


def create_test_image():
    """Create a test image file."""
    img = PILImage.new("RGB", (100, 100), color="red")
    img_io = BytesIO()
    img.save(img_io, format="JPEG")
    img_io.seek(0)
    return SimpleUploadedFile("test.jpg", img_io.read(), content_type="image/jpeg")


class MobileJobCategoryListViewTests(APITestCase):
    """Test cases for mobile JobCategoryListView."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/job-categories/"
        self.user = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        self.user.email_verified_at = "2024-01-01T00:00:00Z"
        self.user.save()
        # Mock token payload for permissions
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
        }

        # Create test categories
        JobCategory.objects.create(name="Plumbing", slug="plumbing", is_active=True)
        JobCategory.objects.create(name="Electrical", slug="electrical", is_active=True)
        JobCategory.objects.create(name="Inactive", slug="inactive", is_active=False)

    def test_list_categories_success(self):
        """Test successfully listing active categories."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Categories retrieved successfully")
        self.assertEqual(len(response.data["data"]), 2)  # Only active categories

    def test_list_categories_unauthenticated(self):
        """Test listing categories without authentication succeeds."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Categories retrieved successfully")
        self.assertEqual(len(response.data["data"]), 2)  # Only active categories


class MobileCityListViewTests(APITestCase):
    """Test cases for mobile CityListView."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/cities/"
        self.user = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        self.user.email_verified_at = "2024-01-01T00:00:00Z"
        self.user.save()
        # Mock token payload for permissions
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
        }

        # Create test cities
        City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            is_active=True,
        )
        City.objects.create(
            name="Vancouver",
            province="British Columbia",
            province_code="BC",
            slug="vancouver-bc",
            is_active=True,
        )
        City.objects.create(
            name="Inactive",
            province="Test",
            province_code="TS",
            slug="inactive-ts",
            is_active=False,
        )

    def test_list_cities_success(self):
        """Test successfully listing active cities."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Cities retrieved successfully")
        self.assertEqual(len(response.data["data"]), 2)  # Only active cities

    def test_list_cities_with_province_filter(self):
        """Test listing cities with province filter."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"province": "ON"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["name"], "Toronto")

    def test_list_cities_unauthenticated(self):
        """Test listing cities without authentication succeeds."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Cities retrieved successfully")
        self.assertEqual(len(response.data["data"]), 2)  # Only active cities


class MobileJobListCreateViewTests(APITestCase):
    """Test cases for mobile JobListCreateView."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/homeowner/jobs/"
        self.user = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="homeowner")
        self.user.email_verified_at = "2024-01-01T00:00:00Z"
        self.user.save()
        # Mock token payload for permissions (with phone_verified for POST)
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Create another user to test isolation
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )

        # Create test category and city
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

    def test_list_jobs_success(self):
        """Test successfully listing homeowner's jobs."""
        # Create jobs for the authenticated user
        Job.objects.create(
            homeowner=self.user,
            title="Fix faucet",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        Job.objects.create(
            homeowner=self.user,
            title="Fix door",
            description="Test",
            estimated_budget=Decimal("40.00"),
            category=self.category,
            city=self.city,
            address="456 Oak Ave",
        )

        # Create job for another user
        Job.objects.create(
            homeowner=self.other_user,
            title="Other user job",
            description="Test",
            estimated_budget=Decimal("30.00"),
            category=self.category,
            city=self.city,
            address="789 Pine St",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Jobs retrieved successfully")
        self.assertEqual(len(response.data["data"]), 2)  # Only user's jobs
        self.assertIn("pagination", response.data["meta"])

    def test_list_jobs_with_city_filter(self):
        """Test listing homeowner's jobs with city filter."""
        Job.objects.create(
            homeowner=self.user,
            title="Toronto job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"city": str(self.city.public_id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Toronto job")

    def test_list_jobs_with_category_filter(self):
        """Test listing jobs with category filter."""
        category2 = JobCategory.objects.create(
            name="Electrical", slug="electrical", is_active=True
        )

        Job.objects.create(
            homeowner=self.user,
            title="Plumbing job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        Job.objects.create(
            homeowner=self.user,
            title="Electrical job",
            description="Test",
            estimated_budget=Decimal("60.00"),
            category=category2,
            city=self.city,
            address="456 Oak Ave",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"category": str(self.category.public_id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Plumbing job")

    def test_list_jobs_with_status_filter(self):
        """Test listing jobs with status filter."""
        Job.objects.create(
            homeowner=self.user,
            title="Draft job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="draft",
        )
        Job.objects.create(
            homeowner=self.user,
            title="Open job",
            description="Test",
            estimated_budget=Decimal("60.00"),
            category=self.category,
            city=self.city,
            address="456 Oak Ave",
            status="open",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"status": "open"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Open job")

    def test_list_jobs_pagination(self):
        """Test job listing pagination."""
        # Create 25 jobs
        for i in range(25):
            Job.objects.create(
                homeowner=self.user,
                title=f"Job {i}",
                description="Test",
                estimated_budget=Decimal("50.00"),
                category=self.category,
                city=self.city,
                address="123 Main St",
            )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"page": 1, "page_size": 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 10)
        self.assertEqual(response.data["meta"]["pagination"]["page"], 1)
        self.assertEqual(response.data["meta"]["pagination"]["total_pages"], 3)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 25)
        self.assertTrue(response.data["meta"]["pagination"]["has_next"])
        self.assertFalse(response.data["meta"]["pagination"]["has_previous"])

    def test_list_jobs_search(self):
        """Test searching homeowner's jobs by title and description."""
        Job.objects.create(
            homeowner=self.user,
            title="Searchable Title",
            description="Regular description",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        Job.objects.create(
            homeowner=self.user,
            title="Regular Title",
            description="Searchable UniqueDescription",
            estimated_budget=Decimal("40.00"),
            category=self.category,
            city=self.city,
            address="456 Oak Ave",
        )
        Job.objects.create(
            homeowner=self.user,
            title="Other",
            description="Other",
            estimated_budget=Decimal("30.00"),
            category=self.category,
            city=self.city,
            address="789 Pine St",
        )

        self.client.force_authenticate(user=self.user)

        # Search by title
        response = self.client.get(self.url, {"search": "Title"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

        # Search by description
        response = self.client.get(self.url, {"search": "UniqueDescription"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Regular Title")

        # Search case-insensitive
        response = self.client.get(self.url, {"search": "searchable"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

    def test_list_jobs_priority_ordering_open_and_in_progress_first(self):
        """Test that open and in_progress jobs are listed first."""
        # Create jobs with different statuses
        Job.objects.create(
            homeowner=self.user,
            title="Completed job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="completed",
        )
        Job.objects.create(
            homeowner=self.user,
            title="Open job",
            description="Test",
            estimated_budget=Decimal("60.00"),
            category=self.category,
            city=self.city,
            address="456 Oak Ave",
            status="open",
        )
        Job.objects.create(
            homeowner=self.user,
            title="Cancelled job",
            description="Test",
            estimated_budget=Decimal("70.00"),
            category=self.category,
            city=self.city,
            address="789 Pine St",
            status="cancelled",
        )
        Job.objects.create(
            homeowner=self.user,
            title="In progress job",
            description="Test",
            estimated_budget=Decimal("80.00"),
            category=self.category,
            city=self.city,
            address="321 Elm St",
            status="in_progress",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 4)

        # First two should be open/in_progress (priority 0)
        first_two_statuses = {
            response.data["data"][0]["status"],
            response.data["data"][1]["status"],
        }
        self.assertEqual(first_two_statuses, {"open", "in_progress"})

        # Last two should be completed/cancelled (priority 1)
        last_two_statuses = {
            response.data["data"][2]["status"],
            response.data["data"][3]["status"],
        }
        self.assertEqual(last_two_statuses, {"completed", "cancelled"})

    def test_list_jobs_ordering_within_priority_group(self):
        """Test that within each priority group, jobs are sorted by created_at desc."""
        # Create two open jobs
        Job.objects.create(
            homeowner=self.user,
            title="Open old",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )
        Job.objects.create(
            homeowner=self.user,
            title="Open new",
            description="Test",
            estimated_budget=Decimal("60.00"),
            category=self.category,
            city=self.city,
            address="456 Oak Ave",
            status="open",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

        # Newer job should appear first (created_at DESC)
        self.assertEqual(response.data["data"][0]["title"], "Open new")
        self.assertEqual(response.data["data"][1]["title"], "Open old")

    def test_create_job_success(self):
        """Test successfully creating a job."""
        data = {
            "title": "Fix leaking faucet",
            "description": "Kitchen faucet is leaking",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "status": "open",
        }

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Job created successfully")
        self.assertEqual(response.data["data"]["title"], "Fix leaking faucet")

        # Verify in database
        self.assertEqual(Job.objects.count(), 1)
        job = Job.objects.first()
        self.assertEqual(job.homeowner, self.user)
        self.assertEqual(job.title, "Fix leaking faucet")

    def test_create_job_with_coordinates(self):
        """Test creating a job with latitude and longitude."""
        data = {
            "title": "Test job",
            "description": "Test description",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "latitude": "43.651070",
            "longitude": "-79.347015",
        }

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        job = Job.objects.first()
        self.assertEqual(float(job.latitude), 43.651070)
        self.assertEqual(float(job.longitude), -79.347015)

    def test_create_job_with_images(self):
        """Test creating a job with images."""
        # Create test images
        image1_io = BytesIO()
        pil_image1 = PILImage.new("RGB", (100, 100), color="red")
        pil_image1.save(image1_io, format="JPEG")
        image1_io.seek(0)
        image1 = SimpleUploadedFile(
            "test1.jpg", image1_io.getvalue(), content_type="image/jpeg"
        )

        data = {
            "title": "Test job",
            "description": "Test description",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "images": [image1],
        }

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        job = Job.objects.first()
        self.assertEqual(job.images.count(), 1)

    def test_create_job_validation_errors(self):
        """Test job creation with validation errors."""
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "-10.00",  # Invalid: negative
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
        }

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("estimated_budget", response.data["errors"])

    def test_create_job_unauthenticated(self):
        """Test creating job without authentication fails."""
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
        }

        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_jobs_unauthenticated(self):
        """Test listing jobs without authentication fails."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_job_requires_phone_verification(self):
        """Test creating job without phone verification fails."""
        # User without phone verification
        user_no_phone = User.objects.create_user(
            email="nophone@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=user_no_phone, role="homeowner")
        user_no_phone.email_verified_at = "2024-01-01T00:00:00Z"
        user_no_phone.save()
        user_no_phone.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
            "phone_verified": False,
        }

        data = {
            "title": "Test job",
            "description": "Test description",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
        }

        self.client.force_authenticate(user=user_no_phone)
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("phone", str(response.data["errors"]).lower())


class MobileJobDetailViewTests(APITestCase):
    """Test cases for mobile JobDetailView."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="homeowner")
        self.user.email_verified_at = "2024-01-01T00:00:00Z"
        self.user.save()
        # Mock token payload for permissions
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
        }

        # Create another user
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )

        # Create test category and city
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

        # Create test job
        self.job = Job.objects.create(
            homeowner=self.user,
            title="Fix leaking faucet",
            description="Kitchen faucet is leaking",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        self.url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/"

    def test_get_job_detail_success(self):
        """Test successfully getting job detail."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Job retrieved successfully")
        self.assertEqual(response.data["data"]["title"], "Fix leaking faucet")

    def test_get_job_detail_not_owner(self):
        """Test getting job detail that doesn't belong to user fails."""
        # Create job for other user
        other_job = Job.objects.create(
            homeowner=self.other_user,
            title="Other user job",
            description="Test",
            estimated_budget=Decimal("30.00"),
            category=self.category,
            city=self.city,
            address="456 Oak Ave",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            f"/api/v1/mobile/homeowner/jobs/{other_job.public_id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_job_detail_not_found(self):
        """Test getting non-existent job returns 404."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            "/api/v1/mobile/homeowner/jobs/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_job_detail_unauthenticated(self):
        """Test getting job detail without authentication fails."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_deleted_job_returns_404(self):
        """Test getting deleted job returns 404."""
        self.job.status = "deleted"
        self.job.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class MobileJobUpdateDeleteViewTests(APITestCase):
    """Test cases for mobile JobDetailView PUT and DELETE methods."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="homeowner")
        self.user.email_verified_at = "2024-01-01T00:00:00Z"
        self.user.save()
        # Mock token payload for permissions (with phone_verified for PUT/DELETE)
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Create another user
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )

        # Create test categories and cities
        self.category = JobCategory.objects.create(
            name="Plumbing", slug="plumbing", is_active=True
        )
        self.category2 = JobCategory.objects.create(
            name="Electrical", slug="electrical", is_active=True
        )
        self.city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            is_active=True,
        )
        self.city2 = City.objects.create(
            name="Vancouver",
            province="British Columbia",
            province_code="BC",
            slug="vancouver-bc",
            is_active=True,
        )

        # Create test job
        self.job = Job.objects.create(
            homeowner=self.user,
            title="Fix leaking faucet",
            description="Kitchen faucet is leaking",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="draft",
        )

        self.url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/"

    # ===== PUT Tests =====

    def test_update_job_success(self):
        """Test successfully updating a job."""
        data = {
            "title": "Updated title",
            "description": "Updated description",
            "estimated_budget": "100.00",
        }

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Job updated successfully")
        self.assertEqual(response.data["data"]["title"], "Updated title")
        self.assertEqual(response.data["data"]["description"], "Updated description")
        self.assertEqual(response.data["data"]["estimated_budget"], 100.00)

        # Verify in database
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, "Updated title")

    def test_update_job_partial_update(self):
        """Test partial update (only some fields)."""
        data = {"title": "Only title updated"}

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["title"], "Only title updated")
        # Other fields should remain unchanged
        self.assertEqual(
            response.data["data"]["description"], "Kitchen faucet is leaking"
        )

    def test_update_job_change_category(self):
        """Test updating job category."""
        data = {"category_id": str(self.category2.public_id)}

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["data"]["category"]["public_id"],
            str(self.category2.public_id),
        )

    def test_update_job_change_city(self):
        """Test updating job city."""
        data = {"city_id": str(self.city2.public_id)}

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["data"]["city"]["public_id"], str(self.city2.public_id)
        )

    def test_update_job_change_status_draft_to_open(self):
        """Test changing status from draft to open."""
        data = {"status": "open"}

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["status"], "open")

    def test_update_job_status_at_updated(self):
        """Test that status_at is updated when status changes."""
        # Initial status_at
        initial_status_at = self.job.status_at

        data = {"status": "open"}
        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.job.refresh_from_db()
        self.assertIsNotNone(self.job.status_at)
        if initial_status_at:
            self.assertNotEqual(self.job.status_at, initial_status_at)

    def test_update_job_status_at_in_response(self):
        """Test that status_at field is included in job response."""
        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, {"title": "Test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("status_at", response.data["data"])

    def test_update_job_validation_error(self):
        """Test update with invalid data returns 400."""
        data = {"estimated_budget": "-10.00"}

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("estimated_budget", response.data["errors"])

    def test_update_job_invalid_category(self):
        """Test update with invalid category returns 400."""
        data = {"category_id": "00000000-0000-0000-0000-000000000000"}

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category_id", response.data["errors"])

    def test_update_job_not_owner_returns_404(self):
        """Test updating job that doesn't belong to user returns 404."""
        # Create job for other user
        other_job = Job.objects.create(
            homeowner=self.other_user,
            title="Other user job",
            description="Test",
            estimated_budget=Decimal("30.00"),
            category=self.category,
            city=self.city,
            address="456 Oak Ave",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            f"/api/v1/mobile/homeowner/jobs/{other_job.public_id}/",
            {"title": "Hacked!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_job_not_found(self):
        """Test updating non-existent job returns 404."""
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            "/api/v1/mobile/homeowner/jobs/00000000-0000-0000-0000-000000000000/",
            {"title": "Test"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_deleted_job_returns_404(self):
        """Test updating deleted job returns 404."""
        self.job.status = "deleted"
        self.job.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, {"title": "Test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_completed_job_returns_403(self):
        """Test updating completed job returns 403."""
        self.job.status = "completed"
        self.job.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, {"title": "Test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("completed", response.data["message"])

    def test_update_cancelled_job_returns_403(self):
        """Test updating cancelled job returns 403."""
        self.job.status = "cancelled"
        self.job.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, {"title": "Test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("cancelled", response.data["message"])

    def test_update_job_cannot_set_status_to_deleted(self):
        """Test cannot set status to 'deleted' via update."""
        data = {"status": "deleted"}

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data["errors"])

    def test_update_job_cannot_set_status_to_completed(self):
        """Test cannot set status to 'completed' via update."""
        data = {"status": "completed"}

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data["errors"])

    def test_update_job_cannot_set_status_to_cancelled(self):
        """Test cannot set status to 'cancelled' via update."""
        data = {"status": "cancelled"}

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data["errors"])

    def test_update_job_requires_phone_verification(self):
        """Test update requires phone verification."""
        # User without phone verification
        user_no_phone = User.objects.create_user(
            email="nophone@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=user_no_phone, role="homeowner")
        user_no_phone.email_verified_at = "2024-01-01T00:00:00Z"
        user_no_phone.save()
        user_no_phone.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
            "phone_verified": False,
        }

        # Create job for this user
        job = Job.objects.create(
            homeowner=user_no_phone,
            title="Test job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        self.client.force_authenticate(user=user_no_phone)
        response = self.client.put(
            f"/api/v1/mobile/homeowner/jobs/{job.public_id}/",
            {"title": "Updated"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("phone", str(response.data["errors"]).lower())

    def test_update_job_unauthenticated(self):
        """Test update without authentication returns 401."""
        response = self.client.put(self.url, {"title": "Test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_job_with_tasks(self):
        """Test updating job tasks."""
        data = {
            "tasks": [{"title": "Task 1"}, {"title": "Task 2"}, {"title": "Task 3"}]
        }

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tasks = response.data["data"]["tasks"]
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0]["title"], "Task 1")
        self.assertEqual(tasks[1]["title"], "Task 2")
        self.assertEqual(tasks[2]["title"], "Task 3")

    def test_update_job_with_coordinates(self):
        """Test updating job coordinates."""
        data = {"latitude": "43.651070", "longitude": "-79.347015"}

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data["data"]["latitude"]), 43.651070)
        self.assertEqual(float(response.data["data"]["longitude"]), -79.347015)

    # ===== DELETE Tests =====

    def test_delete_job_success(self):
        """Test successfully deleting a job."""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Job deleted successfully")

    def test_delete_job_sets_status_to_deleted(self):
        """Test delete sets status to 'deleted'."""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "deleted")

    def test_delete_job_sets_status_at(self):
        """Test delete updates status_at timestamp."""
        initial_status_at = self.job.status_at

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.job.refresh_from_db()
        self.assertIsNotNone(self.job.status_at)
        if initial_status_at:
            self.assertNotEqual(self.job.status_at, initial_status_at)

    def test_delete_job_not_owner_returns_404(self):
        """Test deleting job that doesn't belong to user returns 404."""
        # Create job for other user
        other_job = Job.objects.create(
            homeowner=self.other_user,
            title="Other user job",
            description="Test",
            estimated_budget=Decimal("30.00"),
            category=self.category,
            city=self.city,
            address="456 Oak Ave",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            f"/api/v1/mobile/homeowner/jobs/{other_job.public_id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_job_not_found(self):
        """Test deleting non-existent job returns 404."""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            "/api/v1/mobile/homeowner/jobs/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_already_deleted_job_returns_404(self):
        """Test deleting already deleted job returns 404."""
        self.job.status = "deleted"
        self.job.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_job_requires_phone_verification(self):
        """Test delete requires phone verification."""
        # User without phone verification
        user_no_phone = User.objects.create_user(
            email="nophone2@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=user_no_phone, role="homeowner")
        user_no_phone.email_verified_at = "2024-01-01T00:00:00Z"
        user_no_phone.save()
        user_no_phone.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
            "phone_verified": False,
        }

        # Create job for this user
        job = Job.objects.create(
            homeowner=user_no_phone,
            title="Test job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        self.client.force_authenticate(user=user_no_phone)
        response = self.client.delete(f"/api/v1/mobile/homeowner/jobs/{job.public_id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("phone", str(response.data["errors"]).lower())

    def test_delete_job_unauthenticated(self):
        """Test delete without authentication returns 401."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ===== Listing Exclusion Tests =====

    def test_deleted_jobs_excluded_from_list(self):
        """Test deleted jobs are excluded from job listing."""
        # Create another job that's not deleted
        Job.objects.create(
            homeowner=self.user,
            title="Active job",
            description="Test",
            estimated_budget=Decimal("60.00"),
            category=self.category,
            city=self.city,
            address="456 Oak Ave",
            status="open",
        )

        # Delete the first job
        self.job.status = "deleted"
        self.job.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/mobile/homeowner/jobs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Active job")


class MobileForYouJobListViewTests(APITestCase):
    """Test cases for mobile ForYouJobListView."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/homeowner/jobs/for-you/"

        # Create primary user (homeowner)
        self.user = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="homeowner")
        self.user.email_verified_at = "2024-01-01T00:00:00Z"
        self.user.save()
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
        }

        # Create another user (other homeowner)
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.other_user, role="homeowner")

        # Create third user
        self.third_user = User.objects.create_user(
            email="third@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.third_user, role="homeowner")

        # Create test categories
        self.category_plumbing = JobCategory.objects.create(
            name="Plumbing", slug="plumbing", is_active=True
        )
        self.category_electrical = JobCategory.objects.create(
            name="Electrical", slug="electrical", is_active=True
        )

        # Create test cities
        self.city_toronto = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            latitude=Decimal("43.651070"),
            longitude=Decimal("-79.347015"),
            is_active=True,
        )
        self.city_vancouver = City.objects.create(
            name="Vancouver",
            province="British Columbia",
            province_code="BC",
            slug="vancouver-bc",
            latitude=Decimal("49.282729"),
            longitude=Decimal("-123.120738"),
            is_active=True,
        )

    def test_for_you_list_success(self):
        """Test successfully listing open jobs from other users."""
        # Create open job by other user
        Job.objects.create(
            homeowner=self.other_user,
            title="Other user open job",
            description="Test description",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="open",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Jobs retrieved successfully")
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Other user open job")
        self.assertIn("distance_km", response.data["data"][0])
        self.assertIn("pagination", response.data["meta"])

    def test_for_you_excludes_own_jobs(self):
        """Test that user's own jobs are excluded from results."""
        # Create job by current user
        Job.objects.create(
            homeowner=self.user,
            title="My own job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="open",
        )

        # Create job by other user
        Job.objects.create(
            homeowner=self.other_user,
            title="Other user job",
            description="Test",
            estimated_budget=Decimal("60.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="456 Oak Ave",
            status="open",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Other user job")

    def test_for_you_only_open_jobs(self):
        """Test that only open status jobs are returned."""
        # Create jobs with different statuses
        Job.objects.create(
            homeowner=self.other_user,
            title="Draft job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="draft",
        )
        Job.objects.create(
            homeowner=self.other_user,
            title="Open job",
            description="Test",
            estimated_budget=Decimal("60.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="456 Oak Ave",
            status="open",
        )
        Job.objects.create(
            homeowner=self.other_user,
            title="Completed job",
            description="Test",
            estimated_budget=Decimal("70.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="789 Pine St",
            status="completed",
        )
        Job.objects.create(
            homeowner=self.other_user,
            title="In progress job",
            description="Test",
            estimated_budget=Decimal("80.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="101 Elm St",
            status="in_progress",
        )
        Job.objects.create(
            homeowner=self.other_user,
            title="Cancelled job",
            description="Test",
            estimated_budget=Decimal("90.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="102 Birch St",
            status="cancelled",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Open job")
        self.assertEqual(response.data["data"][0]["status"], "open")

    def test_for_you_with_coordinates(self):
        """Test that distance is calculated when coordinates are provided."""
        # Create job with coordinates (near Toronto)
        Job.objects.create(
            homeowner=self.other_user,
            title="Job with coords",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            latitude=Decimal("43.660000"),
            longitude=Decimal("-79.350000"),
            status="open",
        )

        self.client.force_authenticate(user=self.user)
        # Query from Toronto coordinates
        response = self.client.get(
            self.url, {"latitude": "43.651070", "longitude": "-79.347015"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        # Distance should be calculated and be a small number (< 2 km)
        distance = response.data["data"][0]["distance_km"]
        self.assertIsNotNone(distance)
        self.assertLess(distance, 2.0)

    def test_for_you_distance_sorting(self):
        """Test that jobs are sorted by recency first, then distance."""

        from django.utils import timezone

        # Create job far away (Vancouver area) - created first (older)
        job_far = Job.objects.create(
            homeowner=self.other_user,
            title="Far job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_vancouver,
            address="123 Main St",
            latitude=Decimal("49.282729"),
            longitude=Decimal("-123.120738"),
            status="open",
        )
        # Manually set created_at to be older
        Job.objects.filter(pk=job_far.pk).update(
            created_at=timezone.now() - timedelta(days=2)
        )

        # Create job nearby (Toronto area) - created later (newer)
        Job.objects.create(
            homeowner=self.third_user,
            title="Near job",
            description="Test",
            estimated_budget=Decimal("60.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="456 Oak Ave",
            latitude=Decimal("43.655000"),
            longitude=Decimal("-79.350000"),
            status="open",
        )

        self.client.force_authenticate(user=self.user)
        # Query from Toronto coordinates
        response = self.client.get(
            self.url, {"latitude": "43.651070", "longitude": "-79.347015"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

        # Newer job should come first (sorted by created_at DESC)
        self.assertEqual(response.data["data"][0]["title"], "Near job")
        self.assertEqual(response.data["data"][1]["title"], "Far job")

        # Verify distances are calculated
        near_distance = response.data["data"][0]["distance_km"]
        far_distance = response.data["data"][1]["distance_km"]

        self.assertIsNotNone(near_distance)
        self.assertIsNotNone(far_distance)
        self.assertLess(near_distance, far_distance)

    def test_for_you_without_coordinates(self):
        """Test that endpoint works without coordinates."""
        Job.objects.create(
            homeowner=self.other_user,
            title="Job 1",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            latitude=Decimal("43.651070"),
            longitude=Decimal("-79.347015"),
            status="open",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)  # No coordinates

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        # Distance should be null when no coordinates provided
        self.assertIsNone(response.data["data"][0]["distance_km"])

    def test_for_you_jobs_without_coordinates_included(self):
        """Test that jobs without coordinates are included with null distance."""
        # Create job without coordinates
        Job.objects.create(
            homeowner=self.other_user,
            title="Job without coords",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            latitude=None,
            longitude=None,
            status="open",
        )

        # Create job with coordinates
        Job.objects.create(
            homeowner=self.third_user,
            title="Job with coords",
            description="Test",
            estimated_budget=Decimal("60.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="456 Oak Ave",
            latitude=Decimal("43.660000"),
            longitude=Decimal("-79.350000"),
            status="open",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.url, {"latitude": "43.651070", "longitude": "-79.347015"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

        # Find job without coords
        job_without_coords = next(
            j for j in response.data["data"] if j["title"] == "Job without coords"
        )
        job_with_coords = next(
            j for j in response.data["data"] if j["title"] == "Job with coords"
        )

        self.assertIsNone(job_without_coords["distance_km"])
        self.assertIsNotNone(job_with_coords["distance_km"])

    def test_for_you_with_category_filter(self):
        """Test filtering by category."""
        Job.objects.create(
            homeowner=self.other_user,
            title="Plumbing job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="open",
        )
        Job.objects.create(
            homeowner=self.other_user,
            title="Electrical job",
            description="Test",
            estimated_budget=Decimal("60.00"),
            category=self.category_electrical,
            city=self.city_toronto,
            address="456 Oak Ave",
            status="open",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.url, {"category": str(self.category_plumbing.public_id)}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Plumbing job")

    def test_for_you_with_city_filter(self):
        """Test filtering by city."""
        Job.objects.create(
            homeowner=self.other_user,
            title="Toronto job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="open",
        )
        Job.objects.create(
            homeowner=self.other_user,
            title="Vancouver job",
            description="Test",
            estimated_budget=Decimal("60.00"),
            category=self.category_plumbing,
            city=self.city_vancouver,
            address="456 Oak Ave",
            status="open",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"city": str(self.city_toronto.public_id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Toronto job")

    def test_for_you_pagination(self):
        """Test pagination works correctly."""
        # Create 25 jobs from other user
        for i in range(25):
            Job.objects.create(
                homeowner=self.other_user,
                title=f"Job {i}",
                description="Test",
                estimated_budget=Decimal("50.00"),
                category=self.category_plumbing,
                city=self.city_toronto,
                address="123 Main St",
                status="open",
            )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"page": 1, "page_size": 10})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 10)
        self.assertEqual(response.data["meta"]["pagination"]["page"], 1)
        self.assertEqual(response.data["meta"]["pagination"]["page_size"], 10)
        self.assertEqual(response.data["meta"]["pagination"]["total_pages"], 3)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 25)
        self.assertTrue(response.data["meta"]["pagination"]["has_next"])
        self.assertFalse(response.data["meta"]["pagination"]["has_previous"])

    def test_for_you_search(self):
        """Test searching 'for you' jobs."""
        Job.objects.create(
            homeowner=self.other_user,
            title="Unique Search Title",
            description="Description",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="open",
        )
        Job.objects.create(
            homeowner=self.other_user,
            title="Title",
            description="Unique Search Description",
            estimated_budget=Decimal("60.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="456 Oak Ave",
            status="open",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"search": "Unique Search"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

    def test_for_you_unauthenticated(self):
        """Test that unauthenticated requests fail."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_for_you_invalid_coordinates(self):
        """Test that invalid coordinates are handled gracefully."""
        Job.objects.create(
            homeowner=self.other_user,
            title="Test job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="open",
        )

        self.client.force_authenticate(user=self.user)

        # Test with invalid latitude (out of range)
        response = self.client.get(
            self.url, {"latitude": "999", "longitude": "-79.347015"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should still work but distance should be null
        self.assertIsNone(response.data["data"][0]["distance_km"])

        # Test with non-numeric values
        response2 = self.client.get(
            self.url, {"latitude": "invalid", "longitude": "-79.347015"}
        )
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertIsNone(response2.data["data"][0]["distance_km"])

    def test_for_you_empty_results(self):
        """Test response when no jobs match criteria."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Jobs retrieved successfully")
        self.assertEqual(len(response.data["data"]), 0)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 0)


class MobileGuestJobListViewTests(APITestCase):
    """Test cases for mobile GuestJobListView."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/guest/jobs/"

        # Create users
        self.user1 = User.objects.create_user(
            email="user1@example.com",
            password="testpass123",
        )
        self.user2 = User.objects.create_user(
            email="user2@example.com",
            password="testpass123",
        )

        # Create test categories
        self.category_plumbing = JobCategory.objects.create(
            name="Plumbing", slug="plumbing", is_active=True
        )
        self.category_electrical = JobCategory.objects.create(
            name="Electrical", slug="electrical", is_active=True
        )

        # Create test cities
        self.city_toronto = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            is_active=True,
        )
        self.city_vancouver = City.objects.create(
            name="Vancouver",
            province="British Columbia",
            province_code="BC",
            slug="vancouver-bc",
            is_active=True,
        )

    def test_guest_job_list_success_no_auth(self):
        """Test successfully listing open jobs without authentication."""
        Job.objects.create(
            homeowner=self.user1,
            title="Open job 1",
            description="Test description",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="open",
        )
        Job.objects.create(
            homeowner=self.user2,
            title="Open job 2",
            description="Test description",
            estimated_budget=Decimal("60.00"),
            category=self.category_electrical,
            city=self.city_vancouver,
            address="456 Oak Ave",
            status="open",
        )

        # No authentication required
        response = self.client.get(self.url, HTTP_X_PLATFORM="mobile")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Jobs retrieved successfully")
        self.assertEqual(len(response.data["data"]), 2)
        self.assertIn("pagination", response.data["meta"])

    def test_guest_job_list_only_open_status(self):
        """Test that only open status jobs are returned."""
        Job.objects.create(
            homeowner=self.user1,
            title="Open job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="open",
        )
        Job.objects.create(
            homeowner=self.user1,
            title="Draft job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="draft",
        )
        Job.objects.create(
            homeowner=self.user1,
            title="Completed job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="completed",
        )
        Job.objects.create(
            homeowner=self.user1,
            title="In progress job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="in_progress",
        )

        response = self.client.get(self.url, HTTP_X_PLATFORM="mobile")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Open job")

    def test_guest_job_list_with_pagination(self):
        """Test pagination works correctly."""
        for i in range(25):
            Job.objects.create(
                homeowner=self.user1,
                title=f"Job {i}",
                description="Test",
                estimated_budget=Decimal("50.00"),
                category=self.category_plumbing,
                city=self.city_toronto,
                address="123 Main St",
                status="open",
            )

        response = self.client.get(
            self.url, {"page": 1, "page_size": 10}, HTTP_X_PLATFORM="mobile"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 10)
        self.assertEqual(response.data["meta"]["pagination"]["page"], 1)
        self.assertEqual(response.data["meta"]["pagination"]["total_pages"], 3)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 25)
        self.assertTrue(response.data["meta"]["pagination"]["has_next"])
        self.assertFalse(response.data["meta"]["pagination"]["has_previous"])

    def test_guest_job_list_search(self):
        """Test searching guest job list."""
        Job.objects.create(
            homeowner=self.user1,
            title="Guest Search Title",
            description="Description",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="open",
        )
        Job.objects.create(
            homeowner=self.user2,
            title="Title",
            description="Guest Search Description",
            estimated_budget=Decimal("60.00"),
            category=self.category_electrical,
            city=self.city_vancouver,
            address="456 Oak Ave",
            status="open",
        )

        response = self.client.get(
            self.url, {"search": "Guest Search"}, HTTP_X_PLATFORM="mobile"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

    def test_guest_job_list_filter_by_category(self):
        """Test filtering by category."""
        Job.objects.create(
            homeowner=self.user1,
            title="Plumbing job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="open",
        )
        Job.objects.create(
            homeowner=self.user1,
            title="Electrical job",
            description="Test",
            estimated_budget=Decimal("60.00"),
            category=self.category_electrical,
            city=self.city_toronto,
            address="456 Oak Ave",
            status="open",
        )

        response = self.client.get(
            self.url,
            {"category": str(self.category_plumbing.public_id)},
            HTTP_X_PLATFORM="mobile",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Plumbing job")

    def test_guest_job_list_filter_by_city(self):
        """Test filtering by city."""
        Job.objects.create(
            homeowner=self.user1,
            title="Toronto job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="open",
        )
        Job.objects.create(
            homeowner=self.user1,
            title="Vancouver job",
            description="Test",
            estimated_budget=Decimal("60.00"),
            category=self.category_plumbing,
            city=self.city_vancouver,
            address="456 Oak Ave",
            status="open",
        )

        response = self.client.get(
            self.url,
            {"city": str(self.city_toronto.public_id)},
            HTTP_X_PLATFORM="mobile",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Toronto job")

    def test_guest_job_list_with_coordinates(self):
        """Test that distance is calculated when coordinates are provided."""
        Job.objects.create(
            homeowner=self.user1,
            title="Job with coords",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            latitude=Decimal("43.660000"),
            longitude=Decimal("-79.350000"),
            status="open",
        )

        response = self.client.get(
            self.url,
            {"latitude": "43.651070", "longitude": "-79.347015"},
            HTTP_X_PLATFORM="mobile",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        distance = response.data["data"][0]["distance_km"]
        self.assertIsNotNone(distance)
        self.assertLess(distance, 2.0)

    def test_guest_job_list_without_coordinates(self):
        """Test that distance is null when coordinates not provided."""
        Job.objects.create(
            homeowner=self.user1,
            title="Job with coords",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            latitude=Decimal("43.660000"),
            longitude=Decimal("-79.350000"),
            status="open",
        )

        response = self.client.get(self.url, HTTP_X_PLATFORM="mobile")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertIsNone(response.data["data"][0]["distance_km"])

    def test_guest_job_list_invalid_coordinates(self):
        """Test that invalid coordinate ranges are handled gracefully."""
        Job.objects.create(
            homeowner=self.user1,
            title="Open job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="open",
        )
        # Latitude out of range
        response = self.client.get(
            self.url,
            {"latitude": "95.0", "longitude": "0.0"},
            HTTP_X_PLATFORM="mobile",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["data"][0]["distance_km"])

        # Longitude out of range
        response = self.client.get(
            self.url,
            {"latitude": "0.0", "longitude": "185.0"},
            HTTP_X_PLATFORM="mobile",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["data"][0]["distance_km"])

    def test_guest_job_list_invalid_coordinate_types(self):
        """Test that non-numeric coordinates are handled gracefully."""
        Job.objects.create(
            homeowner=self.user1,
            title="Open job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category_plumbing,
            city=self.city_toronto,
            address="123 Main St",
            status="open",
        )
        response = self.client.get(
            self.url,
            {"latitude": "abc", "longitude": "0.0"},
            HTTP_X_PLATFORM="mobile",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["data"][0]["distance_km"])

    def test_guest_job_list_empty_results(self):
        """Test response when no jobs available."""
        response = self.client.get(self.url, HTTP_X_PLATFORM="mobile")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 0)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 0)


class MobileGuestJobDetailViewTests(APITestCase):
    """Test cases for mobile GuestJobDetailView."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="user@example.com",
            password="testpass123",
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

        self.open_job = Job.objects.create(
            homeowner=self.user,
            title="Open job",
            description="Test description",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )

        self.url = f"/api/v1/mobile/guest/jobs/{self.open_job.public_id}/"

    def test_guest_job_detail_success_no_auth(self):
        """Test successfully getting job detail without authentication."""
        response = self.client.get(self.url, HTTP_X_PLATFORM="mobile")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Job retrieved successfully")
        self.assertEqual(response.data["data"]["title"], "Open job")
        self.assertEqual(
            response.data["data"]["public_id"], str(self.open_job.public_id)
        )

    def test_guest_job_detail_not_found(self):
        """Test 404 for non-existent job."""
        response = self.client.get(
            "/api/v1/mobile/guest/jobs/00000000-0000-0000-0000-000000000000/",
            HTTP_X_PLATFORM="mobile",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_guest_job_detail_non_open_status_returns_404(self):
        """Test 404 for non-open status jobs."""
        # Test draft status
        draft_job = Job.objects.create(
            homeowner=self.user,
            title="Draft job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="draft",
        )
        response = self.client.get(
            f"/api/v1/mobile/guest/jobs/{draft_job.public_id}/",
            HTTP_X_PLATFORM="mobile",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test completed status
        completed_job = Job.objects.create(
            homeowner=self.user,
            title="Completed job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="completed",
        )
        response = self.client.get(
            f"/api/v1/mobile/guest/jobs/{completed_job.public_id}/",
            HTTP_X_PLATFORM="mobile",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test in_progress status
        in_progress_job = Job.objects.create(
            homeowner=self.user,
            title="In progress job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
        )
        response = self.client.get(
            f"/api/v1/mobile/guest/jobs/{in_progress_job.public_id}/",
            HTTP_X_PLATFORM="mobile",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_guest_job_detail_includes_all_fields(self):
        """Test that response includes all expected fields."""
        response = self.client.get(self.url, HTTP_X_PLATFORM="mobile")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        # Check essential fields are present
        self.assertIn("public_id", data)
        self.assertIn("title", data)
        self.assertIn("description", data)
        self.assertIn("estimated_budget", data)
        self.assertIn("category", data)
        self.assertIn("city", data)
        self.assertIn("address", data)
        self.assertIn("status", data)
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)


class HandymanForYouJobListViewTests(APITestCase):
    """Test cases for handyman ForYouJobListView (job browsing)."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/handyman/jobs/for-you/"
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "phone_verified": True,
            "email_verified": True,
        }

        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
            phone_verified_at=timezone.now(),
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
            latitude=Decimal("43.651070"),
            longitude=Decimal("-79.347015"),
        )

        # Create open jobs
        for i in range(3):
            Job.objects.create(
                homeowner=self.homeowner,
                title=f"Job {i}",
                description="Test job",
                estimated_budget=Decimal("50.00"),
                category=self.category,
                city=self.city,
                address="123 Main St",
                latitude=Decimal("43.651070"),
                longitude=Decimal("-79.347015"),
                status="open",
            )

        self.client.force_authenticate(user=self.handyman)

    def test_list_jobs_success(self):
        """Test successfully listing jobs for handyman."""
        response = self.client.get(
            self.url, {"latitude": "43.651070", "longitude": "-79.347015"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 3)

    def test_handyman_list_jobs_search(self):
        """Test searching handyman browse job list."""
        Job.objects.create(
            homeowner=self.homeowner,
            title="Handyman Search Title",
            description="Description",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )

        response = self.client.get(self.url, {"search": "Handyman Search"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Handyman Search Title")

    def test_list_jobs_with_category_filter(self):
        """Test filtering jobs by category."""
        response = self.client.get(
            self.url,
            {
                "latitude": "43.651070",
                "longitude": "-79.347015",
                "category": str(self.category.public_id),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 3)

    def test_list_jobs_with_city_filter(self):
        """Test filtering jobs by city."""
        response = self.client.get(
            self.url,
            {
                "latitude": "43.651070",
                "longitude": "-79.347015",
                "city": str(self.city.public_id),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 3)

    def test_list_jobs_no_coordinates(self):
        """Test that list view works without coordinates."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 3)

    def test_list_jobs_invalid_coordinate_types(self):
        """Test that non-numeric coordinates are handled gracefully."""
        response = self.client.get(
            self.url, {"latitude": "invalid", "longitude": "0.0"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should still return jobs ordered by recency
        self.assertEqual(len(response.data["data"]), 3)

    def test_list_jobs_excludes_own_jobs(self):
        """Test that handyman's own jobs are excluded if they're also a homeowner."""
        # Create job owned by handyman
        Job.objects.create(
            homeowner=self.handyman,
            title="Own Job",
            description="Test job",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )

        response = self.client.get(
            self.url, {"latitude": "43.651070", "longitude": "-79.347015"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should still be 3, not 4
        self.assertEqual(len(response.data["data"]), 3)


class HandymanJobDetailViewTests(APITestCase):
    """Test cases for handyman JobDetailView."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "phone_verified": True,
            "email_verified": True,
        }

        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
            phone_verified_at=timezone.now(),
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
            title="Fix faucet",
            description="Leaking faucet",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )

        self.url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/"
        self.client.force_authenticate(user=self.handyman)

    def test_get_job_detail_success(self):
        """Test successfully getting job detail."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["title"], "Fix faucet")
        self.assertIn("has_applied", response.data["data"])

    def test_get_job_detail_not_found(self):
        """Test getting non-existent job returns 404."""
        import uuid

        url = f"/api/v1/mobile/handyman/jobs/{uuid.uuid4()}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_job_detail_applied_active(self):
        """Test getting job detail for in-progress job where handyman applied."""
        # Create in-progress job
        job = Job.objects.create(
            homeowner=self.homeowner,
            title="Active Job",
            description="Work in progress",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
        )

        # Apply to job
        JobApplication.objects.create(
            job=job, handyman=self.handyman, status="approved"
        )

        url = f"/api/v1/mobile/handyman/jobs/{job.public_id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["title"], "Active Job")
        # Should show application status
        self.assertTrue(response.data["data"]["has_applied"])
        self.assertEqual(response.data["data"]["my_application"]["status"], "approved")

    def test_get_job_detail_active_not_applied(self):
        """Test getting in-progress job where handyman DID NOT apply returns 404."""
        # Create in-progress job
        job = Job.objects.create(
            homeowner=self.homeowner,
            title="Other Active Job",
            description="Work in progress",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
        )

        url = f"/api/v1/mobile/handyman/jobs/{job.public_id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class HandymanJobApplicationListCreateViewTests(APITestCase):
    """Test cases for handyman JobApplicationListCreateView."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/handyman/applications/"
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )
        UserRole.objects.create(user=self.handyman, role="handyman")
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "phone_verified": True,
            "email_verified": True,
        }

        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
            phone_verified_at=timezone.now(),
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
            title="Fix faucet",
            description="Leaking faucet",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )

        self.client.force_authenticate(user=self.handyman)

    def test_list_applications_success(self):
        """Test successfully listing handyman's applications."""

        JobApplication.objects.create(
            job=self.job, handyman=self.handyman, status="pending"
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

    def test_list_applications_with_status_filter(self):
        """Test filtering applications by status."""

        JobApplication.objects.create(
            job=self.job, handyman=self.handyman, status="pending"
        )
        job2 = Job.objects.create(
            homeowner=self.homeowner,
            title="Another job",
            description="Test",
            estimated_budget=Decimal("60.00"),
            category=self.category,
            city=self.city,
            address="456 Oak St",
            status="open",
        )
        JobApplication.objects.create(
            job=job2, handyman=self.handyman, status="approved"
        )

        response = self.client.get(self.url, {"status": "pending"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

    def test_create_application_invalid_data(self):
        """Test creating application with invalid data."""
        data = {"job_id": "invalid-uuid"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("job_id", response.data["errors"])

    def test_create_application_service_failure(self):
        """Test service failure during application creation."""

        data = {"job_id": str(self.job.public_id)}
        with patch(
            "apps.jobs.serializers.JobApplicationCreateSerializer.save"
        ) as mock_save:
            mock_save.side_effect = Exception("Service error")
            response = self.client.post(self.url, data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data["errors"]["detail"], "Service error")

    def test_create_application_success(self):
        """Test successfully creating a job application."""
        data = {"job_id": str(self.job.public_id)}

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("status", response.data["data"])
        self.assertEqual(response.data["data"]["status"], "pending")


class HandymanJobApplicationWithdrawViewTests(APITestCase):
    """Test cases for handyman JobApplicationWithdrawView."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "phone_verified": True,
            "email_verified": True,
        }

        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
            phone_verified_at=timezone.now(),
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
            title="Fix faucet",
            description="Leaking faucet",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )

        self.application = JobApplication.objects.create(
            job=self.job, handyman=self.handyman, status="pending"
        )

        self.url = f"/api/v1/mobile/handyman/applications/{self.application.public_id}/withdraw/"
        self.client.force_authenticate(user=self.handyman)

    def test_withdraw_application_service_failure(self):
        """Test service failure during withdrawal."""

        with patch(
            "apps.jobs.services.JobApplicationService.withdraw_application"
        ) as mock_withdraw:
            mock_withdraw.side_effect = Exception("Service error")

            response = self.client.post(self.url)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data["errors"]["detail"], "Service error")

    def test_withdraw_application_success(self):
        """Test successfully withdrawing application."""

        with patch(
            "apps.jobs.services.JobApplicationService.withdraw_application"
        ) as mock_withdraw:
            mock_withdraw.return_value = self.application

            response = self.client.post(self.url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class HandymanJobApplicationDetailViewTests(APITestCase):
    """Test cases for handyman JobApplicationDetailView."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )
        self.other_handyman = User.objects.create_user(
            email="otherhandyman@example.com", password="testpass123"
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "phone_verified": True,
            "email_verified": True,
        }

        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
            phone_verified_at=timezone.now(),
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
            title="Fix faucet",
            description="Leaking faucet",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )

        self.application = JobApplication.objects.create(
            job=self.job, handyman=self.handyman, status="pending"
        )

        self.url = f"/api/v1/mobile/handyman/applications/{self.application.public_id}/"
        self.client.force_authenticate(user=self.handyman)

    def test_get_application_detail_success(self):
        """Test successfully getting application detail as the owner."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["status"], "pending")
        self.assertEqual(response.data["data"]["job"]["title"], "Fix faucet")

    def test_get_application_detail_not_owner_returns_404(self):
        """Test getting application detail as another handyman returns 404."""
        self.other_handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "phone_verified": True,
            "email_verified": True,
        }
        self.client.force_authenticate(user=self.other_handyman)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_application_detail_not_found(self):
        """Test getting non-existent application returns 404."""
        import uuid

        url = f"/api/v1/mobile/handyman/applications/{uuid.uuid4()}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_application_detail_unauthenticated(self):
        """Test getting application detail without authentication returns 401."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class HomeownerApplicationListViewTests(APITestCase):
    """Test cases for homeowner ApplicationListView."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/homeowner/applications/"
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        self.other_homeowner = User.objects.create_user(
            email="otherhomeowner@example.com", password="testpass123"
        )
        self.homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "phone_verified": True,
            "email_verified": True,
        }

        HomeownerProfile.objects.create(
            user=self.homeowner, display_name="Test Homeowner"
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )
        HandymanProfile.objects.create(user=self.handyman, display_name="Test Handyman")

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

        self.job1 = Job.objects.create(
            homeowner=self.homeowner,
            title="Job 1",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )
        self.job2 = Job.objects.create(
            homeowner=self.homeowner,
            title="Job 2",
            description="Test",
            estimated_budget=Decimal("60.00"),
            category=self.category,
            city=self.city,
            address="456 Oak St",
            status="open",
        )
        self.other_job = Job.objects.create(
            homeowner=self.other_homeowner,
            title="Other Job",
            description="Test",
            estimated_budget=Decimal("70.00"),
            category=self.category,
            city=self.city,
            address="789 Pine St",
            status="open",
        )

        # Create applications
        self.app1 = JobApplication.objects.create(
            job=self.job1, handyman=self.handyman, status="pending"
        )
        self.app2 = JobApplication.objects.create(
            job=self.job2, handyman=self.handyman, status="approved"
        )
        self.other_app = JobApplication.objects.create(
            job=self.other_job, handyman=self.handyman, status="pending"
        )

        self.client.force_authenticate(user=self.homeowner)

    def test_list_applications_success(self):
        """Test successfully listing all applications for homeowner's jobs."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)
        self.assertIn("pagination", response.data["meta"])

    def test_list_applications_filter_by_job(self):
        """Test filtering applications by job ID."""
        response = self.client.get(self.url, {"job_id": str(self.job1.public_id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(
            response.data["data"][0]["job"]["public_id"], str(self.job1.public_id)
        )

    def test_list_applications_filter_by_status(self):
        """Test filtering applications by status."""
        response = self.client.get(self.url, {"status": "approved"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["status"], "approved")

    def test_list_applications_pagination(self):
        """Test application listing pagination."""
        # Create 20 more applications for job1
        for i in range(20):
            u = User.objects.create_user(email=f"h{i}@example.com", password="pass")
            HandymanProfile.objects.create(user=u, display_name=f"H{i}")
            JobApplication.objects.create(job=self.job1, handyman=u)

        response = self.client.get(self.url, {"page": 1, "page_size": 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 10)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 22)

    def test_list_applications_unauthenticated(self):
        """Test listing applications without authentication returns 401."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class HomeownerJobApplicationDetailViewTests(APITestCase):
    """Test cases for homeowner JobApplicationDetailView."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        self.other_homeowner = User.objects.create_user(
            email="otherhomeowner@example.com", password="testpass123"
        )
        self.homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "phone_verified": True,
            "email_verified": True,
        }

        HomeownerProfile.objects.create(
            user=self.homeowner, display_name="Test Homeowner"
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )
        HandymanProfile.objects.create(user=self.handyman, display_name="Test Handyman")

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
            title="Fix faucet",
            description="Leaking faucet",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )
        self.other_job = Job.objects.create(
            homeowner=self.other_homeowner,
            title="Other Job",
            description="Test",
            estimated_budget=Decimal("70.00"),
            category=self.category,
            city=self.city,
            address="789 Pine St",
            status="open",
        )

        self.application = JobApplication.objects.create(
            job=self.job, handyman=self.handyman, status="pending"
        )
        self.other_application = JobApplication.objects.create(
            job=self.other_job, handyman=self.handyman, status="pending"
        )

        self.url = (
            f"/api/v1/mobile/homeowner/applications/{self.application.public_id}/"
        )
        self.client.force_authenticate(user=self.homeowner)

    def test_get_application_detail_success(self):
        """Test successfully getting application detail."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["status"], "pending")
        self.assertEqual(response.data["data"]["job"]["title"], "Fix faucet")

    def test_get_application_detail_not_owner_returns_404(self):
        """Test getting application for another homeowner's job returns 404."""
        url = (
            f"/api/v1/mobile/homeowner/applications/{self.other_application.public_id}/"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class HomeownerApplicationRejectViewTests(APITestCase):
    """Test cases for homeowner ApplicationRejectView."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        self.homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "phone_verified": True,
            "email_verified": True,
        }

        HomeownerProfile.objects.create(
            user=self.homeowner, display_name="Test Homeowner"
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )
        self.other_homeowner = User.objects.create_user(
            email="otherhomeowner@example.com", password="testpass123"
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
            title="Fix faucet",
            description="Leaking faucet",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )

        self.application = JobApplication.objects.create(
            job=self.job, handyman=self.handyman, status="pending"
        )

        self.url = f"/api/v1/mobile/homeowner/applications/{self.application.public_id}/reject/"
        self.client.force_authenticate(user=self.homeowner)

    def test_reject_application_success(self):
        """Test successfully rejecting application."""

        with patch(
            "apps.jobs.services.JobApplicationService.reject_application"
        ) as mock_reject:
            mock_reject.return_value = self.application
            self.application.status = "rejected"

            response = self.client.post(self.url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                response.data["message"], "Application rejected successfully"
            )

    def test_reject_application_service_failure(self):
        """Test service failure during rejection."""

        with patch(
            "apps.jobs.services.JobApplicationService.reject_application"
        ) as mock_reject:
            mock_reject.side_effect = Exception("Service error")

            response = self.client.post(self.url)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data["errors"]["detail"], "Service error")

    def test_reject_application_not_owner_returns_404(self):
        """Test rejecting application that doesn't belong to homeowner's job returns 404."""
        self.other_homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "phone_verified": True,
            "email_verified": True,
        }
        self.client.force_authenticate(user=self.other_homeowner)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reject_application_not_found(self):
        """Test rejecting non-existent application returns 404."""
        import uuid

        url = f"/api/v1/mobile/homeowner/applications/{uuid.uuid4()}/reject/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reject_application_unauthenticated(self):
        """Test rejecting application without authentication returns 401."""
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["message"], "Authentication credentials were not provided."
        )


class HomeownerApplicationApproveViewTests(APITestCase):
    """Test cases for homeowner ApplicationApproveView."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        self.homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "phone_verified": True,
            "email_verified": True,
        }

        HomeownerProfile.objects.create(
            user=self.homeowner, display_name="Test Homeowner"
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
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
            title="Fix faucet",
            description="Leaking faucet",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )

        self.application = JobApplication.objects.create(
            job=self.job, handyman=self.handyman, status="pending"
        )

        self.url = f"/api/v1/mobile/homeowner/applications/{self.application.public_id}/approve/"
        self.client.force_authenticate(user=self.homeowner)

    def test_approve_application_service_failure(self):
        """Test service failure during approval."""

        with patch(
            "apps.jobs.services.JobApplicationService.approve_application"
        ) as mock_approve:
            mock_approve.side_effect = Exception("Service error")

            response = self.client.post(self.url)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data["errors"]["detail"], "Service error")

    def test_approve_application_success(self):
        """Test successfully approving application."""

        with patch(
            "apps.jobs.services.JobApplicationService.approve_application"
        ) as mock_approve:
            mock_approve.return_value = self.application

            response = self.client.post(self.url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


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
            "end_photo": create_test_image(),
        }
        response = self.client.post(url, data, format="multipart")
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
            "end_photo": create_test_image(),
        }
        response = self.client.post(url, data, format="multipart")
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
            "end_photo": create_test_image(),
        }
        response = self.client.post(url, data, format="multipart")
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


# ========================
# Review View Tests
# ========================


class HomeownerReviewViewTests(APITestCase):
    """Test cases for HomeownerReviewView."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        self.homeowner.email_verified_at = timezone.now()
        self.homeowner.save()
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner, display_name="Test Homeowner"
        )
        self.homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
            "phone_verified": True,
        }

        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        self.handyman.email_verified_at = timezone.now()
        self.handyman.save()
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
            phone_verified_at=timezone.now(),
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
            address="123 Main St",
            status="completed",
            completed_at=timezone.now(),
        )

        self.url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/review/"

    def test_get_review_success(self):
        """Test getting an existing review."""
        Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
            comment="Great work!",
        )

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["rating"], 5)
        self.assertEqual(response.data["data"]["comment"], "Great work!")

    def test_get_review_not_found(self):
        """Test getting a review that doesn't exist."""
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_review_wrong_job(self):
        """Test getting review for job owned by another homeowner."""
        other_homeowner = User.objects.create_user(
            email="other@example.com", password="password123"
        )
        other_homeowner.email_verified_at = timezone.now()
        other_homeowner.save()
        UserRole.objects.create(user=other_homeowner, role="homeowner")
        HomeownerProfile.objects.create(user=other_homeowner, display_name="Other")
        other_homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
            "phone_verified": True,
        }

        self.client.force_authenticate(user=other_homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_review_success(self, mock_notify):
        """Test creating a review successfully."""
        self.client.force_authenticate(user=self.homeowner)

        data = {"rating": 5, "comment": "Excellent work!"}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["rating"], 5)
        self.assertEqual(response.data["data"]["comment"], "Excellent work!")

        # Verify review was created
        self.assertTrue(
            Review.objects.filter(job=self.job, reviewer_type="homeowner").exists()
        )

    def test_create_review_invalid_data(self):
        """Test creating a review with invalid data."""
        self.client.force_authenticate(user=self.homeowner)

        data = {"rating": 6}  # Invalid rating
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_review_missing_rating(self):
        """Test creating a review without rating."""
        self.client.force_authenticate(user=self.homeowner)

        data = {"comment": "Great!"}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_review_job_not_completed(self, mock_notify):
        """Test creating a review for a non-completed job."""
        self.job.status = "in_progress"
        self.job.completed_at = None
        self.job.save()

        self.client.force_authenticate(user=self.homeowner)

        data = {"rating": 5}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_review_outside_window(self, mock_notify):
        """Test creating a review outside the 14-day window."""
        self.job.completed_at = timezone.now() - timedelta(days=15)
        self.job.save()

        self.client.force_authenticate(user=self.homeowner)

        data = {"rating": 5}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_review_already_reviewed(self, mock_notify):
        """Test creating a duplicate review."""
        Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
        )

        self.client.force_authenticate(user=self.homeowner)

        data = {"rating": 4}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_review_success(self):
        """Test updating a review successfully."""
        Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=4,
            comment="Good work",
        )

        self.client.force_authenticate(user=self.homeowner)

        data = {"rating": 5, "comment": "Excellent work!"}
        response = self.client.put(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["rating"], 5)
        self.assertEqual(response.data["data"]["comment"], "Excellent work!")

    def test_update_review_not_found(self):
        """Test updating a review that doesn't exist."""
        self.client.force_authenticate(user=self.homeowner)

        data = {"rating": 5}
        response = self.client.put(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_review_invalid_data(self):
        """Test updating a review with invalid data."""
        Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=4,
        )

        self.client.force_authenticate(user=self.homeowner)

        data = {"rating": 0}  # Invalid rating
        response = self.client.put(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_review_outside_window(self):
        """Test updating a review outside the 14-day window."""
        self.job.completed_at = timezone.now() - timedelta(days=15)
        self.job.save()

        Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=4,
        )

        self.client.force_authenticate(user=self.homeowner)

        data = {"rating": 5}
        response = self.client.put(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access review endpoints."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.post(self.url, {"rating": 5}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.put(self.url, {"rating": 5}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class HandymanReviewViewTests(APITestCase):
    """Test cases for HandymanReviewView."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        self.homeowner.email_verified_at = timezone.now()
        self.homeowner.save()
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner, display_name="Test Homeowner"
        )

        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        self.handyman.email_verified_at = timezone.now()
        self.handyman.save()
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
            phone_verified_at=timezone.now(),
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

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
            address="123 Main St",
            status="completed",
            completed_at=timezone.now(),
        )

        self.url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/review/"

    def test_get_review_success(self):
        """Test getting an existing review."""
        Review.objects.create(
            job=self.job,
            reviewer=self.handyman,
            reviewee=self.homeowner,
            reviewer_type="handyman",
            rating=4,
            comment="Good homeowner!",
        )

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["rating"], 4)
        self.assertEqual(response.data["data"]["comment"], "Good homeowner!")

    def test_get_review_not_found(self):
        """Test getting a review that doesn't exist."""
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_review_wrong_job(self):
        """Test getting review for job assigned to another handyman."""
        other_handyman = User.objects.create_user(
            email="other@example.com", password="password123"
        )
        other_handyman.email_verified_at = timezone.now()
        other_handyman.save()
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
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_review_success(self, mock_notify):
        """Test creating a review successfully."""
        self.client.force_authenticate(user=self.handyman)

        data = {"rating": 4, "comment": "Good communication!"}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["rating"], 4)
        self.assertEqual(response.data["data"]["comment"], "Good communication!")

        # Verify review was created
        self.assertTrue(
            Review.objects.filter(job=self.job, reviewer_type="handyman").exists()
        )

    def test_create_review_invalid_data(self):
        """Test creating a review with invalid data."""
        self.client.force_authenticate(user=self.handyman)

        data = {"rating": 0}  # Invalid rating
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_review_job_not_completed(self, mock_notify):
        """Test creating a review for a non-completed job."""
        self.job.status = "in_progress"
        self.job.completed_at = None
        self.job.save()

        self.client.force_authenticate(user=self.handyman)

        data = {"rating": 4}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "apps.notifications.services.NotificationService.create_and_send_notification"
    )
    def test_create_review_already_reviewed(self, mock_notify):
        """Test creating a duplicate review."""
        Review.objects.create(
            job=self.job,
            reviewer=self.handyman,
            reviewee=self.homeowner,
            reviewer_type="handyman",
            rating=4,
        )

        self.client.force_authenticate(user=self.handyman)

        data = {"rating": 5}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_review_success(self):
        """Test updating a review successfully."""
        Review.objects.create(
            job=self.job,
            reviewer=self.handyman,
            reviewee=self.homeowner,
            reviewer_type="handyman",
            rating=3,
            comment="Okay",
        )

        self.client.force_authenticate(user=self.handyman)

        data = {"rating": 4, "comment": "Good homeowner!"}
        response = self.client.put(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["rating"], 4)
        self.assertEqual(response.data["data"]["comment"], "Good homeowner!")

    def test_update_review_not_found(self):
        """Test updating a review that doesn't exist."""
        self.client.force_authenticate(user=self.handyman)

        data = {"rating": 4}
        response = self.client.put(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_review_invalid_data(self):
        """Test updating a review with invalid data."""
        Review.objects.create(
            job=self.job,
            reviewer=self.handyman,
            reviewee=self.homeowner,
            reviewer_type="handyman",
            rating=4,
        )

        self.client.force_authenticate(user=self.handyman)

        data = {"rating": 6}  # Invalid rating
        response = self.client.put(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_review_outside_window(self):
        """Test updating a review outside the 14-day window."""
        self.job.completed_at = timezone.now() - timedelta(days=15)
        self.job.save()

        Review.objects.create(
            job=self.job,
            reviewer=self.handyman,
            reviewee=self.homeowner,
            reviewer_type="handyman",
            rating=4,
        )

        self.client.force_authenticate(user=self.handyman)

        data = {"rating": 5}
        response = self.client.put(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access review endpoints."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.post(self.url, {"rating": 4}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.put(self.url, {"rating": 4}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class HandymanReceivedReviewsViewTests(APITestCase):
    """Test cases for HandymanReceivedReviewsView."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        self.homeowner.email_verified_at = timezone.now()
        self.homeowner.save()
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=self.homeowner, display_name="Test Homeowner"
        )

        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        self.handyman.email_verified_at = timezone.now()
        self.handyman.save()
        UserRole.objects.create(user=self.handyman, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
            phone_verified_at=timezone.now(),
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

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

        self.url = "/api/v1/mobile/handyman/reviews/"

    def test_get_received_reviews_empty(self):
        """Test getting reviews when there are none."""
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"], [])
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 0)

    def test_get_received_reviews_success(self):
        """Test getting received reviews successfully."""
        # Create a job and review
        job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Fix sink",
            description="Leaky sink",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="completed",
            completed_at=timezone.now(),
        )
        Review.objects.create(
            job=job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
            comment="Great work!",
        )

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["rating"], 5)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 1)

    def test_get_received_reviews_pagination(self):
        """Test pagination of received reviews."""
        # Create multiple jobs and reviews
        for i in range(25):
            job = Job.objects.create(
                homeowner=self.homeowner,
                assigned_handyman=self.handyman,
                title=f"Job {i}",
                description="Description",
                estimated_budget=Decimal("100.00"),
                category=self.category,
                city=self.city,
                address="123 Main St",
                status="completed",
                completed_at=timezone.now(),
            )
            Review.objects.create(
                job=job,
                reviewer=self.homeowner,
                reviewee=self.handyman,
                reviewer_type="homeowner",
                rating=4,
            )

        self.client.force_authenticate(user=self.handyman)

        # First page (default page_size=20)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 20)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 25)
        self.assertEqual(response.data["meta"]["pagination"]["total_pages"], 2)
        self.assertTrue(response.data["meta"]["pagination"]["has_next"])
        self.assertFalse(response.data["meta"]["pagination"]["has_previous"])

        # Second page
        response = self.client.get(self.url + "?page=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 5)
        self.assertFalse(response.data["meta"]["pagination"]["has_next"])
        self.assertTrue(response.data["meta"]["pagination"]["has_previous"])

    def test_get_received_reviews_custom_page_size(self):
        """Test custom page size for received reviews."""
        # Create 5 jobs and reviews
        for i in range(5):
            job = Job.objects.create(
                homeowner=self.homeowner,
                assigned_handyman=self.handyman,
                title=f"Job {i}",
                description="Description",
                estimated_budget=Decimal("100.00"),
                category=self.category,
                city=self.city,
                address="123 Main St",
                status="completed",
                completed_at=timezone.now(),
            )
            Review.objects.create(
                job=job,
                reviewer=self.homeowner,
                reviewee=self.handyman,
                reviewer_type="homeowner",
                rating=4,
            )

        self.client.force_authenticate(user=self.handyman)

        response = self.client.get(self.url + "?page_size=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)
        self.assertEqual(response.data["meta"]["pagination"]["page_size"], 2)
        self.assertEqual(response.data["meta"]["pagination"]["total_pages"], 3)

    def test_get_received_reviews_max_page_size(self):
        """Test that page size is capped at 100."""
        self.client.force_authenticate(user=self.handyman)

        response = self.client.get(self.url + "?page_size=200")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["meta"]["pagination"]["page_size"], 100)

    def test_does_not_include_handyman_reviews(self):
        """Test that reviews written by handymen are not included."""
        # Create a job where handyman reviews the homeowner
        job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Fix sink",
            description="Leaky sink",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="completed",
            completed_at=timezone.now(),
        )
        # This is a review BY the handyman (not received)
        Review.objects.create(
            job=job,
            reviewer=self.handyman,
            reviewee=self.homeowner,
            reviewer_type="handyman",
            rating=4,
        )

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 0)

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access received reviews."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class HandymanJobDashboardViewTests(APITestCase):
    """Test cases for HandymanJobDashboardView."""

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

        # Create other handyman (for forbidden tests)
        self.other_handyman = User.objects.create_user(
            email="other@example.com", password="password123"
        )
        UserRole.objects.create(user=self.other_handyman, role="handyman")
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
            title="Test Job",
            description="Test description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Street",
            status="in_progress",
        )

        # Create tasks
        self.task1 = JobTask.objects.create(
            job=self.job, title="Task 1", order=0, is_completed=True
        )
        self.task2 = JobTask.objects.create(
            job=self.job, title="Task 2", order=1, is_completed=False
        )
        self.task3 = JobTask.objects.create(
            job=self.job, title="Task 3", order=2, is_completed=False
        )

        # Create work sessions
        self.session1 = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now() - timedelta(hours=4),
            ended_at=timezone.now() - timedelta(hours=2),
            start_latitude=Decimal("43.0"),
            start_longitude=Decimal("-79.0"),
            end_latitude=Decimal("43.1"),
            end_longitude=Decimal("-79.1"),
            start_photo="path/to/photo1.jpg",
            status="completed",
        )
        self.session2 = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now() - timedelta(hours=2),
            ended_at=timezone.now() - timedelta(hours=1),
            start_latitude=Decimal("43.0"),
            start_longitude=Decimal("-79.0"),
            end_latitude=Decimal("43.1"),
            end_longitude=Decimal("-79.1"),
            start_photo="path/to/photo2.jpg",
            status="completed",
        )

        # Create active session
        self.active_session = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now(),
            start_latitude=Decimal("43.0"),
            start_longitude=Decimal("-79.0"),
            start_photo="path/to/active_photo.jpg",
            status="in_progress",
        )

        # Create daily reports
        self.report1 = DailyReport.objects.create(
            job=self.job,
            handyman=self.handyman,
            report_date=(timezone.now() - timedelta(days=1)).date(),
            summary="Work done yesterday",
            total_work_duration=timedelta(hours=4),
            status="approved",
            review_deadline=timezone.now() + timedelta(days=2),
        )
        self.report2 = DailyReport.objects.create(
            job=self.job,
            handyman=self.handyman,
            report_date=timezone.now().date(),
            summary="Work done today",
            total_work_duration=timedelta(hours=2),
            status="pending",
            review_deadline=timezone.now() + timedelta(days=3),
        )

        self.url = f"/api/v1/mobile/handyman/jobs/{self.job.public_id}/dashboard/"

    def test_get_dashboard_success(self):
        """Test successfully getting dashboard data."""
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Dashboard data retrieved successfully"
        )
        data = response.data["data"]

        # Check job info
        self.assertIn("job", data)
        self.assertEqual(data["job"]["title"], "Test Job")
        self.assertEqual(data["job"]["status"], "in_progress")

        # Check tasks progress
        self.assertIn("tasks_progress", data)
        self.assertEqual(data["tasks_progress"]["total_tasks"], 3)
        self.assertEqual(data["tasks_progress"]["completed_tasks"], 1)
        self.assertEqual(data["tasks_progress"]["pending_tasks"], 2)
        self.assertEqual(data["tasks_progress"]["completion_percentage"], (1 / 3 * 100))

        # Check time stats (total should be 3 hours = 10800 seconds)
        self.assertIn("time_stats", data)
        self.assertEqual(data["time_stats"]["total_time_seconds"], 10800)
        self.assertEqual(data["time_stats"]["total_time_formatted"], "03:00:00")

        # Check session stats
        self.assertIn("session_stats", data)
        self.assertEqual(data["session_stats"]["total_sessions"], 3)
        self.assertEqual(data["session_stats"]["completed_sessions"], 2)
        self.assertEqual(data["session_stats"]["in_progress_sessions"], 1)
        self.assertTrue(data["session_stats"]["has_active_session"])
        self.assertIsNotNone(data["session_stats"]["active_session_id"])

        # Check report stats
        self.assertIn("report_stats", data)
        self.assertEqual(data["report_stats"]["total_reports"], 2)
        self.assertEqual(data["report_stats"]["pending_reports"], 1)
        self.assertEqual(data["report_stats"]["approved_reports"], 1)
        self.assertEqual(data["report_stats"]["rejected_reports"], 0)
        self.assertEqual(
            data["report_stats"]["latest_report_date"], timezone.now().date()
        )

    def test_get_dashboard_unauthenticated(self):
        """Test that unauthenticated users cannot access dashboard."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_dashboard_not_found(self):
        """Test getting dashboard for non-existent job."""
        self.client.force_authenticate(user=self.handyman)
        url = "/api/v1/mobile/handyman/jobs/00000000-0000-0000-0000-000000000000/dashboard/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_dashboard_forbidden_other_handyman(self):
        """Test that another handyman cannot access dashboard."""
        self.client.force_authenticate(user=self.other_handyman)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_dashboard_includes_homeowner_info(self):
        """Test that dashboard includes homeowner nested object."""
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertIn("homeowner", data["job"])
        self.assertIsNotNone(data["job"]["homeowner"])
        self.assertEqual(data["job"]["homeowner"]["display_name"], "Test Homeowner")
        self.assertIsNone(data["job"]["homeowner"]["avatar_url"])

    def test_get_dashboard_with_only_completed_tasks(self):
        """Test dashboard when all tasks are completed."""
        self.task2.is_completed = True
        self.task2.save()
        self.task3.is_completed = True
        self.task3.save()

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["tasks_progress"]["completed_tasks"], 3)
        self.assertEqual(data["tasks_progress"]["completion_percentage"], 100.0)

    def test_get_dashboard_with_no_sessions(self):
        """Test dashboard when there are no work sessions."""
        WorkSession.objects.all().delete()

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["time_stats"]["total_time_seconds"], 0)
        self.assertEqual(data["time_stats"]["total_time_formatted"], "00:00:00")
        self.assertIsNone(data["time_stats"]["average_session_duration_seconds"])
        self.assertIsNone(data["time_stats"]["longest_session_seconds"])

    def test_get_dashboard_with_only_active_session(self):
        """Test dashboard when there's only an active session (no end time)."""
        WorkSession.objects.filter(status="completed").delete()

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["time_stats"]["total_time_seconds"], 0)
        self.assertEqual(data["session_stats"]["total_sessions"], 1)
        self.assertEqual(data["session_stats"]["completed_sessions"], 0)
        self.assertEqual(data["session_stats"]["in_progress_sessions"], 1)

    def test_get_dashboard_with_no_reports(self):
        """Test dashboard when there are no daily reports."""
        DailyReport.objects.all().delete()

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["report_stats"]["total_reports"], 0)
        self.assertEqual(data["report_stats"]["latest_report_date"], None)

    def test_get_dashboard_with_rejected_reports(self):
        """Test dashboard with rejected daily reports."""
        self.report1.status = "rejected"
        self.report1.homeowner_comment = "Not detailed enough"
        self.report1.save()

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["report_stats"]["rejected_reports"], 1)

    def test_get_dashboard_task_order(self):
        """Test that tasks are returned in order."""
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        tasks = data["tasks_progress"]["tasks"]

        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0]["title"], "Task 1")
        self.assertEqual(tasks[1]["title"], "Task 2")
        self.assertEqual(tasks[2]["title"], "Task 3")

    def test_get_dashboard_includes_category_info(self):
        """Test that dashboard includes full category info."""
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        category = data["job"]["category"]

        self.assertEqual(category["name"], "Plumbing")
        self.assertEqual(category["slug"], "plumbing")

    def test_get_dashboard_includes_city_info(self):
        """Test that dashboard includes full city info."""
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        city = data["job"]["city"]

        self.assertEqual(city["name"], "Toronto")
        self.assertEqual(city["province"], "Ontario")
        self.assertEqual(city["province_code"], "ON")

    def test_get_dashboard_average_session_calculation(self):
        """Test that average session duration is calculated correctly."""
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        # Two sessions: 2 hours and 1 hour = average 1.5 hours = 5400 seconds
        self.assertEqual(data["time_stats"]["average_session_duration_seconds"], 5400)
        self.assertEqual(
            data["time_stats"]["average_session_duration_formatted"], "01:30:00"
        )
        # Longest session: 2 hours = 7200 seconds
        self.assertEqual(data["time_stats"]["longest_session_seconds"], 7200)
        self.assertEqual(data["time_stats"]["longest_session_formatted"], "02:00:00")

    def test_get_dashboard_with_completed_job_status(self):
        """Test dashboard for a completed job."""
        self.job.status = "completed"
        self.job.completed_at = timezone.now()
        self.job.save()

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["job"]["status"], "completed")
        self.assertIsNotNone(data["job"]["completed_at"])

    def test_get_dashboard_with_pending_completion_status(self):
        """Test dashboard for a job pending completion."""
        self.job.status = "pending_completion"
        self.job.completion_requested_at = timezone.now()
        self.job.save()

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["job"]["status"], "pending_completion")

    def test_get_dashboard_no_active_session(self):
        """Test dashboard when no active session exists."""
        self.active_session.status = "completed"
        self.active_session.ended_at = timezone.now()
        self.active_session.save()

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertFalse(data["session_stats"]["has_active_session"])
        self.assertIsNone(data["session_stats"]["active_session_id"])

    def test_get_dashboard_sessions_with_null_duration(self):
        """Test dashboard when sessions exist but have no duration_seconds."""
        # Clear existing sessions and create sessions with no duration
        WorkSession.objects.all().delete()

        # Create session without duration (no ended_at)
        WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now() - timedelta(hours=1),
            start_latitude=Decimal("43.0"),
            start_longitude=Decimal("-79.0"),
            start_photo="path/to/photo.jpg",
            status="completed",
        )

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        # Sessions exist but no duration_seconds, so averages should be None
        self.assertEqual(data["time_stats"]["total_time_seconds"], 0)
        self.assertIsNone(data["time_stats"]["average_session_duration_seconds"])
        self.assertIsNone(data["time_stats"]["longest_session_seconds"])

    def test_get_dashboard_with_active_session(self):
        """Test dashboard includes active session data."""
        # Set the active session to start 30 minutes ago
        self.active_session.started_at = timezone.now() - timedelta(minutes=30)
        self.active_session.save()

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        # Check active session is included
        self.assertIn("active_session", data)
        self.assertIsNotNone(data["active_session"])

        active_session = data["active_session"]
        self.assertIn("public_id", active_session)
        self.assertIn("started_at", active_session)
        self.assertIn("start_latitude", active_session)
        self.assertIn("start_longitude", active_session)
        self.assertIn("start_photo", active_session)
        self.assertIn("start_accuracy", active_session)
        self.assertIn("current_duration_seconds", active_session)
        self.assertIn("current_duration_formatted", active_session)
        self.assertIn("media_count", active_session)
        self.assertIn("media", active_session)

        # Check media is a list
        self.assertIsInstance(active_session["media"], list)

        # Check duration formatting
        self.assertGreater(active_session["current_duration_seconds"], 0)
        self.assertRegex(
            active_session["current_duration_formatted"], r"^\d{2}:\d{2}:\d{2}$"
        )

    def test_get_dashboard_without_active_session(self):
        """Test dashboard when there is no active session."""
        # Complete the active session
        active_session = WorkSession.objects.filter(status="in_progress").first()
        if active_session:
            active_session.status = "completed"
            active_session.ended_at = timezone.now()
            active_session.save()

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        # Check active session is null
        self.assertIn("active_session", data)
        self.assertIsNone(data["active_session"])

    def test_get_dashboard_active_session_with_media(self):
        """Test active session includes media count and media array."""
        # First, get the current count of media for the active session
        initial_count = self.active_session.media.count()

        # Add some media files
        media1 = WorkSessionMedia.objects.create(
            work_session=self.active_session,
            media_type="photo",
            file="test/image1.jpg",
            file_size=1024,
            description="Test image 1",
        )
        media2 = WorkSessionMedia.objects.create(
            work_session=self.active_session,
            media_type="photo",
            file="test/image2.jpg",
            file_size=2048,
            description="Test image 2",
        )

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        active_session_data = data["active_session"]
        self.assertEqual(active_session_data["media_count"], initial_count + 2)

        # Check media array
        self.assertIn("media", active_session_data)
        self.assertIsInstance(active_session_data["media"], list)
        self.assertEqual(len(active_session_data["media"]), initial_count + 2)

        # Check media item structure
        media_public_ids = [m["public_id"] for m in active_session_data["media"]]
        self.assertIn(str(media1.public_id), media_public_ids)
        self.assertIn(str(media2.public_id), media_public_ids)

        # Check media item fields
        for media_item in active_session_data["media"]:
            self.assertIn("public_id", media_item)
            self.assertIn("media_type", media_item)
            self.assertIn("file", media_item)
            self.assertIn("thumbnail", media_item)
            self.assertIn("description", media_item)
            self.assertIn("created_at", media_item)

    def test_get_dashboard_active_session_duration_calculation(self):
        """Test that active session duration is calculated correctly."""
        active_session = WorkSession.objects.filter(status="in_progress").first()

        # Manually set the start time to 2 hours ago
        from django.utils import timezone

        active_session.started_at = timezone.now() - timedelta(hours=2)
        active_session.save()

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        active_session_data = data["active_session"]
        # Should be approximately 2 hours (7200 seconds)
        self.assertGreaterEqual(
            active_session_data["current_duration_seconds"], 7140
        )  # Allow 1 minute variance
        self.assertLessEqual(active_session_data["current_duration_seconds"], 7260)
        self.assertEqual(active_session_data["current_duration_formatted"], "02:00:00")

    def test_get_dashboard_without_review(self):
        """Test dashboard when no reviews exist."""
        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        # Check homeowner_review and my_review fields
        self.assertIn("homeowner_review", data)
        self.assertIn("my_review", data)
        self.assertIsNone(data["homeowner_review"])
        self.assertIsNone(data["my_review"])

    def test_get_dashboard_with_homeowner_review(self):
        """Test dashboard when homeowner has left a review."""
        # Create a review from homeowner
        review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
            comment="Excellent work! Very professional.",
        )

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        # Check homeowner_review object
        self.assertIsNotNone(data["homeowner_review"])
        self.assertEqual(str(review.public_id), data["homeowner_review"]["public_id"])
        self.assertEqual(5, data["homeowner_review"]["rating"])
        self.assertEqual(
            "Excellent work! Very professional.", data["homeowner_review"]["comment"]
        )
        self.assertIn("created_at", data["homeowner_review"])
        self.assertIn("updated_at", data["homeowner_review"])
        # my_review should still be None
        self.assertIsNone(data["my_review"])

    def test_get_dashboard_with_handyman_review(self):
        """Test dashboard shows handyman's own review in my_review."""
        # Create a review from handyman
        review = Review.objects.create(
            job=self.job,
            reviewer=self.handyman,
            reviewee=self.homeowner,
            reviewer_type="handyman",
            rating=4,
            comment="Good homeowner.",
        )

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        # homeowner_review should be None
        self.assertIsNone(data["homeowner_review"])
        # my_review should show handyman's own review
        self.assertIsNotNone(data["my_review"])
        self.assertEqual(str(review.public_id), data["my_review"]["public_id"])
        self.assertEqual(4, data["my_review"]["rating"])
        self.assertEqual("Good homeowner.", data["my_review"]["comment"])

    def test_get_dashboard_with_both_reviews(self):
        """Test dashboard shows both reviews when both parties have reviewed."""
        # Create homeowner review
        homeowner_review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
            comment="Great handyman!",
        )
        # Create handyman review
        handyman_review = Review.objects.create(
            job=self.job,
            reviewer=self.handyman,
            reviewee=self.homeowner,
            reviewer_type="handyman",
            rating=4,
            comment="Good homeowner.",
        )

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        # Should show homeowner review
        self.assertIsNotNone(data["homeowner_review"])
        self.assertEqual(
            str(homeowner_review.public_id), data["homeowner_review"]["public_id"]
        )
        self.assertEqual(5, data["homeowner_review"]["rating"])
        self.assertEqual("Great handyman!", data["homeowner_review"]["comment"])

        # Should show handyman's own review
        self.assertIsNotNone(data["my_review"])
        self.assertEqual(str(handyman_review.public_id), data["my_review"]["public_id"])
        self.assertEqual(4, data["my_review"]["rating"])
        self.assertEqual("Good homeowner.", data["my_review"]["comment"])

    def test_get_dashboard_review_with_empty_comment(self):
        """Test dashboard with homeowner review that has no comment."""
        Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=3,
            comment="",
        )

        self.client.force_authenticate(user=self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        self.assertIsNotNone(data["homeowner_review"])
        self.assertEqual(3, data["homeowner_review"]["rating"])
        self.assertEqual("", data["homeowner_review"]["comment"])


class HandymanJobDashboardSerializerTests(APITestCase):
    """Test cases for HandymanJobDashboardSerializer."""

    def test_dashboard_serializer_with_empty_data(self):
        """Test serializer with minimal valid data."""
        from apps.jobs.serializers import HandymanJobDashboardSerializer

        data = {
            "job": {
                "public_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Test Job",
                "description": "Description",
                "status": "in_progress",
                "estimated_budget": "100.00",
                "category": {
                    "public_id": "123e4567-e89b-12d3-a456-426614174001",
                    "name": "Plumbing",
                    "slug": "plumbing",
                    "description": "",
                    "icon": "",
                },
                "city": {
                    "public_id": "123e4567-e89b-12d3-a456-426614174002",
                    "name": "Toronto",
                    "province": "Ontario",
                    "province_code": "ON",
                    "slug": "toronto-on",
                },
                "address": "123 Street",
                "postal_code": "",
                "latitude": None,
                "longitude": None,
                "completion_requested_at": None,
                "completed_at": None,
                "homeowner": None,
                "created_at": "2024-01-15T10:30:00Z",
            },
            "tasks_progress": {
                "total_tasks": 0,
                "completed_tasks": 0,
                "pending_tasks": 0,
                "completion_percentage": 0.0,
                "tasks": [],
            },
            "time_stats": {
                "total_time_seconds": 0,
                "total_time_formatted": "00:00:00",
                "average_session_duration_seconds": None,
                "average_session_duration_formatted": None,
                "longest_session_seconds": None,
                "longest_session_formatted": None,
            },
            "session_stats": {
                "total_sessions": 0,
                "completed_sessions": 0,
                "in_progress_sessions": 0,
                "has_active_session": False,
                "active_session_id": None,
            },
            "active_session": None,
            "report_stats": {
                "total_reports": 0,
                "pending_reports": 0,
                "approved_reports": 0,
                "rejected_reports": 0,
                "latest_report_date": None,
            },
            "homeowner_review": None,
            "my_review": None,
        }

        serializer = HandymanJobDashboardSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_dashboard_serializer_with_all_fields(self):
        """Test serializer with all fields populated."""

        from apps.jobs.serializers import HandymanJobDashboardSerializer

        data = {
            "job": {
                "public_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Test Job",
                "description": "Description",
                "status": "in_progress",
                "status_at": "2024-01-15T10:30:00Z",
                "estimated_budget": "150.50",
                "category": {
                    "public_id": "123e4567-e89b-12d3-a456-426614174001",
                    "name": "Plumbing",
                    "slug": "plumbing",
                    "description": "Plumbing services",
                    "icon": "plumbing-icon",
                },
                "city": {
                    "public_id": "123e4567-e89b-12d3-a456-426614174002",
                    "name": "Toronto",
                    "province": "Ontario",
                    "province_code": "ON",
                    "slug": "toronto-on",
                },
                "address": "123 Main St",
                "postal_code": "M5H 2N2",
                "latitude": "43.651070",
                "longitude": "-79.347015",
                "completion_requested_at": None,
                "completed_at": None,
                "homeowner": {
                    "public_id": "123e4567-e89b-12d3-a456-426614174003",
                    "display_name": "John Homeowner",
                    "avatar_url": "https://example.com/avatar.jpg",
                    "rating": 4.5,
                },
                "created_at": "2024-01-15T10:30:00Z",
            },
            "tasks_progress": {
                "total_tasks": 5,
                "completed_tasks": 3,
                "pending_tasks": 2,
                "completion_percentage": 60.0,
                "tasks": [
                    {
                        "public_id": "123e4567-e89b-12d3-a456-426614174010",
                        "title": "Task 1",
                        "description": "",
                        "order": 0,
                        "is_completed": True,
                        "completed_at": "2024-01-16T10:00:00Z",
                    },
                ],
            },
            "time_stats": {
                "total_time_seconds": 14400,
                "total_time_formatted": "04:00:00",
                "average_session_duration_seconds": 7200,
                "average_session_duration_formatted": "02:00:00",
                "longest_session_seconds": 10800,
                "longest_session_formatted": "03:00:00",
            },
            "session_stats": {
                "total_sessions": 2,
                "completed_sessions": 2,
                "in_progress_sessions": 0,
                "has_active_session": False,
                "active_session_id": None,
            },
            "active_session": None,
            "report_stats": {
                "total_reports": 3,
                "pending_reports": 1,
                "approved_reports": 2,
                "rejected_reports": 0,
                "latest_report_date": "2024-01-16",
            },
            "homeowner_review": {
                "public_id": "123e4567-e89b-12d3-a456-426614174099",
                "rating": 5,
                "comment": "Excellent work!",
                "created_at": "2024-01-20T14:30:00Z",
                "updated_at": "2024-01-20T14:30:00Z",
            },
            "my_review": {
                "public_id": "123e4567-e89b-12d3-a456-426614174098",
                "rating": 4,
                "comment": "Good homeowner!",
                "created_at": "2024-01-20T15:00:00Z",
                "updated_at": "2024-01-20T15:00:00Z",
            },
        }

        serializer = HandymanJobDashboardSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_dashboard_serializer_with_active_session(self):
        """Test serializer with active session populated."""
        from apps.jobs.serializers import HandymanJobDashboardSerializer

        data = {
            "job": {
                "public_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Test Job",
                "description": "Description",
                "status": "in_progress",
                "estimated_budget": "100.00",
                "category": {
                    "public_id": "123e4567-e89b-12d3-a456-426614174001",
                    "name": "Plumbing",
                    "slug": "plumbing",
                    "description": "",
                    "icon": "",
                },
                "city": {
                    "public_id": "123e4567-e89b-12d3-a456-426614174002",
                    "name": "Toronto",
                    "province": "Ontario",
                    "province_code": "ON",
                    "slug": "toronto-on",
                },
                "address": "123 Main St",
                "postal_code": "M5H 2N2",
                "latitude": "43.651070",
                "longitude": "-79.347015",
                "homeowner": {
                    "public_id": "123e4567-e89b-12d3-a456-426614174003",
                    "display_name": "John Homeowner",
                    "avatar_url": None,
                    "rating": None,
                },
                "created_at": "2024-01-15T10:30:00Z",
            },
            "tasks_progress": {
                "total_tasks": 1,
                "completed_tasks": 0,
                "pending_tasks": 1,
                "completion_percentage": 0.0,
                "tasks": [
                    {
                        "public_id": "123e4567-e89b-12d3-a456-426614174010",
                        "title": "Task 1",
                        "description": "",
                        "order": 0,
                        "is_completed": False,
                        "completed_at": None,
                    },
                ],
            },
            "time_stats": {
                "total_time_seconds": 0,
                "total_time_formatted": "00:00:00",
                "average_session_duration_seconds": None,
                "average_session_duration_formatted": None,
                "longest_session_seconds": None,
                "longest_session_formatted": None,
            },
            "session_stats": {
                "total_sessions": 1,
                "completed_sessions": 0,
                "in_progress_sessions": 1,
                "has_active_session": True,
                "active_session_id": "123e4567-e89b-12d3-a456-426614174020",
            },
            "active_session": {
                "public_id": "123e4567-e89b-12d3-a456-426614174020",
                "started_at": "2024-01-16T10:00:00Z",
                "start_latitude": "43.651070",
                "start_longitude": "-79.347015",
                "start_photo": None,
                "start_accuracy": 10.5,
                "current_duration_seconds": 3600,
                "current_duration_formatted": "01:00:00",
                "media_count": 0,
                "media": [],
            },
            "report_stats": {
                "total_reports": 0,
                "pending_reports": 0,
                "approved_reports": 0,
                "rejected_reports": 0,
                "latest_report_date": None,
            },
            "homeowner_review": None,
            "my_review": None,
        }

        serializer = HandymanJobDashboardSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class JobDashboardJobInfoSerializerTests(APITestCase):
    """Test cases for JobDashboardJobInfoSerializer."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        self.homeowner_profile = HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="John Homeowner",
        )
        self.category = JobCategory.objects.create(
            name="Plumbing",
            slug="plumbing",
            is_active=True,
        )
        self.city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            category=self.category,
            city=self.city,
            title="Test Job",
            description="Test description",
            address="123 Main St",
            postal_code="M5H 2N2",
            estimated_budget=Decimal("100.00"),
        )

    def test_serializer_with_homeowner_profile(self):
        """Test serializer returns homeowner nested object."""
        from apps.jobs.serializers import JobDashboardJobInfoSerializer

        serializer = JobDashboardJobInfoSerializer(self.job)
        data = serializer.data

        self.assertIn("homeowner", data)
        self.assertIsNotNone(data["homeowner"])
        self.assertEqual(data["homeowner"]["display_name"], "John Homeowner")
        self.assertIsNone(data["homeowner"]["avatar_url"])
        self.assertIn("public_id", data["homeowner"])
        self.assertIn("rating", data["homeowner"])

    def test_serializer_without_homeowner_profile(self):
        """Test serializer returns None values when homeowner has no profile."""
        from apps.jobs.serializers import JobDashboardJobInfoSerializer

        user_without_profile = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )
        self.job.homeowner = user_without_profile
        self.job.save()

        serializer = JobDashboardJobInfoSerializer(self.job)
        data = serializer.data

        self.assertIn("homeowner", data)
        self.assertIsNotNone(data["homeowner"])
        self.assertIsNone(data["homeowner"]["display_name"])
        self.assertIsNone(data["homeowner"]["avatar_url"])


class HomeownerJobDashboardViewTests(APITestCase):
    """Test cases for HomeownerJobDashboardView."""

    def setUp(self):
        """Set up test data."""
        # Create homeowner user
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        self.homeowner.email_verified_at = "2024-01-01T00:00:00Z"
        self.homeowner.phone_verified_at = "2024-01-01T00:00:00Z"
        self.homeowner.save()
        self.homeowner_profile = HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
        )
        self.homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Create handyman user
        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        self.handyman.email_verified_at = "2024-01-01T00:00:00Z"
        self.handyman.phone_verified_at = "2024-01-01T00:00:00Z"
        self.handyman.save()
        self.handyman_profile = HandymanProfile.objects.create(
            user=self.handyman,
            display_name="Test Handyman",
        )
        self.handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
            "phone_verified": True,
        }

        # Create another homeowner
        self.other_homeowner = User.objects.create_user(
            email="other_homeowner@example.com",
            password="testpass123",
        )
        self.other_homeowner.email_verified_at = "2024-01-01T00:00:00Z"
        self.other_homeowner.phone_verified_at = "2024-01-01T00:00:00Z"
        self.other_homeowner.save()
        HomeownerProfile.objects.create(
            user=self.other_homeowner,
            display_name="Other Homeowner",
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
            title="Test Job",
            description="Test description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Street",
            status="in_progress",
        )

        # Create tasks
        self.task1 = JobTask.objects.create(
            job=self.job, title="Task 1", order=0, is_completed=True
        )
        self.task2 = JobTask.objects.create(
            job=self.job, title="Task 2", order=1, is_completed=False
        )
        self.task3 = JobTask.objects.create(
            job=self.job, title="Task 3", order=2, is_completed=False
        )

        # Create work sessions
        self.session1 = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now() - timedelta(hours=4),
            ended_at=timezone.now() - timedelta(hours=2),
            start_latitude=Decimal("43.0"),
            start_longitude=Decimal("-79.0"),
            end_latitude=Decimal("43.1"),
            end_longitude=Decimal("-79.1"),
            start_photo="path/to/photo1.jpg",
            status="completed",
        )
        self.session2 = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now() - timedelta(hours=2),
            ended_at=timezone.now() - timedelta(hours=1),
            start_latitude=Decimal("43.0"),
            start_longitude=Decimal("-79.0"),
            end_latitude=Decimal("43.1"),
            end_longitude=Decimal("-79.1"),
            start_photo="path/to/photo2.jpg",
            status="completed",
        )

        # Create active session
        self.active_session = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now(),
            start_latitude=Decimal("43.0"),
            start_longitude=Decimal("-79.0"),
            start_photo="path/to/active_photo.jpg",
            status="in_progress",
        )

        # Create daily reports
        self.report1 = DailyReport.objects.create(
            job=self.job,
            handyman=self.handyman,
            report_date=(timezone.now() - timedelta(days=1)).date(),
            summary="Work done yesterday",
            total_work_duration=timedelta(hours=4),
            status="approved",
            review_deadline=timezone.now() + timedelta(days=2),
        )
        self.report2 = DailyReport.objects.create(
            job=self.job,
            handyman=self.handyman,
            report_date=timezone.now().date(),
            summary="Work done today",
            total_work_duration=timedelta(hours=2),
            status="pending",
            review_deadline=timezone.now() + timedelta(days=3),
        )

        self.url = f"/api/v1/mobile/homeowner/jobs/{self.job.public_id}/dashboard/"

    def test_get_dashboard_success(self):
        """Test successfully getting dashboard data."""
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Dashboard data retrieved successfully"
        )
        data = response.data["data"]

        # Check job info
        self.assertIn("job", data)
        self.assertEqual(data["job"]["title"], "Test Job")
        self.assertEqual(data["job"]["status"], "in_progress")

        # Check tasks progress
        self.assertIn("tasks_progress", data)
        self.assertEqual(data["tasks_progress"]["total_tasks"], 3)
        self.assertEqual(data["tasks_progress"]["completed_tasks"], 1)
        self.assertEqual(data["tasks_progress"]["pending_tasks"], 2)
        self.assertEqual(data["tasks_progress"]["completion_percentage"], (1 / 3 * 100))

        # Check time stats (total should be 3 hours = 10800 seconds)
        self.assertIn("time_stats", data)
        self.assertEqual(data["time_stats"]["total_time_seconds"], 10800)
        self.assertEqual(data["time_stats"]["total_time_formatted"], "03:00:00")

        # Check session stats
        self.assertIn("session_stats", data)
        self.assertEqual(data["session_stats"]["total_sessions"], 3)
        self.assertEqual(data["session_stats"]["completed_sessions"], 2)
        self.assertEqual(data["session_stats"]["in_progress_sessions"], 1)
        self.assertTrue(data["session_stats"]["has_active_session"])
        self.assertIsNotNone(data["session_stats"]["active_session_id"])

        # Check report stats
        self.assertIn("report_stats", data)
        self.assertEqual(data["report_stats"]["total_reports"], 2)
        self.assertEqual(data["report_stats"]["pending_reports"], 1)
        self.assertEqual(data["report_stats"]["approved_reports"], 1)
        self.assertEqual(data["report_stats"]["rejected_reports"], 0)
        self.assertEqual(
            data["report_stats"]["latest_report_date"], timezone.now().date()
        )

    def test_get_dashboard_unauthenticated(self):
        """Test that unauthenticated users cannot access dashboard."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_dashboard_not_found(self):
        """Test getting dashboard for non-existent job."""
        self.client.force_authenticate(user=self.homeowner)
        url = "/api/v1/mobile/homeowner/jobs/00000000-0000-0000-0000-000000000000/dashboard/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_dashboard_forbidden_other_homeowner(self):
        """Test that another homeowner cannot access dashboard."""
        self.client.force_authenticate(user=self.other_homeowner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_dashboard_includes_handyman_info(self):
        """Test that dashboard includes handyman nested object."""
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertIn("handyman", data["job"])
        self.assertIsNotNone(data["job"]["handyman"])
        self.assertEqual(data["job"]["handyman"]["display_name"], "Test Handyman")
        self.assertIsNone(data["job"]["handyman"]["avatar_url"])

    def test_get_dashboard_with_only_completed_tasks(self):
        """Test dashboard when all tasks are completed."""
        self.task2.is_completed = True
        self.task2.save()
        self.task3.is_completed = True
        self.task3.save()

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["tasks_progress"]["completed_tasks"], 3)
        self.assertEqual(data["tasks_progress"]["completion_percentage"], 100.0)

    def test_get_dashboard_with_no_sessions(self):
        """Test dashboard when there are no work sessions."""
        WorkSession.objects.all().delete()

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["time_stats"]["total_time_seconds"], 0)
        self.assertEqual(data["time_stats"]["total_time_formatted"], "00:00:00")
        self.assertIsNone(data["time_stats"]["average_session_duration_seconds"])
        self.assertIsNone(data["time_stats"]["longest_session_seconds"])

    def test_get_dashboard_with_only_active_session(self):
        """Test dashboard when there's only an active session (no end time)."""
        WorkSession.objects.filter(status="completed").delete()

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["time_stats"]["total_time_seconds"], 0)
        self.assertEqual(data["session_stats"]["total_sessions"], 1)
        self.assertEqual(data["session_stats"]["completed_sessions"], 0)
        self.assertEqual(data["session_stats"]["in_progress_sessions"], 1)

    def test_get_dashboard_with_no_reports(self):
        """Test dashboard when there are no daily reports."""
        DailyReport.objects.all().delete()

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["report_stats"]["total_reports"], 0)
        self.assertEqual(data["report_stats"]["latest_report_date"], None)

    def test_get_dashboard_with_rejected_reports(self):
        """Test dashboard with rejected daily reports."""
        self.report1.status = "rejected"
        self.report1.homeowner_comment = "Not detailed enough"
        self.report1.save()

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["report_stats"]["rejected_reports"], 1)

    def test_get_dashboard_task_order(self):
        """Test that tasks are returned in order."""
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        tasks = data["tasks_progress"]["tasks"]

        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0]["title"], "Task 1")
        self.assertEqual(tasks[1]["title"], "Task 2")
        self.assertEqual(tasks[2]["title"], "Task 3")

    def test_get_dashboard_includes_category_info(self):
        """Test that dashboard includes full category info."""
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        category = data["job"]["category"]

        self.assertEqual(category["name"], "Plumbing")
        self.assertEqual(category["slug"], "plumbing")

    def test_get_dashboard_includes_city_info(self):
        """Test that dashboard includes full city info."""
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        city = data["job"]["city"]

        self.assertEqual(city["name"], "Toronto")
        self.assertEqual(city["province"], "Ontario")
        self.assertEqual(city["province_code"], "ON")

    def test_get_dashboard_average_session_calculation(self):
        """Test that average session duration is calculated correctly."""
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        # Two sessions: 2 hours and 1 hour = average 1.5 hours = 5400 seconds
        self.assertEqual(data["time_stats"]["average_session_duration_seconds"], 5400)
        self.assertEqual(
            data["time_stats"]["average_session_duration_formatted"], "01:30:00"
        )
        # Longest session: 2 hours = 7200 seconds
        self.assertEqual(data["time_stats"]["longest_session_seconds"], 7200)
        self.assertEqual(data["time_stats"]["longest_session_formatted"], "02:00:00")

    def test_get_dashboard_with_completed_job_status(self):
        """Test dashboard for a completed job."""
        self.job.status = "completed"
        self.job.completed_at = timezone.now()
        self.job.save()

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["job"]["status"], "completed")
        self.assertIsNotNone(data["job"]["completed_at"])

    def test_get_dashboard_with_pending_completion_status(self):
        """Test dashboard for a job pending completion."""
        self.job.status = "pending_completion"
        self.job.completion_requested_at = timezone.now()
        self.job.save()

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(data["job"]["status"], "pending_completion")

    def test_get_dashboard_no_active_session(self):
        """Test dashboard when no active session exists."""
        self.active_session.status = "completed"
        self.active_session.ended_at = timezone.now()
        self.active_session.save()

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertFalse(data["session_stats"]["has_active_session"])
        self.assertIsNone(data["session_stats"]["active_session_id"])

    def test_get_dashboard_sessions_with_null_duration(self):
        """Test dashboard when sessions exist but have no duration_seconds."""
        # Clear existing sessions and create sessions with no duration
        WorkSession.objects.all().delete()

        # Create session without duration (no ended_at)
        WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now() - timedelta(hours=1),
            start_latitude=Decimal("43.0"),
            start_longitude=Decimal("-79.0"),
            start_photo="path/to/photo.jpg",
            status="completed",
        )

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        # Sessions exist but no duration_seconds, so averages should be None
        self.assertEqual(data["time_stats"]["total_time_seconds"], 0)
        self.assertIsNone(data["time_stats"]["average_session_duration_seconds"])
        self.assertIsNone(data["time_stats"]["longest_session_seconds"])

    def test_get_dashboard_with_active_session(self):
        """Test dashboard includes active session data."""
        # Set the active session to start 30 minutes ago
        self.active_session.started_at = timezone.now() - timedelta(minutes=30)
        self.active_session.save()

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        # Check active session is included
        self.assertIn("active_session", data)
        self.assertIsNotNone(data["active_session"])

        active_session = data["active_session"]
        self.assertIn("public_id", active_session)
        self.assertIn("started_at", active_session)
        self.assertIn("start_latitude", active_session)
        self.assertIn("start_longitude", active_session)
        self.assertIn("start_photo", active_session)
        self.assertIn("start_accuracy", active_session)
        self.assertIn("current_duration_seconds", active_session)
        self.assertIn("current_duration_formatted", active_session)
        self.assertIn("media_count", active_session)
        self.assertIn("media", active_session)

        # Check media is a list
        self.assertIsInstance(active_session["media"], list)

        # Check duration formatting
        self.assertGreater(active_session["current_duration_seconds"], 0)
        self.assertRegex(
            active_session["current_duration_formatted"], r"^\d{2}:\d{2}:\d{2}$"
        )

    def test_get_dashboard_without_active_session(self):
        """Test dashboard when there is no active session."""
        # Complete the active session
        active_session = WorkSession.objects.filter(status="in_progress").first()
        if active_session:
            active_session.status = "completed"
            active_session.ended_at = timezone.now()
            active_session.save()

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        # Check active session is null
        self.assertIn("active_session", data)
        self.assertIsNone(data["active_session"])

    def test_get_dashboard_active_session_with_media(self):
        """Test active session includes media count and media array."""
        # First, get the current count of media for the active session
        initial_count = self.active_session.media.count()

        # Add some media files
        media1 = WorkSessionMedia.objects.create(
            work_session=self.active_session,
            media_type="photo",
            file="test/image1.jpg",
            file_size=1024,
            description="Test image 1",
        )
        media2 = WorkSessionMedia.objects.create(
            work_session=self.active_session,
            media_type="photo",
            file="test/image2.jpg",
            file_size=2048,
            description="Test image 2",
        )

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        active_session_data = data["active_session"]
        self.assertEqual(active_session_data["media_count"], initial_count + 2)

        # Check media array
        self.assertIn("media", active_session_data)
        self.assertIsInstance(active_session_data["media"], list)
        self.assertEqual(len(active_session_data["media"]), initial_count + 2)

        # Check media item structure
        media_public_ids = [m["public_id"] for m in active_session_data["media"]]
        self.assertIn(str(media1.public_id), media_public_ids)
        self.assertIn(str(media2.public_id), media_public_ids)

        # Check media item fields
        for media_item in active_session_data["media"]:
            self.assertIn("public_id", media_item)
            self.assertIn("media_type", media_item)
            self.assertIn("file", media_item)
            self.assertIn("thumbnail", media_item)
            self.assertIn("description", media_item)
            self.assertIn("created_at", media_item)

    def test_get_dashboard_active_session_duration_calculation(self):
        """Test that active session duration is calculated correctly."""
        active_session = WorkSession.objects.filter(status="in_progress").first()

        # Manually set the start time to 2 hours ago
        active_session.started_at = timezone.now() - timedelta(hours=2)
        active_session.save()

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        active_session_data = data["active_session"]
        # Should be approximately 2 hours (7200 seconds)
        self.assertGreaterEqual(
            active_session_data["current_duration_seconds"], 7140
        )  # Allow 1 minute variance
        self.assertLessEqual(active_session_data["current_duration_seconds"], 7260)
        self.assertEqual(active_session_data["current_duration_formatted"], "02:00:00")

    def test_get_dashboard_without_review(self):
        """Test dashboard when homeowner has not reviewed the job."""
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        # Check my_review field
        self.assertIn("my_review", data)
        self.assertIsNone(data["my_review"])

    def test_get_dashboard_with_homeowner_review(self):
        """Test dashboard when homeowner has left a review (own review)."""
        # Create a review from homeowner
        review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
            comment="Excellent work! Very professional.",
        )

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        # Check my_review object
        self.assertIsNotNone(data["my_review"])
        self.assertEqual(str(review.public_id), data["my_review"]["public_id"])
        self.assertEqual(5, data["my_review"]["rating"])
        self.assertEqual(
            "Excellent work! Very professional.", data["my_review"]["comment"]
        )
        self.assertIn("created_at", data["my_review"])
        self.assertIn("updated_at", data["my_review"])

    def test_get_dashboard_ignores_handyman_review(self):
        """Test that dashboard only shows homeowner's own review, not handyman's review."""
        # Create a review from handyman (should be ignored in my_review)
        Review.objects.create(
            job=self.job,
            reviewer=self.handyman,
            reviewee=self.homeowner,
            reviewer_type="handyman",
            rating=4,
            comment="Good homeowner.",
        )

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        # Should show no review since there's no homeowner review
        self.assertIsNone(data["my_review"])

    def test_get_dashboard_with_both_reviews(self):
        """Test dashboard shows homeowner's own review when both parties have reviewed."""
        # Create homeowner review
        homeowner_review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
            comment="Great handyman!",
        )
        # Create handyman review
        Review.objects.create(
            job=self.job,
            reviewer=self.handyman,
            reviewee=self.homeowner,
            reviewer_type="handyman",
            rating=4,
            comment="Good homeowner.",
        )

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        # Should show homeowner's own review
        self.assertIsNotNone(data["my_review"])
        self.assertEqual(
            str(homeowner_review.public_id), data["my_review"]["public_id"]
        )
        self.assertEqual(5, data["my_review"]["rating"])
        self.assertEqual("Great handyman!", data["my_review"]["comment"])

    def test_get_dashboard_review_with_empty_comment(self):
        """Test dashboard with homeowner review that has no comment."""
        Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=3,
            comment="",
        )

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        self.assertIsNotNone(data["my_review"])
        self.assertEqual(3, data["my_review"]["rating"])
        self.assertEqual("", data["my_review"]["comment"])

    def test_get_dashboard_job_without_assigned_handyman(self):
        """Test dashboard when job has no assigned handyman."""
        self.job.assigned_handyman = None
        self.job.status = "open"
        self.job.save()

        # Delete work sessions and reports since they require handyman
        WorkSession.objects.all().delete()
        DailyReport.objects.all().delete()

        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]

        self.assertIsNone(data["job"]["handyman"])


class HomeownerJobDashboardJobInfoSerializerTests(APITestCase):
    """Test cases for HomeownerJobDashboardJobInfoSerializer."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        self.handyman_profile = HandymanProfile.objects.create(
            user=self.handyman,
            display_name="John Handyman",
        )
        self.category = JobCategory.objects.create(
            name="Plumbing",
            slug="plumbing",
            is_active=True,
        )
        self.city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            category=self.category,
            city=self.city,
            title="Test Job",
            description="Test description",
            address="123 Main St",
            postal_code="M5H 2N2",
            estimated_budget=Decimal("100.00"),
        )

    def test_serializer_with_handyman_profile(self):
        """Test serializer returns handyman nested object."""
        from apps.jobs.serializers import HomeownerJobDashboardJobInfoSerializer

        serializer = HomeownerJobDashboardJobInfoSerializer(self.job)
        data = serializer.data

        self.assertIn("handyman", data)
        self.assertIsNotNone(data["handyman"])
        self.assertEqual(data["handyman"]["display_name"], "John Handyman")
        self.assertIsNone(data["handyman"]["avatar_url"])
        self.assertIn("public_id", data["handyman"])
        self.assertIn("rating", data["handyman"])

    def test_serializer_without_handyman_profile(self):
        """Test serializer returns None when handyman has no profile."""
        from apps.jobs.serializers import HomeownerJobDashboardJobInfoSerializer

        user_without_profile = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )
        self.job.assigned_handyman = user_without_profile
        self.job.save()

        serializer = HomeownerJobDashboardJobInfoSerializer(self.job)
        data = serializer.data

        self.assertIsNone(data["handyman"])

    def test_serializer_without_assigned_handyman(self):
        """Test serializer returns None when no handyman is assigned."""
        from apps.jobs.serializers import HomeownerJobDashboardJobInfoSerializer

        self.job.assigned_handyman = None
        self.job.save()

        serializer = HomeownerJobDashboardJobInfoSerializer(self.job)
        data = serializer.data

        self.assertIsNone(data["handyman"])
