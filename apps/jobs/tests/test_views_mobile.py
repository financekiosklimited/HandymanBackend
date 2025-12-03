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
            email="customer@example.com",
            password="testpass123",
        )
        self.user.email_verified_at = "2024-01-01T00:00:00Z"
        self.user.save()
        # Mock token payload for permissions
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "customer",
            "roles": ["customer"],
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
            email="customer@example.com",
            password="testpass123",
        )
        self.user.email_verified_at = "2024-01-01T00:00:00Z"
        self.user.save()
        # Mock token payload for permissions
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "customer",
            "roles": ["customer"],
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
        self.url = "/api/v1/mobile/customer/jobs/"
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="customer")
        self.user.email_verified_at = "2024-01-01T00:00:00Z"
        self.user.save()
        # Mock token payload for permissions (with phone_verified for POST)
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "customer",
            "roles": ["customer"],
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
        """Test successfully listing customer's jobs."""
        # Create jobs for the authenticated user
        Job.objects.create(
            customer=self.user,
            title="Fix faucet",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        Job.objects.create(
            customer=self.user,
            title="Fix door",
            description="Test",
            estimated_budget=Decimal("40.00"),
            category=self.category,
            city=self.city,
            address="456 Oak Ave",
        )

        # Create job for another user
        Job.objects.create(
            customer=self.other_user,
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
            customer=self.user,
            title="Plumbing job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        Job.objects.create(
            customer=self.user,
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
            customer=self.user,
            title="Draft job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="draft",
        )
        Job.objects.create(
            customer=self.user,
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
                customer=self.user,
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
        self.assertEqual(job.customer, self.user)
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
        UserRole.objects.create(user=user_no_phone, role="customer")
        user_no_phone.email_verified_at = "2024-01-01T00:00:00Z"
        user_no_phone.save()
        user_no_phone.token_payload = {
            "plat": "mobile",
            "active_role": "customer",
            "roles": ["customer"],
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
            email="customer@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="customer")
        self.user.email_verified_at = "2024-01-01T00:00:00Z"
        self.user.save()
        # Mock token payload for permissions
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "customer",
            "roles": ["customer"],
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
            customer=self.user,
            title="Fix leaking faucet",
            description="Kitchen faucet is leaking",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        self.url = f"/api/v1/mobile/customer/jobs/{self.job.public_id}/"

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
            customer=self.other_user,
            title="Other user job",
            description="Test",
            estimated_budget=Decimal("30.00"),
            category=self.category,
            city=self.city,
            address="456 Oak Ave",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            f"/api/v1/mobile/customer/jobs/{other_job.public_id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_job_detail_not_found(self):
        """Test getting non-existent job returns 404."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            "/api/v1/mobile/customer/jobs/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_job_detail_unauthenticated(self):
        """Test getting job detail without authentication fails."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
