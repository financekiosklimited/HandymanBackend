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
