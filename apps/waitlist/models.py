"""Database models for waitlist functionality."""

from django.db import models

from apps.common.models import BaseModel


class WaitlistEntry(BaseModel):
    """Represents a user who has joined the waitlist."""

    HOMEOWNER = "homeowner"
    HANDYMAN = "handyman"

    USER_TYPE_CHOICES = [
        (HOMEOWNER, "Homeowner"),
        (HANDYMAN, "Handyman"),
    ]

    user_name = models.CharField(max_length=255)
    email = models.EmailField()
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)

    class Meta:
        db_table = "waitlist_entries"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.email} ({self.user_type})"
