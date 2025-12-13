"""
Profile models for different user types.
"""

from django.db import models

from apps.common.models import BaseModel


class HandymanProfile(BaseModel):
    """
    Profile for handyman users.

    Note: Some fields (phone_number, address, latitude/longitude) are intended for
    internal/handyman use and should not be exposed publicly to homeowners.
    """

    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="handyman_profile"
    )
    display_name = models.CharField(max_length=100)
    avatar = models.ImageField(
        upload_to="handyman/avatars/%Y/%m/",
        blank=True,
        null=True,
        help_text="Profile avatar image",
    )
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    # Pricing
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Handyman hourly rate in local currency",
    )

    # Location
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Handyman base latitude (used for nearby search)",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Handyman base longitude (used for nearby search)",
    )

    # Listing status
    is_active = models.BooleanField(default=True, db_index=True)
    is_available = models.BooleanField(default=True, db_index=True)
    is_approved = models.BooleanField(default=True, db_index=True)

    # Contact
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

    @property
    def avatar_url(self):
        """Return the full URL of the avatar image."""
        if self.avatar:
            return self.avatar.url
        return None


class HomeownerProfile(BaseModel):
    """
    Profile for homeowner users.
    """

    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="homeowner_profile"
    )
    display_name = models.CharField(max_length=100)
    avatar = models.ImageField(
        upload_to="homeowner/avatars/%Y/%m/",
        blank=True,
        null=True,
        help_text="Profile avatar image",
    )
    phone_number = models.CharField(max_length=20, blank=True)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        db_table = "homeowner_profiles"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Homeowner: {self.display_name}"

    @property
    def is_phone_verified(self):
        """Check if phone number is verified."""
        return self.phone_verified_at is not None

    @property
    def avatar_url(self):
        """Return the full URL of the avatar image."""
        if self.avatar:
            return self.avatar.url
        return None
