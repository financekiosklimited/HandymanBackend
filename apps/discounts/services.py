"""
Service layer for Discount business logic.
"""

from django.db import models, transaction
from django.utils import timezone

from .models import Discount, UserDiscountUsage


class DiscountService:
    """
    Service class for discount-related business logic.
    """

    def get_active_discounts(self, role=None):
        """
        Get currently active discounts.

        Args:
            role: Optional role filter ('homeowner' or 'handyman')

        Returns:
            QuerySet: Active discounts ordered by created_at desc
        """
        now = timezone.now()

        queryset = Discount.objects.filter(
            is_active=True, start_date__lte=now, end_date__gte=now
        )

        if role:
            queryset = queryset.filter(
                models.Q(target_role=role) | models.Q(target_role="both")
            )

        return queryset.order_by("-created_at")

    def validate_discount_code(self, code, user, target_role):
        """
        Validate a discount code for a specific user and role.

        Args:
            code: Discount code (will be uppercased)
            user: User attempting to use the discount
            target_role: 'homeowner' or 'handyman'

        Returns:
            dict: Validation result with keys:
                - valid: bool
                - discount: Discount instance (if valid)
                - message: Error message (if invalid)
                - remaining_uses: int (if valid)
        """
        code = code.upper()

        try:
            discount = Discount.objects.get(code=code)
        except Discount.DoesNotExist:
            return {
                "valid": False,
                "message": "Invalid discount code.",
            }

        # Check if discount is active and within date range
        if not discount.is_valid():
            now = timezone.now()
            if now < discount.start_date:
                return {
                    "valid": False,
                    "message": "This discount is not yet active.",
                }
            elif now > discount.end_date:
                return {
                    "valid": False,
                    "message": "This discount has expired.",
                }
            else:
                return {
                    "valid": False,
                    "message": "This discount is currently inactive.",
                }

        # Check if discount targets this role
        if not discount.can_use_for_role(target_role):
            allowed_roles = []
            if discount.target_role == "homeowner":
                allowed_roles = ["homeowners"]
            elif discount.target_role == "handyman":
                allowed_roles = ["handymen"]
            else:
                allowed_roles = ["homeowners and handymen"]

            return {
                "valid": False,
                "message": f"This discount is only valid for {allowed_roles[0]}.",
            }

        # Check global usage limit
        if not discount.is_available_globally():
            return {
                "valid": False,
                "message": "This discount has reached its usage limit.",
            }

        # Check per-user usage limit
        remaining_uses = discount.get_remaining_uses_for_user(user)
        if remaining_uses <= 0:
            return {
                "valid": False,
                "message": "You have already used this discount.",
            }

        return {
            "valid": True,
            "discount": discount,
            "remaining_uses": remaining_uses,
        }

    def apply_discount_to_job(self, discount, user, job):
        """
        Apply a discount to a job and record the usage.

        Args:
            discount: Discount instance
            user: User applying the discount
            job: Job instance

        Returns:
            UserDiscountUsage: The created usage record

        Raises:
            ValueError: If user cannot use this discount
        """
        # Validate user can still use this discount
        if not discount.can_user_use(user):
            raise ValueError("You have exceeded your usage limit for this discount.")

        # Record usage
        usage = discount.record_usage(user, job)

        return usage

    @transaction.atomic
    def bulk_assign_discount(self, discount, users, usages_per_user=1):
        """
        Bulk assign discount usages to multiple users.

        Args:
            discount: Discount instance
            users: QuerySet or list of User instances
            usages_per_user: Number of usages to assign each user

        Returns:
            int: Number of usages created
        """
        created_count = 0

        for user in users:
            # Get current usage count for this user
            current_usage = UserDiscountUsage.objects.filter(
                user=user, discount=discount
            ).count()

            # Create new usages
            for i in range(usages_per_user):
                UserDiscountUsage.objects.create(
                    user=user,
                    discount=discount,
                    job=None,  # Pre-assigned, no job yet
                    usage_number=current_usage + i + 1,
                )
                created_count += 1

        return created_count


# Singleton instance for service
discount_service = DiscountService()
