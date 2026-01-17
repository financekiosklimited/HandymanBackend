"""Tests for mobile profile views."""

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.profiles.models import HandymanCategory, HandymanProfile, HomeownerProfile


class MobileHandymanCategoryListViewTests(APITestCase):
    """Test cases for mobile HandymanCategoryListView."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/handyman-categories/"

        # Create test categories
        HandymanCategory.objects.create(name="Plumbing", is_active=True)
        HandymanCategory.objects.create(name="Electrical", is_active=True)
        HandymanCategory.objects.create(name="Inactive", is_active=False)

    def test_list_categories_success_no_auth(self):
        """Test successfully listing active categories without authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Categories retrieved successfully")
        self.assertEqual(len(response.data["data"]), 2)  # Only active categories

    def test_list_categories_returns_only_active(self):
        """Test only active categories are returned."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        category_names = [c["name"] for c in response.data["data"]]
        self.assertIn("Plumbing", category_names)
        self.assertIn("Electrical", category_names)
        self.assertNotIn("Inactive", category_names)

    def test_list_categories_returns_expected_fields(self):
        """Test response contains expected fields."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for category in response.data["data"]:
            self.assertIn("public_id", category)
            self.assertIn("name", category)

    def test_list_categories_web_platform_blocked(self):
        """Test web platform cannot access mobile endpoint."""
        user = User.objects.create_user(
            email="webuser@example.com",
            password="testpass123",
        )
        user.token_payload = {
            "plat": "web",
            "active_role": None,
            "roles": [],
            "email_verified": False,
        }
        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MobileHomeownerProfileViewTests(APITestCase):
    """Test cases for mobile HomeownerProfileView."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/homeowner/profile"
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
        self.profile = HomeownerProfile.objects.create(
            user=self.user,
            display_name="Test Homeowner",
            phone_number="+1234567890",
            address="123 Main St",
        )

        # Add handymen browsing tests here to keep related data isolated.

    def test_get_profile_success(self):
        """Test successfully getting homeowner profile."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Profile retrieved successfully")
        self.assertEqual(response.data["data"]["display_name"], "Test Homeowner")
        self.assertEqual(response.data["data"]["phone_number"], "+1234567890")

    def test_get_profile_unauthenticated(self):
        """Test getting profile without authentication fails."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile_success(self):
        """Test successfully updating homeowner profile."""
        self.client.force_authenticate(user=self.user)
        data = {
            "display_name": "Updated Name",
            "address": "456 Oak Ave",
            "date_of_birth": "1990-01-01",
        }
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Profile updated successfully")

        # Verify update in database
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, "Updated Name")
        self.assertEqual(self.profile.address, "456 Oak Ave")
        self.assertEqual(self.profile.date_of_birth.isoformat(), "1990-01-01")
        # phone_number should be ignored/unchanged
        self.assertEqual(self.profile.phone_number, "+1234567890")

    def test_update_profile_partial(self):
        """Test partial update of homeowner profile."""
        self.client.force_authenticate(user=self.user)
        data = {"display_name": "Only Name Updated"}
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify only display_name was updated
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, "Only Name Updated")
        self.assertEqual(self.profile.phone_number, "+1234567890")  # Unchanged

    def test_update_profile_unauthenticated(self):
        """Test updating profile without authentication fails."""
        data = {"display_name": "New Name"}
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile_not_found_returns_error(self):
        """Test fetching profile returns 404 when profile is missing."""
        self.profile.delete()
        user = User.objects.get(pk=self.user.pk)
        user.token_payload = self.user.token_payload
        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Profile not found")

    def test_update_profile_not_found_returns_error(self):
        """Test updating profile returns 404 when profile is missing."""
        self.profile.delete()
        # Ensure we don't have a cached profile on request.user
        user = User.objects.get(pk=self.user.pk)
        user.token_payload = self.user.token_payload
        self.client.force_authenticate(user=user)
        response = self.client.put(
            self.url, {"display_name": "New Name"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Profile not found")

    def test_update_profile_validation_error(self):
        """Test updating profile returns validation errors for invalid data."""
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            self.url,
            {"display_name": "", "phone_number": "", "address": ""},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Validation failed")
        self.assertIn("display_name", response.data["errors"])


class MobileHomeownerHandymanDetailViewTests(APITestCase):
    """Test cases for mobile HomeownerHandymanDetailView."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="homeowner_detail@example.com",
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

        # Handyman user
        self.handyman_user = User.objects.create_user(
            email="handyman_detail_ho@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user, role="handyman")
        self.handyman = HandymanProfile.objects.create(
            user=self.handyman_user,
            display_name="Detail Handyman",
            phone_number="+1234567890",
            address="123 Main St",
            hourly_rate="75.00",
            latitude="43.651070",
            longitude="-79.347015",
            is_active=True,
            is_available=True,
            is_approved=True,
        )
        self.url = f"/api/v1/mobile/homeowner/handymen/{self.handyman.user.public_id}/"

    def test_get_handyman_detail_success(self):
        """Test successfully getting handyman detail as homeowner."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Handyman retrieved successfully")
        self.assertEqual(response.data["data"]["display_name"], "Detail Handyman")

    def test_get_handyman_detail_not_found(self):
        """Test getting handyman detail fails if criteria not met."""
        self.client.force_authenticate(user=self.user)

        # 1. Not approved
        self.handyman.is_approved = False
        self.handyman.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # 2. Not active
        self.handyman.is_approved = True
        self.handyman.is_active = False
        self.handyman.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # 3. Not available
        self.handyman.is_active = True
        self.handyman.is_available = False
        self.handyman.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # 4. Missing coordinates
        self.handyman.is_available = True
        self.handyman.latitude = None
        self.handyman.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class MobileHandymanBrowsingTests(APITestCase):
    """Test cases for homeowner browsing handymen."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/homeowner/handymen/nearby/"
        self.user = User.objects.create_user(
            email="homeowner_browse@example.com",
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

    def test_list_handymen_without_coordinates_success(self):
        """Test listing handymen without coordinates returns all visible handymen."""
        # Create a handyman
        handyman_user = User.objects.create_user(
            email="handyman@example.com", password="password"
        )
        UserRole.objects.create(user=handyman_user, role="handyman")
        HandymanProfile.objects.create(
            user=handyman_user,
            display_name="Test Handyman",
            is_active=True,
            is_available=True,
            is_approved=True,
            latitude=43.651070,
            longitude=-79.347015,
            rating=4.5,
            review_count=10,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["display_name"], "Test Handyman")
        # distance_km should be None when no coordinates provided
        self.assertIsNone(response.data["data"][0]["distance_km"])

    def test_list_handymen_with_coordinates_validation(self):
        """Test coordinate validation for handymen listing."""
        self.client.force_authenticate(user=self.user)

        # Invalid numbers - should return 400
        response = self.client.get(f"{self.url}?latitude=abc&longitude=123")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Out of range latitude
        response = self.client.get(f"{self.url}?latitude=100&longitude=45")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Out of range longitude
        response = self.client.get(f"{self.url}?latitude=45&longitude=200")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_handymen_with_coordinates_success(self):
        """Test listing handymen with coordinates includes distance."""
        # Create a handyman
        handyman_user = User.objects.create_user(
            email="handyman2@example.com", password="password"
        )
        UserRole.objects.create(user=handyman_user, role="handyman")
        HandymanProfile.objects.create(
            user=handyman_user,
            display_name="Nearby Handyman",
            is_active=True,
            is_available=True,
            is_approved=True,
            latitude=43.651070,
            longitude=-79.347015,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.url}?latitude=43.65&longitude=-79.34")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["display_name"], "Nearby Handyman")
        # distance_km should be calculated
        self.assertIsNotNone(response.data["data"][0]["distance_km"])

    def test_list_handymen_shows_all_no_radius_filter(self):
        """Test all handymen are returned regardless of distance (no radius filter)."""
        # Create a near handyman
        near_user = User.objects.create_user(
            email="near_handyman@example.com", password="password"
        )
        UserRole.objects.create(user=near_user, role="handyman")
        HandymanProfile.objects.create(
            user=near_user,
            display_name="Near Handyman",
            is_active=True,
            is_available=True,
            is_approved=True,
            latitude=43.651070,
            longitude=-79.347015,
        )

        # Create a far handyman (about 1000km away)
        far_user = User.objects.create_user(
            email="far_handyman@example.com", password="password"
        )
        UserRole.objects.create(user=far_user, role="handyman")
        HandymanProfile.objects.create(
            user=far_user,
            display_name="Far Handyman",
            is_active=True,
            is_available=True,
            is_approved=True,
            latitude=53.0,  # Very far north
            longitude=-79.0,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.url}?latitude=43.65&longitude=-79.34")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Both handymen should be returned regardless of distance
        self.assertEqual(len(response.data["data"]), 2)

    def test_list_handymen_without_coords_appear_last(self):
        """Test handymen without coordinates appear at end of list."""
        # Create handyman with coordinates and high rating
        with_coords_user = User.objects.create_user(
            email="with_coords@example.com", password="password"
        )
        UserRole.objects.create(user=with_coords_user, role="handyman")
        HandymanProfile.objects.create(
            user=with_coords_user,
            display_name="With Coords",
            is_active=True,
            is_available=True,
            is_approved=True,
            latitude=43.651070,
            longitude=-79.347015,
            rating=3.0,
            review_count=5,
        )

        # Create handyman without coordinates but higher rating
        no_coords_user = User.objects.create_user(
            email="no_coords@example.com", password="password"
        )
        UserRole.objects.create(user=no_coords_user, role="handyman")
        HandymanProfile.objects.create(
            user=no_coords_user,
            display_name="No Coords High Rating",
            is_active=True,
            is_available=True,
            is_approved=True,
            latitude=None,
            longitude=None,
            rating=5.0,
            review_count=100,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.url}?latitude=43.65&longitude=-79.34")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)
        # Handyman with coords should be first, despite lower rating
        self.assertEqual(response.data["data"][0]["display_name"], "With Coords")
        # Handyman without coords at end
        self.assertEqual(
            response.data["data"][1]["display_name"], "No Coords High Rating"
        )

    def test_list_handymen_ordered_by_popularity(self):
        """Test handymen are ordered by popularity score."""
        # Create low popularity handyman
        low_user = User.objects.create_user(
            email="low_pop@example.com", password="password"
        )
        UserRole.objects.create(user=low_user, role="handyman")
        HandymanProfile.objects.create(
            user=low_user,
            display_name="Low Popularity",
            is_active=True,
            is_available=True,
            is_approved=True,
            latitude=43.651070,
            longitude=-79.347015,
            rating=2.0,
            review_count=1,
        )

        # Create high popularity handyman
        high_user = User.objects.create_user(
            email="high_pop@example.com", password="password"
        )
        UserRole.objects.create(user=high_user, role="handyman")
        HandymanProfile.objects.create(
            user=high_user,
            display_name="High Popularity",
            is_active=True,
            is_available=True,
            is_approved=True,
            latitude=43.651070,
            longitude=-79.347015,
            rating=5.0,
            review_count=100,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)
        # High popularity should be first
        self.assertEqual(response.data["data"][0]["display_name"], "High Popularity")
        self.assertEqual(response.data["data"][1]["display_name"], "Low Popularity")


class MobileHandymanProfileViewTests(APITestCase):
    """Test cases for mobile HandymanProfileView."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/handyman/profile"
        self.user = User.objects.create_user(
            email="handyman@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="handyman")
        self.user.email_verified_at = "2024-01-01T00:00:00Z"
        self.user.save()
        # Mock token payload for permissions
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
        }
        self.profile = HandymanProfile.objects.create(
            user=self.user,
            display_name="Test Handyman",
            phone_number="+1234567890",
            address="789 Pine Rd",
        )

    def test_get_profile_success(self):
        """Test successfully getting handyman profile."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Profile retrieved successfully")
        self.assertEqual(response.data["data"]["display_name"], "Test Handyman")
        self.assertEqual(response.data["data"]["phone_number"], "+1234567890")

    def test_get_profile_includes_rating(self):
        """Test getting profile includes rating field."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("rating", response.data["data"])

    def test_get_profile_unauthenticated(self):
        """Test getting profile without authentication fails."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile_success(self):
        """Test successfully updating handyman profile."""
        self.client.force_authenticate(user=self.user)
        data = {
            "display_name": "Updated Handyman",
            "address": "123 New St",
            "job_title": "Master Electrician",
            "date_of_birth": "1990-01-01",
        }
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Profile updated successfully")

        # Verify update in database
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, "Updated Handyman")
        self.assertEqual(self.profile.address, "123 New St")
        self.assertEqual(self.profile.job_title, "Master Electrician")
        self.assertEqual(self.profile.date_of_birth.isoformat(), "1990-01-01")
        # phone_number should be ignored/unchanged
        self.assertEqual(self.profile.phone_number, "+1234567890")

    def test_update_profile_partial(self):
        """Test partial update of handyman profile."""
        self.client.force_authenticate(user=self.user)
        data = {"display_name": "Only Name Updated"}
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify only display_name was updated
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, "Only Name Updated")
        self.assertEqual(self.profile.phone_number, "+1234567890")  # Unchanged

    def test_update_profile_unauthenticated(self):
        """Test updating profile without authentication fails."""
        data = {"display_name": "New Name"}
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile_not_found_returns_error(self):
        """Test fetching profile returns 404 when profile is missing."""
        self.profile.delete()
        user = User.objects.get(pk=self.user.pk)
        user.token_payload = self.user.token_payload
        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Profile not found")

    def test_update_profile_not_found_returns_error(self):
        """Test updating profile returns 404 when profile is missing."""
        self.profile.delete()
        user = User.objects.get(pk=self.user.pk)
        user.token_payload = self.user.token_payload
        self.client.force_authenticate(user=user)
        response = self.client.put(
            self.url,
            {"display_name": "Missing", "phone_number": "+1", "address": "Addr"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Profile not found")

    def test_update_profile_validation_error(self):
        """Test updating profile returns validation errors for invalid data."""
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            self.url,
            {"display_name": "", "phone_number": "", "address": ""},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Validation failed")
        self.assertIn("display_name", response.data["errors"])


class MobileGuestHandymanListViewTests(APITestCase):
    """Test cases for mobile GuestHandymanListView (no auth required)."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/guest/handymen/"

        # Visible handyman (approved, active, available, has coords)
        self.handyman_user_visible = User.objects.create_user(
            email="handyman_visible@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user_visible, role="handyman")
        self.handyman_visible = HandymanProfile.objects.create(
            user=self.handyman_user_visible,
            display_name="Visible Handyman",
            phone_number="+1234567890",
            address="123 Main St",
            hourly_rate="75.00",
            latitude="43.651070",
            longitude="-79.347015",
            is_active=True,
            is_available=True,
            is_approved=True,
        )

        # Visible handyman (far location)
        self.handyman_user_far = User.objects.create_user(
            email="handyman_far@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user_far, role="handyman")
        self.handyman_far = HandymanProfile.objects.create(
            user=self.handyman_user_far,
            display_name="Far Handyman",
            phone_number="+1234567891",
            address="456 Oak Ave",
            hourly_rate="80.00",
            latitude="43.800000",
            longitude="-79.400000",
            is_active=True,
            is_available=True,
            is_approved=True,
        )

        # Not visible: not approved
        self.handyman_user_not_approved = User.objects.create_user(
            email="handyman_not_approved@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user_not_approved, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman_user_not_approved,
            display_name="Not Approved Handyman",
            phone_number="+1234567892",
            address="789 Pine Rd",
            hourly_rate="70.00",
            latitude="43.651070",
            longitude="-79.347015",
            is_active=True,
            is_available=True,
            is_approved=False,
        )

        # Not visible: not active
        self.handyman_user_not_active = User.objects.create_user(
            email="handyman_not_active@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user_not_active, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman_user_not_active,
            display_name="Not Active Handyman",
            phone_number="+1234567893",
            address="321 Elm St",
            hourly_rate="65.00",
            latitude="43.651070",
            longitude="-79.347015",
            is_active=False,
            is_available=True,
            is_approved=True,
        )

        # Not visible: not available
        self.handyman_user_not_available = User.objects.create_user(
            email="handyman_not_available@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user_not_available, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman_user_not_available,
            display_name="Not Available Handyman",
            phone_number="+1234567894",
            address="654 Maple Ln",
            hourly_rate="85.00",
            latitude="43.651070",
            longitude="-79.347015",
            is_active=True,
            is_available=False,
            is_approved=True,
        )

    def test_list_handymen_no_auth_required(self):
        """Test listing handymen without authentication succeeds."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Handymen retrieved successfully")

    def test_list_handymen_returns_only_visible(self):
        """Test only approved, active, available handymen are returned."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["data"]
        self.assertEqual(len(results), 2)

        display_names = [r["display_name"] for r in results]
        self.assertIn("Visible Handyman", display_names)
        self.assertIn("Far Handyman", display_names)
        self.assertNotIn("Not Approved Handyman", display_names)
        self.assertNotIn("Not Active Handyman", display_names)
        self.assertNotIn("Not Available Handyman", display_names)

    def test_list_handymen_hides_sensitive_fields(self):
        """Test sensitive fields are not exposed in list response."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for item in response.data["data"]:
            self.assertIn("public_id", item)
            self.assertIn("display_name", item)
            self.assertIn("rating", item)
            self.assertIn("hourly_rate", item)
            self.assertNotIn("phone_number", item)
            self.assertNotIn("address", item)
            self.assertNotIn("latitude", item)
            self.assertNotIn("longitude", item)

    def test_list_handymen_with_location_includes_distance(self):
        """Test distance_km is calculated when lat/lng provided."""
        response = self.client.get(
            self.url,
            {"latitude": "43.651070", "longitude": "-79.347015"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for item in response.data["data"]:
            self.assertIn("distance_km", item)

    def test_list_handymen_without_location_no_distance(self):
        """Test distance_km is None when lat/lng not provided."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for item in response.data["data"]:
            self.assertIsNone(item.get("distance_km"))

    def test_list_handymen_shows_all_no_radius_filter(self):
        """Test all visible handymen are returned regardless of distance."""
        response = self.client.get(
            self.url,
            {"latitude": "43.651070", "longitude": "-79.347015"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["data"]
        # Both visible and far handymen should be included (no radius filter)
        self.assertEqual(len(results), 2)
        display_names = [r["display_name"] for r in results]
        self.assertIn("Visible Handyman", display_names)
        self.assertIn("Far Handyman", display_names)

    def test_list_handymen_ordered_by_popularity_then_distance(self):
        """Test handymen are ordered by popularity first, then distance."""
        # Update far handyman to have higher rating
        self.handyman_far.rating = 5.0
        self.handyman_far.review_count = 100
        self.handyman_far.save()

        # Update visible handyman to have lower rating
        self.handyman_visible.rating = 2.0
        self.handyman_visible.review_count = 1
        self.handyman_visible.save()

        response = self.client.get(
            self.url,
            {"latitude": "43.651070", "longitude": "-79.347015"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["data"]
        # Far handyman has higher popularity, so should be first despite distance
        self.assertEqual(results[0]["display_name"], "Far Handyman")
        self.assertEqual(results[1]["display_name"], "Visible Handyman")

    def test_list_handymen_includes_pagination(self):
        """Test response includes pagination metadata."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("pagination", response.data["meta"])

    def test_list_handymen_invalid_coordinates(self):
        """Test invalid coordinates are treated as no coordinates (no filtering)."""
        response = self.client.get(
            self.url,
            {"latitude": "invalid", "longitude": "-79.347015"},
        )
        # Invalid coordinates are treated as no coordinates - returns all visible handymen
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return all visible handymen since coordinates are invalid
        self.assertEqual(len(response.data["data"]), 2)

    def test_list_handymen_partial_coordinates(self):
        """Test providing only lat or lng is treated as no coordinates."""
        response = self.client.get(self.url, {"latitude": "43.651070"})
        # Partial coordinates are treated as no coordinates - returns all visible handymen
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

    def test_list_handymen_web_platform_blocked(self):
        """Test web platform cannot access mobile guest endpoint."""
        # Create a user with web platform token
        user = User.objects.create_user(
            email="webuser@example.com",
            password="testpass123",
        )
        user.token_payload = {
            "plat": "web",
            "active_role": None,
            "roles": [],
            "email_verified": False,
        }
        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_handymen_coordinate_validation_edge_cases(self):
        """Test guest list coordinate validation failure branches."""
        # Latitude out of range - treated as no coordinates (graceful fallback)
        response = self.client.get(self.url, {"latitude": "91", "longitude": "0"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["data"][0]["distance_km"])

        # Longitude out of range - treated as no coordinates (graceful fallback)
        response = self.client.get(self.url, {"latitude": "0", "longitude": "181"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["data"][0]["distance_km"])

    def test_list_handymen_without_coords_appear_last(self):
        """Test handymen without coordinates appear at end of list when coords provided."""
        # Create handyman without coordinates
        no_coords_user = User.objects.create_user(
            email="no_coords@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=no_coords_user, role="handyman")
        HandymanProfile.objects.create(
            user=no_coords_user,
            display_name="No Coords Handyman",
            phone_number="+1234567899",
            address="999 No Coords St",
            hourly_rate="100.00",
            latitude=None,
            longitude=None,
            is_active=True,
            is_available=True,
            is_approved=True,
            rating=5.0,  # High rating
            review_count=100,
        )

        response = self.client.get(
            self.url,
            {"latitude": "43.651070", "longitude": "-79.347015"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["data"]
        # Handymen with coordinates first, then without coordinates at end
        self.assertEqual(len(results), 3)
        # Last one should be the handyman without coordinates
        self.assertEqual(results[-1]["display_name"], "No Coords Handyman")
        self.assertIsNone(results[-1]["distance_km"])

    def test_list_handymen_ordered_by_popularity_without_coords(self):
        """Test handymen ordered by popularity when no coordinates provided."""
        # Set different ratings
        self.handyman_visible.rating = 5.0
        self.handyman_visible.review_count = 100
        self.handyman_visible.save()

        self.handyman_far.rating = 2.0
        self.handyman_far.review_count = 1
        self.handyman_far.save()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["data"]
        # Higher popularity first
        self.assertEqual(results[0]["display_name"], "Visible Handyman")
        self.assertEqual(results[1]["display_name"], "Far Handyman")


class MobileGuestHandymanDetailViewTests(APITestCase):
    """Test cases for mobile GuestHandymanDetailView (no auth required)."""

    def setUp(self):
        """Set up test data."""
        # Visible handyman
        self.handyman_user = User.objects.create_user(
            email="handyman_detail@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user, role="handyman")
        self.handyman = HandymanProfile.objects.create(
            user=self.handyman_user,
            display_name="Detail Handyman",
            phone_number="+1234567890",
            address="123 Main St",
            hourly_rate="75.00",
            latitude="43.651070",
            longitude="-79.347015",
            is_active=True,
            is_available=True,
            is_approved=True,
        )
        self.url = f"/api/v1/mobile/guest/handymen/{self.handyman.user.public_id}/"

        # Not approved handyman
        self.handyman_user_not_approved = User.objects.create_user(
            email="handyman_not_approved_detail@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user_not_approved, role="handyman")
        self.handyman_not_approved = HandymanProfile.objects.create(
            user=self.handyman_user_not_approved,
            display_name="Not Approved Detail",
            phone_number="+1234567891",
            address="456 Oak Ave",
            hourly_rate="80.00",
            is_active=True,
            is_available=True,
            is_approved=False,
        )

    def test_get_handyman_no_auth_required(self):
        """Test getting handyman detail without authentication succeeds."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Handyman retrieved successfully")

    def test_get_handyman_returns_correct_data(self):
        """Test handyman detail returns expected fields."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["data"]
        self.assertEqual(data["display_name"], "Detail Handyman")
        self.assertEqual(str(data["hourly_rate"]), "75.00")
        self.assertIn("rating", data)
        self.assertIn("avatar_url", data)

    def test_get_handyman_hides_sensitive_fields(self):
        """Test sensitive fields are not exposed in detail response."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["data"]
        self.assertNotIn("phone_number", data)
        self.assertNotIn("address", data)
        self.assertNotIn("latitude", data)
        self.assertNotIn("longitude", data)

    def test_get_handyman_not_found(self):
        """Test getting non-existent handyman returns 404."""
        response = self.client.get(
            "/api/v1/mobile/guest/handymen/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Handyman not found")

    def test_get_handyman_not_approved_returns_404(self):
        """Test getting not approved handyman returns 404."""
        url = f"/api/v1/mobile/guest/handymen/{self.handyman_not_approved.user.public_id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Handyman not found")

    def test_get_handyman_not_active_returns_404(self):
        """Test getting not active handyman returns 404."""
        self.handyman.is_active = False
        self.handyman.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_handyman_not_available_returns_404(self):
        """Test getting not available handyman returns 404."""
        self.handyman.is_available = False
        self.handyman.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_handyman_web_platform_blocked(self):
        """Test web platform cannot access mobile guest endpoint."""
        user = User.objects.create_user(
            email="webuser_detail@example.com",
            password="testpass123",
        )
        user.token_payload = {
            "plat": "web",
            "active_role": None,
            "roles": [],
            "email_verified": False,
        }
        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
