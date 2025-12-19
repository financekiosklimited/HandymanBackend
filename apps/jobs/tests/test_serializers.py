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

    def test_my_application_null_when_not_applied(self):
        """Test my_application is None when handyman has not applied."""
        request = self.factory.get("/")
        request.user = self.handyman

        from apps.jobs.serializers import HandymanJobDetailSerializer

        serializer = HandymanJobDetailSerializer(self.job, context={"request": request})

        self.assertIsNone(serializer.data["my_application"])


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

    def test_handyman_profile_included_when_exists(self):
        """Test handyman profile is included in serialization."""
        from apps.jobs.models import JobApplication
        from apps.jobs.serializers import HomeownerJobApplicationListSerializer

        application = JobApplication.objects.create(
            job=self.job, handyman=self.handyman, status="pending"
        )

        serializer = HomeownerJobApplicationListSerializer(application)
        data = serializer.data

        self.assertIn("handyman_profile", data)
        self.assertIsNotNone(data["handyman_profile"])
        self.assertEqual(data["handyman_profile"]["display_name"], "Test Handyman")
