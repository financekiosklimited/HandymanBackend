"""Tests for mobile profile views."""

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.profiles.models import HandymanProfile, HomeownerProfile


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
            "phone_number": "+9876543210",
            "address": "456 Oak Ave",
        }
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Profile updated successfully")

        # Verify update in database
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, "Updated Name")
        self.assertEqual(self.profile.phone_number, "+9876543210")
        self.assertEqual(self.profile.address, "456 Oak Ave")

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

    def test_list_nearby_handymen_validation(self):
        """Test coordinate validation for nearby handymen."""
        self.client.force_authenticate(user=self.user)

        # Missing coordinates
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid numbers
        response = self.client.get(f"{self.url}?latitude=abc&longitude=123")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Out of range
        response = self.client.get(f"{self.url}?latitude=100&longitude=45")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.get(f"{self.url}?latitude=45&longitude=200")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid radius
        response = self.client.get(f"{self.url}?latitude=45&longitude=45&radius_km=-1")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_nearby_handymen_success(self):
        """Test successfully listing nearby handymen."""
        # Create a handyman
        handyman_user = User.objects.create_user(
            email="handyman@example.com", password="password"
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
            "phone_number": "+9876543210",
            "address": "123 New St",
        }
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Profile updated successfully")

        # Verify update in database
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, "Updated Handyman")
        self.assertEqual(self.profile.phone_number, "+9876543210")
        self.assertEqual(self.profile.address, "123 New St")

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

    def test_list_handymen_filter_by_radius(self):
        """Test filtering by radius excludes far handymen."""
        response = self.client.get(
            self.url,
            {"latitude": "43.651070", "longitude": "-79.347015", "radius_km": "1"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["data"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["display_name"], "Visible Handyman")

    def test_list_handymen_orders_by_distance_when_location_provided(self):
        """Test handymen are ordered by distance when location provided."""
        response = self.client.get(
            self.url,
            {"latitude": "43.651070", "longitude": "-79.347015"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["data"]
        self.assertEqual(results[0]["display_name"], "Visible Handyman")
        self.assertEqual(results[1]["display_name"], "Far Handyman")

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
        self.url = f"/api/v1/mobile/guest/handymen/{self.handyman.public_id}/"

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
        url = f"/api/v1/mobile/guest/handymen/{self.handyman_not_approved.public_id}/"
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
