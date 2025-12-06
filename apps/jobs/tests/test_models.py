from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.jobs.models import (
    MAX_JOB_ITEM_LENGTH,
    MAX_JOB_ITEMS,
    City,
    Job,
    JobCategory,
    JobImage,
)


class JobCategoryModelTests(TestCase):
    """Test cases for JobCategory model."""

    def test_create_category_success(self):
        """Test creating a job category."""
        category = JobCategory.objects.create(
            name="Plumbing",
            slug="plumbing",
            description="Plumbing services",
            icon="plumbing_icon",
            is_active=True,
        )
        self.assertEqual(category.name, "Plumbing")
        self.assertEqual(category.slug, "plumbing")
        self.assertTrue(category.is_active)
        self.assertIsNotNone(category.public_id)

    def test_category_string_representation(self):
        """Test category string representation."""
        category = JobCategory.objects.create(name="Electrical", slug="electrical")
        self.assertEqual(str(category), "Electrical")

    def test_category_unique_name(self):
        """Test category name must be unique."""
        JobCategory.objects.create(name="Plumbing", slug="plumbing")
        with self.assertRaises(IntegrityError):
            JobCategory.objects.create(name="Plumbing", slug="plumbing-2")

    def test_category_ordering(self):
        """Test categories are ordered by name."""
        JobCategory.objects.create(name="Plumbing", slug="plumbing")
        JobCategory.objects.create(name="Electrical", slug="electrical")
        JobCategory.objects.create(name="Carpentry", slug="carpentry")

        categories = list(JobCategory.objects.all())
        self.assertEqual(categories[0].name, "Carpentry")
        self.assertEqual(categories[1].name, "Electrical")
        self.assertEqual(categories[2].name, "Plumbing")


class CityModelTests(TestCase):
    """Test cases for City model."""

    def test_create_city_success(self):
        """Test creating a city."""
        city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            latitude=Decimal("43.651070"),
            longitude=Decimal("-79.347015"),
            is_active=True,
        )
        self.assertEqual(city.name, "Toronto")
        self.assertEqual(city.province, "Ontario")
        self.assertEqual(city.province_code, "ON")
        self.assertTrue(city.is_active)
        self.assertIsNotNone(city.public_id)

    def test_city_string_representation(self):
        """Test city string representation."""
        city = City.objects.create(
            name="Toronto", province="Ontario", province_code="ON", slug="toronto-on"
        )
        self.assertEqual(str(city), "Toronto, ON")

    def test_city_unique_together(self):
        """Test city name and province must be unique together."""
        City.objects.create(
            name="Toronto", province="Ontario", province_code="ON", slug="toronto-on"
        )
        with self.assertRaises(IntegrityError):
            City.objects.create(
                name="Toronto",
                province="Ontario",
                province_code="ON",
                slug="toronto-on-2",
            )

    def test_city_same_name_different_province(self):
        """Test cities can have same name in different provinces."""
        city1 = City.objects.create(
            name="Vancouver",
            province="British Columbia",
            province_code="BC",
            slug="vancouver-bc",
        )
        city2 = City.objects.create(
            name="Vancouver",
            province="Washington",
            province_code="WA",
            slug="vancouver-wa",
        )
        self.assertNotEqual(city1.pk, city2.pk)

    def test_city_ordering(self):
        """Test cities are ordered by name."""
        City.objects.create(
            name="Vancouver", province="BC", province_code="BC", slug="vancouver-bc"
        )
        City.objects.create(
            name="Toronto", province="ON", province_code="ON", slug="toronto-on"
        )
        City.objects.create(
            name="Montreal", province="QC", province_code="QC", slug="montreal-qc"
        )

        cities = list(City.objects.all())
        self.assertEqual(cities[0].name, "Montreal")
        self.assertEqual(cities[1].name, "Toronto")
        self.assertEqual(cities[2].name, "Vancouver")


class JobModelTests(TestCase):
    """Test cases for Job model."""

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

    def test_create_job_success(self):
        """Test creating a job."""
        job = Job.objects.create(
            homeowner=self.user,
            title="Fix leaking faucet",
            description="Kitchen faucet is leaking",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            latitude=Decimal("43.651070"),
            longitude=Decimal("-79.347015"),
            status="open",
        )
        self.assertEqual(job.title, "Fix leaking faucet")
        self.assertEqual(job.homeowner, self.user)
        self.assertEqual(job.category, self.category)
        self.assertEqual(job.city, self.city)
        self.assertEqual(job.status, "open")
        self.assertIsNotNone(job.public_id)

    def test_job_string_representation(self):
        """Test job string representation."""
        job = Job.objects.create(
            homeowner=self.user,
            title="Fix door",
            description="Broken door",
            estimated_budget=Decimal("40.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        self.assertEqual(str(job), "Fix door - homeowner@example.com")

    def test_job_default_status(self):
        """Test job default status is draft."""
        job = Job.objects.create(
            homeowner=self.user,
            title="Test",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        self.assertEqual(job.status, "draft")

    def test_job_negative_budget_validation(self):
        """Test job budget must be positive."""
        with self.assertRaises(ValidationError):
            job = Job(
                homeowner=self.user,
                title="Test",
                description="Test",
                estimated_budget=Decimal("-10.00"),
                category=self.category,
                city=self.city,
                address="123 Main St",
            )
            job.save()

    def test_job_inactive_category_validation(self):
        """Test job cannot use inactive category."""
        inactive_category = JobCategory.objects.create(
            name="Inactive", slug="inactive", is_active=False
        )
        with self.assertRaises(ValidationError):
            job = Job(
                homeowner=self.user,
                title="Test",
                description="Test",
                estimated_budget=Decimal("50.00"),
                category=inactive_category,
                city=self.city,
                address="123 Main St",
            )
            job.save()

    def test_job_inactive_city_validation(self):
        """Test job cannot use inactive city."""
        inactive_city = City.objects.create(
            name="Inactive",
            province="Test",
            province_code="TS",
            slug="inactive-ts",
            is_active=False,
        )
        with self.assertRaises(ValidationError):
            job = Job(
                homeowner=self.user,
                title="Test",
                description="Test",
                estimated_budget=Decimal("50.00"),
                category=self.category,
                city=inactive_city,
                address="123 Main St",
            )
            job.save()

    def test_job_latitude_without_longitude_validation(self):
        """Test job cannot have latitude without longitude."""
        with self.assertRaises(ValidationError):
            job = Job(
                homeowner=self.user,
                title="Test",
                description="Test",
                estimated_budget=Decimal("50.00"),
                category=self.category,
                city=self.city,
                address="123 Main St",
                latitude=Decimal("43.651070"),
            )
            job.save()

    def test_job_longitude_without_latitude_validation(self):
        """Test job cannot have longitude without latitude."""
        with self.assertRaises(ValidationError):
            job = Job(
                homeowner=self.user,
                title="Test",
                description="Test",
                estimated_budget=Decimal("50.00"),
                category=self.category,
                city=self.city,
                address="123 Main St",
                longitude=Decimal("-79.347015"),
            )
            job.save()

    def test_job_invalid_latitude_validation(self):
        """Test job latitude must be between -90 and 90."""
        with self.assertRaises(ValidationError):
            job = Job(
                homeowner=self.user,
                title="Test",
                description="Test",
                estimated_budget=Decimal("50.00"),
                category=self.category,
                city=self.city,
                address="123 Main St",
                latitude=Decimal("91.0"),
                longitude=Decimal("-79.347015"),
            )
            job.save()

    def test_job_invalid_longitude_validation(self):
        """Test job longitude must be between -180 and 180."""
        with self.assertRaises(ValidationError):
            job = Job(
                homeowner=self.user,
                title="Test",
                description="Test",
                estimated_budget=Decimal("50.00"),
                category=self.category,
                city=self.city,
                address="123 Main St",
                latitude=Decimal("43.651070"),
                longitude=Decimal("181.0"),
            )
            job.save()

    def test_job_cascade_delete_with_customer(self):
        """Test job is deleted when homeowner is deleted."""
        job = Job.objects.create(
            homeowner=self.user,
            title="Test",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        job_id = job.id
        self.user.delete()
        self.assertFalse(Job.objects.filter(id=job_id).exists())

    def test_job_ordering(self):
        """Test jobs are ordered by created_at descending."""
        job1 = Job.objects.create(
            homeowner=self.user,
            title="First",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        job2 = Job.objects.create(
            homeowner=self.user,
            title="Second",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )

        jobs = list(Job.objects.all())
        self.assertEqual(jobs[0].id, job2.id)  # Most recent first
        self.assertEqual(jobs[1].id, job1.id)

    def test_create_job_with_job_items(self):
        """Test creating a job with job_items."""
        job_items = ["Fix the faucet", "Replace pipes", "Install new sink"]
        job = Job.objects.create(
            homeowner=self.user,
            title="Plumbing Work",
            description="Multiple plumbing tasks",
            estimated_budget=Decimal("200.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            job_items=job_items,
        )
        self.assertEqual(job.job_items, job_items)
        self.assertEqual(len(job.job_items), 3)

    def test_job_items_default_empty_list(self):
        """Test job_items defaults to empty list."""
        job = Job.objects.create(
            homeowner=self.user,
            title="Test",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        self.assertEqual(job.job_items, [])

    def test_job_items_max_items_validation(self):
        """Test job cannot have more than MAX_JOB_ITEMS items."""
        job_items = [f"Task {i}" for i in range(MAX_JOB_ITEMS + 1)]
        with self.assertRaises(ValidationError) as context:
            job = Job(
                homeowner=self.user,
                title="Test",
                description="Test",
                estimated_budget=Decimal("50.00"),
                category=self.category,
                city=self.city,
                address="123 Main St",
                job_items=job_items,
            )
            job.save()
        self.assertIn("job_items", context.exception.message_dict)

    def test_job_items_max_length_validation(self):
        """Test job item cannot exceed MAX_JOB_ITEM_LENGTH characters."""
        long_item = "x" * (MAX_JOB_ITEM_LENGTH + 1)
        with self.assertRaises(ValidationError) as context:
            job = Job(
                homeowner=self.user,
                title="Test",
                description="Test",
                estimated_budget=Decimal("50.00"),
                category=self.category,
                city=self.city,
                address="123 Main St",
                job_items=[long_item],
            )
            job.save()
        self.assertIn("job_items", context.exception.message_dict)

    def test_job_items_must_be_list(self):
        """Test job_items must be a list."""
        with self.assertRaises(ValidationError) as context:
            job = Job(
                homeowner=self.user,
                title="Test",
                description="Test",
                estimated_budget=Decimal("50.00"),
                category=self.category,
                city=self.city,
                address="123 Main St",
                job_items="not a list",
            )
            job.save()
        self.assertIn("job_items", context.exception.message_dict)

    def test_job_items_items_must_be_strings(self):
        """Test each job item must be a string."""
        with self.assertRaises(ValidationError) as context:
            job = Job(
                homeowner=self.user,
                title="Test",
                description="Test",
                estimated_budget=Decimal("50.00"),
                category=self.category,
                city=self.city,
                address="123 Main St",
                job_items=["Valid item", 123, "Another valid"],
            )
            job.save()
        self.assertIn("job_items", context.exception.message_dict)


class JobImageModelTests(TestCase):
    """Test cases for JobImage model."""

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

    def test_job_image_string_representation(self):
        """Test job image string representation."""
        image = JobImage.objects.create(job=self.job, order=0)
        self.assertEqual(str(image), "Image 0 for Test")

    def test_job_image_cascade_delete(self):
        """Test job image is deleted when job is deleted."""
        image = JobImage.objects.create(job=self.job, order=0)
        image_id = image.id
        self.job.delete()
        self.assertFalse(JobImage.objects.filter(id=image_id).exists())

    def test_job_image_ordering(self):
        """Test job images are ordered by order and created_at."""
        image2 = JobImage.objects.create(job=self.job, order=2)
        image1 = JobImage.objects.create(job=self.job, order=1)
        image0 = JobImage.objects.create(job=self.job, order=0)

        images = list(JobImage.objects.all())
        self.assertEqual(images[0].id, image0.id)
        self.assertEqual(images[1].id, image1.id)
        self.assertEqual(images[2].id, image2.id)
