"""
Development settings for sb project.
"""

from .base import *  # noqa: F403, F401

# Override for development
DEBUG = True  # noqa: F405
ALLOWED_HOSTS = ["*"]  # noqa: F405

# Force PostgreSQL in development - remove SQLite override
# Database configuration is inherited from base.py which uses PostgreSQL

# Use SMTP backend for emails in development (Mailhog)
# Comment out the line below to use Mailhog instead of console
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Optional: Disable S3 for development and use local file storage
# DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
# MEDIA_ROOT = BASE_DIR / 'media'
# MEDIA_URL = '/media/'

# Add debug toolbar if available
try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1", "localhost"]
except ImportError:
    pass
