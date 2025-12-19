from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image as PILImage
from rest_framework.test import APIRequestFactory

from apps.accounts.models import User
from apps.jobs.models import (
    MAX_JOB_ITEM_LENGTH,
    MAX_JOB_ITEMS,
    City,
    Job,
    JobCategory,
    JobImage,
)
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
            email="homeowner@example.com",
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
            homeowner=self.user,
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
            email="homeowner@example.com",
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
            homeowner=self.user,
            title="Fix leaking faucet",
            description="Kitchen faucet is leaking",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
            job_items=["Check pipes", "Replace washer"],
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

        # Check job_items
        self.assertIn("job_items", data)
        self.assertEqual(data["job_items"], ["Check pipes", "Replace washer"])


class JobDetailSerializerTests(TestCase):
    """Test cases for JobDetailSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="homeowner@example.com",
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
            homeowner=self.user,
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
            email="homeowner@example.com",
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
        self.assertEqual(job.homeowner, self.user)
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

    def test_validate_images_max_count_exceeds(self):
        """Test validation fails with too many images."""
        import io

        from PIL import Image

        from apps.jobs.serializers import JobCreateSerializer

        def create_image():
            file_obj = io.BytesIO()
            image = Image.new("RGBA", size=(100, 100), color=(155, 0, 0))
            image.save(file_obj, "png")
            file_obj.seek(0)
            return SimpleUploadedFile(
                "test.png", file_obj.read(), content_type="image/png"
            )

        images = [create_image() for i in range(11)]
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
        self.assertIn(
            "ensure this field has no more than 10 elements",
            str(serializer.errors["images"]).lower(),
        )

    def test_validate_images_invalid_type(self):
        """Test validation fails with invalid image type."""
        import io

        from PIL import Image

        from apps.jobs.serializers import JobCreateSerializer

        # Create a valid image but with wrong content type
        file_obj = io.BytesIO()
        image = Image.new("RGBA", size=(100, 100), color=(155, 0, 0))
        image.save(file_obj, "png")
        file_obj.seek(0)

        image_file = SimpleUploadedFile(
            "test.png", file_obj.read(), content_type="image/bmp"
        )
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "images": [image_file],
        }
        serializer = JobCreateSerializer(data=data, context={"request": self.request})

        from rest_framework import serializers

        # Manually call validate_images
        try:
            serializer.validate_images([image_file])
            self.fail("ValidationError not raised for invalid content type")
        except serializers.ValidationError as e:
            self.assertIn("must be a JPEG or PNG file", str(e))

        # Also test image size
        large_file = SimpleUploadedFile(
            "large.png", b"x" * (6 * 1024 * 1024), content_type="image/png"
        )
        try:
            serializer.validate_images([large_file])
            self.fail("ValidationError not raised for large image")
        except serializers.ValidationError as e:
            self.assertIn("exceeds maximum size of 5MB", str(e))

        # Also test max count
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.validate_images([image_file] * 11)
        self.assertIn("Maximum 10 images allowed", str(cm.exception))

    def test_validate_job_items(self):
        """Test validation and cleaning of job items."""
        from apps.jobs.serializers import JobCreateSerializer

        serializer = JobCreateSerializer(context={"request": self.request})

        items = ["  Task 1  ", "", "Task 2", "   "]
        cleaned = serializer.validate_job_items(items)
        self.assertEqual(cleaned, ["Task 1", "Task 2"])

        self.assertEqual(serializer.validate_job_items([]), [])
        self.assertEqual(serializer.validate_job_items(None), [])


class JobUpdateSerializerTests(TestCase):
    """Test cases for JobUpdateSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="owner@example.com", password="password"
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
            homeowner=self.user,
            title="Old Title",
            description="Old Desc",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Old St",
            status="open",
        )
        from unittest.mock import MagicMock

        self.request = MagicMock()
        self.request.user = self.user

    def test_update_category_city(self):
        """Test updating category and city."""
        from apps.jobs.serializers import JobUpdateSerializer

        new_category = JobCategory.objects.create(name="Electrical", slug="electrical")
        new_city = City.objects.create(
            name="Ottawa", province="Ontario", province_code="ON", slug="ottawa-on"
        )

        data = {
            "category_id": str(new_category.public_id),
            "city_id": str(new_city.public_id),
        }
        serializer = JobUpdateSerializer(self.job, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_job = serializer.save()
        self.assertEqual(updated_job.category, new_category)
        self.assertEqual(updated_job.city, new_city)

    def test_validate_inactive_category_city(self):
        """Test validation for inactive category/city in update."""
        from apps.jobs.serializers import JobUpdateSerializer

        inactive_cat = JobCategory.objects.create(
            name="Inactive", slug="inactive", is_active=False
        )
        inactive_city = City.objects.create(
            name="Inactive", slug="inactive-city", is_active=False
        )

        serializer = JobUpdateSerializer(
            self.job, data={"category_id": str(inactive_cat.public_id)}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("category_id", serializer.errors)

        serializer = JobUpdateSerializer(
            self.job, data={"city_id": str(inactive_city.public_id)}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("city_id", serializer.errors)

    def test_update_validate_postal_code_invalid(self):
        """Test postal code validation in update."""
        from apps.jobs.serializers import JobUpdateSerializer

        serializer = JobUpdateSerializer(
            self.job, data={"postal_code": "INVALID"}, partial=True
        )
        self.assertFalse(serializer.is_valid())

        # Branch for invalid pattern
        serializer = JobUpdateSerializer(
            self.job, data={"postal_code": "1A1A1A"}, partial=True
        )
        self.assertFalse(serializer.is_valid())

    def test_validate_coordinates_update(self):
        """Test coordinate validation during update."""
        from apps.jobs.serializers import JobUpdateSerializer

        # Update only latitude, should fail because longitude is missing on instance
        serializer = JobUpdateSerializer(
            self.job, data={"latitude": 43.0}, partial=True
        )
        self.assertFalse(serializer.is_valid())

        # Update both
        serializer = JobUpdateSerializer(
            self.job, data={"latitude": 43.0, "longitude": -79.0}, partial=True
        )
        self.assertTrue(serializer.is_valid())

        # Out of range
        serializer = JobUpdateSerializer(
            self.job, data={"latitude": 100.0}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        serializer = JobUpdateSerializer(
            self.job, data={"longitude": 200.0}, partial=True
        )
        self.assertFalse(serializer.is_valid())

    def test_validate_postal_code_invalid(self):
        """Test validation fails with invalid postal code."""
        from apps.jobs.serializers import JobCreateSerializer

        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "postal_code": "INVALID",
        }
        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("postal_code", serializer.errors)

        data["postal_code"] = "A1A 1A"  # Too short
        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())

        data["postal_code"] = "1A1 A1A"  # Invalid format
        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())

    def test_validate_coordinates_mismatch(self):
        """Test validation fails if only one coordinate is provided."""
        from apps.jobs.serializers import JobCreateSerializer

        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "latitude": 43.6532,
        }
        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_validate_coordinates_out_of_range(self):
        """Test validation fails with coordinates out of range."""
        from apps.jobs.serializers import JobCreateSerializer

        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "latitude": 100.0,
            "longitude": 45.0,
        }
        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("latitude", serializer.errors)

        data["latitude"] = 45.0
        data["longitude"] = 200.0
        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("longitude", serializer.errors)

    def test_create_job_with_job_items(self):
        """Test creating a job with job_items."""
        data = {
            "title": "Bathroom Renovation",
            "description": "Complete renovation",
            "estimated_budget": "1000.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "job_items": ["Remove old tiles", "Install new tiles", "Paint walls"],
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid())

        job = serializer.save()
        self.assertEqual(
            job.job_items, ["Remove old tiles", "Install new tiles", "Paint walls"]
        )

    def test_create_job_without_job_items(self):
        """Test creating a job without job_items defaults to empty list."""
        data = {
            "title": "Test Job",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid())

        job = serializer.save()
        self.assertEqual(job.job_items, [])

    def test_job_items_serialization_in_response(self):
        """Test job_items is included in serialized response."""
        job = Job.objects.create(
            homeowner=self.user,
            title="Test",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            job_items=["Task 1", "Task 2"],
        )

        serializer = JobDetailSerializer(job)
        data = serializer.data

        self.assertIn("job_items", data)
        self.assertEqual(data["job_items"], ["Task 1", "Task 2"])

    def test_job_items_max_items_validation(self):
        """Test job_items cannot exceed maximum number of items."""
        job_items = [f"Task {i}" for i in range(MAX_JOB_ITEMS + 1)]
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "job_items": job_items,
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("job_items", serializer.errors)

    def test_job_items_max_length_validation(self):
        """Test each job item cannot exceed maximum length."""
        long_item = "x" * (MAX_JOB_ITEM_LENGTH + 1)
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "job_items": [long_item],
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("job_items", serializer.errors)

    def test_job_items_strips_whitespace(self):
        """Test job_items strips whitespace from items."""
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "job_items": ["  Task with spaces  ", "Normal task"],
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid())

        job = serializer.save()
        self.assertEqual(job.job_items, ["Task with spaces", "Normal task"])

    def test_job_items_removes_empty_strings(self):
        """Test job_items removes empty strings after stripping."""
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "job_items": ["Valid task", "", "  ", "Another valid task"],
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid())

        job = serializer.save()
        self.assertEqual(job.job_items, ["Valid task", "Another valid task"])


class HandymanJobDetailSerializerTests(TestCase):
    """Test cases for HandymanJobDetailSerializer."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
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
        self.factory = APIRequestFactory()

    def test_has_applied_true_when_applied(self):
        """Test has_applied is True when handyman has applied."""
        from apps.jobs.models import JobApplication

        JobApplication.objects.create(
            job=self.job, handyman=self.handyman, status="pending"
        )

        request = self.factory.get("/")
        request.user = self.handyman

        from apps.jobs.serializers import HandymanJobDetailSerializer

        serializer = HandymanJobDetailSerializer(self.job, context={"request": request})

        self.assertTrue(serializer.data["has_applied"])

    def test_has_applied_false_when_not_applied(self):
        """Test has_applied is False when handyman has not applied."""
        request = self.factory.get("/")
        request.user = self.handyman

        from apps.jobs.serializers import HandymanJobDetailSerializer

        serializer = HandymanJobDetailSerializer(self.job, context={"request": request})

        self.assertFalse(serializer.data["has_applied"])

    def test_my_application_returned_when_exists(self):
        """Test my_application is returned when handyman has applied."""
        from apps.jobs.models import JobApplication

        application = JobApplication.objects.create(
            job=self.job, handyman=self.handyman, status="pending"
        )

        request = self.factory.get("/")
        request.user = self.handyman

        from apps.jobs.serializers import HandymanJobDetailSerializer

        serializer = HandymanJobDetailSerializer(self.job, context={"request": request})

        self.assertIsNotNone(serializer.data["my_application"])
        self.assertEqual(
            serializer.data["my_application"]["public_id"], str(application.public_id)
        )

    def test_get_has_applied_anonymous(self):
        """Test has_applied is False for anonymous user."""
        from apps.jobs.serializers import HandymanJobDetailSerializer

        request = self.factory.get("/")
        request.user = type("AnonymousUser", (), {"is_authenticated": False})()
        serializer = HandymanJobDetailSerializer(self.job, context={"request": request})
        self.assertFalse(serializer.data["has_applied"])

    def test_get_my_application_anonymous(self):
        """Test my_application is None for anonymous user."""
        from apps.jobs.serializers import HandymanJobDetailSerializer

        request = self.factory.get("/")
        request.user = type("AnonymousUser", (), {"is_authenticated": False})()
        serializer = HandymanJobDetailSerializer(self.job, context={"request": request})
        self.assertIsNone(serializer.data["my_application"])

    def test_get_has_applied_no_request(self):
        """Test has_applied is False when no request in context."""
        from apps.jobs.serializers import HandymanJobDetailSerializer

        serializer = HandymanJobDetailSerializer(self.job, context={})
        self.assertFalse(serializer.data["has_applied"])


class JobCreateSerializerValidationTests(TestCase):
    """Test cases for JobCreateSerializer validation edge cases."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
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
        self.factory = APIRequestFactory()
        self.request = self.factory.post("/")
        self.request.user = self.user

    def test_validate_images_max_10(self):
        """Test validation fails with more than 10 images."""
        images = []
        for i in range(11):
            image = PILImage.new("RGB", (100, 100), color="red")
            image_file = BytesIO()
            image.save(image_file, format="JPEG")
            image_file.seek(0)
            images.append(
                SimpleUploadedFile(
                    f"image{i}.jpg", image_file.read(), content_type="image/jpeg"
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

        from apps.jobs.serializers import JobCreateSerializer

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("images", serializer.errors)

    def test_validate_images_content_type(self):
        """Test validation fails with invalid image content type."""
        # Create a text file pretending to be an image
        text_file = SimpleUploadedFile(
            "not_image.txt", b"This is not an image", content_type="text/plain"
        )

        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "images": [text_file],
        }

        from apps.jobs.serializers import JobCreateSerializer

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("images", serializer.errors)

    def test_validate_postal_code_invalid_format(self):
        """Test postal code validation with invalid format."""
        invalid_codes = ["12345", "ABCDEF", "A1A-1A1", "A1A 1A1A"]

        from apps.jobs.serializers import JobCreateSerializer

        for code in invalid_codes:
            data = {
                "title": "Test",
                "description": "Test",
                "estimated_budget": "50.00",
                "category_id": str(self.category.public_id),
                "city_id": str(self.city.public_id),
                "address": "123 Main St",
                "postal_code": code,
            }

            serializer = JobCreateSerializer(
                data=data, context={"request": self.request}
            )
            self.assertFalse(
                serializer.is_valid(), f"Should fail for postal code: {code}"
            )
            self.assertIn("postal_code", serializer.errors)

    def test_validate_postal_code_wrong_length(self):
        """Test postal code validation with wrong length."""
        from apps.jobs.serializers import JobCreateSerializer

        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "postal_code": "A1A",  # Too short
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("postal_code", serializer.errors)

    def test_validate_postal_code_formatting(self):
        """Test postal code formatting (returns with space)."""
        from apps.jobs.serializers import JobCreateSerializer

        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "postal_code": "m5h2n2",
        }
        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["postal_code"], "M5H 2N2")

    def test_validate_postal_code_none(self):
        """Test postal code None branch."""
        from apps.jobs.serializers import JobCreateSerializer

        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "postal_code": "",
        }
        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data.get("postal_code"), "")

    def test_validate_inactive_category(self):
        """Test validation fails with inactive category."""
        from apps.jobs.serializers import JobCreateSerializer

        inactive_cat = JobCategory.objects.create(
            name="Inactive", slug="inactive", is_active=False
        )
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(inactive_cat.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
        }
        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("category_id", serializer.errors)
        self.assertIn("not active", str(serializer.errors["category_id"]))

    def test_validate_invalid_category(self):
        """Test validation fails with non-existent category."""
        import uuid

        from apps.jobs.serializers import JobCreateSerializer

        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(uuid.uuid4()),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
        }
        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("category_id", serializer.errors)
        self.assertIn("Invalid category", str(serializer.errors["category_id"]))

    def test_validate_inactive_city(self):
        """Test validation fails with inactive city."""
        from apps.jobs.serializers import JobCreateSerializer

        inactive_city = City.objects.create(
            name="Inactive City", slug="inactive-city", is_active=False
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
        self.assertIn("not active", str(serializer.errors["city_id"]))

    def test_validate_invalid_city(self):
        """Test validation fails with non-existent city."""
        import uuid

        from apps.jobs.serializers import JobCreateSerializer

        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(uuid.uuid4()),
            "address": "123 Main St",
        }
        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("city_id", serializer.errors)
        self.assertIn("Invalid city", str(serializer.errors["city_id"]))

    def test_validate_job_items_empty_returns_empty_list(self):
        """Test empty job_items returns empty list."""
        from apps.jobs.serializers import JobCreateSerializer

        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "job_items": [],
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid())
        job = serializer.save()
        self.assertEqual(job.job_items, [])


class JobUpdateSerializerValidationTests(TestCase):
    """Test cases for JobUpdateSerializer validation edge cases."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        self.category = JobCategory.objects.create(
            name="Plumbing", slug="plumbing", is_active=True
        )
        self.inactive_category = JobCategory.objects.create(
            name="Inactive", slug="inactive", is_active=False
        )
        self.city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            is_active=True,
        )
        self.inactive_city = City.objects.create(
            name="Inactive",
            province="Test",
            province_code="TS",
            slug="inactive-ts",
            is_active=False,
        )
        self.job = Job.objects.create(
            homeowner=self.user,
            title="Test Job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        self.factory = APIRequestFactory()
        self.request = self.factory.patch("/")
        self.request.user = self.user

    def test_update_with_inactive_category_fails(self):
        """Test updating job with inactive category fails."""
        from apps.jobs.serializers import JobUpdateSerializer

        data = {"category_id": str(self.inactive_category.public_id)}

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("category_id", serializer.errors)

    def test_update_with_inactive_city_fails(self):
        """Test updating job with inactive city fails."""
        from apps.jobs.serializers import JobUpdateSerializer

        data = {"city_id": str(self.inactive_city.public_id)}

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("city_id", serializer.errors)

    def test_update_with_nonexistent_city_fails(self):
        """Test updating job with non-existent city fails."""
        import uuid

        from apps.jobs.serializers import JobUpdateSerializer

        data = {"city_id": str(uuid.uuid4())}

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("city_id", serializer.errors)

    def test_update_postal_code_validation(self):
        """Test postal code validation in update."""
        from apps.jobs.serializers import JobUpdateSerializer

        data = {"postal_code": "INVALID"}

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("postal_code", serializer.errors)

    def test_update_coordinate_cross_validation_latitude_only(self):
        """Test updating only latitude when instance has longitude."""
        from apps.jobs.serializers import JobUpdateSerializer

        # Set job with coordinates
        self.job.latitude = Decimal("43.651070")
        self.job.longitude = Decimal("-79.347015")
        self.job.save()

        data = {"latitude": "44.0"}

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())

    def test_update_coordinate_cross_validation_longitude_only(self):
        """Test updating only longitude when instance has latitude."""
        from apps.jobs.serializers import JobUpdateSerializer

        # Set job with coordinates
        self.job.latitude = Decimal("43.651070")
        self.job.longitude = Decimal("-79.347015")
        self.job.save()

        data = {"longitude": "-80.0"}

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())

    def test_update_coordinate_range_validation(self):
        """Test coordinate range validation in update."""
        from apps.jobs.serializers import JobUpdateSerializer

        data = {"latitude": "91.0", "longitude": "-79.0"}

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("latitude", serializer.errors)

    def test_update_empty_job_items(self):
        """Test updating with empty job_items."""
        from apps.jobs.serializers import JobUpdateSerializer

        data = {"job_items": []}

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())

    def test_update_postal_code_formatting(self):
        """Test postal code formatting in update."""
        from apps.jobs.serializers import JobUpdateSerializer

        data = {"postal_code": "a1a1a1"}

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["postal_code"], "A1A 1A1")

    def test_update_postal_code_none(self):
        """Test postal code None branch in update."""
        from apps.jobs.serializers import JobUpdateSerializer

        data = {"postal_code": ""}

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data.get("postal_code"), "")

    def test_update_coordinate_range_validation_latitude_out_of_range(self):
        """Test latitude range validation in update."""
        from apps.jobs.serializers import JobUpdateSerializer

        data = {"latitude": "91.0", "longitude": "-79.0"}

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("latitude", serializer.errors)

    def test_update_coordinate_range_validation_longitude_out_of_range(self):
        """Test longitude range validation in update."""
        from apps.jobs.serializers import JobUpdateSerializer

        data = {"latitude": "45.0", "longitude": "181.0"}

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("longitude", serializer.errors)

    def test_update_coordinate_branch_coverage(self):
        """Test branch coverage for coordinates in update."""
        from apps.jobs.serializers import JobUpdateSerializer

        # 1. Instance has NO coordinates, updating only latitude -> should fail cross-validation
        self.job.latitude = None
        self.job.longitude = None
        self.job.save()

        data = {"latitude": "45.0"}
        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())

        # 2. Instance has NO coordinates, updating only longitude -> should fail cross-validation
        data = {"longitude": "-79.0"}
        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())

        # 3. Instance has coordinates, updating latitude to None -> should fail cross-validation
        self.job.latitude = Decimal("45.0")
        self.job.longitude = Decimal("-79.0")
        self.job.save()

        data = {"latitude": None}
        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())

        # 4. Instance has coordinates, updating longitude to None -> should fail cross-validation
        data = {"longitude": None}
        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())

        # 5. Coordinate update without instance (JobUpdateSerializer(data=...))
        # Note: JobUpdateSerializer is typically used with an instance, but let's test this branch.
        data = {"latitude": "45.0"}
        serializer = JobUpdateSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        data = {"longitude": "-79.0"}
        serializer = JobUpdateSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())

        # 6. Valid coordinate update with instance
        self.job.latitude = Decimal("45.0")
        self.job.longitude = Decimal("-79.0")
        self.job.save()
        data = {"latitude": "46.0", "longitude": "-80.0"}
        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())


class JobApplicationCreateSerializerTests(TestCase):
    """Test cases for JobApplicationCreateSerializer."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
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
        self.factory = APIRequestFactory()

    def test_create_with_nonexistent_job_fails(self):
        """Test creating application with non-existent job fails."""
        import uuid

        from apps.jobs.serializers import JobApplicationCreateSerializer

        request = self.factory.post("/")
        request.user = self.handyman

        data = {"job_id": str(uuid.uuid4())}

        serializer = JobApplicationCreateSerializer(
            data=data, context={"request": request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("job_id", serializer.errors)

    def test_create_calls_service(self):
        """Test create method calls JobApplicationService."""
        from unittest.mock import MagicMock, patch

        from apps.jobs.serializers import JobApplicationCreateSerializer

        request = self.factory.post("/")
        request.user = self.handyman

        data = {"job_id": str(self.job.public_id)}

        mock_application = MagicMock()

        with patch(
            "apps.jobs.services.JobApplicationService.apply_to_job"
        ) as mock_apply:
            mock_apply.return_value = mock_application

            serializer = JobApplicationCreateSerializer(
                data=data, context={"request": request}
            )
            self.assertTrue(serializer.is_valid())
            application = serializer.save()

            mock_apply.assert_called_once_with(handyman=self.handyman, job=self.job)
            self.assertEqual(application, mock_application)


class HomeownerJobApplicationListSerializerTests(TestCase):
    """Test cases for HomeownerJobApplicationListSerializer."""

    def setUp(self):
        """Set up test data."""
        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )

        from apps.profiles.models import HandymanProfile

        self.handyman_profile = HandymanProfile.objects.create(
            user=self.handyman, display_name="Test Handyman"
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
        from unittest.mock import MagicMock

        self.request = MagicMock()
        self.request.user = self.homeowner

    def test_handyman_profile_none(self):
        """Test handyman profile is None if not exists."""
        from apps.jobs.models import JobApplication
        from apps.jobs.serializers import HomeownerJobApplicationListSerializer

        # User without handyman profile
        other_user = User.objects.create_user(
            email="no-profile@example.com", password="password"
        )
        application = JobApplication.objects.create(
            job=self.job, handyman=other_user, status="pending"
        )

        serializer = HomeownerJobApplicationListSerializer(application)
        data = serializer.data

        self.assertIsNone(data["handyman_profile"])

    def test_handyman_profile_none_no_attribute(self):
        """Test handyman profile is None if attribute missing (e.g. patched user)."""
        from unittest.mock import MagicMock

        from apps.jobs.serializers import HomeownerJobApplicationListSerializer

        application = MagicMock()
        application.handyman = MagicMock(spec=[])  # No handyman_profile attribute

        serializer = HomeownerJobApplicationListSerializer(application)
        self.assertIsNone(serializer.get_handyman_profile(application))

    def test_validate_images_size_exceeds(self):
        """Test validation fails with large image."""
        from apps.jobs.serializers import JobCreateSerializer

        image_file = SimpleUploadedFile(
            "large.jpg", b"x" * (6 * 1024 * 1024), content_type="image/jpeg"
        )
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "images": [image_file],
        }
        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("images", serializer.errors)
