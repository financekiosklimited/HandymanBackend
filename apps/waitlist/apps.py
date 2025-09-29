"""App configuration for waitlist."""

from django.apps import AppConfig


class WaitlistConfig(AppConfig):
    """Configuration for the waitlist app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.waitlist"
    verbose_name = "Waitlist"
