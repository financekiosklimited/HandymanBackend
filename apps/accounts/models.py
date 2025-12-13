"""
User and role models for accounts app.
"""

import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from apps.common.models import BaseModel


class UserManager(BaseUserManager):
    """
    Custom manager for User model.
    """

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password."""
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model with email as unique identifier.
    Note: Inherits from AbstractUser instead of BaseModel to maintain Django auth compatibility.
    We'll add the BaseModel fields manually here.
    """

    # Override the default id field to be explicit
    id = models.BigAutoField(primary_key=True)

    # Remove username field and use email as unique identifier
    username = None
    email = models.EmailField(unique=True)

    # Additional fields
    google_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    # Public UUID for external references (from BaseModel pattern)
    public_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True
    )

    # Timestamps (from BaseModel pattern) - note: date_joined already exists in AbstractUser
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    # Dummy data flag for demo purposes
    is_dummy = models.BooleanField(default=False, db_index=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        """Override save to ensure public_id is set."""
        if not self.public_id:
            self.public_id = uuid.uuid4()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

    @property
    def is_email_verified(self):
        return self.email_verified_at is not None

    def get_role(self, role_name):
        """Get specific role for this user."""
        try:
            return self.roles.get(role=role_name)
        except UserRole.DoesNotExist:
            return None

    def has_role(self, role_name):
        """Check if user has a specific role."""
        return self.roles.filter(role=role_name).exists()


class UserRole(BaseModel):
    """
    Roles that a user can have (admin, handyman, customer).
    """

    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("handyman", "Handyman"),
        ("homeowner", "Homeowner"),
    ]

    NEXT_ACTION_CHOICES = [
        ("verify_email", "Verify Email"),
        ("fill_profile", "Fill Profile"),
        ("none", "None"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roles")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    next_action = models.CharField(
        max_length=20, choices=NEXT_ACTION_CHOICES, default="verify_email"
    )

    class Meta:
        db_table = "user_roles"
        unique_together = ("user", "role")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.role}"
