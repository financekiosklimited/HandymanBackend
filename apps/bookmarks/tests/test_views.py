"""Tests for bookmark mobile views."""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.bookmarks.models import HandymanBookmark, JobBookmark
from apps.jobs.models import City, Job, JobCategory
from apps.profiles.models import HandymanProfile, HomeownerProfile


class HandymanJobBookmarkListCreateViewTests(APITestCase):
    """Test cases for HandymanJobBookmarkListCreateView."""

    def setUp(self):
        """Set up test data."""
        self.list_create_url = "/api/v1/mobile/handyman/bookmarks/jobs/"

        # Create handyman user
        self.handyman_user = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user, role="handyman")
        self.handyman_user.email_verified_at = "2024-01-01T00:00:00Z"
        self.handyman_user.save()
        self.handyman_user.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
        }
        self.handyman_profile = HandymanProfile.objects.create(
            user=self.handyman_user,
            display_name="John Handyman",
            is_approved=True,
            is_active=True,
        )

        # Create homeowner user
        self.homeowner_user = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner_user, role="homeowner")
        self.homeowner_user.email_verified_at = "2024-01-01T00:00:00Z"
        self.homeowner_user.save()
        self.homeowner_user.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
        }
        self.homeowner_profile = HomeownerProfile.objects.create(
            user=self.homeowner_user,
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

        # Create jobs
        self.job1 = Job.objects.create(
            homeowner=self.homeowner_user,
            title="Fix leaking faucet",
            description="Kitchen faucet needs fixing",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
            latitude=Decimal("43.6532"),
            longitude=Decimal("-79.3832"),
        )
        self.job2 = Job.objects.create(
            homeowner=self.homeowner_user,
            title="Repair door",
            description="Front door is squeaky",
            estimated_budget=Decimal("75.00"),
            category=self.category,
            city=self.city,
            address="456 Oak Ave",
            status="open",
            latitude=Decimal("43.6600"),
            longitude=Decimal("-79.3900"),
        )
        self.completed_job = Job.objects.create(
            homeowner=self.homeowner_user,
            title="Completed job",
            description="Already done",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="789 Pine St",
            status="completed",
        )
        self.deleted_job = Job.objects.create(
            homeowner=self.homeowner_user,
            title="Deleted job",
            description="This was deleted",
            estimated_budget=Decimal("200.00"),
            category=self.category,
            city=self.city,
            address="999 Elm St",
            status="deleted",
        )

    def test_list_bookmarked_jobs_empty(self):
        """Test listing bookmarked jobs when none exist."""
        self.client.force_authenticate(user=self.handyman_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Bookmarked jobs retrieved successfully"
        )
        self.assertEqual(len(response.data["data"]), 0)
        self.assertIn("pagination", response.data["meta"])

    def test_list_bookmarked_jobs_success(self):
        """Test successfully listing bookmarked jobs."""
        # Create bookmarks
        JobBookmark.objects.create(handyman=self.handyman_user, job=self.job1)
        JobBookmark.objects.create(handyman=self.handyman_user, job=self.job2)

        self.client.force_authenticate(user=self.handyman_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 2)

    def test_list_bookmarked_jobs_excludes_deleted_jobs(self):
        """Test that deleted jobs are excluded from bookmark list."""
        # Bookmark both a regular job and a deleted job
        JobBookmark.objects.create(handyman=self.handyman_user, job=self.job1)
        JobBookmark.objects.create(handyman=self.handyman_user, job=self.deleted_job)

        self.client.force_authenticate(user=self.handyman_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Fix leaking faucet")

    def test_list_bookmarked_jobs_includes_completed_jobs(self):
        """Test that completed jobs are still shown in bookmark list."""
        JobBookmark.objects.create(handyman=self.handyman_user, job=self.completed_job)

        self.client.force_authenticate(user=self.handyman_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["status"], "completed")

    def test_list_bookmarked_jobs_with_coordinates(self):
        """Test listing bookmarked jobs with distance calculation."""
        JobBookmark.objects.create(handyman=self.handyman_user, job=self.job1)

        self.client.force_authenticate(user=self.handyman_user)
        response = self.client.get(
            self.list_create_url,
            {"latitude": "43.6532", "longitude": "-79.3832"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        # Distance should be calculated (very close to 0 since same coordinates)
        self.assertIn("distance_km", response.data["data"][0])

    def test_list_bookmarked_jobs_with_invalid_coordinates_out_of_range(self):
        """Test listing bookmarked jobs with out-of-range coordinates."""
        JobBookmark.objects.create(handyman=self.handyman_user, job=self.job1)

        self.client.force_authenticate(user=self.handyman_user)
        # Latitude out of range (> 90)
        response = self.client.get(
            self.list_create_url,
            {"latitude": "100.0", "longitude": "-79.3832"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        # Distance should be None since coordinates are invalid
        self.assertIsNone(response.data["data"][0]["distance_km"])

    def test_list_bookmarked_jobs_with_invalid_coordinates_non_numeric(self):
        """Test listing bookmarked jobs with non-numeric coordinates."""
        JobBookmark.objects.create(handyman=self.handyman_user, job=self.job1)

        self.client.force_authenticate(user=self.handyman_user)
        # Non-numeric coordinates
        response = self.client.get(
            self.list_create_url,
            {"latitude": "invalid", "longitude": "-79.3832"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        # Distance should be None since coordinates are invalid
        self.assertIsNone(response.data["data"][0]["distance_km"])

    def test_list_bookmarked_jobs_pagination(self):
        """Test pagination of bookmarked jobs."""
        # Create 15 jobs and bookmark them
        for i in range(15):
            job = Job.objects.create(
                homeowner=self.homeowner_user,
                title=f"Job {i}",
                description="Test job",
                estimated_budget=Decimal("50.00"),
                category=self.category,
                city=self.city,
                address=f"{i} Test St",
                status="open",
            )
            JobBookmark.objects.create(handyman=self.handyman_user, job=job)

        self.client.force_authenticate(user=self.handyman_user)
        response = self.client.get(self.list_create_url, {"page": 1, "page_size": 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 10)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 15)
        self.assertEqual(response.data["meta"]["pagination"]["total_pages"], 2)
        self.assertTrue(response.data["meta"]["pagination"]["has_next"])
        self.assertFalse(response.data["meta"]["pagination"]["has_previous"])

    def test_list_bookmarked_jobs_includes_bookmarked_at(self):
        """Test that bookmarked_at field is included in response."""
        JobBookmark.objects.create(handyman=self.handyman_user, job=self.job1)

        self.client.force_authenticate(user=self.handyman_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("bookmarked_at", response.data["data"][0])

    def test_list_bookmarked_jobs_unauthenticated(self):
        """Test that unauthenticated users cannot list bookmarks."""
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_bookmarked_jobs_wrong_role(self):
        """Test that homeowners cannot access handyman bookmark endpoints."""
        self.client.force_authenticate(user=self.homeowner_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_job_bookmark_success(self):
        """Test successfully creating a job bookmark."""
        self.client.force_authenticate(user=self.handyman_user)
        response = self.client.post(
            self.list_create_url,
            {"job_id": str(self.job1.public_id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Job bookmarked successfully")
        self.assertEqual(
            JobBookmark.objects.filter(
                handyman=self.handyman_user, job=self.job1
            ).count(),
            1,
        )

    def test_create_job_bookmark_already_bookmarked(self):
        """Test that bookmarking an already bookmarked job returns existing bookmark."""
        JobBookmark.objects.create(handyman=self.handyman_user, job=self.job1)

        self.client.force_authenticate(user=self.handyman_user)
        response = self.client.post(
            self.list_create_url,
            {"job_id": str(self.job1.public_id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Should not create a duplicate
        self.assertEqual(
            JobBookmark.objects.filter(
                handyman=self.handyman_user, job=self.job1
            ).count(),
            1,
        )

    def test_create_job_bookmark_job_not_found(self):
        """Test bookmarking a non-existent job."""
        self.client.force_authenticate(user=self.handyman_user)
        response = self.client.post(
            self.list_create_url,
            {"job_id": "00000000-0000-0000-0000-000000000000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("job_id", response.data["errors"])

    def test_create_job_bookmark_only_open_jobs(self):
        """Test that only open jobs can be bookmarked."""
        self.client.force_authenticate(user=self.handyman_user)
        response = self.client.post(
            self.list_create_url,
            {"job_id": str(self.completed_job.public_id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("job_id", response.data["errors"])

    def test_create_job_bookmark_unauthenticated(self):
        """Test that unauthenticated users cannot create bookmarks."""
        response = self.client.post(
            self.list_create_url,
            {"job_id": str(self.job1.public_id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class HandymanJobBookmarkDeleteViewTests(APITestCase):
    """Test cases for HandymanJobBookmarkDeleteView."""

    def setUp(self):
        """Set up test data."""
        # Create handyman user
        self.handyman_user = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user, role="handyman")
        self.handyman_user.email_verified_at = "2024-01-01T00:00:00Z"
        self.handyman_user.save()
        self.handyman_user.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
        }
        self.handyman_profile = HandymanProfile.objects.create(
            user=self.handyman_user,
            display_name="John Handyman",
            is_approved=True,
            is_active=True,
        )

        # Create homeowner user
        self.homeowner_user = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner_user, role="homeowner")
        HomeownerProfile.objects.create(user=self.homeowner_user)

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

        # Create job
        self.job = Job.objects.create(
            homeowner=self.homeowner_user,
            title="Fix leaking faucet",
            description="Kitchen faucet needs fixing",
            estimated_budget=Decimal("50.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )

        # Create bookmark
        self.bookmark = JobBookmark.objects.create(
            handyman=self.handyman_user,
            job=self.job,
        )

        self.delete_url = (
            f"/api/v1/mobile/handyman/bookmarks/jobs/{self.job.public_id}/"
        )

    def test_delete_job_bookmark_success(self):
        """Test successfully deleting a job bookmark."""
        self.client.force_authenticate(user=self.handyman_user)
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Bookmark removed successfully")
        self.assertEqual(JobBookmark.objects.count(), 0)

    def test_delete_job_bookmark_not_found(self):
        """Test deleting a non-existent bookmark."""
        self.client.force_authenticate(user=self.handyman_user)
        response = self.client.delete(
            "/api/v1/mobile/handyman/bookmarks/jobs/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_job_bookmark_other_users_bookmark(self):
        """Test that a user cannot delete another user's bookmark."""
        # Create another handyman
        other_handyman = User.objects.create_user(
            email="other.handyman@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=other_handyman, role="handyman")
        other_handyman.email_verified_at = "2024-01-01T00:00:00Z"
        other_handyman.save()
        other_handyman.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
        }
        HandymanProfile.objects.create(
            user=other_handyman,
            display_name="Other Handyman",
            is_approved=True,
            is_active=True,
        )

        self.client.force_authenticate(user=other_handyman)
        response = self.client.delete(self.delete_url)
        # Should return 404 since the bookmark belongs to another user
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # Original bookmark should still exist
        self.assertEqual(JobBookmark.objects.count(), 1)

    def test_delete_job_bookmark_unauthenticated(self):
        """Test that unauthenticated users cannot delete bookmarks."""
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class HomeownerHandymanBookmarkListCreateViewTests(APITestCase):
    """Test cases for HomeownerHandymanBookmarkListCreateView."""

    def setUp(self):
        """Set up test data."""
        self.list_create_url = "/api/v1/mobile/homeowner/bookmarks/handymen/"

        # Create homeowner user
        self.homeowner_user = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner_user, role="homeowner")
        self.homeowner_user.email_verified_at = "2024-01-01T00:00:00Z"
        self.homeowner_user.save()
        self.homeowner_user.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
        }
        self.homeowner_profile = HomeownerProfile.objects.create(
            user=self.homeowner_user,
        )

        # Create handyman users
        self.handyman_user1 = User.objects.create_user(
            email="handyman1@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user1, role="handyman")
        self.handyman_user1.email_verified_at = "2024-01-01T00:00:00Z"
        self.handyman_user1.save()
        self.handyman_user1.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
        }
        self.handyman_profile1 = HandymanProfile.objects.create(
            user=self.handyman_user1,
            display_name="John Handyman",
            is_approved=True,
            is_active=True,
            latitude=Decimal("43.6532"),
            longitude=Decimal("-79.3832"),
        )

        self.handyman_user2 = User.objects.create_user(
            email="handyman2@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user2, role="handyman")
        self.handyman_user2.email_verified_at = "2024-01-01T00:00:00Z"
        self.handyman_user2.save()
        self.handyman_profile2 = HandymanProfile.objects.create(
            user=self.handyman_user2,
            display_name="Jane Handyman",
            is_approved=True,
            is_active=True,
            latitude=Decimal("43.6600"),
            longitude=Decimal("-79.3900"),
        )

        # Create inactive handyman
        self.inactive_handyman_user = User.objects.create_user(
            email="inactive.handyman@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.inactive_handyman_user, role="handyman")
        self.inactive_handyman_profile = HandymanProfile.objects.create(
            user=self.inactive_handyman_user,
            display_name="Inactive Handyman",
            is_approved=True,
            is_active=False,
        )

        # Create unapproved handyman
        self.unapproved_handyman_user = User.objects.create_user(
            email="unapproved.handyman@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.unapproved_handyman_user, role="handyman")
        self.unapproved_handyman_profile = HandymanProfile.objects.create(
            user=self.unapproved_handyman_user,
            display_name="Unapproved Handyman",
            is_approved=False,
            is_active=True,
        )

    def test_list_bookmarked_handymen_empty(self):
        """Test listing bookmarked handymen when none exist."""
        self.client.force_authenticate(user=self.homeowner_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Bookmarked handymen retrieved successfully"
        )
        self.assertEqual(len(response.data["data"]), 0)
        self.assertIn("pagination", response.data["meta"])

    def test_list_bookmarked_handymen_success(self):
        """Test successfully listing bookmarked handymen."""
        # Create bookmarks
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user, handyman_profile=self.handyman_profile1
        )
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user, handyman_profile=self.handyman_profile2
        )

        self.client.force_authenticate(user=self.homeowner_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 2)

    def test_list_bookmarked_handymen_excludes_inactive(self):
        """Test that inactive handymen are excluded from bookmark list."""
        # Bookmark both an active and inactive handyman
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user, handyman_profile=self.handyman_profile1
        )
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user,
            handyman_profile=self.inactive_handyman_profile,
        )

        self.client.force_authenticate(user=self.homeowner_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["display_name"], "John Handyman")

    def test_list_bookmarked_handymen_excludes_unapproved(self):
        """Test that unapproved handymen are excluded from bookmark list."""
        # Bookmark both an approved and unapproved handyman
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user, handyman_profile=self.handyman_profile1
        )
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user,
            handyman_profile=self.unapproved_handyman_profile,
        )

        self.client.force_authenticate(user=self.homeowner_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["display_name"], "John Handyman")

    def test_list_bookmarked_handymen_with_coordinates(self):
        """Test listing bookmarked handymen with distance calculation."""
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user, handyman_profile=self.handyman_profile1
        )

        self.client.force_authenticate(user=self.homeowner_user)
        response = self.client.get(
            self.list_create_url,
            {"latitude": "43.6532", "longitude": "-79.3832"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        # Distance should be calculated
        self.assertIn("distance_km", response.data["data"][0])

    def test_list_bookmarked_handymen_with_invalid_coordinates_out_of_range(self):
        """Test listing bookmarked handymen with out-of-range coordinates."""
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user, handyman_profile=self.handyman_profile1
        )

        self.client.force_authenticate(user=self.homeowner_user)
        # Longitude out of range (> 180)
        response = self.client.get(
            self.list_create_url,
            {"latitude": "43.6532", "longitude": "200.0"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        # Distance should be None since coordinates are invalid
        self.assertIsNone(response.data["data"][0]["distance_km"])

    def test_list_bookmarked_handymen_with_invalid_coordinates_non_numeric(self):
        """Test listing bookmarked handymen with non-numeric coordinates."""
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user, handyman_profile=self.handyman_profile1
        )

        self.client.force_authenticate(user=self.homeowner_user)
        # Non-numeric coordinates
        response = self.client.get(
            self.list_create_url,
            {"latitude": "43.6532", "longitude": "not_a_number"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        # Distance should be None since coordinates are invalid
        self.assertIsNone(response.data["data"][0]["distance_km"])

    def test_list_bookmarked_handymen_pagination(self):
        """Test pagination of bookmarked handymen."""
        # Create 15 handymen and bookmark them
        for i in range(15):
            user = User.objects.create_user(
                email=f"pagination_handyman{i}@example.com",
                password="testpass123",
            )
            UserRole.objects.create(user=user, role="handyman")
            profile = HandymanProfile.objects.create(
                user=user,
                display_name=f"Pagination Handyman {i}",
                is_approved=True,
                is_active=True,
            )
            HandymanBookmark.objects.create(
                homeowner=self.homeowner_user, handyman_profile=profile
            )

        self.client.force_authenticate(user=self.homeowner_user)
        response = self.client.get(self.list_create_url, {"page": 1, "page_size": 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 10)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 15)
        self.assertEqual(response.data["meta"]["pagination"]["total_pages"], 2)
        self.assertTrue(response.data["meta"]["pagination"]["has_next"])
        self.assertFalse(response.data["meta"]["pagination"]["has_previous"])

    def test_list_bookmarked_handymen_includes_bookmarked_at(self):
        """Test that bookmarked_at field is included in response."""
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user, handyman_profile=self.handyman_profile1
        )

        self.client.force_authenticate(user=self.homeowner_user)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("bookmarked_at", response.data["data"][0])

    def test_list_bookmarked_handymen_unauthenticated(self):
        """Test that unauthenticated users cannot list bookmarks."""
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_bookmarked_handymen_wrong_role(self):
        """Test that handymen cannot access homeowner bookmark endpoints."""
        self.client.force_authenticate(user=self.handyman_user1)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_handyman_bookmark_success(self):
        """Test successfully creating a handyman bookmark."""
        self.client.force_authenticate(user=self.homeowner_user)
        response = self.client.post(
            self.list_create_url,
            {"handyman_id": str(self.handyman_profile1.public_id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Handyman bookmarked successfully")
        self.assertEqual(
            HandymanBookmark.objects.filter(
                homeowner=self.homeowner_user, handyman_profile=self.handyman_profile1
            ).count(),
            1,
        )

    def test_create_handyman_bookmark_already_bookmarked(self):
        """Test that bookmarking an already bookmarked handyman returns existing bookmark."""
        HandymanBookmark.objects.create(
            homeowner=self.homeowner_user, handyman_profile=self.handyman_profile1
        )

        self.client.force_authenticate(user=self.homeowner_user)
        response = self.client.post(
            self.list_create_url,
            {"handyman_id": str(self.handyman_profile1.public_id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Should not create a duplicate
        self.assertEqual(
            HandymanBookmark.objects.filter(
                homeowner=self.homeowner_user, handyman_profile=self.handyman_profile1
            ).count(),
            1,
        )

    def test_create_handyman_bookmark_handyman_not_found(self):
        """Test bookmarking a non-existent handyman."""
        self.client.force_authenticate(user=self.homeowner_user)
        response = self.client.post(
            self.list_create_url,
            {"handyman_id": "00000000-0000-0000-0000-000000000000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("handyman_id", response.data["errors"])

    def test_create_handyman_bookmark_only_active_approved_handymen(self):
        """Test that only active and approved handymen can be bookmarked."""
        self.client.force_authenticate(user=self.homeowner_user)

        # Try to bookmark inactive handyman
        response = self.client.post(
            self.list_create_url,
            {"handyman_id": str(self.inactive_handyman_profile.public_id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("handyman_id", response.data["errors"])

        # Try to bookmark unapproved handyman
        response = self.client.post(
            self.list_create_url,
            {"handyman_id": str(self.unapproved_handyman_profile.public_id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("handyman_id", response.data["errors"])

    def test_create_handyman_bookmark_unauthenticated(self):
        """Test that unauthenticated users cannot create bookmarks."""
        response = self.client.post(
            self.list_create_url,
            {"handyman_id": str(self.handyman_profile1.public_id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class HomeownerHandymanBookmarkDeleteViewTests(APITestCase):
    """Test cases for HomeownerHandymanBookmarkDeleteView."""

    def setUp(self):
        """Set up test data."""
        # Create homeowner user
        self.homeowner_user = User.objects.create_user(
            email="homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner_user, role="homeowner")
        self.homeowner_user.email_verified_at = "2024-01-01T00:00:00Z"
        self.homeowner_user.save()
        self.homeowner_user.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
        }
        self.homeowner_profile = HomeownerProfile.objects.create(
            user=self.homeowner_user,
        )

        # Create handyman user
        self.handyman_user = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user, role="handyman")
        self.handyman_profile = HandymanProfile.objects.create(
            user=self.handyman_user,
            display_name="John Handyman",
            is_approved=True,
            is_active=True,
        )

        # Create bookmark
        self.bookmark = HandymanBookmark.objects.create(
            homeowner=self.homeowner_user,
            handyman_profile=self.handyman_profile,
        )

        self.delete_url = f"/api/v1/mobile/homeowner/bookmarks/handymen/{self.handyman_profile.public_id}/"

    def test_delete_handyman_bookmark_success(self):
        """Test successfully deleting a handyman bookmark."""
        self.client.force_authenticate(user=self.homeowner_user)
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Bookmark removed successfully")
        self.assertEqual(HandymanBookmark.objects.count(), 0)

    def test_delete_handyman_bookmark_not_found(self):
        """Test deleting a non-existent bookmark."""
        self.client.force_authenticate(user=self.homeowner_user)
        response = self.client.delete(
            "/api/v1/mobile/homeowner/bookmarks/handymen/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_handyman_bookmark_other_users_bookmark(self):
        """Test that a user cannot delete another user's bookmark."""
        # Create another homeowner
        other_homeowner = User.objects.create_user(
            email="other.homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=other_homeowner, role="homeowner")
        other_homeowner.email_verified_at = "2024-01-01T00:00:00Z"
        other_homeowner.save()
        other_homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
        }
        HomeownerProfile.objects.create(user=other_homeowner)

        self.client.force_authenticate(user=other_homeowner)
        response = self.client.delete(self.delete_url)
        # Should return 404 since the bookmark belongs to another user
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # Original bookmark should still exist
        self.assertEqual(HandymanBookmark.objects.count(), 1)

    def test_delete_handyman_bookmark_unauthenticated(self):
        """Test that unauthenticated users cannot delete bookmarks."""
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
