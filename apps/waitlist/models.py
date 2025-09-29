"""Database models for waitlist functionality."""

from django.db import models


class WaitlistEntry(models.Model):
    """Represents a user who has joined the waitlist."""

    CUSTOMER = "customer"
    HANDYMAN = "handyman"

    USER_TYPE_CHOICES = [
        (CUSTOMER, "Customer"),
        (HANDYMAN, "Handyman"),
    ]

    user_name = models.CharField(max_length=255)
    email = models.EmailField()
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "waitlist_entries"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.email} ({self.user_type})"
