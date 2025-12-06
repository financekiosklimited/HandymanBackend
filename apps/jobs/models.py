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
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
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
    job_items = models.JSONField(
        default=list,
        blank=True,
        help_text="List of tasks/items to be done for this job",
    )

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

        # Validate job_items
        if self.job_items:
            if not isinstance(self.job_items, list):
                raise ValidationError({"job_items": "Job items must be a list."})

            if len(self.job_items) > MAX_JOB_ITEMS:
                raise ValidationError(
                    {"job_items": f"Maximum {MAX_JOB_ITEMS} items allowed."}
                )

            for idx, item in enumerate(self.job_items):
                if not isinstance(item, str):
                    raise ValidationError(
                        {"job_items": f"Item at index {idx} must be a string."}
                    )
                if len(item) > MAX_JOB_ITEM_LENGTH:
                    raise ValidationError(
                        {
                            "job_items": f"Item at index {idx} exceeds maximum length of {MAX_JOB_ITEM_LENGTH} characters."
                        }
                    )

    def save(self, *args, **kwargs):
        """
        Override save to run validation.
        """
        self.full_clean()
        super().save(*args, **kwargs)


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
