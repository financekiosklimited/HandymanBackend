from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import BaseModel

# Configurable limits for job items
MAX_JOB_ITEMS = 20  # Maximum number of items per job
MAX_JOB_ITEM_LENGTH = 255  # Maximum characters per item


class JobCategory(BaseModel):
    """
    Job category model for categorizing different types of home services.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "job_categories"
        ordering = ["name"]
        verbose_name = "Job Category"
        verbose_name_plural = "Job Categories"
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.name


class City(BaseModel):
    """
    City model for major Canadian cities.
    """

    name = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    province_code = models.CharField(max_length=2)  # e.g., ON, BC, AB
    slug = models.SlugField(max_length=150)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "cities"
        ordering = ["name"]
        verbose_name = "City"
        verbose_name_plural = "Cities"
        unique_together = [["name", "province"]]
        indexes = [
            models.Index(fields=["province_code"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return f"{self.name}, {self.province_code}"


class Job(BaseModel):
    """
    Job listing model for homeowners to post jobs.
    """

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("pending_completion", "Pending Completion"),
        ("completed", "Completed"),
        ("disputed", "Disputed"),
        ("cancelled", "Cancelled"),
        ("deleted", "Deleted"),
    ]

    homeowner = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="jobs"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    estimated_budget = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(
        "JobCategory", on_delete=models.PROTECT, related_name="jobs"
    )
    city = models.ForeignKey("City", on_delete=models.PROTECT, related_name="jobs")
    address = models.TextField()
    postal_code = models.CharField(max_length=7, blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    status_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when status was last changed",
    )

    assigned_handyman = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_jobs",
        help_text="The handyman assigned to this job",
    )
    completion_requested_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Dummy data flag for demo purposes
    is_dummy = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "jobs"
        ordering = ["-created_at"]
        verbose_name = "Job"
        verbose_name_plural = "Jobs"
        indexes = [
            models.Index(fields=["homeowner"]),
            models.Index(fields=["category"]),
            models.Index(fields=["city"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.homeowner.email}"

    def clean(self):
        """
        Validate the job data.
        """
        super().clean()

        # Validate budget is positive
        if self.estimated_budget is not None:
            if self.estimated_budget <= Decimal("0"):
                raise ValidationError(
                    {"estimated_budget": "Budget must be greater than 0."}
                )

        # Validate category is active
        if self.category and not self.category.is_active:
            raise ValidationError({"category": "Selected category is not active."})

        # Validate city is active
        if self.city and not self.city.is_active:
            raise ValidationError({"city": "Selected city is not active."})

        # Validate that if latitude or longitude is provided, both must be provided
        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError(
                "Both latitude and longitude must be provided together."
            )

        # Validate coordinate ranges
        if self.latitude is not None:
            if not (-90 <= self.latitude <= 90):
                raise ValidationError(
                    {"latitude": "Latitude must be between -90 and 90."}
                )
        if self.longitude is not None:
            if not (-180 <= self.longitude <= 180):
                raise ValidationError(
                    {"longitude": "Longitude must be between -180 and 180."}
                )

    def save(self, *args, **kwargs):
        """
        Override save to run validation and track status changes.
        """
        from django.utils import timezone

        # Track status changes
        if self.pk:
            old_status = Job.objects.filter(pk=self.pk).values("status").first()
            if old_status and old_status["status"] != self.status:
                self.status_at = timezone.now()
        elif self.status:
            # New instance with status set
            self.status_at = timezone.now()

        self.full_clean()
        super().save(*args, **kwargs)


class JobTask(BaseModel):
    """
    Individual task/item within a job.
    Tracks completion status, who completed it, and when.
    """

    job = models.ForeignKey("Job", on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_tasks",
    )

    class Meta:
        db_table = "job_tasks"
        ordering = ["order", "created_at"]
        verbose_name = "Job Task"
        verbose_name_plural = "Job Tasks"
        indexes = [
            models.Index(fields=["job"]),
            models.Index(fields=["is_completed"]),
        ]

    def __str__(self):
        status = "✓" if self.is_completed else "○"
        return f"{status} {self.title}"


class JobImage(BaseModel):
    """
    Job image model for storing multiple images per job.
    """

    job = models.ForeignKey("Job", on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="jobs/images/%Y/%m/%d/")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "job_images"
        ordering = ["order", "created_at"]
        verbose_name = "Job Image"
        verbose_name_plural = "Job Images"
        unique_together = [["job", "order"]]
        indexes = [
            models.Index(fields=["job"]),
            models.Index(fields=["order"]),
        ]

    def __str__(self):
        return f"Image {self.order} for {self.job.title}"


class WorkSession(BaseModel):
    """
    Tracks a work session (START to STOP) for a job.
    """

    STATUS_CHOICES = [
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
    ]

    job = models.ForeignKey(
        "Job", on_delete=models.CASCADE, related_name="work_sessions"
    )
    handyman = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="work_sessions",
    )

    # Timestamps
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)

    # Start location & photo (required)
    start_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    start_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    start_accuracy = models.FloatField(null=True, blank=True)
    start_photo = models.ImageField(upload_to="work-sessions/start-photos/%Y/%m/%d/")

    # End location (captured on STOP)
    end_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    end_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    end_accuracy = models.FloatField(null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="in_progress"
    )

    class Meta:
        db_table = "work_sessions"
        ordering = ["-started_at"]
        verbose_name = "Work Session"
        verbose_name_plural = "Work Sessions"
        indexes = [
            models.Index(fields=["job"]),
            models.Index(fields=["handyman"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-started_at"]),
        ]

    def __str__(self):
        return f"Work session for {self.job.title} on {self.started_at.date()}"

    @property
    def duration(self):
        """Return duration as timedelta."""
        if self.ended_at and self.started_at:
            return self.ended_at - self.started_at
        return None

    @property
    def duration_seconds(self):
        """Return duration in seconds."""
        if self.duration:
            return int(self.duration.total_seconds())
        return None


class WorkSessionMedia(BaseModel):
    """
    Photos/videos uploaded during a work session.
    """

    MEDIA_TYPE_CHOICES = [
        ("photo", "Photo"),
        ("video", "Video"),
    ]

    work_session = models.ForeignKey(
        "WorkSession", on_delete=models.CASCADE, related_name="media"
    )
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    file = models.FileField(upload_to="work-sessions/media/%Y/%m/%d/")
    thumbnail = models.ImageField(
        upload_to="work-sessions/thumbnails/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    description = models.TextField(blank=True)
    task = models.ForeignKey(
        "JobTask",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="media",
        help_text="Optional: Link to specific task",
    )
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    duration_seconds = models.PositiveIntegerField(
        null=True, blank=True, help_text="Duration for videos"
    )

    class Meta:
        db_table = "work_session_media"
        ordering = ["-created_at"]
        verbose_name = "Work Session Media"
        verbose_name_plural = "Work Session Media"
        indexes = [
            models.Index(fields=["work_session"]),
            models.Index(fields=["media_type"]),
        ]

    def __str__(self):
        return f"{self.media_type} for {self.work_session}"


class DailyReport(BaseModel):
    """
    Daily work report submitted by handyman.
    """

    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    job = models.ForeignKey(
        "Job", on_delete=models.CASCADE, related_name="daily_reports"
    )
    handyman = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="daily_reports_submitted",
    )
    report_date = models.DateField()

    # Content
    summary = models.TextField(help_text="Description of work done today")

    # Calculated from work sessions
    total_work_duration = models.DurationField(
        help_text="Total work duration for this day"
    )

    # Review
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    homeowner_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_reports_reviewed",
    )

    # Auto-approval deadline (3 days from creation)
    review_deadline = models.DateTimeField()

    class Meta:
        db_table = "daily_reports"
        ordering = ["-report_date"]
        verbose_name = "Daily Report"
        verbose_name_plural = "Daily Reports"
        unique_together = ["job", "report_date"]
        indexes = [
            models.Index(fields=["job"]),
            models.Index(fields=["handyman"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-report_date"]),
            models.Index(fields=["review_deadline"]),
        ]

    def __str__(self):
        return f"Daily report for {self.job.title} on {self.report_date}"


class DailyReportTask(BaseModel):
    """
    Tasks worked on in a daily report.
    """

    daily_report = models.ForeignKey(
        "DailyReport", on_delete=models.CASCADE, related_name="tasks_worked"
    )
    task = models.ForeignKey(
        "JobTask", on_delete=models.CASCADE, related_name="daily_report_entries"
    )
    notes = models.TextField(blank=True, help_text="Notes about this task")
    marked_complete = models.BooleanField(
        default=False, help_text="Handyman marked this task as complete"
    )

    class Meta:
        db_table = "daily_report_tasks"
        unique_together = ["daily_report", "task"]
        ordering = ["task__order"]
        verbose_name = "Daily Report Task"
        verbose_name_plural = "Daily Report Tasks"

    def __str__(self):
        return f"{self.task.title} in report {self.daily_report.report_date}"


class JobDispute(BaseModel):
    """
    Dispute raised by homeowner about job work.
    """

    STATUS_CHOICES = [
        ("pending", "Pending Admin Review"),
        ("in_review", "Under Review"),
        ("resolved_full_refund", "Resolved - Full Refund"),
        ("resolved_partial_refund", "Resolved - Partial Refund"),
        ("resolved_pay_handyman", "Resolved - Pay Handyman"),
        ("cancelled", "Cancelled"),
    ]

    job = models.ForeignKey("Job", on_delete=models.CASCADE, related_name="disputes")
    initiated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="disputes_initiated",
    )

    # Dispute details
    reason = models.TextField()
    disputed_reports = models.ManyToManyField(
        "DailyReport", blank=True, related_name="disputes"
    )

    # Resolution
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    admin_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disputes_resolved",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    refund_percentage = models.PositiveIntegerField(
        null=True, blank=True, help_text="Refund percentage (0-100)"
    )

    # Auto-resolution deadline (3 days)
    resolution_deadline = models.DateTimeField()

    class Meta:
        db_table = "job_disputes"
        ordering = ["-created_at"]
        verbose_name = "Job Dispute"
        verbose_name_plural = "Job Disputes"
        indexes = [
            models.Index(fields=["job"]),
            models.Index(fields=["status"]),
            models.Index(fields=["resolution_deadline"]),
        ]
        permissions = [
            ("can_manage_disputes", "Can resolve and manage job disputes"),
        ]

    def __str__(self):
        return f"Dispute for {self.job.title} ({self.status})"


class JobApplication(BaseModel):
    """
    Job application model for handymen to apply to jobs.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
    ]

    job = models.ForeignKey(
        "Job", on_delete=models.CASCADE, related_name="applications"
    )
    handyman = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="job_applications"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    status_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when status was last changed",
    )

    class Meta:
        db_table = "job_applications"
        ordering = ["-created_at"]
        verbose_name = "Job Application"
        verbose_name_plural = "Job Applications"
        unique_together = [["job", "handyman"]]
        indexes = [
            models.Index(fields=["job"]),
            models.Index(fields=["handyman"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.handyman.email} → {self.job.title} ({self.status})"

    def save(self, *args, **kwargs):
        """
        Override save to track status changes.
        """
        from django.utils import timezone

        # Track status changes
        if self.pk:
            old_status = (
                JobApplication.objects.filter(pk=self.pk).values("status").first()
            )
            if old_status and old_status["status"] != self.status:
                self.status_at = timezone.now()
        elif self.status:
            # New instance with status set
            self.status_at = timezone.now()

        super().save(*args, **kwargs)
