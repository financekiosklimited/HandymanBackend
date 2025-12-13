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
        self.assertEqual(
            response.data["errors"],
            {"detail": "The requested resource was not found"},
        )

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


class MobileHomeownerHandymenBrowseTests(APITestCase):
    """Test cases for mobile homeowner handymen list/detail views."""

    def setUp(self):
        self.nearby_url = "/api/v1/mobile/homeowner/handymen/nearby/"

        self.homeowner = User.objects.create_user(
            email="homeowner_browse@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        self.homeowner.email_verified_at = "2024-01-01T00:00:00Z"
        self.homeowner.save()
        self.homeowner.token_payload = {
            "plat": "mobile",
            "active_role": "homeowner",
            "roles": ["homeowner"],
            "email_verified": True,
        }

        # Visible handyman (near)
        self.handyman_user_near = User.objects.create_user(
            email="handyman_near@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user_near, role="handyman")
        self.handyman_near = HandymanProfile.objects.create(
            user=self.handyman_user_near,
            display_name="Near Handyman",
            phone_number="+1234567890",
            address="Somewhere",
            hourly_rate="75.00",
            latitude="43.651070",
            longitude="-79.347015",
            is_active=True,
            is_available=True,
            is_approved=True,
        )

        # Visible handyman (far)
        self.handyman_user_far = User.objects.create_user(
            email="handyman_far@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user_far, role="handyman")
        self.handyman_far = HandymanProfile.objects.create(
            user=self.handyman_user_far,
            display_name="Far Handyman",
            phone_number="+1234567890",
            address="Somewhere",
            hourly_rate="80.00",
            latitude="43.800000",
            longitude="-79.400000",
            is_active=True,
            is_available=True,
            is_approved=True,
        )

        # Not visible: missing coordinates
        self.handyman_user_no_coords = User.objects.create_user(
            email="handyman_nocoords@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user_no_coords, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman_user_no_coords,
            display_name="No Coords Handyman",
            phone_number="+1234567890",
            address="Somewhere",
            hourly_rate="70.00",
            latitude=None,
            longitude=None,
            is_active=True,
            is_available=True,
            is_approved=True,
        )

        # Not visible: not approved
        self.handyman_user_not_approved = User.objects.create_user(
            email="handyman_notapproved@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.handyman_user_not_approved, role="handyman")
        HandymanProfile.objects.create(
            user=self.handyman_user_not_approved,
            display_name="Not Approved Handyman",
            phone_number="+1234567890",
            address="Somewhere",
            hourly_rate="70.00",
            latitude="43.651070",
            longitude="-79.347015",
            is_active=True,
            is_available=True,
            is_approved=False,
        )

    def test_nearby_list_requires_lat_lng(self):
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(self.nearby_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Validation failed")
        self.assertIn("coordinates", response.data["errors"])

    def test_nearby_list_success_hides_sensitive_fields(self):
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(
            self.nearby_url,
            {"latitude": "43.651070", "longitude": "-79.347015", "radius_km": "50"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Handymen retrieved successfully")

        results = response.data["data"]
        self.assertEqual(len(results), 2)

        for item in results:
            self.assertIn("public_id", item)
            self.assertIn("display_name", item)
            self.assertIn("rating", item)
            self.assertIn("hourly_rate", item)
            self.assertIn("distance_km", item)
            self.assertNotIn("phone_number", item)
            self.assertNotIn("address", item)
            self.assertNotIn("latitude", item)
            self.assertNotIn("longitude", item)

        self.assertIn("pagination", response.data["meta"])

        near = next(r for r in results if r["display_name"] == "Near Handyman")
        self.assertIsNotNone(near["distance_km"])

    def test_nearby_list_orders_by_distance(self):
        """Near handyman should be listed before far handyman."""
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(
            self.nearby_url,
            {"latitude": "43.651070", "longitude": "-79.347015", "radius_km": "50"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["data"]
        self.assertEqual(results[0]["display_name"], "Near Handyman")
        self.assertEqual(results[1]["display_name"], "Far Handyman")

    def test_nearby_list_filters_by_radius(self):
        """Small radius excludes far handyman."""
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(
            self.nearby_url,
            {"latitude": "43.651070", "longitude": "-79.347015", "radius_km": "1"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["data"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["display_name"], "Near Handyman")

    def test_detail_success(self):
        self.client.force_authenticate(user=self.homeowner)
        detail_url = (
            f"/api/v1/mobile/homeowner/handymen/{self.handyman_near.public_id}/"
        )
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Handyman retrieved successfully")

        data = response.data["data"]
        self.assertEqual(data["display_name"], "Near Handyman")
        self.assertIn("hourly_rate", data)
        self.assertNotIn("phone_number", data)
        self.assertNotIn("address", data)
        self.assertNotIn("latitude", data)
        self.assertNotIn("longitude", data)

    def test_detail_not_found(self):
        self.client.force_authenticate(user=self.homeowner)
        response = self.client.get(
            "/api/v1/mobile/homeowner/handymen/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Handyman not found")

    def test_role_guard_blocks_non_homeowner(self):
        """Handyman role cannot access homeowner endpoints."""
        handyman_user = User.objects.create_user(
            email="handyman_actor@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=handyman_user, role="handyman")
        handyman_user.email_verified_at = "2024-01-01T00:00:00Z"
        handyman_user.save()
        handyman_user.token_payload = {
            "plat": "mobile",
            "active_role": "handyman",
            "roles": ["handyman"],
            "email_verified": True,
        }

        self.client.force_authenticate(user=handyman_user)
        response = self.client.get(
            self.nearby_url,
            {"latitude": "43.651070", "longitude": "-79.347015", "radius_km": "50"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Role mismatch")


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
