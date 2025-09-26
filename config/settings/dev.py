"""
Development settings for sb project.
"""

# Override for development
DEBUG = True
ALLOWED_HOSTS = ["*"]

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
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    INTERNAL_IPS = ["127.0.0.1", "localhost"]
except ImportError:
    pass
