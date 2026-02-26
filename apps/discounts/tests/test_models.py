"""
Tests for Discount models.
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.jobs.models import City, Job, JobCategory

from ..models import Discount, UserDiscountUsage


class DiscountModelTests(TestCase):
    """Tests for Discount model."""

    def setUp(self):
        """Set up test data."""
        self.now = timezone.now()
        self.future = self.now + timedelta(days=7)
        self.past = self.now - timedelta(days=7)

        self.user = User.objects.create_user(
            email="testuser@test.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="homeowner")

        self.category = JobCategory.objects.create(
            name="Test Category", slug="test-category"
        )

        self.city = City.objects.create(
            name="Test City", province="Test Province", province_code="TP"
        )

    def test_discount_code_uppercase_on_save(self):
        """Test that code is converted to uppercase on save."""
        discount = Discount.objects.create(
            name="Test Discount",
            code="lowercase123",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now,
            end_date=self.future,
        )

        self.assertEqual(discount.code, "LOWERCASE123")

    def test_discount_validation_end_date_before_start(self):
        """Test that end_date must be after start_date."""
        discount = Discount(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.future,
            end_date=self.now,
        )

        with self.assertRaises(ValidationError):
            discount.full_clean()

    def test_discount_validation_negative_value(self):
        """Test that discount value must be positive."""
        discount = Discount(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="percentage",
            discount_value=-10,
            target_role="homeowner",
            start_date=self.now,
            end_date=self.future,
        )

        with self.assertRaises(ValidationError):
            discount.full_clean()

    def test_discount_validation_percentage_over_100(self):
        """Test that percentage discount cannot exceed 100%."""
        discount = Discount(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="percentage",
            discount_value=150,
            target_role="homeowner",
            start_date=self.now,
            end_date=self.future,
        )

        with self.assertRaises(ValidationError):
            discount.full_clean()

    def test_is_valid_within_date_range(self):
        """Test is_valid() returns True for active discount within dates."""
        discount = Discount.objects.create(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=7),
            is_active=True,
        )

        self.assertTrue(discount.is_valid())

    def test_is_valid_not_active(self):
        """Test is_valid() returns False for inactive discount."""
        discount = Discount.objects.create(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now - timedelta(days=1),
            end_date=self.now + timedelta(days=7),
            is_active=False,
        )

        self.assertFalse(discount.is_valid())

    def test_is_valid_expired(self):
        """Test is_valid() returns False for expired discount."""
        discount = Discount.objects.create(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now - timedelta(days=7),
            end_date=self.now - timedelta(days=1),
            is_active=True,
        )

        self.assertFalse(discount.is_valid())

    def test_is_available_globally_unlimited(self):
        """Test is_available_globally() returns True when unlimited."""
        discount = Discount.objects.create(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now,
            end_date=self.future,
            max_uses_global=0,
            total_used_count=100,
        )

        self.assertTrue(discount.is_available_globally())

    def test_is_available_globally_limited(self):
        """Test is_available_globally() with usage limit."""
        discount = Discount.objects.create(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now,
            end_date=self.future,
            max_uses_global=10,
            total_used_count=5,
        )

        self.assertTrue(discount.is_available_globally())

        discount.total_used_count = 10
        discount.save()

        self.assertFalse(discount.is_available_globally())

    def test_can_use_for_role(self):
        """Test can_use_for_role() method."""
        homeowner_discount = Discount.objects.create(
            name="Homeowner Discount",
            code="HOME01",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now,
            end_date=self.future,
        )

        handyman_discount = Discount.objects.create(
            name="Handyman Discount",
            code="HAND01",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="handyman",
            start_date=self.now,
            end_date=self.future,
        )

        both_discount = Discount.objects.create(
            name="Both Discount",
            code="BOTH01",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="both",
            start_date=self.now,
            end_date=self.future,
        )

        # Test homeowner role
        self.assertTrue(homeowner_discount.can_use_for_role("homeowner"))
        self.assertFalse(homeowner_discount.can_use_for_role("handyman"))

        # Test handyman role
        self.assertFalse(handyman_discount.can_use_for_role("homeowner"))
        self.assertTrue(handyman_discount.can_use_for_role("handyman"))

        # Test both
        self.assertTrue(both_discount.can_use_for_role("homeowner"))
        self.assertTrue(both_discount.can_use_for_role("handyman"))

    def test_get_remaining_uses_for_user(self):
        """Test get_remaining_uses_for_user() method."""
        discount = Discount.objects.create(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now,
            end_date=self.future,
            max_uses_per_user=2,
        )

        # Initially has 2 uses remaining
        self.assertEqual(discount.get_remaining_uses_for_user(self.user), 2)

        # Use once
        UserDiscountUsage.objects.create(
            user=self.user, discount=discount, usage_number=1
        )

        # Now has 1 use remaining
        discount.refresh_from_db()
        self.assertEqual(discount.get_remaining_uses_for_user(self.user), 1)

        # Use again
        UserDiscountUsage.objects.create(
            user=self.user, discount=discount, usage_number=2
        )

        # Now has 0 uses remaining
        discount.refresh_from_db()
        self.assertEqual(discount.get_remaining_uses_for_user(self.user), 0)

    def test_can_user_use(self):
        """Test can_user_use() method."""
        discount = Discount.objects.create(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now,
            end_date=self.future,
            max_uses_per_user=1,
        )

        self.assertTrue(discount.can_user_use(self.user))

        # Use the discount
        UserDiscountUsage.objects.create(
            user=self.user, discount=discount, usage_number=1
        )

        discount.refresh_from_db()
        self.assertFalse(discount.can_user_use(self.user))

    def test_get_ends_in_days(self):
        """Test get_ends_in_days() method."""
        # Create discount ending in exactly 5 days from now (at end of day)
        end_date = self.now + timedelta(days=5, hours=23, minutes=59)
        discount = Discount.objects.create(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now,
            end_date=end_date,
        )

        # Should be at least 4 days (accounting for time of day)
        days_remaining = discount.get_ends_in_days()
        self.assertGreaterEqual(days_remaining, 4)
        self.assertLessEqual(days_remaining, 6)

    def test_get_expiry_text(self):
        """Test get_expiry_text() method."""
        # Create discount ending in exactly 5 days from now (at end of day)
        end_date = self.now + timedelta(days=5, hours=23, minutes=59)
        discount = Discount.objects.create(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now,
            end_date=end_date,
        )

        expiry_text = discount.get_expiry_text()
        # Should start with "Ends in" and contain "days"
        self.assertTrue(expiry_text.startswith("Ends in"))
        self.assertIn("days", expiry_text)

        # Test single day
        discount.end_date = self.now + timedelta(days=1, hours=12)
        discount.save()
        self.assertEqual(discount.get_expiry_text(), "Ends in 1 day")

    def test_get_discount_display_percentage(self):
        """Test get_discount_display() for percentage discount."""
        discount = Discount.objects.create(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="percentage",
            discount_value=20.50,
            target_role="homeowner",
            start_date=self.now,
            end_date=self.future,
        )

        self.assertEqual(discount.get_discount_display(), "20% OFF")

    def test_get_discount_display_fixed(self):
        """Test get_discount_display() for fixed amount discount."""
        discount = Discount.objects.create(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="fixed_amount",
            discount_value=50.00,
            target_role="homeowner",
            start_date=self.now,
            end_date=self.future,
        )

        self.assertEqual(discount.get_discount_display(), "$50 OFF")

    def test_record_usage(self):
        """Test record_usage() method."""
        discount = Discount.objects.create(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now,
            end_date=self.future,
            max_uses_per_user=2,
            total_used_count=0,
        )

        job = Job.objects.create(
            homeowner=self.user,
            title="Test Job",
            description="Test description",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Test St",
        )

        # Record first usage
        usage1 = discount.record_usage(self.user, job)
        self.assertEqual(usage1.usage_number, 1)

        # Refresh discount and check count
        discount.refresh_from_db()
        self.assertEqual(discount.total_used_count, 1)

        # Record second usage
        usage2 = discount.record_usage(self.user, job)
        self.assertEqual(usage2.usage_number, 2)

        discount.refresh_from_db()
        self.assertEqual(discount.total_used_count, 2)


class UserDiscountUsageModelTests(TestCase):
    """Tests for UserDiscountUsage model."""

    def setUp(self):
        """Set up test data."""
        self.now = timezone.now()
        self.future = self.now + timedelta(days=7)

        self.user = User.objects.create_user(
            email="testuser@test.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.user, role="homeowner")

        self.category = JobCategory.objects.create(
            name="Test Category", slug="test-category"
        )

        self.city = City.objects.create(
            name="Test City", province="Test Province", province_code="TP"
        )

        self.discount = Discount.objects.create(
            name="Test Discount",
            code="TEST01",
            description="Test description",
            discount_type="percentage",
            discount_value=20,
            target_role="homeowner",
            start_date=self.now,
            end_date=self.future,
        )

    def test_usage_creation(self):
        """Test creating a usage record."""
        job = Job.objects.create(
            homeowner=self.user,
            title="Test Job",
            description="Test description",
            estimated_budget=100,
            category=self.category,
            city=self.city,
            address="123 Test St",
        )

        usage = UserDiscountUsage.objects.create(
            user=self.user, discount=self.discount, job=job, usage_number=1
        )

        self.assertEqual(usage.user, self.user)
        self.assertEqual(usage.discount, self.discount)
        self.assertEqual(usage.job, job)
        self.assertEqual(usage.usage_number, 1)
        self.assertIsNotNone(usage.used_at)

    def test_usage_without_job(self):
        """Test creating a pre-assigned usage without job."""
        usage = UserDiscountUsage.objects.create(
            user=self.user, discount=self.discount, job=None, usage_number=1
        )

        self.assertIsNone(usage.job)
        self.assertEqual(usage.usage_number, 1)

    def test_unique_constraint(self):
        """Test that user+discount+usage_number must be unique."""
        UserDiscountUsage.objects.create(
            user=self.user, discount=self.discount, usage_number=1
        )

        # Should raise integrity error for duplicate
        with self.assertRaises(IntegrityError):
            UserDiscountUsage.objects.create(
                user=self.user, discount=self.discount, usage_number=1
            )
