"""Tests for mobile profile views."""

from decimal import Decimal

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

    def test_list_handymen_search_by_display_name_success(self):
        """Test searching handymen by display name returns matching results."""
        # Create handymen with different names
        user1 = User.objects.create_user(
            email="john_doe@example.com", password="password"
        )
        UserRole.objects.create(user=user1, role="handyman")
        HandymanProfile.objects.create(
            user=user1,
            display_name="John Doe",
            is_active=True,
            is_available=True,
            is_approved=True,
        )

        user2 = User.objects.create_user(
            email="jane_smith@example.com", password="password"
        )
        UserRole.objects.create(user=user2, role="handyman")
        HandymanProfile.objects.create(
            user=user2,
            display_name="Jane Smith",
            is_active=True,
            is_available=True,
            is_approved=True,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.url}?search=John")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["display_name"], "John Doe")

    def test_list_handymen_search_case_insensitive(self):
        """Test search is case-insensitive."""
        user = User.objects.create_user(
            email="mike_handyman@example.com", password="password"
        )
        UserRole.objects.create(user=user, role="handyman")
        HandymanProfile.objects.create(
            user=user,
            display_name="Mike Johnson",
            is_active=True,
            is_available=True,
            is_approved=True,
        )

        self.client.force_authenticate(user=self.user)

        # Search with lowercase
        response = self.client.get(f"{self.url}?search=mike")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["display_name"], "Mike Johnson")

        # Search with uppercase
        response = self.client.get(f"{self.url}?search=MIKE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

    def test_list_handymen_search_partial_match(self):
        """Test search returns partial matches."""
        user = User.objects.create_user(
            email="alexander@example.com", password="password"
        )
        UserRole.objects.create(user=user, role="handyman")
        HandymanProfile.objects.create(
            user=user,
            display_name="Alexander Hamilton",
            is_active=True,
            is_available=True,
            is_approved=True,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.url}?search=Alex")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["display_name"], "Alexander Hamilton")

    def test_list_handymen_search_no_results(self):
        """Test search with no matches returns empty list."""
        user = User.objects.create_user(
            email="bob_builder@example.com", password="password"
        )
        UserRole.objects.create(user=user, role="handyman")
        HandymanProfile.objects.create(
            user=user,
            display_name="Bob Builder",
            is_active=True,
            is_available=True,
            is_approved=True,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.url}?search=NonExistentName")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 0)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 0)

    def test_list_handymen_search_with_coordinates(self):
        """Test search works together with coordinate filtering."""
        user1 = User.objects.create_user(
            email="nearby_john@example.com", password="password"
        )
        UserRole.objects.create(user=user1, role="handyman")
        HandymanProfile.objects.create(
            user=user1,
            display_name="John Nearby",
            is_active=True,
            is_available=True,
            is_approved=True,
            latitude=43.651070,
            longitude=-79.347015,
        )

        user2 = User.objects.create_user(
            email="far_john@example.com", password="password"
        )
        UserRole.objects.create(user=user2, role="handyman")
        HandymanProfile.objects.create(
            user=user2,
            display_name="John Far",
            is_active=True,
            is_available=True,
            is_approved=True,
            latitude=53.0,
            longitude=-79.0,
        )

        user3 = User.objects.create_user(
            email="jane_nearby@example.com", password="password"
        )
        UserRole.objects.create(user=user3, role="handyman")
        HandymanProfile.objects.create(
            user=user3,
            display_name="Jane Nearby",
            is_active=True,
            is_available=True,
            is_approved=True,
            latitude=43.651070,
            longitude=-79.347015,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            f"{self.url}?search=John&latitude=43.65&longitude=-79.34"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return only the 2 Johns, not Jane
        self.assertEqual(len(response.data["data"]), 2)
        names = [h["display_name"] for h in response.data["data"]]
        self.assertIn("John Nearby", names)
        self.assertIn("John Far", names)
        self.assertNotIn("Jane Nearby", names)
        # Distance should be calculated
        self.assertIsNotNone(response.data["data"][0]["distance_km"])


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

    def test_list_handymen_search_by_display_name_success(self):
        """Test searching handymen by display name returns matching results."""
        response = self.client.get(f"{self.url}?search=Visible")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["display_name"], "Visible Handyman")

    def test_list_handymen_search_case_insensitive(self):
        """Test search is case-insensitive."""
        # Search with lowercase
        response = self.client.get(f"{self.url}?search=visible")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["display_name"], "Visible Handyman")

        # Search with uppercase
        response = self.client.get(f"{self.url}?search=VISIBLE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

    def test_list_handymen_search_no_results(self):
        """Test search with no matches returns empty list."""
        response = self.client.get(f"{self.url}?search=NonExistentName")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 0)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 0)

    def test_list_handymen_search_with_coordinates(self):
        """Test search works together with coordinate filtering."""
        response = self.client.get(
            f"{self.url}?search=Handyman&latitude=43.651070&longitude=-79.347015"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return both visible and far handymen (both have "Handyman" in name)
        self.assertEqual(len(response.data["data"]), 2)
        # Distance should be calculated
        self.assertIsNotNone(response.data["data"][0]["distance_km"])


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


class MobileHandymanListReviewCountTests(APITestCase):
    """Test cases for review_count field in handyman list/detail APIs."""

    def setUp(self):
        """Set up test data."""
        # Homeowner user
        self.homeowner_user = User.objects.create_user(
            email="homeowner_rc@example.com",
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
        HomeownerProfile.objects.create(
            user=self.homeowner_user,
            display_name="Test Homeowner",
        )

        # Handyman user
        self.handyman_user = User.objects.create_user(
            email="handyman_rc@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user, role="handyman")
        self.handyman = HandymanProfile.objects.create(
            user=self.handyman_user,
            display_name="Review Count Handyman",
            hourly_rate="75.00",
            latitude="43.651070",
            longitude="-79.347015",
            is_active=True,
            is_available=True,
            is_approved=True,
            rating=4.5,
            review_count=25,
        )

    def test_homeowner_list_handymen_includes_review_count(self):
        """Test homeowner list handymen includes review_count field."""
        self.client.force_authenticate(user=self.homeowner_user)
        response = self.client.get("/api/v1/mobile/homeowner/handymen/nearby/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertIn("review_count", response.data["data"][0])
        self.assertEqual(response.data["data"][0]["review_count"], 25)

    def test_homeowner_detail_handymen_includes_review_count(self):
        """Test homeowner handyman detail includes review_count field."""
        self.client.force_authenticate(user=self.homeowner_user)
        url = f"/api/v1/mobile/homeowner/handymen/{self.handyman.user.public_id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("review_count", response.data["data"])
        self.assertEqual(response.data["data"]["review_count"], 25)

    def test_guest_list_handymen_includes_review_count(self):
        """Test guest list handymen includes review_count field."""
        response = self.client.get("/api/v1/mobile/guest/handymen/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertIn("review_count", response.data["data"][0])
        self.assertEqual(response.data["data"][0]["review_count"], 25)

    def test_guest_detail_handymen_includes_review_count(self):
        """Test guest handyman detail includes review_count field."""
        url = f"/api/v1/mobile/guest/handymen/{self.handyman.user.public_id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("review_count", response.data["data"])
        self.assertEqual(response.data["data"]["review_count"], 25)


class MobileHomeownerHandymanReviewListViewTests(APITestCase):
    """Test cases for mobile HomeownerHandymanReviewListView."""

    def setUp(self):
        """Set up test data."""
        from apps.jobs.models import City, Job, JobCategory, Review

        # Homeowner user (viewer)
        self.viewer_user = User.objects.create_user(
            email="viewer@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.viewer_user, role="homeowner")
        self.viewer_user.email_verified_at = "2024-01-01T00:00:00Z"
        self.viewer_user.save()
        self.viewer_user.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
        }
        HomeownerProfile.objects.create(
            user=self.viewer_user,
            display_name="Viewer Homeowner",
        )

        # Handyman user (being reviewed)
        self.handyman_user = User.objects.create_user(
            email="handyman_reviewed@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user, role="handyman")
        self.handyman = HandymanProfile.objects.create(
            user=self.handyman_user,
            display_name="Reviewed Handyman",
            hourly_rate="75.00",
            latitude="43.651070",
            longitude="-79.347015",
            is_active=True,
            is_available=True,
            is_approved=True,
        )

        # Reviewer homeowners
        self.reviewer1 = User.objects.create_user(
            email="reviewer1@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.reviewer1, role="homeowner")
        self.reviewer1_profile = HomeownerProfile.objects.create(
            user=self.reviewer1,
            display_name="John Doe",
        )

        self.reviewer2 = User.objects.create_user(
            email="reviewer2@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.reviewer2, role="homeowner")
        self.reviewer2_profile = HomeownerProfile.objects.create(
            user=self.reviewer2,
            display_name="Mary Smith",
        )

        self.reviewer3 = User.objects.create_user(
            email="reviewer3@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.reviewer3, role="homeowner")
        self.reviewer3_profile = HomeownerProfile.objects.create(
            user=self.reviewer3,
            display_name="A",  # Single character name
        )

        # Job category and city
        self.category = JobCategory.objects.create(
            name="Test Category",
            slug="test-category",
        )
        self.city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            is_active=True,
        )

        # Create jobs and reviews
        self.job1 = Job.objects.create(
            homeowner=self.reviewer1,
            assigned_handyman=self.handyman_user,
            title="Job 1",
            description="Test job 1 description",
            estimated_budget=Decimal("100.00"),
            address="123 Main St",
            category=self.category,
            city=self.city,
            status="completed",
        )
        self.review1 = Review.objects.create(
            job=self.job1,
            reviewer=self.reviewer1,
            reviewee=self.handyman_user,
            reviewer_type="homeowner",
            rating=5,
            comment="Excellent work!",
        )

        self.job2 = Job.objects.create(
            homeowner=self.reviewer2,
            assigned_handyman=self.handyman_user,
            title="Job 2",
            description="Test job 2 description",
            estimated_budget=Decimal("150.00"),
            address="456 Oak Ave",
            category=self.category,
            city=self.city,
            status="completed",
        )
        self.review2 = Review.objects.create(
            job=self.job2,
            reviewer=self.reviewer2,
            reviewee=self.handyman_user,
            reviewer_type="homeowner",
            rating=4,
            comment="",  # Empty comment
        )

        self.job3 = Job.objects.create(
            homeowner=self.reviewer3,
            assigned_handyman=self.handyman_user,
            title="Job 3",
            description="Test job 3 description",
            estimated_budget=Decimal("200.00"),
            address="789 Pine Rd",
            category=self.category,
            city=self.city,
            status="completed",
        )
        self.review3 = Review.objects.create(
            job=self.job3,
            reviewer=self.reviewer3,
            reviewee=self.handyman_user,
            reviewer_type="homeowner",
            rating=3,
            comment="Good job",
        )

        self.url = (
            f"/api/v1/mobile/homeowner/handymen/{self.handyman.user.public_id}/reviews/"
        )

    def test_list_reviews_success(self):
        """Test successfully listing handyman reviews."""
        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Reviews retrieved successfully")
        self.assertEqual(len(response.data["data"]), 3)

    def test_list_reviews_ordered_by_created_at_desc(self):
        """Test reviews are ordered by created_at descending (newest first)."""
        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["data"]
        # Reviews should be ordered from newest to oldest
        created_dates = [r["created_at"] for r in results]
        self.assertEqual(created_dates, sorted(created_dates, reverse=True))

    def test_list_reviews_censored_name(self):
        """Test reviewer names are censored correctly."""
        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["data"]
        display_names = [r["reviewer_display_name"] for r in results]

        # "John Doe" -> "J*** D**"
        self.assertIn("J*** D**", display_names)
        # "Mary Smith" -> "M*** S****"
        self.assertIn("M*** S****", display_names)
        # "A" -> "A" (single char stays same)
        self.assertIn("A", display_names)

    def test_list_reviews_empty_comment_returns_null(self):
        """Test empty comment returns null."""
        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Find review2 which has empty comment
        for review in response.data["data"]:
            if review["rating"] == 4:  # review2 has rating 4
                self.assertIsNone(review["comment"])
                break

    def test_list_reviews_non_empty_comment_returned(self):
        """Test non-empty comment is returned correctly."""
        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Find review1 which has comment "Excellent work!"
        for review in response.data["data"]:
            if review["rating"] == 5:  # review1 has rating 5
                self.assertEqual(review["comment"], "Excellent work!")
                break

    def test_list_reviews_includes_expected_fields(self):
        """Test response includes all expected fields."""
        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for review in response.data["data"]:
            self.assertIn("public_id", review)
            self.assertIn("reviewer_avatar_url", review)
            self.assertIn("reviewer_display_name", review)
            self.assertIn("rating", review)
            self.assertIn("comment", review)
            self.assertIn("created_at", review)

    def test_list_reviews_pagination(self):
        """Test pagination works correctly."""
        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get(f"{self.url}?page=1&page_size=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 3)
        self.assertEqual(response.data["meta"]["pagination"]["total_pages"], 2)
        self.assertTrue(response.data["meta"]["pagination"]["has_next"])
        self.assertFalse(response.data["meta"]["pagination"]["has_previous"])

        # Get second page
        response = self.client.get(f"{self.url}?page=2&page_size=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertFalse(response.data["meta"]["pagination"]["has_next"])
        self.assertTrue(response.data["meta"]["pagination"]["has_previous"])

    def test_list_reviews_rating_stats(self):
        """Test rating_stats is included in meta."""
        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify rating_stats structure
        self.assertIn("rating_stats", response.data["meta"])
        rating_stats = response.data["meta"]["rating_stats"]

        self.assertIn("average", rating_stats)
        self.assertIn("total_count", rating_stats)
        self.assertIn("distribution", rating_stats)

        # Verify distribution structure
        distribution = rating_stats["distribution"]
        self.assertIn("5", distribution)
        self.assertIn("4", distribution)
        self.assertIn("3", distribution)
        self.assertIn("2", distribution)
        self.assertIn("1", distribution)

        # Verify values based on setUp data (ratings: 5, 4, 3)
        self.assertEqual(rating_stats["total_count"], 3)
        self.assertEqual(distribution["5"], 1)
        self.assertEqual(distribution["4"], 1)
        self.assertEqual(distribution["3"], 1)
        self.assertEqual(distribution["2"], 0)
        self.assertEqual(distribution["1"], 0)

        # Verify average calculation: (5 + 4 + 3) / 3 = 4.0
        self.assertEqual(rating_stats["average"], 4.0)

    def test_list_reviews_rating_stats_empty(self):
        """Test rating_stats with no reviews."""
        from apps.jobs.models import Review

        Review.objects.all().delete()

        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        rating_stats = response.data["meta"]["rating_stats"]
        self.assertEqual(rating_stats["average"], 0.0)
        self.assertEqual(rating_stats["total_count"], 0)
        self.assertEqual(rating_stats["distribution"]["5"], 0)
        self.assertEqual(rating_stats["distribution"]["4"], 0)
        self.assertEqual(rating_stats["distribution"]["3"], 0)
        self.assertEqual(rating_stats["distribution"]["2"], 0)
        self.assertEqual(rating_stats["distribution"]["1"], 0)

    def test_list_reviews_handyman_not_found(self):
        """Test returns 404 when handyman not found."""
        self.client.force_authenticate(user=self.viewer_user)
        url = "/api/v1/mobile/homeowner/handymen/00000000-0000-0000-0000-000000000000/reviews/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Handyman not found")

    def test_list_reviews_handyman_not_visible(self):
        """Test returns 404 when handyman is not visible."""
        self.client.force_authenticate(user=self.viewer_user)

        # Not approved
        self.handyman.is_approved = False
        self.handyman.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Not active
        self.handyman.is_approved = True
        self.handyman.is_active = False
        self.handyman.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Not available
        self.handyman.is_active = True
        self.handyman.is_available = False
        self.handyman.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_reviews_unauthenticated(self):
        """Test unauthenticated request returns 401."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_reviews_empty_list(self):
        """Test returns empty list when no reviews exist."""
        from apps.jobs.models import Review

        # Delete all reviews
        Review.objects.all().delete()

        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 0)
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 0)

    def test_list_reviews_only_homeowner_reviews(self):
        """Test only reviews from homeowners are returned."""
        from apps.jobs.models import Job, Review

        # Create a review from handyman (should not be included)
        another_homeowner = User.objects.create_user(
            email="another_homeowner@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=another_homeowner, role="homeowner")
        HomeownerProfile.objects.create(
            user=another_homeowner,
            display_name="Another Homeowner",
        )

        job = Job.objects.create(
            homeowner=another_homeowner,
            assigned_handyman=self.handyman_user,
            title="Job for handyman review",
            description="Test job for handyman review",
            estimated_budget=Decimal("100.00"),
            address="123 Test St",
            category=self.category,
            city=self.city,
            status="completed",
        )

        # Handyman reviews homeowner (should not appear in handyman's reviews)
        Review.objects.create(
            job=job,
            reviewer=self.handyman_user,
            reviewee=another_homeowner,
            reviewer_type="handyman",
            rating=5,
            comment="Great homeowner!",
        )

        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should still only have 3 reviews (from homeowners)
        self.assertEqual(len(response.data["data"]), 3)

    def test_list_reviews_reviewer_without_homeowner_profile(self):
        """Test reviewer without homeowner_profile returns None for avatar and name."""
        from apps.jobs.models import Job, Review

        # Create reviewer without homeowner profile
        reviewer_no_profile = User.objects.create_user(
            email="no_profile_reviewer@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=reviewer_no_profile, role="homeowner")
        # Note: NOT creating HomeownerProfile for this user

        job = Job.objects.create(
            homeowner=reviewer_no_profile,
            assigned_handyman=self.handyman_user,
            title="Job without profile",
            description="Test job without profile",
            estimated_budget=Decimal("100.00"),
            address="123 No Profile St",
            category=self.category,
            city=self.city,
            status="completed",
        )
        Review.objects.create(
            job=job,
            reviewer=reviewer_no_profile,
            reviewee=self.handyman_user,
            reviewer_type="homeowner",
            rating=2,
            comment="Review from user without profile",
        )

        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Find the review with rating 2 (from reviewer without profile)
        for review in response.data["data"]:
            if review["rating"] == 2:
                self.assertIsNone(review["reviewer_avatar_url"])
                self.assertIsNone(review["reviewer_display_name"])
                break

    def test_list_reviews_reviewer_with_empty_display_name(self):
        """Test reviewer with empty display_name returns None."""
        from apps.jobs.models import Job, Review

        # Create reviewer with empty display_name
        reviewer_empty_name = User.objects.create_user(
            email="empty_name_reviewer@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=reviewer_empty_name, role="homeowner")
        HomeownerProfile.objects.create(
            user=reviewer_empty_name,
            display_name="",  # Empty display name
        )

        job = Job.objects.create(
            homeowner=reviewer_empty_name,
            assigned_handyman=self.handyman_user,
            title="Job with empty name",
            description="Test job with empty name",
            estimated_budget=Decimal("100.00"),
            address="456 Empty Name Ave",
            category=self.category,
            city=self.city,
            status="completed",
        )
        Review.objects.create(
            job=job,
            reviewer=reviewer_empty_name,
            reviewee=self.handyman_user,
            reviewer_type="homeowner",
            rating=1,
            comment="Review from user with empty name",
        )

        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Find the review with rating 1 (from reviewer with empty name)
        for review in response.data["data"]:
            if review["rating"] == 1:
                self.assertIsNone(review["reviewer_display_name"])
                break


class MobileGuestHandymanReviewListViewTests(APITestCase):
    """Test cases for mobile GuestHandymanReviewListView (no auth required)."""

    def setUp(self):
        """Set up test data."""
        from apps.jobs.models import City, Job, JobCategory, Review

        # Handyman user (being reviewed)
        self.handyman_user = User.objects.create_user(
            email="handyman_guest_review@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user, role="handyman")
        self.handyman = HandymanProfile.objects.create(
            user=self.handyman_user,
            display_name="Guest Reviewed Handyman",
            hourly_rate="75.00",
            latitude="43.651070",
            longitude="-79.347015",
            is_active=True,
            is_available=True,
            is_approved=True,
        )

        # Reviewer homeowner
        self.reviewer = User.objects.create_user(
            email="guest_reviewer@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.reviewer, role="homeowner")
        self.reviewer_profile = HomeownerProfile.objects.create(
            user=self.reviewer,
            display_name="Jane Wilson",
        )

        # Job category and city
        self.category = JobCategory.objects.create(
            name="Guest Test Category",
            slug="guest-test-category",
        )
        self.city = City.objects.create(
            name="Vancouver",
            province="British Columbia",
            province_code="BC",
            slug="vancouver-bc",
            is_active=True,
        )

        # Create job and review
        self.job = Job.objects.create(
            homeowner=self.reviewer,
            assigned_handyman=self.handyman_user,
            title="Guest Review Job",
            description="Test guest review job",
            estimated_budget=Decimal("75.00"),
            address="456 Guest Ave",
            category=self.category,
            city=self.city,
            status="completed",
        )
        self.review = Review.objects.create(
            job=self.job,
            reviewer=self.reviewer,
            reviewee=self.handyman_user,
            reviewer_type="homeowner",
            rating=5,
            comment="Amazing service!",
        )

        self.url = (
            f"/api/v1/mobile/guest/handymen/{self.handyman.user.public_id}/reviews/"
        )

    def test_list_reviews_no_auth_required(self):
        """Test listing reviews without authentication succeeds."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Reviews retrieved successfully")

    def test_list_reviews_returns_correct_data(self):
        """Test reviews return expected fields."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)

        review = response.data["data"][0]
        self.assertEqual(review["rating"], 5)
        self.assertEqual(review["comment"], "Amazing service!")
        # "Jane Wilson" -> "J*** W*****"
        self.assertEqual(review["reviewer_display_name"], "J*** W*****")

    def test_list_reviews_pagination(self):
        """Test pagination metadata is included."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("pagination", response.data["meta"])
        self.assertEqual(response.data["meta"]["pagination"]["total_count"], 1)

    def test_list_reviews_rating_stats(self):
        """Test rating_stats is included in meta for guest endpoint."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify rating_stats structure
        self.assertIn("rating_stats", response.data["meta"])
        rating_stats = response.data["meta"]["rating_stats"]

        self.assertIn("average", rating_stats)
        self.assertIn("total_count", rating_stats)
        self.assertIn("distribution", rating_stats)

        # Verify distribution structure
        distribution = rating_stats["distribution"]
        self.assertIn("5", distribution)
        self.assertIn("4", distribution)
        self.assertIn("3", distribution)
        self.assertIn("2", distribution)
        self.assertIn("1", distribution)

        # Verify values based on setUp data (1 review with rating 5)
        self.assertEqual(rating_stats["total_count"], 1)
        self.assertEqual(distribution["5"], 1)
        self.assertEqual(distribution["4"], 0)
        self.assertEqual(distribution["3"], 0)
        self.assertEqual(distribution["2"], 0)
        self.assertEqual(distribution["1"], 0)
        self.assertEqual(rating_stats["average"], 5.0)

    def test_list_reviews_rating_stats_empty(self):
        """Test rating_stats with no reviews for guest endpoint."""
        from apps.jobs.models import Review

        Review.objects.all().delete()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        rating_stats = response.data["meta"]["rating_stats"]
        self.assertEqual(rating_stats["average"], 0.0)
        self.assertEqual(rating_stats["total_count"], 0)
        self.assertEqual(rating_stats["distribution"]["5"], 0)
        self.assertEqual(rating_stats["distribution"]["4"], 0)
        self.assertEqual(rating_stats["distribution"]["3"], 0)
        self.assertEqual(rating_stats["distribution"]["2"], 0)
        self.assertEqual(rating_stats["distribution"]["1"], 0)

    def test_list_reviews_handyman_not_found(self):
        """Test returns 404 when handyman not found."""
        url = "/api/v1/mobile/guest/handymen/00000000-0000-0000-0000-000000000000/reviews/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Handyman not found")

    def test_list_reviews_handyman_not_visible(self):
        """Test returns 404 when handyman is not visible."""
        self.handyman.is_approved = False
        self.handyman.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_reviews_web_platform_blocked(self):
        """Test web platform cannot access mobile guest endpoint."""
        user = User.objects.create_user(
            email="webuser_review@example.com",
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
