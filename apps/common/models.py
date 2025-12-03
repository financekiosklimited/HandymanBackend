"""
Base models and common utilities.
"""

import uuid

from django.db import models


class BaseModel(models.Model):
    """
    Abstract base model with standard fields for all custom models.
    Provides id, public_id, created_at, and updated_at fields.
    """

    # Primary key (Django's default AutoField)
    id = models.BigAutoField(primary_key=True)

    # Public UUID for external references (API responses, etc.)
    public_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True
        # Default ordering by creation date (newest first)
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        """Override save to ensure public_id is set."""
        if not self.public_id:
            self.public_id = uuid.uuid4()
        super().save(*args, **kwargs)


class CountryPhoneCode(BaseModel):
    """
    Country dialing codes for phone number validation.
    """

    country_code = models.CharField(
        max_length=3,
        unique=True,
        help_text="ISO 3166-1 alpha-2 code (e.g., 'ID', 'CA')",
    )
    country_name = models.CharField(max_length=100)
    dial_code = models.CharField(max_length=10, help_text="Dialing code (e.g., '+62')")
    flag_emoji = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(
        default=0, help_text="Lower numbers appear first"
    )

    class Meta:
        db_table = "country_phone_codes"
        ordering = ["display_order", "country_name"]

    def __str__(self):
        return f"{self.country_name} ({self.dial_code})"
