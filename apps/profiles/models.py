"""
Profile models for different user types.
"""

from django.db import models

from apps.common.models import BaseModel


class HandymanProfile(BaseModel):
    """
    Profile for handyman users.
    """

    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="handyman_profile"
    )
    display_name = models.CharField(max_length=100)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        db_table = "handyman_profiles"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Handyman: {self.display_name}"

    @property
    def is_phone_verified(self):
        """Check if phone number is verified."""
        return self.phone_verified_at is not None


class CustomerProfile(BaseModel):
    """
    Profile for customer users.
    """

    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="customer_profile"
    )
    display_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        db_table = "customer_profiles"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Customer: {self.display_name}"

    @property
    def is_phone_verified(self):
        """Check if phone number is verified."""
        return self.phone_verified_at is not None
