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
    Job,
    JobApplication,
    JobCategory,
)
from apps.profiles.models import HandymanProfile, HomeownerProfile


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

    def test_update_job_with_job_items(self):
        """Test updating job items."""
        data = {"job_items": ["Task 1", "Task 2", "Task 3"]}

        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["data"]["job_items"], ["Task 1", "Task 2", "Task 3"]
        )

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
