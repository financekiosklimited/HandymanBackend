"""
Discount models for managing promotional discounts for homeowners and handymen.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel


class Discount(BaseModel):
    """
    Discount model for promotional codes targeting homeowners or handymen.

    Homeowner discounts reduce the platform fee percentage when creating a job.
    Handyman discounts reduce the platform fee percentage when applying to a job.
    """

    DISCOUNT_TYPE_CHOICES = [
        ("percentage", "Percentage"),
        ("fixed_amount", "Fixed Amount"),
    ]

    TARGET_ROLE_CHOICES = [
        ("homeowner", "Homeowner"),
        ("handyman", "Handyman"),
        ("both", "Both"),
    ]

    ICON_CHOICES = [
        ("sparkles", "Sparkles"),
        ("gift", "Gift"),
        ("wrench", "Wrench"),
        ("tag", "Tag"),
        ("percent", "Percent"),
        ("dollar_sign", "Dollar Sign"),
        ("star", "Star"),
        ("zap", "Zap"),
    ]

    name = models.CharField(max_length=100, help_text="Display name for the discount")
    code = models.CharField(
        max_length=50, unique=True, help_text="Unique code in ALL CAPS (e.g., FIRST20)"
    )
    description = models.TextField(help_text="Marketing description shown to users")
    terms_and_conditions = models.TextField(
        help_text="Terms and conditions including app cut fee disclaimer",
        default="This discount applies to the platform fee only, not the job value.",
    )

    discount_type = models.CharField(
        max_length=20, choices=DISCOUNT_TYPE_CHOICES, default="percentage"
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Percentage (e.g., 20.00 for 20%) or fixed amount",
    )

    target_role = models.CharField(
        max_length=20,
        choices=TARGET_ROLE_CHOICES,
        default="homeowner",
        help_text="Who can use this discount",
    )

    start_date = models.DateTimeField(help_text="When discount becomes active")
    end_date = models.DateTimeField(help_text="When discount expires")

    max_uses_global = models.PositiveIntegerField(
        default=0, help_text="Maximum total uses (0 = unlimited)"
    )
    total_used_count = models.PositiveIntegerField(
        default=0, help_text="Total times this discount has been used"
    )
    max_uses_per_user = models.PositiveIntegerField(
        default=1, help_text="Maximum uses per user"
    )

    is_active = models.BooleanField(
        default=True, help_text="Whether discount is currently active"
    )

    # Visual styling
    color = models.CharField(
        max_length=7, default="#0C9A5C", help_text="Hex color code (e.g., #0C9A5C)"
    )
    icon = models.CharField(
        max_length=20,
        choices=ICON_CHOICES,
        default="sparkles",
        help_text="Icon to display on discount card",
    )
    badge_text = models.CharField(
        max_length=50, blank=True, help_text="Optional badge (e.g., 'POPULAR', 'NEW')"
    )

    class Meta:
        db_table = "discounts"
        ordering = ["-created_at"]
        verbose_name = "Discount"
        verbose_name_plural = "Discounts"
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["target_role"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["start_date", "end_date"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        """Validate discount configuration."""
        super().clean()

        # Ensure code is uppercase
        if self.code:
            self.code = self.code.upper()

        # Validate dates
        if self.start_date and self.end_date:
            if self.end_date <= self.start_date:
                raise ValidationError("End date must be after start date.")

        # Validate discount value
        if self.discount_value is not None:
            if self.discount_value <= 0:
                raise ValidationError("Discount value must be greater than 0.")

            if self.discount_type == "percentage" and self.discount_value > 100:
                raise ValidationError("Percentage discount cannot exceed 100%.")

    def save(self, *args, **kwargs):
        """Ensure code is uppercase before saving."""
        if self.code:
            self.code = self.code.upper()
        super().save(*args, **kwargs)

    def is_valid(self):
        """
        Check if discount is currently valid based on dates and active status.
        """
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

    def is_available_globally(self):
        """
        Check if discount has remaining global uses.
        """
        if self.max_uses_global == 0:
            return True
        return self.total_used_count < self.max_uses_global

    def can_use_for_role(self, role):
        """
        Check if discount can be used by specific role.

        Args:
            role: 'homeowner' or 'handyman'

        Returns:
            bool: True if discount targets this role
        """
        return self.target_role in [role, "both"]

    def get_remaining_uses_for_user(self, user):
        """
        Get remaining uses for a specific user.

        Args:
            user: User instance

        Returns:
            int: Number of remaining uses (0 if exhausted)
        """
        used_count = UserDiscountUsage.objects.filter(user=user, discount=self).count()
        return max(0, self.max_uses_per_user - used_count)

    def can_user_use(self, user):
        """
        Check if a specific user can use this discount.

        Args:
            user: User instance

        Returns:
            bool: True if user has remaining uses
        """
        return self.get_remaining_uses_for_user(user) > 0

    def get_ends_in_days(self):
        """
        Calculate days until discount expires.

        Returns:
            int: Days remaining, 0 if expired
        """
        now = timezone.now()
        if now > self.end_date:
            return 0
        delta = self.end_date - now
        return max(0, delta.days)

    def get_expiry_text(self):
        """
        Get human-readable expiry text.

        Returns:
            str: "Ends in X days" or "Expires today"
        """
        days = self.get_ends_in_days()
        if days == 0:
            return "Expires today"
        elif days == 1:
            return "Ends in 1 day"
        else:
            return f"Ends in {days} days"

    def get_discount_display(self):
        """
        Get formatted discount string for display.

        Returns:
            str: "20% OFF" or "$50 OFF"
        """
        if self.discount_type == "percentage":
            return f"{int(self.discount_value)}% OFF"
        else:
            return f"${int(self.discount_value)} OFF"

    def record_usage(self, user, job=None):
        """
        Record that a user has used this discount.

        Args:
            user: User who used the discount
            job: Optional Job instance (null for pre-assigned usages)

        Returns:
            UserDiscountUsage: The created usage record
        """
        usage_number = (
            UserDiscountUsage.objects.filter(user=user, discount=self).count() + 1
        )

        usage = UserDiscountUsage.objects.create(
            user=user, discount=self, job=job, usage_number=usage_number
        )

        # Increment total count
        self.total_used_count += 1
        self.save(update_fields=["total_used_count"])

        return usage


class UserDiscountUsage(BaseModel):
    """
    Tracks individual discount usages per user.
    Allows for multiple usages per user based on max_uses_per_user setting.
    """

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="discount_usages"
    )
    discount = models.ForeignKey(
        Discount, on_delete=models.CASCADE, related_name="user_usages"
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discount_usages",
    )
    used_at = models.DateTimeField(auto_now_add=True)
    usage_number = models.PositiveIntegerField(
        default=1, help_text="Which usage number this is for the user (1, 2, 3, etc.)"
    )

    class Meta:
        db_table = "user_discount_usages"
        ordering = ["-used_at"]
        verbose_name = "User Discount Usage"
        verbose_name_plural = "User Discount Usages"
        unique_together = [["user", "discount", "usage_number"]]
        indexes = [
            models.Index(fields=["user", "discount"]),
            models.Index(fields=["used_at"]),
        ]

    def __str__(self):
        job_str = f" for job {self.job.public_id}" if self.job else " (pre-assigned)"
        return f"{self.user.email} used {self.discount.code}{job_str}"
