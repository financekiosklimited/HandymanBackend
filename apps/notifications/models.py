from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import BaseModel


class UserDevice(BaseModel):
    """
    Stores FCM device tokens for push notifications.
    """

    DEVICE_TYPE_CHOICES = [
        ("ios", "iOS"),
        ("android", "Android"),
        ("web", "Web"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="devices"
    )
    device_token = models.CharField(max_length=512, unique=True)
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPE_CHOICES)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user_devices"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["device_token"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.device_type} ({self.device_token[:20]}...)"


class Notification(BaseModel):
    """
    Stores in-app notifications for users.
    """

    NOTIFICATION_TYPE_CHOICES = [
        ("job_application_received", "Job Application Received"),
        ("application_approved", "Application Approved"),
        ("application_rejected", "Application Rejected"),
        ("application_withdrawn", "Application Withdrawn"),
        ("admin_broadcast", "Admin Broadcast"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=50, choices=NOTIFICATION_TYPE_CHOICES
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    data = models.JSONField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["notification_type"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.title}"

    def clean(self):
        super().clean()
        if self.data is not None and not isinstance(self.data, dict):
            raise ValidationError({"data": "Data must be a JSON object."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class BroadcastNotification(BaseModel):
    """
    Stores broadcast notifications sent by admin.
    """

    TARGET_CHOICES = [
        ("all", "All Users"),
        ("handyman", "All Handymen"),
        ("homeowner", "All Homeowners"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    title = models.CharField(max_length=200)
    body = models.TextField()
    data = models.JSONField(null=True, blank=True)
    target_audience = models.CharField(max_length=20, choices=TARGET_CHOICES)

    # Push notification option
    send_push = models.BooleanField(default=True)

    # Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    sent_at = models.DateTimeField(null=True, blank=True)

    # Stats
    total_recipients = models.PositiveIntegerField(default=0)
    push_success_count = models.PositiveIntegerField(default=0)
    push_failure_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "broadcast_notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_target_audience_display()})"
