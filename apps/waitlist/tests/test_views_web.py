"""Tests for waitlist API views."""

from rest_framework import status
from rest_framework.test import APITestCase

from apps.waitlist.models import WaitlistEntry


class WaitlistSignupViewTests(APITestCase):
    """Test cases for WaitlistSignupView API endpoint."""

    def setUp(self):
        """Set up test data."""
        self.url = "/api/v1/web/waitlist/"

    def test_signup_success_customer(self):
        """Test successful signup for customer."""
        data = {
            "user_name": "John Doe",
            "email": "john@example.com",
            "user_type": "customer",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Joined waitlist successfully")
        self.assertIsNone(response.data["errors"])

        # Verify entry was created in database
        self.assertEqual(WaitlistEntry.objects.count(), 1)
        entry = WaitlistEntry.objects.first()
        self.assertEqual(entry.user_name, "John Doe")
        self.assertEqual(entry.email, "john@example.com")
        self.assertEqual(entry.user_type, "customer")

    def test_signup_success_handyman(self):
        """Test successful signup for handyman."""
        data = {
            "user_name": "Jane Smith",
            "email": "jane@example.com",
            "user_type": "handyman",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Joined waitlist successfully")

        # Verify entry was created
        entry = WaitlistEntry.objects.first()
        self.assertEqual(entry.user_type, "handyman")

    def test_signup_duplicate_entry_updates(self):
        """Test that duplicate signup updates existing entry."""
        data = {
            "user_name": "John Doe",
            "email": "john@example.com",
            "user_type": "customer",
        }
        # First signup
        response1 = self.client.post(self.url, data, format="json")
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second signup with same data
        response2 = self.client.post(self.url, data, format="json")
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data["message"], "Waitlist entry updated")

        # Should still have only one entry
        self.assertEqual(WaitlistEntry.objects.count(), 1)

    def test_signup_missing_user_name(self):
        """Test signup fails with missing user_name."""
        data = {
            "email": "john@example.com",
            "user_type": "customer",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Validation failed")
        self.assertIn("user_name", response.data["errors"])

    def test_signup_missing_email(self):
        """Test signup fails with missing email."""
        data = {
            "user_name": "John Doe",
            "user_type": "customer",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data["errors"])

    def test_signup_missing_user_type(self):
        """Test signup fails with missing user_type."""
        data = {
            "user_name": "John Doe",
            "email": "john@example.com",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("user_type", response.data["errors"])

    def test_signup_invalid_email(self):
        """Test signup fails with invalid email format."""
        data = {
            "user_name": "John Doe",
            "email": "not-an-email",
            "user_type": "customer",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data["errors"])

    def test_signup_invalid_user_type(self):
        """Test signup fails with invalid user_type."""
        data = {
            "user_name": "John Doe",
            "email": "john@example.com",
            "user_type": "invalid_type",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("user_type", response.data["errors"])

    def test_signup_no_authentication_required(self):
        """Test that signup endpoint doesn't require authentication."""
        data = {
            "user_name": "John Doe",
            "email": "john@example.com",
            "user_type": "customer",
        }
        # APITestCase client is not authenticated by default
        response = self.client.post(self.url, data, format="json")
        # Should succeed without authentication
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_signup_empty_user_name(self):
        """Test signup fails with empty user_name."""
        data = {
            "user_name": "",
            "email": "john@example.com",
            "user_type": "customer",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("user_name", response.data["errors"])

    def test_signup_long_user_name(self):
        """Test signup handles maximum user_name length."""
        data = {
            "user_name": "A" * 255,  # Exactly at the limit
            "email": "john@example.com",
            "user_type": "customer",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_signup_user_name_exceeds_limit(self):
        """Test signup fails when user_name exceeds maximum length."""
        data = {
            "user_name": "A" * 256,  # One character over the limit
            "email": "john@example.com",
            "user_type": "customer",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("user_name", response.data["errors"])
