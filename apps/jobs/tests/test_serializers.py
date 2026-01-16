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
    JobAttachment,
    JobCategory,
    JobTask,
)
from apps.jobs.serializers import (
    CitySerializer,
    JobAttachmentSerializer,
    JobCategorySerializer,
    JobCreateSerializer,
    JobDetailSerializer,
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


class JobAttachmentSerializerTests(TestCase):
    """Test cases for JobAttachmentSerializer."""

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

    def test_job_attachment_serialization(self):
        """Test job attachment serialization."""
        # Create a simple test image
        image_io = BytesIO()
        pil_image = PILImage.new("RGB", (100, 100), color="red")
        pil_image.save(image_io, format="JPEG")
        image_io.seek(0)
        image_file = SimpleUploadedFile(
            "test.jpg", image_io.getvalue(), content_type="image/jpeg"
        )

        job_attachment = JobAttachment.objects.create(
            job=self.job,
            file=image_file,
            file_type="image",
            file_name="test.jpg",
            file_size=image_file.size,
            order=0,
        )
        serializer = JobAttachmentSerializer(job_attachment)
        data = serializer.data

        self.assertIn("public_id", data)
        self.assertIn("file_url", data)
        self.assertEqual(data["file_type"], "image")
        self.assertEqual(data["order"], 0)
        # In test environment, file URL may be relative or absolute
        self.assertIn("jobs/attachments/", data["file_url"])
        self.assertEqual(data["thumbnail_url"], data["file_url"])


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
        )
        # Create tasks for the job
        JobTask.objects.create(job=job, title="Check pipes", order=0)
        JobTask.objects.create(job=job, title="Replace washer", order=1)

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

        # Check attachments (should be empty list)
        self.assertIn("attachments", data)
        self.assertEqual(data["attachments"], [])

        # Check tasks
        self.assertIn("tasks", data)
        self.assertEqual(len(data["tasks"]), 2)
        self.assertEqual(data["tasks"][0]["title"], "Check pipes")
        self.assertEqual(data["tasks"][1]["title"], "Replace washer")


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

    def test_validate_attachments_empty_list(self):
        """Test empty attachments list returns empty list."""
        serializer = JobCreateSerializer(context={"request": self.request})
        self.assertEqual(serializer.validate_attachments([]), [])

    def test_validate_attachments_max_count_exceeds(self):
        """Test validation fails with too many attachments."""
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

        # New indexed format: list of dicts with file key
        attachments = [{"file": create_image()} for i in range(11)]
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "attachments": attachments,
        }
        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)
        # Error message changed - now validate_attachments checks count
        self.assertIn(
            "maximum 10 attachments allowed",
            str(serializer.errors["attachments"]).lower(),
        )

    def test_validate_attachments_invalid_type(self):
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
        # New indexed format
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "attachments": [{"file": image_file}],
        }
        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)
        # Error is now on the nested file field
        self.assertIn("unsupported file type", str(serializer.errors).lower())

        # Also test image size
        file_obj2 = io.BytesIO()
        image2 = Image.new("RGBA", size=(100, 100), color=(155, 0, 0))
        image2.save(file_obj2, "png")
        file_obj2.seek(0)
        valid_file = SimpleUploadedFile(
            "test.png", file_obj2.read(), content_type="image/png"
        )

        large_file = SimpleUploadedFile(
            "large.png", b"x" * (11 * 1024 * 1024), content_type="image/png"
        )
        data2 = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "attachments": [{"file": large_file}],
        }
        serializer2 = JobCreateSerializer(data=data2, context={"request": self.request})
        self.assertFalse(serializer2.is_valid())
        self.assertIn("exceeds maximum size of 10mb", str(serializer2.errors).lower())

        # Also test max count with new format
        attachments_11 = [{"file": valid_file} for _ in range(11)]
        data3 = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "attachments": attachments_11,
        }
        serializer3 = JobCreateSerializer(data=data3, context={"request": self.request})
        self.assertFalse(serializer3.is_valid())
        self.assertIn("Maximum 10 attachments allowed", str(serializer3.errors))

    def test_validate_tasks(self):
        """Test validation and cleaning of tasks."""
        from apps.jobs.serializers import JobCreateSerializer

        serializer = JobCreateSerializer(context={"request": self.request})

        tasks = [
            {"title": "  Task 1  "},
            {"title": ""},
            {"title": "Task 2"},
            {"title": "   "},
        ]
        cleaned = serializer.validate_tasks(tasks)
        self.assertEqual(cleaned, [{"title": "Task 1"}, {"title": "Task 2"}])

        self.assertEqual(serializer.validate_tasks([]), [])
        self.assertEqual(serializer.validate_tasks(None), [])


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

    def test_validate_attachments_empty_list(self):
        """Test empty attachments list returns empty list."""
        from apps.jobs.serializers import JobUpdateSerializer

        serializer = JobUpdateSerializer(self.job, data={}, partial=True)
        self.assertEqual(serializer.validate_attachments([]), [])

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

    def test_update_tasks_removes_empty_titles(self):
        """Test updating tasks removes entries with empty titles after stripping."""
        from apps.jobs.serializers import JobUpdateSerializer

        data = {
            "tasks": [
                {"title": "Valid task"},
                {"title": ""},
                {"title": "  "},
                {"title": "Another valid task"},
            ],
        }

        serializer = JobUpdateSerializer(self.job, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        updated_job = serializer.save()
        task_titles = list(updated_job.tasks.values_list("title", flat=True))
        self.assertEqual(task_titles, ["Valid task", "Another valid task"])

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

    def test_create_job_with_tasks(self):
        """Test creating a job with tasks."""
        data = {
            "title": "Bathroom Renovation",
            "description": "Complete renovation",
            "estimated_budget": "1000.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "tasks": [
                {"title": "Remove old tiles"},
                {"title": "Install new tiles"},
                {"title": "Paint walls"},
            ],
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid())

        job = serializer.save()
        self.assertEqual(job.tasks.count(), 3)
        task_titles = list(job.tasks.values_list("title", flat=True))
        self.assertEqual(
            task_titles, ["Remove old tiles", "Install new tiles", "Paint walls"]
        )

    def test_create_job_without_tasks(self):
        """Test creating a job without tasks defaults to empty."""
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
        self.assertEqual(job.tasks.count(), 0)

    def test_tasks_serialization_in_response(self):
        """Test tasks is included in serialized response."""
        job = Job.objects.create(
            homeowner=self.user,
            title="Test",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        JobTask.objects.create(job=job, title="Task 1", order=0)
        JobTask.objects.create(job=job, title="Task 2", order=1)

        serializer = JobDetailSerializer(job)
        data = serializer.data

        self.assertIn("tasks", data)
        self.assertEqual(len(data["tasks"]), 2)
        self.assertEqual(data["tasks"][0]["title"], "Task 1")
        self.assertEqual(data["tasks"][1]["title"], "Task 2")

    def test_tasks_max_items_validation(self):
        """Test tasks cannot exceed maximum number of items."""
        tasks = [{"title": f"Task {i}"} for i in range(MAX_JOB_ITEMS + 1)]
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "tasks": tasks,
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("tasks", serializer.errors)

    def test_tasks_max_length_validation(self):
        """Test each task title cannot exceed maximum length."""
        long_title = "x" * (MAX_JOB_ITEM_LENGTH + 1)
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "tasks": [{"title": long_title}],
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("tasks", serializer.errors)

    def test_tasks_strips_whitespace(self):
        """Test tasks strips whitespace from titles."""
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "tasks": [{"title": "  Task with spaces  "}, {"title": "Normal task"}],
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid())

        job = serializer.save()
        task_titles = list(job.tasks.values_list("title", flat=True))
        self.assertEqual(task_titles, ["Task with spaces", "Normal task"])

    def test_tasks_removes_empty_titles(self):
        """Test tasks removes entries with empty titles after stripping."""
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "tasks": [
                {"title": "Valid task"},
                {"title": ""},
                {"title": "  "},
                {"title": "Another valid task"},
            ],
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid())

        job = serializer.save()
        task_titles = list(job.tasks.values_list("title", flat=True))
        self.assertEqual(task_titles, ["Valid task", "Another valid task"])


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

    def test_validate_attachments_max_10(self):
        """Test validation fails with more than 10 attachments."""
        attachments = []
        for i in range(11):
            image = PILImage.new("RGB", (100, 100), color="red")
            image_file = BytesIO()
            image.save(image_file, format="JPEG")
            image_file.seek(0)
            attachments.append(
                {
                    "file": SimpleUploadedFile(
                        f"image{i}.jpg", image_file.read(), content_type="image/jpeg"
                    )
                }
            )

        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "attachments": attachments,
        }

        from apps.jobs.serializers import JobCreateSerializer

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)

    def test_validate_attachments_content_type(self):
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
            "attachments": [{"file": text_file}],
        }

        from apps.jobs.serializers import JobCreateSerializer

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)

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

    def test_validate_tasks_empty_returns_empty(self):
        """Test empty tasks returns empty and creates no tasks."""
        from apps.jobs.serializers import JobCreateSerializer

        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "tasks": [],
        }

        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertTrue(serializer.is_valid())
        job = serializer.save()
        self.assertEqual(job.tasks.count(), 0)


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

    def test_update_empty_tasks(self):
        """Test updating with empty tasks preserves existing tasks (no implicit delete)."""
        from apps.jobs.serializers import JobUpdateSerializer

        # First create some tasks
        JobTask.objects.create(job=self.job, title="Existing Task", order=0)
        self.assertEqual(self.job.tasks.count(), 1)

        # Empty tasks array should preserve existing tasks
        data = {"tasks": []}

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        job = serializer.save()
        # Tasks are preserved (no implicit delete)
        self.assertEqual(job.tasks.count(), 1)

    def test_update_tasks_replaces_all(self):
        """Test updating tasks with explicit deletes replaces specified tasks."""
        from apps.jobs.serializers import JobUpdateSerializer

        # First create some tasks
        task1 = JobTask.objects.create(job=self.job, title="Old Task 1", order=0)
        task2 = JobTask.objects.create(job=self.job, title="Old Task 2", order=1)
        self.assertEqual(self.job.tasks.count(), 2)

        # To replace all tasks, explicitly delete old ones and create new ones
        data = {
            "tasks": [
                {"public_id": str(task1.public_id), "_delete": True},
                {"public_id": str(task2.public_id), "_delete": True},
                {"title": "New Task 1"},
                {"title": "New Task 2"},
                {"title": "New Task 3"},
            ]
        }

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        job = serializer.save()
        self.assertEqual(job.tasks.count(), 3)
        task_titles = list(job.tasks.values_list("title", flat=True))
        self.assertEqual(task_titles, ["New Task 1", "New Task 2", "New Task 3"])

    def test_update_task_preserves_is_completed(self):
        """Test updating a task preserves its is_completed status."""
        from apps.jobs.serializers import JobUpdateSerializer

        # Create a completed task
        task = JobTask.objects.create(
            job=self.job, title="Completed Task", order=0, is_completed=True
        )

        # Update the title
        data = {
            "tasks": [
                {"public_id": str(task.public_id), "title": "Renamed Task"},
            ]
        }

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        serializer.save()

        task.refresh_from_db()
        self.assertEqual(task.title, "Renamed Task")
        self.assertTrue(task.is_completed)  # Preserved!

    def test_update_task_by_public_id(self):
        """Test updating an existing task by public_id."""
        from apps.jobs.serializers import JobUpdateSerializer

        task = JobTask.objects.create(
            job=self.job, title="Original Title", description="", order=0
        )
        original_public_id = task.public_id

        data = {
            "tasks": [
                {
                    "public_id": str(task.public_id),
                    "title": "Updated Title",
                    "description": "New description",
                },
            ]
        }

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        serializer.save()

        task.refresh_from_db()
        self.assertEqual(task.public_id, original_public_id)  # Same ID
        self.assertEqual(task.title, "Updated Title")
        self.assertEqual(task.description, "New description")

    def test_delete_task_by_public_id(self):
        """Test deleting a task using _delete flag."""
        from apps.jobs.serializers import JobUpdateSerializer

        task1 = JobTask.objects.create(job=self.job, title="Task 1", order=0)
        JobTask.objects.create(job=self.job, title="Task 2", order=1)

        data = {
            "tasks": [
                {"public_id": str(task1.public_id), "_delete": True},
            ]
        }

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        job = serializer.save()

        self.assertEqual(job.tasks.count(), 1)
        self.assertEqual(job.tasks.first().title, "Task 2")

    def test_mixed_task_operations(self):
        """Test creating, updating, and deleting tasks in one request."""
        from apps.jobs.serializers import JobUpdateSerializer

        JobTask.objects.create(job=self.job, title="Keep Me", order=0)
        task2 = JobTask.objects.create(job=self.job, title="Update Me", order=1)
        task3 = JobTask.objects.create(job=self.job, title="Delete Me", order=2)

        data = {
            "tasks": [
                {"public_id": str(task2.public_id), "title": "I Was Updated"},
                {"public_id": str(task3.public_id), "_delete": True},
                {"title": "I Am New"},
            ]
        }

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        job = serializer.save()

        self.assertEqual(job.tasks.count(), 3)  # 1 updated + 1 new + 1 preserved
        titles = list(job.tasks.order_by("order").values_list("title", flat=True))
        # Order: updated (idx 0), new (idx 2), preserved (moved to end)
        self.assertIn("I Was Updated", titles)
        self.assertIn("I Am New", titles)
        self.assertIn("Keep Me", titles)  # Preserved
        self.assertNotIn("Delete Me", titles)  # Deleted

    def test_validate_delete_without_public_id(self):
        """Test that _delete without public_id raises validation error."""
        from apps.jobs.serializers import JobUpdateSerializer

        data = {
            "tasks": [
                {"_delete": True},  # No public_id
            ]
        }

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("tasks", serializer.errors)

    def test_validate_invalid_public_id(self):
        """Test that invalid public_id raises validation error."""
        from uuid import uuid4

        from apps.jobs.serializers import JobUpdateSerializer

        data = {
            "tasks": [
                {"public_id": str(uuid4()), "title": "Should Fail"},
            ]
        }

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("tasks", serializer.errors)

    def test_omitted_tasks_preserved(self):
        """Test that tasks not in the update request are preserved."""
        from apps.jobs.serializers import JobUpdateSerializer

        JobTask.objects.create(job=self.job, title="Task 1", order=0)
        JobTask.objects.create(job=self.job, title="Task 2", order=1)

        # Only send one new task, don't mention existing tasks
        data = {
            "tasks": [
                {"title": "New Task"},
            ]
        }

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        job = serializer.save()

        # All 3 tasks should exist (2 preserved + 1 new)
        self.assertEqual(job.tasks.count(), 3)
        titles = list(job.tasks.values_list("title", flat=True))
        self.assertIn("Task 1", titles)
        self.assertIn("Task 2", titles)
        self.assertIn("New Task", titles)

    def test_update_task_description_only(self):
        """Test updating only a task's description without changing title."""
        from apps.jobs.serializers import JobUpdateSerializer

        task = JobTask.objects.create(
            job=self.job, title="Original Title", description="Old desc", order=0
        )

        # Update only description, no title field
        data = {
            "tasks": [
                {
                    "public_id": str(task.public_id),
                    "description": "New description",
                },
            ]
        }

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        serializer.save()

        task.refresh_from_db()
        self.assertEqual(task.title, "Original Title")  # Unchanged
        self.assertEqual(task.description, "New description")

    def test_validate_tasks_without_instance(self):
        """Test validate_tasks returns value as-is when no instance."""
        from apps.jobs.serializers import JobUpdateSerializer

        # Create serializer without instance
        serializer = JobUpdateSerializer(data={})
        # Manually call validate_tasks without instance
        result = serializer.validate_tasks([{"title": "Test"}])
        self.assertEqual(result, [{"title": "Test"}])

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

    def test_update_coordinate_none_explicit(self):
        """Test explicitly setting both coordinates to None."""
        from apps.jobs.serializers import JobUpdateSerializer

        # Set job with coordinates
        self.job.latitude = Decimal("43.651070")
        self.job.longitude = Decimal("-79.347015")
        self.job.save()

        data = {"latitude": None, "longitude": None}

        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_job = serializer.save()
        self.assertIsNone(updated_job.latitude)
        self.assertIsNone(updated_job.longitude)

    def test_update_coordinate_validation_skips_when_not_in_attrs(self):
        """Test that coordinate validation is skipped when neither is in attrs."""
        from apps.jobs.serializers import JobUpdateSerializer

        data = {"title": "New Title"}
        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())

    def test_update_add_attachments_success(self):
        """Test adding attachments to a job with no existing attachments succeeds."""
        from apps.jobs.serializers import JobUpdateSerializer

        image = PILImage.new("RGB", (100, 100), color="red")
        image_file = BytesIO()
        image.save(image_file, format="JPEG")
        image_file.seek(0)
        uploaded_image = SimpleUploadedFile(
            "test.jpg", image_file.read(), content_type="image/jpeg"
        )

        data = {"attachments": [{"file": uploaded_image}]}
        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_job = serializer.save()

        self.assertEqual(updated_job.attachments.count(), 1)
        self.assertEqual(updated_job.attachments.first().order, 0)

    def test_update_remove_attachments_success(self):
        """Test removing existing attachments works correctly."""
        from apps.jobs.serializers import JobUpdateSerializer

        # Create an existing image
        image = PILImage.new("RGB", (100, 100), color="blue")
        image_file = BytesIO()
        image.save(image_file, format="JPEG")
        image_file.seek(0)
        uploaded_image = SimpleUploadedFile(
            "existing.jpg", image_file.read(), content_type="image/jpeg"
        )
        job_attachment = JobAttachment.objects.create(
            job=self.job,
            file=uploaded_image,
            file_type="image",
            file_name=uploaded_image.name,
            file_size=uploaded_image.size,
            order=0,
        )

        self.assertEqual(self.job.attachments.count(), 1)

        data = {"attachments_to_remove": [str(job_attachment.public_id)]}
        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_job = serializer.save()

        self.assertEqual(updated_job.attachments.count(), 0)

    def test_update_add_and_remove_attachments(self):
        """Test adding and removing attachments in same request works."""
        from apps.jobs.serializers import JobUpdateSerializer

        # Create existing attachments
        for i in range(3):
            image = PILImage.new("RGB", (100, 100), color="blue")
            image_file = BytesIO()
            image.save(image_file, format="JPEG")
            image_file.seek(0)
            uploaded_image = SimpleUploadedFile(
                f"existing{i}.jpg", image_file.read(), content_type="image/jpeg"
            )
            JobAttachment.objects.create(
                job=self.job,
                file=uploaded_image,
                file_type="image",
                file_name=uploaded_image.name,
                file_size=uploaded_image.size,
                order=i,
            )

        self.assertEqual(self.job.attachments.count(), 3)
        image_to_remove = self.job.attachments.first()

        # Create new image to add
        new_image = PILImage.new("RGB", (100, 100), color="green")
        new_image_file = BytesIO()
        new_image.save(new_image_file, format="JPEG")
        new_image_file.seek(0)
        new_uploaded_image = SimpleUploadedFile(
            "new.jpg", new_image_file.read(), content_type="image/jpeg"
        )

        data = {
            "attachments": [{"file": new_uploaded_image}],
            "attachments_to_remove": [str(image_to_remove.public_id)],
        }
        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_job = serializer.save()

        # 3 - 1 + 1 = 3
        self.assertEqual(updated_job.attachments.count(), 3)

    def test_update_attachments_total_count_exceeded(self):
        """Test adding attachments that would exceed 10 total fails validation."""
        from apps.jobs.serializers import JobUpdateSerializer

        # Create 8 existing attachments
        for i in range(8):
            image = PILImage.new("RGB", (100, 100), color="blue")
            image_file = BytesIO()
            image.save(image_file, format="JPEG")
            image_file.seek(0)
            uploaded_image = SimpleUploadedFile(
                f"existing{i}.jpg", image_file.read(), content_type="image/jpeg"
            )
            JobAttachment.objects.create(
                job=self.job,
                file=uploaded_image,
                file_type="image",
                file_name=uploaded_image.name,
                file_size=uploaded_image.size,
                order=i,
            )

        self.assertEqual(self.job.attachments.count(), 8)

        # Try to add 5 more (8 + 5 = 13 > 10)
        new_attachments = []
        for i in range(5):
            new_image = PILImage.new("RGB", (100, 100), color="green")
            new_image_file = BytesIO()
            new_image.save(new_image_file, format="JPEG")
            new_image_file.seek(0)
            new_attachments.append(
                {
                    "file": SimpleUploadedFile(
                        f"new{i}.jpg", new_image_file.read(), content_type="image/jpeg"
                    )
                }
            )

        data = {"attachments": new_attachments}
        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)
        self.assertIn(
            "Maximum 10 attachments allowed", str(serializer.errors["attachments"])
        )

    def test_update_attachments_with_removal_under_limit(self):
        """Test removing some + adding some that stays under 10 succeeds."""
        from apps.jobs.serializers import JobUpdateSerializer

        # Create 9 existing attachments
        for i in range(9):
            image = PILImage.new("RGB", (100, 100), color="blue")
            image_file = BytesIO()
            image.save(image_file, format="JPEG")
            image_file.seek(0)
            uploaded_image = SimpleUploadedFile(
                f"existing{i}.jpg", image_file.read(), content_type="image/jpeg"
            )
            JobAttachment.objects.create(
                job=self.job,
                file=uploaded_image,
                file_type="image",
                file_name=uploaded_image.name,
                file_size=uploaded_image.size,
                order=i,
            )

        self.assertEqual(self.job.attachments.count(), 9)

        # Remove 2, add 3: 9 - 2 + 3 = 10 (exactly at limit)
        attachments_to_remove = [
            str(img.public_id) for img in self.job.attachments.all()[:2]
        ]

        new_attachments = []
        for i in range(3):
            new_image = PILImage.new("RGB", (100, 100), color="green")
            new_image_file = BytesIO()
            new_image.save(new_image_file, format="JPEG")
            new_image_file.seek(0)
            new_attachments.append(
                {
                    "file": SimpleUploadedFile(
                        f"new{i}.jpg", new_image_file.read(), content_type="image/jpeg"
                    )
                }
            )

        data = {
            "attachments": new_attachments,
            "attachments_to_remove": attachments_to_remove,
        }
        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_job = serializer.save()

        self.assertEqual(updated_job.attachments.count(), 10)

    def test_update_attachments_invalid_size(self):
        """Test image over 10MB fails validation."""
        from apps.jobs.serializers import JobUpdateSerializer

        # Create a minimal valid 1x1 PNG image
        tiny_image = PILImage.new("RGB", (1, 1), color="red")
        image_file = BytesIO()
        tiny_image.save(image_file, format="PNG")
        image_file.seek(0)
        image_content = image_file.read()

        # Create a mock file object that reports size > 10MB but has valid image content
        large_file = SimpleUploadedFile(
            "large.png", image_content, content_type="image/png"
        )
        # Override the size attribute to simulate a large file
        large_file.size = 11 * 1024 * 1024

        data = {"attachments": [{"file": large_file}]}
        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)
        self.assertIn(
            "exceeds maximum size of 10MB", str(serializer.errors["attachments"])
        )

    def test_update_attachments_invalid_type(self):
        """Test non-JPEG/PNG image fails validation."""
        from apps.jobs.serializers import JobUpdateSerializer

        # Create image with invalid content type
        image = PILImage.new("RGB", (100, 100), color="red")
        image_file = BytesIO()
        image.save(image_file, format="JPEG")
        image_file.seek(0)
        invalid_type_image = SimpleUploadedFile(
            "test.bmp", image_file.read(), content_type="image/bmp"
        )

        data = {"attachments": [{"file": invalid_type_image}]}
        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)
        self.assertIn("unsupported file type", str(serializer.errors).lower())

    def test_update_remove_nonexistent_attachments(self):
        """Test removing UUIDs that don't exist doesn't cause errors."""
        import uuid

        from apps.jobs.serializers import JobUpdateSerializer

        # Create one existing image
        image = PILImage.new("RGB", (100, 100), color="blue")
        image_file = BytesIO()
        image.save(image_file, format="JPEG")
        image_file.seek(0)
        uploaded_image = SimpleUploadedFile(
            "existing.jpg", image_file.read(), content_type="image/jpeg"
        )
        JobAttachment.objects.create(
            job=self.job,
            file=uploaded_image,
            file_type="image",
            file_name=uploaded_image.name,
            file_size=uploaded_image.size,
            order=0,
        )

        self.assertEqual(self.job.attachments.count(), 1)

        # Try to remove a non-existent UUID
        data = {"attachments_to_remove": [str(uuid.uuid4())]}
        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_job = serializer.save()

        # Image count should remain unchanged
        self.assertEqual(updated_job.attachments.count(), 1)

    def test_update_attachments_order_calculation(self):
        """Test new attachments get correct order values after existing attachments."""
        from apps.jobs.serializers import JobUpdateSerializer

        # Create existing attachments with orders 0, 1, 2
        for i in range(3):
            image = PILImage.new("RGB", (100, 100), color="blue")
            image_file = BytesIO()
            image.save(image_file, format="JPEG")
            image_file.seek(0)
            uploaded_image = SimpleUploadedFile(
                f"existing{i}.jpg", image_file.read(), content_type="image/jpeg"
            )
            JobAttachment.objects.create(
                job=self.job,
                file=uploaded_image,
                file_type="image",
                file_name=uploaded_image.name,
                file_size=uploaded_image.size,
                order=i,
            )

        # Add 2 new attachments
        new_attachments = []
        for i in range(2):
            new_image = PILImage.new("RGB", (100, 100), color="green")
            new_image_file = BytesIO()
            new_image.save(new_image_file, format="JPEG")
            new_image_file.seek(0)
            new_attachments.append(
                {
                    "file": SimpleUploadedFile(
                        f"new{i}.jpg", new_image_file.read(), content_type="image/jpeg"
                    )
                }
            )

        data = {"attachments": new_attachments}
        serializer = JobUpdateSerializer(
            self.job, data=data, partial=True, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_job = serializer.save()

        self.assertEqual(updated_job.attachments.count(), 5)

        # Check that new attachments have orders 3 and 4
        orders = list(
            updated_job.attachments.order_by("order").values_list("order", flat=True)
        )
        self.assertEqual(orders, [0, 1, 2, 3, 4])


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

        data = {
            "job_id": str(self.job.public_id),
            "predicted_hours": "8.5",
            "estimated_total_price": "450.00",
        }

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

            mock_apply.assert_called_once_with(
                handyman=self.handyman,
                job=self.job,
                predicted_hours=Decimal("8.5"),
                estimated_total_price=Decimal("450.00"),
                negotiation_reasoning="",
                materials_data=[],
                attachments=[],
            )
            self.assertEqual(application, mock_application)

    def test_create_with_materials_and_attachments(self):
        """Test create with materials and attachments."""
        from unittest.mock import MagicMock, patch

        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.jobs.serializers import JobApplicationCreateSerializer

        request = self.factory.post("/")
        request.user = self.handyman

        image_io = BytesIO()
        image = PILImage.new("RGB", (100, 100), color="green")
        image.save(image_io, format="JPEG")
        image_io.seek(0)
        file = SimpleUploadedFile(
            "test.jpg", image_io.read(), content_type="image/jpeg"
        )
        data = {
            "job_id": str(self.job.public_id),
            "predicted_hours": "8.5",
            "estimated_total_price": "450.00",
            "negotiation_reasoning": "Test reasoning",
            "materials": [{"name": "PVC Pipe", "price": "25.50", "description": "2m"}],
            "attachments": [{"file": file}],
        }

        mock_application = MagicMock()

        with patch(
            "apps.jobs.services.JobApplicationService.apply_to_job"
        ) as mock_apply:
            mock_apply.return_value = mock_application

            serializer = JobApplicationCreateSerializer(
                data=data, context={"request": request}
            )
            self.assertTrue(serializer.is_valid())
            serializer.save()

            call_kwargs = mock_apply.call_args.kwargs
            self.assertEqual(call_kwargs["predicted_hours"], Decimal("8.5"))
            self.assertEqual(call_kwargs["estimated_total_price"], Decimal("450.00"))
            self.assertEqual(call_kwargs["negotiation_reasoning"], "Test reasoning")
            self.assertEqual(len(call_kwargs["materials_data"]), 1)
            self.assertEqual(len(call_kwargs["attachments"]), 1)

    def test_create_attachment_count_limit(self):
        """Test create fails if attachment count exceeds limit."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.common.constants import MAX_JOB_APPLICATION_ATTACHMENTS
        from apps.jobs.serializers import JobApplicationCreateSerializer

        request = self.factory.post("/")
        request.user = self.handyman

        # Create more attachments than allowed
        attachments = []
        for i in range(MAX_JOB_APPLICATION_ATTACHMENTS + 1):
            image_io = BytesIO()
            image = PILImage.new("RGB", (100, 100), color="green")
            image.save(image_io, format="JPEG")
            image_io.seek(0)
            file = SimpleUploadedFile(
                f"test{i}.jpg", image_io.read(), content_type="image/jpeg"
            )
            attachments.append({"file": file})

        data = {
            "job_id": str(self.job.public_id),
            "predicted_hours": "8.5",
            "estimated_total_price": "450.00",
            "attachments": attachments,
        }

        serializer = JobApplicationCreateSerializer(
            data=data, context={"request": request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)
        self.assertIn(
            f"Cannot upload more than {MAX_JOB_APPLICATION_ATTACHMENTS}",
            str(serializer.errors["attachments"]),
        )

    def test_create_with_document_attachment(self):
        """Test create with document attachment succeeds."""
        from unittest.mock import MagicMock, patch

        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.jobs.serializers import JobApplicationCreateSerializer

        request = self.factory.post("/")
        request.user = self.handyman

        pdf_file = SimpleUploadedFile(
            "quote.pdf", b"%PDF-1.4 test content", content_type="application/pdf"
        )
        data = {
            "job_id": str(self.job.public_id),
            "predicted_hours": "8.5",
            "estimated_total_price": "450.00",
            "attachments": [{"file": pdf_file}],
        }

        mock_application = MagicMock()

        with patch(
            "apps.jobs.services.JobApplicationService.apply_to_job"
        ) as mock_apply:
            mock_apply.return_value = mock_application

            serializer = JobApplicationCreateSerializer(
                data=data, context={"request": request}
            )
            self.assertTrue(serializer.is_valid())
            serializer.save()

            call_kwargs = mock_apply.call_args.kwargs
            self.assertEqual(len(call_kwargs["attachments"]), 1)
            self.assertEqual(call_kwargs["attachments"][0]["file_type"], "document")


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

    def test_validate_attachments_size_exceeds(self):
        """Test validation fails with large image."""
        from apps.jobs.serializers import JobCreateSerializer

        image_file = SimpleUploadedFile(
            "large.jpg", b"x" * (11 * 1024 * 1024), content_type="image/jpeg"
        )
        data = {
            "title": "Test",
            "description": "Test",
            "estimated_budget": "50.00",
            "category_id": str(self.category.public_id),
            "city_id": str(self.city.public_id),
            "address": "123 Main St",
            "attachments": [{"file": image_file}],
        }
        serializer = JobCreateSerializer(data=data, context={"request": self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)
        self.assertIn(
            "exceeds maximum size of 10MB", str(serializer.errors["attachments"])
        )


class OngoingSerializerTests(TestCase):
    """Test cases for ongoing job serializers."""

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
            assigned_handyman=self.handyman,
            title="Fix sink",
            description="Leaky sink",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
        )
        from apps.jobs.models import JobTask

        self.task = JobTask.objects.create(job=self.job, title="Task 1", order=0)

    def test_work_session_media_create_video_without_duration(self):
        """Test video media upload requires duration_seconds."""
        from apps.jobs.serializers import WorkSessionMediaCreateSerializer

        image = PILImage.new("RGB", (100, 100), color="red")
        image_file = BytesIO()
        image.save(image_file, format="JPEG")
        image_file.seek(0)
        video_file = SimpleUploadedFile(
            "video.mp4", image_file.read(), content_type="video/mp4"
        )

        data = {
            "media_type": "video",
            "file": video_file,
            "file_size": 1000,
        }
        serializer = WorkSessionMediaCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("duration_seconds", str(serializer.errors))

    def test_work_session_media_create_invalid_task_id(self):
        """Test media upload with invalid task_id."""
        import uuid

        from apps.jobs.serializers import WorkSessionMediaCreateSerializer

        image = PILImage.new("RGB", (100, 100), color="red")
        image_file = BytesIO()
        image.save(image_file, format="JPEG")
        image_file.seek(0)
        photo_file = SimpleUploadedFile(
            "photo.jpg", image_file.read(), content_type="image/jpeg"
        )

        data = {
            "media_type": "photo",
            "file": photo_file,
            "file_size": 1000,
            "task_id": str(uuid.uuid4()),
        }
        serializer = WorkSessionMediaCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("task_id", serializer.errors)

    def test_work_session_media_create_valid_task_id(self):
        """Test media upload with valid task_id."""
        from apps.jobs.serializers import WorkSessionMediaCreateSerializer

        image = PILImage.new("RGB", (100, 100), color="red")
        image_file = BytesIO()
        image.save(image_file, format="JPEG")
        image_file.seek(0)
        photo_file = SimpleUploadedFile(
            "photo.jpg", image_file.read(), content_type="image/jpeg"
        )

        data = {
            "media_type": "photo",
            "file": photo_file,
            "file_size": 1000,
            "task_id": str(self.task.public_id),
        }
        serializer = WorkSessionMediaCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["task_id"], self.task)

    def test_work_session_media_create_task_id_none(self):
        """Test media upload with task_id None."""
        from apps.jobs.serializers import WorkSessionMediaCreateSerializer

        image = PILImage.new("RGB", (100, 100), color="red")
        image_file = BytesIO()
        image.save(image_file, format="JPEG")
        image_file.seek(0)
        photo_file = SimpleUploadedFile(
            "photo.jpg", image_file.read(), content_type="image/jpeg"
        )

        data = {
            "media_type": "photo",
            "file": photo_file,
            "file_size": 1000,
        }
        serializer = WorkSessionMediaCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_work_session_media_create_task_id_explicit_none(self):
        """Test media upload with task_id explicitly set to None."""
        from apps.jobs.serializers import WorkSessionMediaCreateSerializer

        image = PILImage.new("RGB", (100, 100), color="red")
        image_file = BytesIO()
        image.save(image_file, format="JPEG")
        image_file.seek(0)
        photo_file = SimpleUploadedFile(
            "photo.jpg", image_file.read(), content_type="image/jpeg"
        )

        data = {
            "media_type": "photo",
            "file": photo_file,
            "file_size": 1000,
            "task_id": None,
        }
        serializer = WorkSessionMediaCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data.get("task_id"))

    def test_dispute_create_invalid_report_ids(self):
        """Test dispute create with invalid report IDs."""
        import uuid

        from apps.jobs.serializers import DisputeCreateSerializer

        data = {
            "reason": "Work not complete",
            "disputed_report_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
        }
        serializer = DisputeCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("disputed_report_ids", serializer.errors)

    def test_dispute_create_empty_report_ids(self):
        """Test dispute create with empty report IDs list."""
        from apps.jobs.serializers import DisputeCreateSerializer

        data = {
            "reason": "Work not complete",
            "disputed_report_ids": [],
        }
        serializer = DisputeCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["disputed_report_ids"], [])

    def test_dispute_resolve_refund_without_percentage(self):
        """Test dispute resolve with full refund auto-sets percentage to 100."""
        from apps.jobs.serializers import DisputeResolveSerializer

        data = {
            "status": "resolved_full_refund",
        }
        serializer = DisputeResolveSerializer(data=data)
        # Full refund no longer requires manual percentage - it's auto-set to 100
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["refund_percentage"], 100)

    def test_dispute_resolve_partial_refund_without_percentage(self):
        """Test dispute resolve with partial refund status but no percentage."""
        from apps.jobs.serializers import DisputeResolveSerializer

        data = {
            "status": "resolved_partial_refund",
        }
        serializer = DisputeResolveSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("refund_percentage", str(serializer.errors))

    def test_dispute_resolve_pay_handyman_no_percentage_required(self):
        """Test dispute resolve with pay_handyman doesn't require percentage."""
        from apps.jobs.serializers import DisputeResolveSerializer

        data = {
            "status": "resolved_pay_handyman",
            "admin_notes": "Resolved in favor of handyman",
        }
        serializer = DisputeResolveSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_dispute_create_valid_report_ids(self):
        """Test dispute create with valid report IDs."""
        from datetime import timedelta

        from django.utils import timezone

        from apps.jobs.models import DailyReport
        from apps.jobs.serializers import DisputeCreateSerializer

        report = DailyReport.objects.create(
            job=self.job,
            handyman=self.handyman,
            report_date=timezone.now().date(),
            summary="Work done",
            total_work_duration=timedelta(hours=2),
            review_deadline=timezone.now() + timedelta(days=3),
        )

        data = {
            "reason": "Issue with report",
            "disputed_report_ids": [str(report.public_id)],
        }
        serializer = DisputeCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(len(serializer.validated_data["disputed_report_ids"]), 1)
        self.assertEqual(serializer.validated_data["disputed_report_ids"][0], report)


class ReviewSerializerTests(TestCase):
    """Test cases for Review serializers."""

    def setUp(self):
        """Set up test data."""
        from django.utils import timezone

        from apps.accounts.models import UserRole
        from apps.profiles.models import HandymanProfile, HomeownerProfile

        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        UserRole.objects.create(user=self.handyman, role="handyman")

        self.homeowner_profile = HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
        )
        self.handyman_profile = HandymanProfile.objects.create(
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

    def test_review_create_serializer_valid(self):
        """Test ReviewCreateSerializer with valid data."""
        from apps.jobs.serializers import ReviewCreateSerializer

        data = {"rating": 5, "comment": "Great work!"}
        serializer = ReviewCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["rating"], 5)
        self.assertEqual(serializer.validated_data["comment"], "Great work!")

    def test_review_create_serializer_rating_required(self):
        """Test ReviewCreateSerializer requires rating."""
        from apps.jobs.serializers import ReviewCreateSerializer

        data = {"comment": "Great work!"}
        serializer = ReviewCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("rating", serializer.errors)

    def test_review_create_serializer_rating_range(self):
        """Test ReviewCreateSerializer validates rating range."""
        from apps.jobs.serializers import ReviewCreateSerializer

        # Rating below 1
        data = {"rating": 0}
        serializer = ReviewCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("rating", serializer.errors)

        # Rating above 5
        data = {"rating": 6}
        serializer = ReviewCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("rating", serializer.errors)

    def test_review_create_serializer_comment_optional(self):
        """Test ReviewCreateSerializer comment is optional."""
        from apps.jobs.serializers import ReviewCreateSerializer

        data = {"rating": 4}
        serializer = ReviewCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_review_update_serializer_valid(self):
        """Test ReviewUpdateSerializer with valid data."""
        from apps.jobs.serializers import ReviewUpdateSerializer

        data = {"rating": 4, "comment": "Updated comment"}
        serializer = ReviewUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_review_serializer_can_edit(self):
        """Test ReviewSerializer includes can_edit field."""

        from apps.jobs.models import Review
        from apps.jobs.serializers import ReviewSerializer

        review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
            comment="Great!",
        )

        serializer = ReviewSerializer(review)
        data = serializer.data

        self.assertIn("can_edit", data)
        self.assertTrue(data["can_edit"])  # Within 14 days

    def test_review_serializer_can_edit_false_after_window(self):
        """Test ReviewSerializer can_edit is False after 14 days."""
        from datetime import timedelta

        from django.utils import timezone

        from apps.jobs.models import Review
        from apps.jobs.serializers import ReviewSerializer

        # Set job completed_at to 15 days ago
        self.job.completed_at = timezone.now() - timedelta(days=15)
        self.job.save()

        review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
        )

        serializer = ReviewSerializer(review)
        data = serializer.data

        self.assertFalse(data["can_edit"])

    def test_review_serializer_can_edit_false_no_completed_at(self):
        """Test ReviewSerializer can_edit is False when job has no completed_at."""
        from apps.jobs.models import Review
        from apps.jobs.serializers import ReviewSerializer

        self.job.completed_at = None
        self.job.save()

        review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
        )

        serializer = ReviewSerializer(review)
        data = serializer.data

        self.assertFalse(data["can_edit"])

    def test_review_detail_serializer_homeowner_reviewer(self):
        """Test ReviewDetailSerializer with homeowner as reviewer."""
        from apps.jobs.models import Review
        from apps.jobs.serializers import ReviewDetailSerializer

        review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
            comment="Excellent work!",
        )

        serializer = ReviewDetailSerializer(review)
        data = serializer.data

        self.assertEqual(data["reviewer_display_name"], "Test Homeowner")
        # avatar_url is None when no avatar is set
        self.assertIsNone(data["reviewer_avatar_url"])
        self.assertEqual(data["job_title"], "Fix sink")
        self.assertEqual(data["rating"], 5)

    def test_review_detail_serializer_handyman_reviewer(self):
        """Test ReviewDetailSerializer with handyman as reviewer."""
        from apps.jobs.models import Review
        from apps.jobs.serializers import ReviewDetailSerializer

        review = Review.objects.create(
            job=self.job,
            reviewer=self.handyman,
            reviewee=self.homeowner,
            reviewer_type="handyman",
            rating=4,
            comment="Good homeowner!",
        )

        serializer = ReviewDetailSerializer(review)
        data = serializer.data

        self.assertEqual(data["reviewer_display_name"], "Test Handyman")
        # avatar_url is None when no avatar is set
        self.assertIsNone(data["reviewer_avatar_url"])

    def test_review_detail_serializer_no_profile(self):
        """Test ReviewDetailSerializer when reviewer has no profile."""
        from apps.jobs.models import Review
        from apps.jobs.serializers import ReviewDetailSerializer

        # Create user without profile
        user_no_profile = User.objects.create_user(
            email="noprofile@example.com", password="password123"
        )

        review = Review.objects.create(
            job=self.job,
            reviewer=user_no_profile,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=3,
        )

        serializer = ReviewDetailSerializer(review)
        data = serializer.data

        self.assertIsNone(data["reviewer_display_name"])
        self.assertIsNone(data["reviewer_avatar_url"])

    def test_review_detail_serializer_handyman_no_profile(self):
        """Test ReviewDetailSerializer when handyman reviewer has no profile."""
        from apps.jobs.models import Review
        from apps.jobs.serializers import ReviewDetailSerializer

        # Create handyman user without profile
        handyman_no_profile = User.objects.create_user(
            email="handyman_noprofile@example.com", password="password123"
        )

        review = Review.objects.create(
            job=self.job,
            reviewer=handyman_no_profile,
            reviewee=self.homeowner,
            reviewer_type="handyman",
            rating=4,
        )

        serializer = ReviewDetailSerializer(review)
        data = serializer.data

        self.assertIsNone(data["reviewer_display_name"])
        self.assertIsNone(data["reviewer_avatar_url"])

    def test_review_detail_serializer_unknown_reviewer_type(self):
        """Test ReviewDetailSerializer with unknown reviewer_type returns None."""
        from unittest.mock import MagicMock

        from apps.jobs.serializers import ReviewDetailSerializer

        # Create a mock review object with an unknown reviewer_type
        mock_review = MagicMock()
        mock_review.reviewer_type = "unknown"
        mock_review.public_id = "test-uuid"
        mock_review.rating = 5
        mock_review.comment = "Test"
        mock_review.created_at = None
        mock_review.updated_at = None
        mock_review.job.title = "Test Job"
        mock_review.job.public_id = "job-uuid"

        serializer = ReviewDetailSerializer()

        # Test get_reviewer_display_name returns None for unknown type
        result = serializer.get_reviewer_display_name(mock_review)
        self.assertIsNone(result)

        # Test get_reviewer_avatar_url returns None for unknown type
        result = serializer.get_reviewer_avatar_url(mock_review)
        self.assertIsNone(result)


class HandymanForYouJobSerializerTests(TestCase):
    """Test cases for HandymanForYouJobSerializer."""

    def setUp(self):
        """Set up test data."""
        from django.utils import timezone

        from apps.accounts.models import UserRole
        from apps.profiles.models import HandymanProfile, HomeownerProfile

        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="testpass123"
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="testpass123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        UserRole.objects.create(user=self.handyman, role="handyman")

        self.homeowner_profile = HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
            rating=Decimal("4.5"),
            review_count=10,
        )
        self.handyman_profile = HandymanProfile.objects.create(
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
            title="Fix sink",
            description="Leaky sink",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )

    def test_handyman_for_you_job_serializer_includes_homeowner_rating(self):
        """Test HandymanForYouJobSerializer includes homeowner rating."""
        from apps.jobs.serializers import HandymanForYouJobSerializer

        serializer = HandymanForYouJobSerializer(self.job)
        data = serializer.data

        self.assertIn("homeowner_rating", data)
        self.assertEqual(Decimal(str(data["homeowner_rating"])), Decimal("4.5"))
        self.assertIn("homeowner_review_count", data)
        self.assertEqual(data["homeowner_review_count"], 10)

    def test_handyman_for_you_job_serializer_no_profile(self):
        """Test HandymanForYouJobSerializer when homeowner has no profile."""
        from apps.jobs.serializers import HandymanForYouJobSerializer

        # Create homeowner without profile
        other_homeowner = User.objects.create_user(
            email="noprofile@example.com", password="password123"
        )
        job = Job.objects.create(
            homeowner=other_homeowner,
            title="Another job",
            description="Description",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="456 Main St",
            status="open",
        )

        serializer = HandymanForYouJobSerializer(job)
        data = serializer.data

        self.assertIsNone(data["homeowner_rating"])
        self.assertEqual(data["homeowner_review_count"], 0)

    def test_handyman_job_detail_serializer_includes_homeowner_rating(self):
        """Test HandymanJobDetailSerializer includes homeowner rating."""
        from apps.jobs.serializers import HandymanJobDetailSerializer

        request = APIRequestFactory().get("/")
        request.user = self.handyman

        serializer = HandymanJobDetailSerializer(self.job, context={"request": request})
        data = serializer.data

        self.assertIn("homeowner_rating", data)
        self.assertEqual(Decimal(str(data["homeowner_rating"])), Decimal("4.5"))
        self.assertIn("homeowner_review_count", data)
        self.assertEqual(data["homeowner_review_count"], 10)

    def test_handyman_job_detail_serializer_no_profile(self):
        """Test HandymanJobDetailSerializer when homeowner has no profile."""
        from apps.jobs.serializers import HandymanJobDetailSerializer

        # Create homeowner without profile
        other_homeowner = User.objects.create_user(
            email="noprofile@example.com", password="password123"
        )
        job = Job.objects.create(
            homeowner=other_homeowner,
            title="Another job",
            description="Description",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="456 Main St",
            status="open",
        )

        request = APIRequestFactory().get("/")
        request.user = self.handyman

        serializer = HandymanJobDetailSerializer(job, context={"request": request})
        data = serializer.data

        self.assertIsNone(data["homeowner_rating"])
        self.assertEqual(data["homeowner_review_count"], 0)


# ========================
# Reimbursement Serializer Tests
# ========================


class JobReimbursementSerializerTests(TestCase):
    """Test cases for JobReimbursementSerializer."""

    def setUp(self):
        """Set up test data."""
        from apps.jobs.models import JobReimbursement, JobReimbursementCategory

        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
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
        self.reimbursement_category, _ = JobReimbursementCategory.objects.get_or_create(
            slug="materials",
            defaults={
                "name": "Materials",
                "description": "Material expenses",
                "is_active": True,
            },
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Fix leaky faucet",
            description="Kitchen faucet is leaking",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
        )
        self.reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Plumbing materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
            notes="Required for repair",
        )

    def test_serializer_fields(self):
        """Test serializer returns expected fields."""
        from apps.jobs.serializers import JobReimbursementSerializer

        serializer = JobReimbursementSerializer(self.reimbursement)
        data = serializer.data

        self.assertIn("public_id", data)
        self.assertIn("name", data)
        self.assertIn("category", data)
        self.assertIn("amount", data)
        self.assertIn("notes", data)
        self.assertIn("status", data)
        self.assertIn("homeowner_comment", data)
        self.assertIn("reviewed_at", data)
        self.assertIn("attachments", data)
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

    def test_serializer_values(self):
        """Test serializer returns correct values."""
        from apps.jobs.serializers import JobReimbursementSerializer

        serializer = JobReimbursementSerializer(self.reimbursement)
        data = serializer.data

        self.assertEqual(data["name"], "Plumbing materials")
        # Category is now a nested object
        self.assertIn("public_id", data["category"])
        self.assertEqual(data["category"]["name"], "Materials")
        self.assertEqual(data["category"]["slug"], "materials")
        self.assertEqual(data["amount"], "50.00")
        self.assertEqual(data["notes"], "Required for repair")
        self.assertEqual(data["status"], "pending")


class JobReimbursementCreateSerializerTests(TestCase):
    """Test cases for JobReimbursementCreateSerializer."""

    def setUp(self):
        """Set up test data."""
        from apps.jobs.models import JobReimbursementCategory

        self.reimbursement_category, _ = JobReimbursementCategory.objects.get_or_create(
            slug="materials",
            defaults={
                "name": "Materials",
                "description": "Material expenses",
                "is_active": True,
            },
        )
        self.inactive_category, _ = JobReimbursementCategory.objects.get_or_create(
            slug="test-inactive-create",
            defaults={
                "name": "Test Inactive Create",
                "description": "Inactive category for create serializer test",
                "is_active": False,
            },
        )
        # Ensure inactive status
        self.inactive_category.is_active = False
        self.inactive_category.save()

    def test_valid_data(self):
        """Test serializer with valid data."""
        from apps.jobs.serializers import JobReimbursementCreateSerializer

        image = SimpleUploadedFile(
            "receipt.jpg", b"file content", content_type="image/jpeg"
        )
        data = {
            "name": "Plumbing materials",
            "category_id": str(self.reimbursement_category.public_id),
            "amount": "50.00",
            "notes": "Required for repair",
            "attachments": [{"file": image}],
        }
        serializer = JobReimbursementCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_amount_must_be_positive(self):
        """Test amount validation."""
        from apps.jobs.serializers import JobReimbursementCreateSerializer

        image = SimpleUploadedFile(
            "receipt.jpg", b"file content", content_type="image/jpeg"
        )
        data = {
            "name": "Materials",
            "category_id": str(self.reimbursement_category.public_id),
            "amount": "0",
            "attachments": [{"file": image}],
        }
        serializer = JobReimbursementCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)

    def test_negative_amount_fails(self):
        """Test negative amount validation."""
        from apps.jobs.serializers import JobReimbursementCreateSerializer

        image = SimpleUploadedFile(
            "receipt.jpg", b"file content", content_type="image/jpeg"
        )
        data = {
            "name": "Materials",
            "category_id": str(self.reimbursement_category.public_id),
            "amount": "-10.00",
            "attachments": [{"file": image}],
        }
        serializer = JobReimbursementCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_attachments_required(self):
        """Test attachments are required."""
        from apps.jobs.serializers import JobReimbursementCreateSerializer

        data = {
            "name": "Materials",
            "category_id": str(self.reimbursement_category.public_id),
            "amount": "50.00",
        }
        serializer = JobReimbursementCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)

    def test_invalid_category_id(self):
        """Test invalid category_id fails."""
        from apps.jobs.serializers import JobReimbursementCreateSerializer

        image = SimpleUploadedFile(
            "receipt.jpg", b"file content", content_type="image/jpeg"
        )
        data = {
            "name": "Materials",
            "category_id": "00000000-0000-0000-0000-000000000000",
            "amount": "50.00",
            "attachments": [{"file": image}],
        }
        serializer = JobReimbursementCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("category_id", serializer.errors)

    def test_inactive_category_fails(self):
        """Test inactive category_id fails."""
        from apps.jobs.serializers import JobReimbursementCreateSerializer

        image = SimpleUploadedFile(
            "receipt.jpg", b"file content", content_type="image/jpeg"
        )
        data = {
            "name": "Materials",
            "category_id": str(self.inactive_category.public_id),
            "amount": "50.00",
            "attachments": [{"file": image}],
        }
        serializer = JobReimbursementCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("category_id", serializer.errors)

    def test_attachment_count_limit(self):
        """Test attachment count cannot exceed limit."""
        from apps.common.constants import MAX_REIMBURSEMENT_ATTACHMENTS
        from apps.jobs.serializers import JobReimbursementCreateSerializer

        # Create more attachments than allowed
        attachments = []
        for i in range(MAX_REIMBURSEMENT_ATTACHMENTS + 1):
            image = SimpleUploadedFile(
                f"receipt{i}.jpg", b"file content", content_type="image/jpeg"
            )
            attachments.append({"file": image})

        data = {
            "name": "Materials",
            "category_id": str(self.reimbursement_category.public_id),
            "amount": "50.00",
            "attachments": attachments,
        }
        serializer = JobReimbursementCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)
        self.assertIn(
            f"Cannot upload more than {MAX_REIMBURSEMENT_ATTACHMENTS}",
            str(serializer.errors["attachments"]),
        )

    def test_document_attachment_accepted(self):
        """Test document attachments are accepted."""
        from apps.jobs.serializers import JobReimbursementCreateSerializer

        pdf_file = SimpleUploadedFile(
            "invoice.pdf", b"%PDF-1.4 test content", content_type="application/pdf"
        )
        data = {
            "name": "Materials",
            "category_id": str(self.reimbursement_category.public_id),
            "amount": "50.00",
            "notes": "Invoice attached",
            "attachments": [{"file": pdf_file}],
        }
        serializer = JobReimbursementCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(
            serializer.validated_data["attachments"][0]["file_type"], "document"
        )


class JobReimbursementReviewSerializerTests(TestCase):
    """Test cases for JobReimbursementReviewSerializer."""

    def test_valid_approve(self):
        """Test valid approve decision."""
        from apps.jobs.serializers import JobReimbursementReviewSerializer

        data = {"decision": "approved", "comment": "Looks good"}
        serializer = JobReimbursementReviewSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["decision"], "approved")

    def test_valid_reject(self):
        """Test valid reject decision."""
        from apps.jobs.serializers import JobReimbursementReviewSerializer

        data = {"decision": "rejected", "comment": "Receipt not clear"}
        serializer = JobReimbursementReviewSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["decision"], "rejected")

    def test_invalid_decision(self):
        """Test invalid decision fails."""
        from apps.jobs.serializers import JobReimbursementReviewSerializer

        data = {"decision": "pending"}
        serializer = JobReimbursementReviewSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("decision", serializer.errors)

    def test_comment_optional(self):
        """Test comment is optional."""
        from apps.jobs.serializers import JobReimbursementReviewSerializer

        data = {"decision": "approved"}
        serializer = JobReimbursementReviewSerializer(data=data)
        self.assertTrue(serializer.is_valid())


class JobReimbursementUpdateSerializerTests(TestCase):
    """Test cases for JobReimbursementUpdateSerializer."""

    def setUp(self):
        """Set up test data."""
        from apps.jobs.models import JobReimbursementCategory

        self.reimbursement_category, _ = JobReimbursementCategory.objects.get_or_create(
            slug="materials",
            defaults={
                "name": "Materials",
                "description": "Material expenses",
                "is_active": True,
            },
        )
        self.tools_category, _ = JobReimbursementCategory.objects.get_or_create(
            slug="tools",
            defaults={
                "name": "Tools",
                "description": "Tool expenses",
                "is_active": True,
            },
        )
        self.inactive_category, _ = JobReimbursementCategory.objects.get_or_create(
            slug="test-inactive-update",
            defaults={
                "name": "Test Inactive Update",
                "description": "Inactive category for update serializer test",
                "is_active": False,
            },
        )
        # Ensure inactive status
        self.inactive_category.is_active = False
        self.inactive_category.save()

    def test_valid_partial_update(self):
        """Test valid partial update."""
        from apps.jobs.serializers import JobReimbursementUpdateSerializer

        data = {"name": "Updated Name", "amount": "75.00"}
        serializer = JobReimbursementUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["name"], "Updated Name")

    def test_all_fields_optional(self):
        """Test all fields are optional."""
        from apps.jobs.serializers import JobReimbursementUpdateSerializer

        data = {}
        serializer = JobReimbursementUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_amount_must_be_positive(self):
        """Test amount validation."""
        from apps.jobs.serializers import JobReimbursementUpdateSerializer

        data = {"amount": "0"}
        serializer = JobReimbursementUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)

    def test_negative_amount_fails(self):
        """Test negative amount validation."""
        from apps.jobs.serializers import JobReimbursementUpdateSerializer

        data = {"amount": "-10.00"}
        serializer = JobReimbursementUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_invalid_category_id(self):
        """Test invalid category_id fails."""
        from apps.jobs.serializers import JobReimbursementUpdateSerializer

        data = {"category_id": "00000000-0000-0000-0000-000000000000"}
        serializer = JobReimbursementUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("category_id", serializer.errors)

    def test_valid_category_id(self):
        """Test valid category_id."""
        from apps.jobs.serializers import JobReimbursementUpdateSerializer

        data = {"category_id": str(self.tools_category.public_id)}
        serializer = JobReimbursementUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["category_id"], self.tools_category)

    def test_inactive_category_id_fails(self):
        """Test inactive category_id fails."""
        from apps.jobs.serializers import JobReimbursementUpdateSerializer

        data = {"category_id": str(self.inactive_category.public_id)}
        serializer = JobReimbursementUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("category_id", serializer.errors)


class JobReimbursementUpdateSerializerValidateTests(TestCase):
    """Test cases for JobReimbursementUpdateSerializer.validate() method."""

    def setUp(self):
        """Set up test data."""
        from apps.jobs.models import (
            JobReimbursement,
            JobReimbursementAttachment,
            JobReimbursementCategory,
        )

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
            status="in_progress",
            assigned_handyman=self.handyman,
        )
        self.reimbursement_category, _ = JobReimbursementCategory.objects.get_or_create(
            slug="materials",
            defaults={
                "name": "Materials",
                "description": "Material expenses",
                "is_active": True,
            },
        )
        # Create a reimbursement with one attachment
        self.reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            category=self.reimbursement_category,
            name="Test Reimbursement",
            amount=Decimal("50.00"),
            status="pending",
        )
        # Create an existing attachment
        image_io = BytesIO()
        image = PILImage.new("RGB", (100, 100), color="green")
        image.save(image_io, format="JPEG")
        image_io.seek(0)
        from django.core.files.uploadedfile import SimpleUploadedFile

        file = SimpleUploadedFile(
            "test.jpg", image_io.read(), content_type="image/jpeg"
        )
        self.attachment = JobReimbursementAttachment.objects.create(
            reimbursement=self.reimbursement,
            file=file,
            file_type="image",
            file_name="test.jpg",
            file_size=file.size,
        )

    def test_validate_with_instance_covers_branch(self):
        """Test validate() with instance to cover the if instance: branch."""
        from apps.jobs.serializers import JobReimbursementUpdateSerializer

        data = {"name": "Updated Name"}
        serializer = JobReimbursementUpdateSerializer(
            instance=self.reimbursement, data=data
        )
        self.assertTrue(serializer.is_valid())

    def test_validate_attachment_minimum_fails(self):
        """Test validation fails when trying to remove all attachments."""
        from apps.jobs.serializers import JobReimbursementUpdateSerializer

        # Try to remove the only attachment
        data = {"attachments_to_remove": [str(self.attachment.public_id)]}
        serializer = JobReimbursementUpdateSerializer(
            instance=self.reimbursement, data=data
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)
        self.assertIn("At least one attachment", str(serializer.errors["attachments"]))

    def test_validate_attachment_maximum_fails(self):
        """Test validation fails when total attachments exceeds limit."""
        from apps.common.constants import MAX_REIMBURSEMENT_ATTACHMENTS

        # Create attachments up to the limit
        from apps.jobs.models import JobReimbursementAttachment
        from apps.jobs.serializers import JobReimbursementUpdateSerializer

        for i in range(MAX_REIMBURSEMENT_ATTACHMENTS - 1):
            image_io = BytesIO()
            image = PILImage.new("RGB", (100, 100), color="blue")
            image.save(image_io, format="JPEG")
            image_io.seek(0)
            from django.core.files.uploadedfile import SimpleUploadedFile

            file = SimpleUploadedFile(
                f"test{i}.jpg", image_io.read(), content_type="image/jpeg"
            )
            JobReimbursementAttachment.objects.create(
                reimbursement=self.reimbursement,
                file=file,
                file_type="image",
                file_name=f"test{i}.jpg",
                file_size=file.size,
            )

        # Now we have MAX_REIMBURSEMENT_ATTACHMENTS attachments
        self.assertEqual(
            self.reimbursement.attachments.count(), MAX_REIMBURSEMENT_ATTACHMENTS
        )

        # Try to add more attachments
        image_io = BytesIO()
        image = PILImage.new("RGB", (100, 100), color="red")
        image.save(image_io, format="JPEG")
        image_io.seek(0)
        new_file = SimpleUploadedFile(
            "new.jpg", image_io.read(), content_type="image/jpeg"
        )

        data = {"attachments": [{"file": new_file}]}
        serializer = JobReimbursementUpdateSerializer(
            instance=self.reimbursement, data=data
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)
        self.assertIn("exceed the limit", str(serializer.errors["attachments"]))


class JobReimbursementCreateSerializerEmptyAttachmentsTests(TestCase):
    """Test cases for JobReimbursementCreateSerializer empty attachments validation."""

    def test_empty_attachments_fails_validation(self):
        """Test validation fails when attachments is empty."""
        from apps.jobs.models import JobReimbursementCategory
        from apps.jobs.serializers import JobReimbursementCreateSerializer

        category, _ = JobReimbursementCategory.objects.get_or_create(
            slug="materials",
            defaults={
                "name": "Materials",
                "description": "Material expenses",
                "is_active": True,
            },
        )

        data = {
            "name": "Test Reimbursement",
            "category_id": str(category.public_id),
            "amount": "50.00",
            "attachments": [],
        }
        serializer = JobReimbursementCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)
        self.assertIn("At least one attachment", str(serializer.errors["attachments"]))


class JobApplicationUpdateSerializerValidateTests(TestCase):
    """Test cases for JobApplicationUpdateSerializer.validate() method."""

    def setUp(self):
        """Set up test data."""
        from apps.jobs.models import JobApplication, JobApplicationAttachment

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
        # Create an application
        self.application = JobApplication.objects.create(
            job=self.job,
            handyman=self.handyman,
            predicted_hours=Decimal("8.0"),
            estimated_total_price=Decimal("400.00"),
            status="pending",
        )
        # Create existing attachments up to the limit
        from apps.common.constants import MAX_JOB_APPLICATION_ATTACHMENTS

        for i in range(MAX_JOB_APPLICATION_ATTACHMENTS):
            image_io = BytesIO()
            image = PILImage.new("RGB", (100, 100), color="green")
            image.save(image_io, format="JPEG")
            image_io.seek(0)
            from django.core.files.uploadedfile import SimpleUploadedFile

            file = SimpleUploadedFile(
                f"test{i}.jpg", image_io.read(), content_type="image/jpeg"
            )
            JobApplicationAttachment.objects.create(
                application=self.application,
                file=file,
                file_type="image",
                file_name=f"test{i}.jpg",
                file_size=file.size,
            )

    def test_validate_with_instance_attachment_count_exceeded(self):
        """Test validate() fails when total attachments would exceed limit."""
        from apps.common.constants import MAX_JOB_APPLICATION_ATTACHMENTS
        from apps.jobs.serializers import JobApplicationUpdateSerializer

        # Verify we're at the limit
        self.assertEqual(
            self.application.attachments.count(), MAX_JOB_APPLICATION_ATTACHMENTS
        )

        # Try to add another attachment
        image_io = BytesIO()
        image = PILImage.new("RGB", (100, 100), color="red")
        image.save(image_io, format="JPEG")
        image_io.seek(0)
        from django.core.files.uploadedfile import SimpleUploadedFile

        new_file = SimpleUploadedFile(
            "new.jpg", image_io.read(), content_type="image/jpeg"
        )

        data = {"attachments": [{"file": new_file}]}
        serializer = JobApplicationUpdateSerializer(
            instance=self.application, data=data
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("attachments", serializer.errors)
        self.assertIn("exceed the limit", str(serializer.errors["attachments"]))

    def test_validate_without_instance_skips_attachment_count_check(self):
        """Test validate() skips attachment count check when no instance.

        Covers branch 1328->1352: when instance is None.
        """
        from apps.jobs.serializers import JobApplicationUpdateSerializer

        # Serializer without instance (e.g., in create mode)
        data = {"predicted_hours": "5.0", "estimated_total_price": "250.00"}
        serializer = JobApplicationUpdateSerializer(data=data)

        # Manually call validate to test the branch
        validated = serializer.validate(data)
        self.assertEqual(validated, data)
