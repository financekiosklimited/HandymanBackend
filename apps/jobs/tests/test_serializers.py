from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image as PILImage
from rest_framework.test import APIRequestFactory

from apps.accounts.models import User
from apps.jobs.models import City, Job, JobCategory, JobImage
from apps.jobs.serializers import (
    CitySerializer,
    JobCategorySerializer,
    JobCreateSerializer,
    JobDetailSerializer,
    JobImageSerializer,
    JobListSerializer,
)


class JobCategorySerializerTests(TestCase):
    """Test cases for JobCategorySerializer."""

    def test_category_serialization(self):
        """Test category serialization."""
        category = JobCategory.objects.create(
            name="Plumbing",
            slug="plumbing",
            description="Plumbing services",
            icon="plumbing_icon",
        )
        serializer = JobCategorySerializer(category)
        data = serializer.data

        self.assertEqual(data["name"], "Plumbing")
        self.assertEqual(data["slug"], "plumbing")
        self.assertEqual(data["description"], "Plumbing services")
        self.assertEqual(data["icon"], "plumbing_icon")
        self.assertIn("public_id", data)


class CitySerializerTests(TestCase):
    """Test cases for CitySerializer."""

    def test_city_serialization(self):
        """Test city serialization."""
        city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
        )
        serializer = CitySerializer(city)
        data = serializer.data

        self.assertEqual(data["name"], "Toronto")
        self.assertEqual(data["province"], "Ontario")
        self.assertEqual(data["province_code"], "ON")
        self.assertEqual(data["slug"], "toronto-on")
        self.assertIn("public_id", data)


class JobImageSerializerTests(TestCase):
    """Test cases for JobImageSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="customer@example.com",
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
        self.job = Job.objects.create(
            customer=self.user,
            title="Test",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

    def test_job_image_serialization(self):
        """Test job image serialization."""
        # Create a simple test image
        image_io = BytesIO()
        pil_image = PILImage.new("RGB", (100, 100), color="red")
        pil_image.save(image_io, format="JPEG")
        image_io.seek(0)
        image_file = SimpleUploadedFile(
            "test.jpg", image_io.getvalue(), content_type="image/jpeg"
        )

        job_image = JobImage.objects.create(job=self.job, image=image_file, order=0)
        serializer = JobImageSerializer(job_image)
        data = serializer.data

        self.assertIn("public_id", data)
        self.assertIn("image", data)
        self.assertEqual(data["order"], 0)
        # In test environment, image URL may be relative or absolute
        self.assertIn("jobs/images/", data["image"])


class JobListSerializerTests(TestCase):
    """Test cases for JobListSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="customer@example.com",
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

    def test_job_list_serialization(self):
        """Test job list serialization with nested data."""
        job = Job.objects.create(
            customer=self.user,
            title="Fix leaking faucet",
            description="Kitchen faucet is leaking",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )

        serializer = JobListSerializer(job)
        data = serializer.data

        self.assertEqual(data["title"], "Fix leaking faucet")
        self.assertEqual(data["description"], "Kitchen faucet is leaking")
        self.assertEqual(float(data["estimated_budget"]), 50.00)
        self.assertEqual(data["status"], "open")

        # Check nested category
        self.assertIn("category", data)
        self.assertEqual(data["category"]["name"], "Plumbing")
        self.assertEqual(data["category"]["slug"], "plumbing")

        # Check nested city
        self.assertIn("city", data)
        self.assertEqual(data["city"]["name"], "Toronto")
        self.assertEqual(data["city"]["province"], "Ontario")

        # Check images (should be empty list)
        self.assertIn("images", data)
        self.assertEqual(data["images"], [])


class JobDetailSerializerTests(TestCase):
    """Test cases for JobDetailSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="customer@example.com",
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

    def test_job_detail_serialization(self):
        """Test job detail serialization."""
        job = Job.objects.create(
            customer=self.user,
            title="Fix door",
            description="Broken door",
            estimated_budget=Decimal("40.00"),
            category=self.category,
            city=self.city,
            address="456 Oak Ave",
            latitude=Decimal("43.651070"),
            longitude=Decimal("-79.347015"),
            status="draft",
        )

        serializer = JobDetailSerializer(job)
        data = serializer.data

        self.assertEqual(data["title"], "Fix door")
        self.assertEqual(float(data["estimated_budget"]), 40.00)
        self.assertEqual(data["address"], "456 Oak Ave")
        self.assertEqual(float(data["latitude"]), 43.651070)
        self.assertEqual(float(data["longitude"]), -79.347015)
        self.assertEqual(data["status"], "draft")


class JobCreateSerializerTests(TestCase):
    """Test cases for JobCreateSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="customer@example.com",
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

        # Create a mock request with user
        factory = APIRequestFactory()
        self.request = factory.post("/")
        self.request.user = self.user

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

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid())

        job = serializer.save()
        self.assertEqual(job.title, "Fix leaking faucet")
        self.assertEqual(job.customer, self.user)
        self.assertEqual(job.category, self.category)
        self.assertEqual(job.city, self.city)
        self.assertEqual(job.status, "open")

    def test_create_job_with_coordinates(self):
        """Test creating a job with latitude and longitude."""
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "latitude": "43.651070",
            "longitude": "-79.347015",
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid())

        job = serializer.save()
        self.assertEqual(float(job.latitude), 43.651070)
        self.assertEqual(float(job.longitude), -79.347015)

    def test_create_job_negative_budget_validation(self):
        """Test job budget must be positive."""
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "-10.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("estimated_budget", serializer.errors)

    def test_create_job_invalid_category_validation(self):
        """Test job with invalid category fails."""
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": "00000000-0000-0000-0000-000000000000",
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("category_id", serializer.errors)

    def test_create_job_inactive_category_validation(self):
        """Test job with inactive category fails."""
        inactive_category = JobCategory.objects.create(
            name="Inactive", slug="inactive", is_active=False
        )
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(inactive_category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("category_id", serializer.errors)

    def test_create_job_invalid_city_validation(self):
        """Test job with invalid city fails."""
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": "00000000-0000-0000-0000-000000000000",
            "address": "123 Main St",
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("city_id", serializer.errors)

    def test_create_job_inactive_city_validation(self):
        """Test job with inactive city fails."""
        inactive_city = City.objects.create(
            name="Inactive",
            province="Test",
            province_code="TS",
            slug="inactive-ts",
            is_active=False,
        )
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(inactive_city.public_id),
            "address": "123 Main St",
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("city_id", serializer.errors)

    def test_create_job_latitude_without_longitude_validation(self):
        """Test job with latitude but no longitude fails."""
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "latitude": "43.651070",
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_create_job_invalid_latitude_validation(self):
        """Test job with invalid latitude fails."""
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "latitude": "91.0",
            "longitude": "-79.347015",
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("latitude", serializer.errors)

    def test_create_job_invalid_longitude_validation(self):
        """Test job with invalid longitude fails."""
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "latitude": "43.651070",
            "longitude": "181.0",
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("longitude", serializer.errors)

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

        image2_io = BytesIO()
        pil_image2 = PILImage.new("RGB", (100, 100), color="blue")
        pil_image2.save(image2_io, format="JPEG")
        image2_io.seek(0)
        image2 = SimpleUploadedFile(
            "test2.jpg", image2_io.getvalue(), content_type="image/jpeg"
        )

        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "images": [image1, image2],
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid())

        job = serializer.save()
        self.assertEqual(job.images.count(), 2)
        self.assertEqual(job.images.first().order, 0)
        self.assertEqual(job.images.last().order, 1)

    def test_create_job_max_images_validation(self):
        """Test job cannot have more than 10 images."""
        # Create 11 test images
        images = []
        for i in range(11):
            image_io = BytesIO()
            pil_image = PILImage.new("RGB", (100, 100), color="red")
            pil_image.save(image_io, format="JPEG")
            image_io.seek(0)
            images.append(
                SimpleUploadedFile(
                    f"test{i}.jpg", image_io.getvalue(), content_type="image/jpeg"
                )
            )

        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "images": images,
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("images", serializer.errors)
