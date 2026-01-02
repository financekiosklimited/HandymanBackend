"""Test settings for sb project.

Uses SQLite for faster test execution and no PostgreSQL dependency.
"""

import tempfile

from .base import *  # noqa: F403

# Override database to use SQLite for testing
# Using file-based SQLite instead of :memory: to support parallel test execution
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",  # noqa: F405
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

# Use local filesystem storage for tests to avoid hitting external S3/R2 services
TEST_MEDIA_ROOT = tempfile.mkdtemp()
MEDIA_ROOT = TEST_MEDIA_ROOT
MEDIA_URL = "/media/"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": TEST_MEDIA_ROOT},
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Remove WhiteNoiseMiddleware for tests since we don't need static file serving in test environment
MIDDLEWARE = [
    mw
    for mw in MIDDLEWARE  # noqa: F405
    if mw != "whitenoise.middleware.WhiteNoiseMiddleware"
]

# Disable throttling during tests
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": dict.fromkeys(
        REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],  # noqa: F405
        "1000/sec",
    ),
}
