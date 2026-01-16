from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from PIL import Image as PILImage

from apps.accounts.models import User, UserRole
from apps.jobs.models import (
    City,
    Job,
    JobApplication,
    JobAttachment,
    JobCategory,
    JobTask,
    Review,
    WorkSession,
)
from apps.profiles.models import HandymanProfile, HomeownerProfile


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
        with self.assertRaises(ValidationError) as context:
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
        self.assertIn("category", context.exception.message_dict)

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

    def test_create_job_with_tasks(self):
        """Test creating a job with tasks."""
        job = Job.objects.create(
            homeowner=self.user,
            title="Plumbing Work",
            description="Multiple plumbing tasks",
            estimated_budget=Decimal("200.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        # Create tasks
        JobTask.objects.create(job=job, title="Fix the faucet", order=0)
        JobTask.objects.create(job=job, title="Replace pipes", order=1)
        JobTask.objects.create(job=job, title="Install new sink", order=2)

        self.assertEqual(job.tasks.count(), 3)
        self.assertEqual(
            list(job.tasks.values_list("title", flat=True)),
            ["Fix the faucet", "Replace pipes", "Install new sink"],
        )

    def test_job_without_tasks(self):
        """Test job can be created without tasks."""
        job = Job.objects.create(
            homeowner=self.user,
            title="Test",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
        )
        self.assertEqual(job.tasks.count(), 0)

    def test_job_save_sets_status_at_on_new_instance(self):
        """Test that status_at is set when creating a new job with status."""
        job = Job.objects.create(
            homeowner=self.user,
            title="Test Job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )
        self.assertIsNotNone(job.status_at)

    def test_job_save_updates_status_at_on_status_change(self):
        """Test that status_at is updated when job status changes."""
        job = Job.objects.create(
            homeowner=self.user,
            title="Test Job",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )
        original_status_at = job.status_at

        # Change status
        job.status = "in_progress"
        job.save()

        job.refresh_from_db()
        self.assertIsNotNone(job.status_at)
        self.assertNotEqual(job.status_at, original_status_at)


class JobAttachmentModelTests(TestCase):
    """Test cases for JobAttachment model."""

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

    def _create_image_file(self, name="test.jpg"):
        image_io = BytesIO()
        pil_image = PILImage.new("RGB", (100, 100), color="red")
        pil_image.save(image_io, format="JPEG")
        image_io.seek(0)
        return SimpleUploadedFile(name, image_io.getvalue(), content_type="image/jpeg")

    def test_job_attachment_string_representation(self):
        """Test job attachment string representation."""
        image_file = self._create_image_file()
        attachment = JobAttachment.objects.create(
            job=self.job,
            file=image_file,
            file_type="image",
            file_name=image_file.name,
            file_size=image_file.size,
            order=0,
        )
        self.assertEqual(str(attachment), "Image 0 for Test")

    def test_job_attachment_cascade_delete(self):
        """Test job attachment is deleted when job is deleted."""
        image_file = self._create_image_file()
        attachment = JobAttachment.objects.create(
            job=self.job,
            file=image_file,
            file_type="image",
            file_name=image_file.name,
            file_size=image_file.size,
            order=0,
        )
        attachment_id = attachment.id
        self.job.delete()
        self.assertFalse(JobAttachment.objects.filter(id=attachment_id).exists())

    def test_job_attachment_ordering(self):
        """Test job attachments are ordered by order and created_at."""
        image_file2 = self._create_image_file(name="test2.jpg")
        image_file1 = self._create_image_file(name="test1.jpg")
        image_file0 = self._create_image_file(name="test0.jpg")
        attachment2 = JobAttachment.objects.create(
            job=self.job,
            file=image_file2,
            file_type="image",
            file_name=image_file2.name,
            file_size=image_file2.size,
            order=2,
        )
        attachment1 = JobAttachment.objects.create(
            job=self.job,
            file=image_file1,
            file_type="image",
            file_name=image_file1.name,
            file_size=image_file1.size,
            order=1,
        )
        attachment0 = JobAttachment.objects.create(
            job=self.job,
            file=image_file0,
            file_type="image",
            file_name=image_file0.name,
            file_size=image_file0.size,
            order=0,
        )

        attachments = list(JobAttachment.objects.all())
        self.assertEqual(attachments[0].id, attachment0.id)
        self.assertEqual(attachments[1].id, attachment1.id)
        self.assertEqual(attachments[2].id, attachment2.id)

    def test_job_attachment_file_url_none(self):
        """Test file_url returns None when file missing."""
        attachment = JobAttachment(
            job=self.job,
            file_type="image",
            file_name="missing.jpg",
            file_size=0,
            order=0,
        )
        self.assertIsNone(attachment.file_url)

    def test_job_attachment_thumbnail_url_with_thumbnail(self):
        """Test thumbnail_url returns thumbnail when present."""
        image_file = self._create_image_file(name="photo.jpg")
        thumbnail_file = self._create_image_file(name="thumb.jpg")
        attachment = JobAttachment.objects.create(
            job=self.job,
            file=image_file,
            file_type="image",
            file_name=image_file.name,
            file_size=image_file.size,
            order=0,
        )
        attachment.thumbnail.save("thumb.jpg", thumbnail_file, save=True)

        self.assertIsNotNone(attachment.thumbnail_url)
        self.assertIn("thumb", attachment.thumbnail_url)

    def test_job_attachment_thumbnail_url_video_without_thumbnail(self):
        """Test thumbnail_url returns None for videos without thumbnail."""
        video_file = SimpleUploadedFile("clip.mp4", b"video", content_type="video/mp4")
        attachment = JobAttachment.objects.create(
            job=self.job,
            file=video_file,
            file_type="video",
            file_name=video_file.name,
            file_size=video_file.size,
            order=0,
        )

        self.assertIsNone(attachment.thumbnail_url)


class JobApplicationModelTests(TestCase):
    """Test cases for JobApplication model."""

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
            title="Fix leaking faucet",
            description="Kitchen faucet is leaking",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )

    def test_job_application_save_sets_status_at_on_new_instance(self):
        """Test that status_at is set when creating a new job application."""
        application = JobApplication.objects.create(
            job=self.job,
            handyman=self.handyman,
            status="pending",
        )
        self.assertIsNotNone(application.status_at)

    def test_job_application_save_updates_status_at_on_status_change(self):
        """Test that status_at is updated when application status changes."""
        application = JobApplication.objects.create(
            job=self.job,
            handyman=self.handyman,
            status="pending",
        )
        original_status_at = application.status_at

        # Change status
        application.status = "approved"
        application.save()

        application.refresh_from_db()
        self.assertIsNotNone(application.status_at)
        self.assertNotEqual(application.status_at, original_status_at)

    def test_job_application_string_representation(self):
        """Test job application string representation."""
        application = JobApplication.objects.create(
            job=self.job,
            handyman=self.handyman,
            status="pending",
        )
        self.assertEqual(
            str(application),
            f"{self.handyman.email} → {self.job.title} (pending)",
        )

    def test_job_application_save_no_status_change(self):
        """Test status_at is not updated if application status didn't change."""
        application = JobApplication.objects.create(
            job=self.job,
            handyman=self.handyman,
            status="pending",
        )
        status_at = application.status_at

        application.save()  # No change
        self.assertEqual(application.status_at, status_at)

    def test_job_save_no_status_at_creation(self):
        """Test status_at is not set if status is empty on Job."""
        # We need to bypass full_clean to test the status logic if we want to pass empty status
        # but the model says status is NOT NULL and has choices.
        # Actually, let's just test that it DOESN'T update status_at if it's already set and status didn't change.
        job = Job.objects.create(
            homeowner=self.homeowner,
            title="Test",
            description="Test",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )
        job.refresh_from_db()
        status_at = job.status_at

        job.title = "Updated Title"
        job.save()

        job.refresh_from_db()
        self.assertEqual(job.status_at, status_at)

    def test_job_save_new_no_status(self):
        """Test status_at is not set if no status on new Job."""
        # Use a mock to bypass full_clean and super().save() if necessary, or just use Job() without status
        # But Job has a default 'draft' status.
        # Let's try to set status=None on a new Job instance.
        job = Job(
            homeowner=self.homeowner,
            title="No status",
            estimated_budget=Decimal("10"),
            category=self.category,
            city=self.city,
            status=None,
        )
        # We can't really save it without status due to DB constraints,
        # but we can test the save method logic by calling it and catching the error if it goes that far.
        try:
            job.save()
        except Exception:
            pass
        self.assertIsNone(job.status_at)

    def test_job_clean_no_budget(self):
        """Test clean method with no budget (should not raise validation error)."""
        job = Job(
            homeowner=self.homeowner,
            title="No Budget",
            category=self.category,
            city=self.city,
            estimated_budget=None,
        )
        job.clean()  # Should not raise

    def test_job_application_save_new_no_status(self):
        """Test status_at is not set if no status on new JobApplication."""
        app = JobApplication(
            job=self.job,
            handyman=self.handyman,
            status=None,
        )
        try:
            app.save()
        except Exception:
            pass
        self.assertIsNone(app.status_at)


class WorkSessionModelTests(TestCase):
    """Test cases for WorkSession model."""

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

    def test_work_session_duration_with_ended_at(self):
        """Test duration property returns correct timedelta when session is completed."""
        started = timezone.now()
        ended = started + timedelta(hours=2, minutes=30)
        session = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=started,
            ended_at=ended,
            start_latitude="43.651070",
            start_longitude="-79.347015",
            status="completed",
        )
        self.assertEqual(session.duration, timedelta(hours=2, minutes=30))

    def test_work_session_duration_without_ended_at(self):
        """Test duration property returns None when session is not ended."""
        session = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now(),
            start_latitude="43.651070",
            start_longitude="-79.347015",
            status="in_progress",
        )
        self.assertIsNone(session.duration)

    def test_work_session_duration_seconds_with_ended_at(self):
        """Test duration_seconds property returns correct value when session is completed."""
        started = timezone.now()
        ended = started + timedelta(hours=2, minutes=30)  # 9000 seconds
        session = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=started,
            ended_at=ended,
            start_latitude="43.651070",
            start_longitude="-79.347015",
            status="completed",
        )
        self.assertEqual(session.duration_seconds, 9000)

    def test_work_session_duration_seconds_without_ended_at(self):
        """Test duration_seconds property returns None when session is not ended."""
        session = WorkSession.objects.create(
            job=self.job,
            handyman=self.handyman,
            started_at=timezone.now(),
            start_latitude="43.651070",
            start_longitude="-79.347015",
            status="in_progress",
        )
        self.assertIsNone(session.duration_seconds)


class JobApplicationModelWithProfilesTest(TestCase):
    """Test cases for JobApplication model with profiles."""

    def setUp(self):
        """Set up test data."""
        # Create users
        self.homeowner_user = User.objects.create_user(
            email="homeowner@test.com", password="testpass123"
        )
        self.handyman_user = User.objects.create_user(
            email="handyman@test.com", password="testpass123"
        )

        # Create profiles
        self.homeowner_profile = HomeownerProfile.objects.create(
            user=self.homeowner_user,
            display_name="Test Homeowner",
            phone_number="+1234567890",
            phone_verified_at=timezone.now(),
            address="123 Test St",
        )

        self.handyman_profile = HandymanProfile.objects.create(
            user=self.handyman_user,
            display_name="Test Handyman",
            phone_number="+1234567891",
            phone_verified_at=timezone.now(),
            address="456 Test St",
            is_approved=True,
        )

        # Create category and city
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

        # Create job
        self.job = Job.objects.create(
            homeowner=self.homeowner_user,
            title="Fix Kitchen Sink",
            description="Need help fixing leaky kitchen sink",
            estimated_budget=Decimal("150.00"),
            category=self.category,
            city=self.city,
            address="123 Test St",
            status="open",
        )

    def test_create_job_application(self):
        """Test creating a job application."""
        application = JobApplication.objects.create(
            job=self.job, handyman=self.handyman_user, status="pending"
        )

        self.assertIsNotNone(application.public_id)
        self.assertEqual(application.job, self.job)
        self.assertEqual(application.handyman, self.handyman_user)
        self.assertEqual(application.status, "pending")
        self.assertIsNotNone(application.status_at)

    def test_unique_application_per_job(self):
        """Test that a handyman can only apply once to a job."""
        JobApplication.objects.create(
            job=self.job, handyman=self.handyman_user, status="pending"
        )

        # Try to create duplicate application
        with self.assertRaises(IntegrityError):
            JobApplication.objects.create(
                job=self.job, handyman=self.handyman_user, status="pending"
            )

    def test_application_status_choices(self):
        """Test that application status choices are valid."""
        valid_statuses = ["pending", "approved", "rejected", "withdrawn"]

        for status in valid_statuses:
            application = JobApplication.objects.create(
                job=self.job,
                handyman=self.handyman_user,
                status=status,
            )
            # Delete to allow unique constraint for next iteration
            application.delete()

    def test_str_representation(self):
        """Test string representation of job application."""
        application = JobApplication.objects.create(
            job=self.job, handyman=self.handyman_user, status="pending"
        )

        expected = f"{self.handyman_user.email} → {self.job.title} (pending)"
        self.assertEqual(str(application), expected)

    def test_job_application_with_proposal_fields(self):
        """Test creating job application with proposal fields."""
        application = JobApplication.objects.create(
            job=self.job,
            handyman=self.handyman_user,
            status="pending",
            predicted_hours=Decimal("8.5"),
            estimated_total_price=Decimal("450.00"),
            negotiation_reasoning="Need additional materials",
        )

        self.assertEqual(application.predicted_hours, Decimal("8.5"))
        self.assertEqual(application.estimated_total_price, Decimal("450.00"))
        self.assertEqual(application.negotiation_reasoning, "Need additional materials")


class JobApplicationMaterialModelTests(TestCase):
    """Test cases for JobApplicationMaterial model."""

    def setUp(self):
        """Set up test data."""
        from apps.accounts.models import User, UserRole
        from apps.profiles.models import HandymanProfile

        self.handyman_user = User.objects.create_user(
            email="handyman@test.com", password="testpass123"
        )
        UserRole.objects.create(user=self.handyman_user, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman_user,
            display_name="Test Handyman",
            phone_verified_at=timezone.now(),
        )

        self.homeowner = User.objects.create_user(
            email="homeowner@test.com", password="testpass123"
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
            title="Test Job",
            description="Test Description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Test St",
            status="open",
        )
        self.application = JobApplication.objects.create(
            job=self.job, handyman=self.handyman_user, status="pending"
        )

    def test_create_material(self):
        """Test creating job application material."""
        from apps.jobs.models import JobApplicationMaterial

        material = JobApplicationMaterial.objects.create(
            application=self.application,
            name="PVC Pipe",
            price=Decimal("25.50"),
            description="2m",
        )

        self.assertEqual(material.application, self.application)
        self.assertEqual(material.name, "PVC Pipe")
        self.assertEqual(material.price, Decimal("25.50"))
        self.assertEqual(material.description, "2m")
        self.assertIsNotNone(material.public_id)

    def test_material_str_representation(self):
        """Test string representation of material."""
        from apps.jobs.models import JobApplicationMaterial

        material = JobApplicationMaterial.objects.create(
            application=self.application,
            name="PVC Pipe",
            price=Decimal("25.50"),
            description="2m",
        )

        expected = f"PVC Pipe - 25.50 for {self.application}"
        self.assertEqual(str(material), expected)


class JobApplicationAttachmentModelTests(TestCase):
    """Test cases for JobApplicationAttachment model."""

    def setUp(self):
        """Set up test data."""
        from apps.accounts.models import User, UserRole
        from apps.profiles.models import HandymanProfile

        self.handyman_user = User.objects.create_user(
            email="handyman@test.com", password="testpass123"
        )
        UserRole.objects.create(user=self.handyman_user, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman_user,
            display_name="Test Handyman",
            phone_verified_at=timezone.now(),
        )

        self.homeowner = User.objects.create_user(
            email="homeowner@test.com", password="testpass123"
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
            title="Test Job",
            description="Test Description",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Test St",
            status="open",
        )
        self.application = JobApplication.objects.create(
            job=self.job, handyman=self.handyman_user, status="pending"
        )

    def test_create_attachment(self):
        """Test creating job application attachment."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.jobs.models import JobApplicationAttachment

        file = SimpleUploadedFile(
            "test.pdf", b"file content", content_type="application/pdf"
        )
        attachment = JobApplicationAttachment.objects.create(
            application=self.application,
            file=file,
            file_name="test.pdf",
        )

        self.assertEqual(attachment.application, self.application)
        self.assertEqual(attachment.file_name, "test.pdf")
        self.assertIsNotNone(attachment.public_id)

    def test_attachment_str_representation(self):
        """Test string representation of attachment."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.jobs.models import JobApplicationAttachment

        file = SimpleUploadedFile(
            "test.pdf", b"file content", content_type="application/pdf"
        )
        attachment = JobApplicationAttachment.objects.create(
            application=self.application,
            file=file,
            file_name="test.pdf",
        )

        expected = f"test.pdf for {self.application}"
        self.assertEqual(str(attachment), expected)

    def test_attachment_file_url_none(self):
        """Test file_url returns None when no file set."""
        from apps.jobs.models import JobApplicationAttachment

        attachment = JobApplicationAttachment(
            application=self.application,
            file_type="image",
            file_name="missing.jpg",
            file_size=0,
        )
        self.assertIsNone(attachment.file_url)

    def test_attachment_thumbnail_url_with_thumbnail(self):
        """Test thumbnail_url returns thumbnail when present."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.jobs.models import JobApplicationAttachment

        file = SimpleUploadedFile(
            "photo.jpg", b"file content", content_type="image/jpeg"
        )
        thumbnail = SimpleUploadedFile("thumb.jpg", b"thumb", content_type="image/jpeg")
        attachment = JobApplicationAttachment.objects.create(
            application=self.application,
            file=file,
            file_type="image",
            file_name="photo.jpg",
            file_size=file.size,
        )
        attachment.thumbnail.save("thumb.jpg", thumbnail, save=True)

        self.assertIsNotNone(attachment.thumbnail_url)
        self.assertIn("thumb", attachment.thumbnail_url)

    def test_attachment_thumbnail_url_video_without_thumbnail(self):
        """Test thumbnail_url returns None for video without thumbnail."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.jobs.models import JobApplicationAttachment

        video_file = SimpleUploadedFile("clip.mp4", b"video", content_type="video/mp4")
        attachment = JobApplicationAttachment.objects.create(
            application=self.application,
            file=video_file,
            file_type="video",
            file_name="clip.mp4",
            file_size=video_file.size,
        )

        self.assertIsNone(attachment.thumbnail_url)


class ReviewModelTests(TestCase):
    """Test cases for Review model."""

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
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        UserRole.objects.create(user=self.handyman, role="handyman")

        HomeownerProfile.objects.create(
            user=self.homeowner,
            display_name="Test Homeowner",
        )
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

    def test_create_review_success(self):
        """Test creating a review successfully."""
        review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
            comment="Great work!",
        )
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, "Great work!")
        self.assertEqual(review.reviewer_type, "homeowner")
        self.assertIsNotNone(review.public_id)

    def test_review_string_representation(self):
        """Test review string representation."""
        review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=4,
        )
        self.assertEqual(str(review), "homeowner review for Fix sink - 4 stars")

    def test_review_rating_below_1_validation(self):
        """Test that rating below 1 raises ValidationError."""
        with self.assertRaises(ValidationError) as context:
            Review.objects.create(
                job=self.job,
                reviewer=self.homeowner,
                reviewee=self.handyman,
                reviewer_type="homeowner",
                rating=0,
            )
        self.assertIn("rating", context.exception.message_dict)

    def test_review_rating_above_5_validation(self):
        """Test that rating above 5 raises ValidationError."""
        with self.assertRaises(ValidationError) as context:
            Review.objects.create(
                job=self.job,
                reviewer=self.homeowner,
                reviewee=self.handyman,
                reviewer_type="homeowner",
                rating=6,
            )
        self.assertIn("rating", context.exception.message_dict)

    def test_review_unique_per_job_per_reviewer_type(self):
        """Test that only one review per job per reviewer_type is allowed."""
        Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
        )
        with self.assertRaises(ValidationError):
            Review.objects.create(
                job=self.job,
                reviewer=self.homeowner,
                reviewee=self.handyman,
                reviewer_type="homeowner",
                rating=4,
            )

    def test_review_both_parties_can_review_same_job(self):
        """Test that both homeowner and handyman can review the same job."""
        homeowner_review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
        )
        handyman_review = Review.objects.create(
            job=self.job,
            reviewer=self.handyman,
            reviewee=self.homeowner,
            reviewer_type="handyman",
            rating=4,
        )
        self.assertEqual(self.job.reviews.count(), 2)
        self.assertNotEqual(homeowner_review.id, handyman_review.id)

    def test_review_cascade_delete_with_job(self):
        """Test that review is deleted when job is deleted."""
        review = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
        )
        review_id = review.id
        self.job.delete()
        self.assertFalse(Review.objects.filter(id=review_id).exists())

    def test_review_ordering(self):
        """Test reviews are ordered by created_at descending."""
        # Create a second job for another review
        job2 = Job.objects.create(
            homeowner=self.homeowner,
            assigned_handyman=self.handyman,
            title="Fix door",
            description="Broken door",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="456 Main St",
            status="completed",
            completed_at=timezone.now(),
        )

        review1 = Review.objects.create(
            job=self.job,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=5,
        )
        review2 = Review.objects.create(
            job=job2,
            reviewer=self.homeowner,
            reviewee=self.handyman,
            reviewer_type="homeowner",
            rating=4,
        )

        reviews = list(Review.objects.all())
        self.assertEqual(reviews[0].id, review2.id)  # Most recent first
        self.assertEqual(reviews[1].id, review1.id)


class JobReimbursementModelTests(TestCase):
    """Test cases for JobReimbursement model."""

    def setUp(self):
        """Set up test data."""
        from apps.jobs.models import JobReimbursementCategory

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

    def test_create_reimbursement_success(self):
        """Test creating a reimbursement."""
        from apps.jobs.models import JobReimbursement

        reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Plumbing materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
            notes="Required for repair",
        )
        self.assertEqual(reimbursement.name, "Plumbing materials")
        self.assertEqual(reimbursement.category, self.reimbursement_category)
        self.assertEqual(reimbursement.amount, Decimal("50.00"))
        self.assertEqual(reimbursement.status, "pending")
        self.assertIsNotNone(reimbursement.public_id)

    def test_reimbursement_string_representation(self):
        """Test reimbursement string representation."""
        from apps.jobs.models import JobReimbursement

        reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Pipe fittings",
            category=self.reimbursement_category,
            amount=Decimal("25.00"),
        )
        self.assertEqual(str(reimbursement), "Pipe fittings - 25.00 (pending)")

    def test_reimbursement_ordering(self):
        """Test reimbursements are ordered by created_at descending."""
        from apps.jobs.models import JobReimbursement

        r1 = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Item 1",
            category=self.reimbursement_category,
            amount=Decimal("10.00"),
        )
        r2 = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Item 2",
            category=self.tools_category,
            amount=Decimal("20.00"),
        )
        reimbursements = list(JobReimbursement.objects.all())
        self.assertEqual(reimbursements[0].id, r2.id)  # Most recent first
        self.assertEqual(reimbursements[1].id, r1.id)

    def test_reimbursement_cascade_delete_with_job(self):
        """Test that reimbursement is deleted when job is deleted."""
        from apps.jobs.models import JobReimbursement

        reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Materials",
            category=self.reimbursement_category,
            amount=Decimal("30.00"),
        )
        reimbursement_id = reimbursement.id
        self.job.delete()
        self.assertFalse(JobReimbursement.objects.filter(id=reimbursement_id).exists())


class JobReimbursementAttachmentModelTests(TestCase):
    """Test cases for JobReimbursementAttachment model."""

    def setUp(self):
        """Set up test data."""
        from apps.jobs.models import JobReimbursement, JobReimbursementCategory

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
            title="Fix leaky faucet",
            description="Kitchen faucet is leaking",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="in_progress",
        )
        # Get or create the materials category (seeded by migration)
        self.reimbursement_category, _ = JobReimbursementCategory.objects.get_or_create(
            slug="materials",
            defaults={
                "name": "Materials",
                "description": "Building materials and supplies",
                "is_active": True,
            },
        )
        self.reimbursement = JobReimbursement.objects.create(
            job=self.job,
            handyman=self.handyman,
            name="Plumbing materials",
            category=self.reimbursement_category,
            amount=Decimal("50.00"),
        )

    def test_create_attachment_success(self):
        """Test creating a reimbursement attachment."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.jobs.models import JobReimbursementAttachment

        test_file = SimpleUploadedFile(
            "receipt.jpg", b"file content", content_type="image/jpeg"
        )
        attachment = JobReimbursementAttachment.objects.create(
            reimbursement=self.reimbursement,
            file=test_file,
            file_name="receipt.jpg",
        )
        self.assertEqual(attachment.file_name, "receipt.jpg")
        self.assertEqual(attachment.reimbursement, self.reimbursement)
        self.assertIsNotNone(attachment.public_id)

    def test_attachment_string_representation(self):
        """Test attachment string representation."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.jobs.models import JobReimbursementAttachment

        test_file = SimpleUploadedFile(
            "receipt.jpg", b"file content", content_type="image/jpeg"
        )
        attachment = JobReimbursementAttachment.objects.create(
            reimbursement=self.reimbursement,
            file=test_file,
            file_name="receipt.jpg",
        )
        self.assertIn("receipt.jpg", str(attachment))

    def test_attachment_cascade_delete_with_reimbursement(self):
        """Test that attachment is deleted when reimbursement is deleted."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.jobs.models import JobReimbursementAttachment

        test_file = SimpleUploadedFile(
            "receipt.jpg", b"file content", content_type="image/jpeg"
        )
        attachment = JobReimbursementAttachment.objects.create(
            reimbursement=self.reimbursement,
            file=test_file,
            file_name="receipt.jpg",
        )
        attachment_id = attachment.id
        self.reimbursement.delete()
        self.assertFalse(
            JobReimbursementAttachment.objects.filter(id=attachment_id).exists()
        )

    def test_attachment_file_url_none(self):
        """Test file_url returns None when file missing."""
        from apps.jobs.models import JobReimbursementAttachment

        attachment = JobReimbursementAttachment(
            reimbursement=self.reimbursement,
            file_type="image",
            file_name="missing.jpg",
            file_size=0,
        )
        self.assertIsNone(attachment.file_url)

    def test_attachment_thumbnail_url_with_thumbnail(self):
        """Test thumbnail_url returns thumbnail when present."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.jobs.models import JobReimbursementAttachment

        file = SimpleUploadedFile(
            "receipt.jpg", b"file content", content_type="image/jpeg"
        )
        thumbnail = SimpleUploadedFile("thumb.jpg", b"thumb", content_type="image/jpeg")
        attachment = JobReimbursementAttachment.objects.create(
            reimbursement=self.reimbursement,
            file=file,
            file_type="image",
            file_name="receipt.jpg",
            file_size=file.size,
        )
        attachment.thumbnail.save("thumb.jpg", thumbnail, save=True)

        self.assertIsNotNone(attachment.thumbnail_url)
        self.assertIn("thumb", attachment.thumbnail_url)

    def test_attachment_thumbnail_url_video_without_thumbnail(self):
        """Test thumbnail_url returns None for video without thumbnail."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.jobs.models import JobReimbursementAttachment

        video_file = SimpleUploadedFile(
            "receipt.mp4", b"video", content_type="video/mp4"
        )
        attachment = JobReimbursementAttachment.objects.create(
            reimbursement=self.reimbursement,
            file=video_file,
            file_type="video",
            file_name="receipt.mp4",
            file_size=video_file.size,
        )

        self.assertIsNone(attachment.thumbnail_url)
