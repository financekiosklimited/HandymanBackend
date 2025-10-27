"""Test settings for sb project.

Uses SQLite for faster test execution and no PostgreSQL dependency.
"""

from .base import *  # noqa: F403

# Override database to use SQLite for testing
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable debug for tests
DEBUG = False

# Use a simple password hasher for faster tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
    },
}

# Use a simple static files storage for tests (avoids WhiteNoise manifest requirement)
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# Remove WhiteNoiseMiddleware for tests since we don't need static file serving in test environment
MIDDLEWARE = [
    mw
    for mw in MIDDLEWARE  # noqa: F405
    if mw != "whitenoise.middleware.WhiteNoiseMiddleware"
]
