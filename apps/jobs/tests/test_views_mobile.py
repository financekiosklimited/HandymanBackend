from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image as PILImage
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.jobs.models import City, Job, JobCategory


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
        """Test listing categories without authentication fails."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


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
        """Test listing cities without authentication fails."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


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
        from datetime import timedelta

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

        # Test second page
        response2 = self.client.get(self.url, {"page": 2, "page_size": 10})
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response2.data["data"]), 10)
        self.assertTrue(response2.data["meta"]["pagination"]["has_previous"])

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
