"""Tests for discount service layer."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.jobs.models import City, Job, JobCategory

from ..models import Discount, UserDiscountUsage
from ..services import discount_service


class DiscountServiceTests(TestCase):
    """Tests for DiscountService."""

    def setUp(self):
        self.now = timezone.now()
        self.homeowner = User.objects.create_user(
            email="homeowner-discount@test.com",
            password="testpass123",
        )
        self.handyman = User.objects.create_user(
            email="handyman-discount@test.com",
            password="testpass123",
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")
        UserRole.objects.create(user=self.handyman, role="handyman")

        self.category = JobCategory.objects.create(name="Plumbing", slug="plumbing")
        self.city = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            is_active=True,
        )
        self.job = Job.objects.create(
            homeowner=self.homeowner,
            title="Fix sink",
            description="Leaky sink",
            estimated_budget=Decimal("100.00"),
            category=self.category,
            city=self.city,
            address="123 Main St",
            status="open",
        )

    def _create_discount(self, **overrides):
        defaults = {
            "name": "Test Discount",
            "code": "TEST20",
            "description": "20% off",
            "discount_type": "percentage",
            "discount_value": 20,
            "target_role": "homeowner",
            "start_date": self.now - timedelta(days=1),
            "end_date": self.now + timedelta(days=7),
            "is_active": True,
            "max_uses_global": 0,
            "max_uses_per_user": 2,
        }
        defaults.update(overrides)
        return Discount.objects.create(**defaults)

    def test_get_active_discounts_with_role_filter(self):
        self._create_discount(code="HOME20", target_role="homeowner")
        self._create_discount(code="HAND10", target_role="handyman")
        self._create_discount(code="BOTH05", target_role="both")
        self._create_discount(code="INACTIVE", is_active=False)
        self._create_discount(
            code="EXPIRED",
            start_date=self.now - timedelta(days=10),
            end_date=self.now - timedelta(days=1),
        )

        homeowner_codes = {
            discount.code
            for discount in discount_service.get_active_discounts(role="homeowner")
        }
        self.assertEqual(homeowner_codes, {"HOME20", "BOTH05"})

    def test_validate_discount_code_not_yet_active(self):
        discount = self._create_discount(
            code="FUTURE20",
            start_date=self.now + timedelta(days=1),
            end_date=self.now + timedelta(days=5),
        )

        result = discount_service.validate_discount_code(
            code=discount.code,
            user=self.homeowner,
            target_role="homeowner",
        )

        self.assertFalse(result["valid"])
        self.assertEqual(result["message"], "This discount is not yet active.")

    def test_validate_discount_code_expired(self):
        discount = self._create_discount(
            code="PAST20",
            start_date=self.now - timedelta(days=10),
            end_date=self.now - timedelta(days=1),
        )

        result = discount_service.validate_discount_code(
            code=discount.code,
            user=self.homeowner,
            target_role="homeowner",
        )

        self.assertFalse(result["valid"])
        self.assertEqual(result["message"], "This discount has expired.")

    def test_validate_discount_code_inactive(self):
        discount = self._create_discount(code="OFF20", is_active=False)

        result = discount_service.validate_discount_code(
            code=discount.code,
            user=self.homeowner,
            target_role="homeowner",
        )

        self.assertFalse(result["valid"])
        self.assertEqual(result["message"], "This discount is currently inactive.")

    def test_validate_discount_code_role_message_for_handymen(self):
        discount = self._create_discount(code="HAND20", target_role="handyman")

        result = discount_service.validate_discount_code(
            code=discount.code,
            user=self.homeowner,
            target_role="homeowner",
        )

        self.assertFalse(result["valid"])
        self.assertIn("handymen", result["message"].lower())

    def test_validate_discount_code_role_message_for_custom_target(self):
        discount = self._create_discount(code="CUSTOM20", target_role="homeowner")
        Discount.objects.filter(pk=discount.pk).update(target_role="custom")

        result = discount_service.validate_discount_code(
            code=discount.code,
            user=self.homeowner,
            target_role="homeowner",
        )

        self.assertFalse(result["valid"])
        self.assertIn("homeowners and handymen", result["message"].lower())

    def test_validate_discount_code_global_usage_limit_reached(self):
        discount = self._create_discount(
            code="LIMIT1",
            max_uses_global=1,
            total_used_count=1,
        )

        result = discount_service.validate_discount_code(
            code=discount.code,
            user=self.homeowner,
            target_role="homeowner",
        )

        self.assertFalse(result["valid"])
        self.assertEqual(
            result["message"], "This discount has reached its usage limit."
        )

    def test_apply_discount_to_job_success(self):
        discount = self._create_discount(code="APPLY20", max_uses_per_user=2)

        usage = discount_service.apply_discount_to_job(
            discount, self.homeowner, self.job
        )

        self.assertEqual(usage.user, self.homeowner)
        self.assertEqual(usage.discount, discount)
        self.assertEqual(usage.job, self.job)
        discount.refresh_from_db()
        self.assertEqual(discount.total_used_count, 1)

    def test_apply_discount_to_job_raises_when_user_limit_reached(self):
        discount = self._create_discount(code="ONCE20", max_uses_per_user=1)
        UserDiscountUsage.objects.create(
            user=self.homeowner,
            discount=discount,
            job=self.job,
            usage_number=1,
        )

        with self.assertRaisesRegex(ValueError, "usage limit"):
            discount_service.apply_discount_to_job(discount, self.homeowner, self.job)

    def test_bulk_assign_discount_creates_usage_numbers_per_user(self):
        discount = self._create_discount(code="BULK20", max_uses_per_user=10)
        UserDiscountUsage.objects.create(
            user=self.homeowner,
            discount=discount,
            usage_number=1,
        )

        created_count = discount_service.bulk_assign_discount(
            discount=discount,
            users=[self.homeowner, self.handyman],
            usages_per_user=2,
        )

        self.assertEqual(created_count, 4)

        homeowner_numbers = list(
            UserDiscountUsage.objects.filter(
                user=self.homeowner,
                discount=discount,
            )
            .order_by("usage_number")
            .values_list("usage_number", flat=True)
        )
        handyman_numbers = list(
            UserDiscountUsage.objects.filter(
                user=self.handyman,
                discount=discount,
            )
            .order_by("usage_number")
            .values_list("usage_number", flat=True)
        )

        self.assertEqual(homeowner_numbers, [1, 2, 3])
        self.assertEqual(handyman_numbers, [1, 2])
