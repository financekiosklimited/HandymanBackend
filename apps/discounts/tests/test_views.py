"""
Tests for Discount API views.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole

from ..models import Discount, UserDiscountUsage


class DiscountListViewTests(TestCase):
    """Tests for DiscountListView."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.now = timezone.now()

        # Create test discounts
        self.active_homeowner = Discount.objects.create(
            name="Active Homeowner Discount",
            code="HOME20",
            description="20% off for homeowners",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=7),
            is_active=True,
        )

        self.active_handyman = Discount.objects.create(
            name="Active Handyman Discount",
            code="HAND15",
            description="15% off for handymen",
            discount_type="percentage",
            discount_value=15,
            target_role="handyman",
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=7),
            is_active=True,
        )

        self.active_both = Discount.objects.create(
            name="Both Discount",
            code="BOTH10",
            description="10% off for everyone",
            discount_type="percentage",
            discount_value=10,
            target_role="both",
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=7),
            is_active=True,
        )

        self.inactive_discount = Discount.objects.create(
            name="Inactive Discount",
            code="INACTIVE",
            description="Should not appear",
            discount_type="percentage",
            discount_value=50,
            target_role="homeowner",
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=7),
            is_active=False,
        )

        self.expired_discount = Discount.objects.create(
            name="Expired Discount",
            code="EXPIRED",
            description="Already expired",
            discount_type="percentage",
            discount_value=30,
            target_role="homeowner",
            start_date=self.now - timedelta(days=7),
            end_date=self.now - timedelta(days=1),
            is_active=True,
        )

    def test_list_discounts_unauthenticated(self):
        """Test listing discounts without authentication."""
        url = reverse("discounts:mobile:discount-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should see active discounts only
        codes = [d["code"] for d in data["data"]]
        self.assertIn("HOME20", codes)
        self.assertIn("HAND15", codes)
        self.assertIn("BOTH10", codes)
        self.assertNotIn("INACTIVE", codes)
        self.assertNotIn("EXPIRED", codes)

    def test_list_discounts_filter_by_role_homeowner(self):
        """Test filtering discounts by homeowner role."""
        url = reverse("discounts:mobile:discount-list")
        response = self.client.get(url, {"role": "homeowner"})

        self.assertEqual(response.status_code, 200)
        data = response.json()

        codes = [d["code"] for d in data["data"]]
        self.assertIn("HOME20", codes)
        self.assertNotIn("HAND15", codes)  # Handyman only
        self.assertIn("BOTH10", codes)

    def test_list_discounts_filter_by_role_handyman(self):
        """Test filtering discounts by handyman role."""
        url = reverse("discounts:mobile:discount-list")
        response = self.client.get(url, {"role": "handyman"})

        self.assertEqual(response.status_code, 200)
        data = response.json()

        codes = [d["code"] for d in data["data"]]
        self.assertNotIn("HOME20", codes)  # Homeowner only
        self.assertIn("HAND15", codes)
        self.assertIn("BOTH10", codes)

    def test_list_discounts_response_format(self):
        """Test response format includes all expected fields."""
        url = reverse("discounts:mobile:discount-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check response structure
        self.assertIn("message", data)
        self.assertIn("data", data)
        self.assertIn("errors", data)
        self.assertIn("meta", data)

        # Check discount fields
        if data["data"]:
            discount = data["data"][0]
            self.assertIn("public_id", discount)
            self.assertIn("name", discount)
            self.assertIn("code", discount)
            self.assertIn("description", discount)
            self.assertIn("terms_and_conditions", discount)
            self.assertIn("discount_type", discount)
            self.assertIn("discount_value", discount)
            self.assertIn("discount_display", discount)
            self.assertIn("target_role", discount)
            self.assertIn("color", discount)
            self.assertIn("icon", discount)
            self.assertIn("badge_text", discount)
            self.assertIn("expiry_text", discount)
            self.assertIn("ends_in_days", discount)


class DiscountValidateViewTests(TestCase):
    """Tests for DiscountValidateView."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.now = timezone.now()

        self.user = User.objects.create_user(
            email="testuser@test.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="homeowner")

        self.discount = Discount.objects.create(
            name="Test Discount",
            code="TEST20",
            description="20% off",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=7),
            is_active=True,
            max_uses_per_user=1,
        )

    def test_validate_valid_code(self):
        """Test validating a valid discount code."""
        self.client.force_authenticate(user=self.user)

        url = reverse("discounts:mobile:discount-validate")
        response = self.client.post(
            url,
            {
                "code": "TEST20",
                "target_role": "homeowner",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data["data"]["valid"])
        self.assertIn("discount", data["data"])
        self.assertEqual(data["data"]["remaining_uses"], 1)

    def test_validate_invalid_code(self):
        """Test validating an invalid discount code."""
        self.client.force_authenticate(user=self.user)

        url = reverse("discounts:mobile:discount-validate")
        response = self.client.post(
            url,
            {
                "code": "INVALID",
                "target_role": "homeowner",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertFalse(data["data"]["valid"])
        self.assertIn("message", data["data"])

    def test_validate_wrong_role(self):
        """Test validating a code for wrong role."""
        self.client.force_authenticate(user=self.user)

        url = reverse("discounts:mobile:discount-validate")
        response = self.client.post(
            url,
            {
                "code": "TEST20",
                "target_role": "handyman",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertFalse(data["data"]["valid"])
        self.assertIn("homeowners", data["data"]["message"].lower())

    def test_validate_already_used(self):
        """Test validating a code user has already used."""
        # Record usage
        UserDiscountUsage.objects.create(
            user=self.user, discount=self.discount, usage_number=1
        )

        self.client.force_authenticate(user=self.user)

        url = reverse("discounts:mobile:discount-validate")
        response = self.client.post(
            url,
            {
                "code": "TEST20",
                "target_role": "homeowner",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertFalse(data["data"]["valid"])
        self.assertIn("already used", data["data"]["message"].lower())

    def test_validate_unauthenticated(self):
        """Test validating without authentication."""
        url = reverse("discounts:mobile:discount-validate")
        response = self.client.post(
            url,
            {
                "code": "TEST20",
                "target_role": "homeowner",
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_validate_missing_fields(self):
        """Test validating with missing required fields."""
        self.client.force_authenticate(user=self.user)

        url = reverse("discounts:mobile:discount-validate")
        response = self.client.post(
            url,
            {
                "code": "TEST20",
                # Missing target_role
            },
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()

        self.assertIn("errors", data)


class DiscountDetailViewTests(TestCase):
    """Tests for DiscountDetailView."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.now = timezone.now()

        self.discount = Discount.objects.create(
            name="Test Discount",
            code="TEST20",
            description="20% off",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=7),
            is_active=True,
        )

    def test_get_discount_by_code(self):
        """Test getting discount details by code."""
        url = reverse("discounts:mobile:discount-detail", kwargs={"code": "TEST20"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["data"]["code"], "TEST20")
        self.assertEqual(data["data"]["name"], "Test Discount")

    def test_get_discount_case_insensitive(self):
        """Test that code lookup is case insensitive."""
        url = reverse("discounts:mobile:discount-detail", kwargs={"code": "test20"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["data"]["code"], "TEST20")

    def test_get_nonexistent_discount(self):
        """Test getting a discount that doesn't exist."""
        url = reverse(
            "discounts:mobile:discount-detail", kwargs={"code": "NONEXISTENT"}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
