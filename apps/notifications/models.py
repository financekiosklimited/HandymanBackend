from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import BaseModel

TARGET_ROLE_CHOICES = [
    ("handyman", "Handyman"),
    ("homeowner", "Homeowner"),
]


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
        ("work_session_started", "Work Session Started"),
        ("work_session_ended", "Work Session Ended"),
        ("work_session_media_uploaded", "Work Session Media Uploaded"),
        ("daily_report_submitted", "Daily Report Submitted"),
        ("daily_report_approved", "Daily Report Approved"),
        ("daily_report_rejected", "Daily Report Rejected"),
        ("daily_report_updated", "Daily Report Updated"),
        ("job_completion_requested", "Job Completion Requested"),
        ("job_completion_approved", "Job Completion Approved"),
        ("job_completion_rejected", "Job Completion Rejected"),
        ("job_dispute_opened", "Job Dispute Opened"),
        ("job_dispute_resolved", "Job Dispute Resolved"),
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
    target_role = models.CharField(
        max_length=20,
        choices=TARGET_ROLE_CHOICES,
        db_index=True,
        help_text="Target role for this notification",
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notifications",
        help_text="User who triggered this notification (if any)",
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(
                fields=["user", "target_role", "-created_at"],
                name="notificatio_user_id_target_idx",
            ),
            models.Index(fields=["notification_type"]),
            models.Index(fields=["target_role"], name="notificatio_target_idx"),
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
        ("specific", "Specific Users"),
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
    target_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="targeted_broadcasts",
        blank=True,
    )

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
