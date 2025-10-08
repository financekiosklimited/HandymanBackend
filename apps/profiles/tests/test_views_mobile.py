"""Tests for mobile profile views."""

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.profiles.models import CustomerProfile, HandymanProfile


class MobileCustomerProfileViewTests(APITestCase):
    """Test cases for mobile CustomerProfileView."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/mobile/customer/profile"
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="customer")
        self.user.email_verified_at = "2024-01-01T00:00:00Z"
        self.user.save()
        # Mock token payload for permissions
        self.user.token_payload = {
            "plat": "mobile",
            "active_role": "customer",
            "roles": ["customer"],
            "email_verified": True,
        }
        self.profile = CustomerProfile.objects.create(
            user=self.user,
            display_name="Test Customer",
            phone_number="+1234567890",
            address="123 Main St",
        )

    def test_get_profile_success(self):
        """Test successfully getting customer profile."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Profile retrieved successfully")
        self.assertEqual(response.data["data"]["display_name"], "Test Customer")
        self.assertEqual(response.data["data"]["phone_number"], "+1234567890")

    def test_get_profile_unauthenticated(self):
        """Test getting profile without authentication fails."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile_success(self):
        """Test successfully updating customer profile."""
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
        """Test partial update of customer profile."""
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
