"""
Custom storage backends for file uploads.
"""

import logging

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)


class MediaStorage(S3Boto3Storage):
    """
    Custom S3 storage for media files (Cloudflare R2 compatible).

    This storage backend is configured to work with:
    - Cloudflare R2 (S3-compatible object storage)
    - AWS S3
    - Any S3-compatible storage service

    Configuration is done via environment variables in settings.

    Features:
    - Automatic file organization in 'media/' directory
    - Prevents file overwriting (generates unique names)
    - No ACL requirement (R2 compatible)
    - Public URL generation without query strings
    - Cache control headers for optimal CDN performance
    """

    location = "media"
    file_overwrite = False
    default_acl = None
    querystring_auth = False

    def __init__(self, **settings_override):
        """Initialize storage with custom settings."""
        # Set R2-compatible defaults before calling parent __init__
        # For Cloudflare R2, we need to disable some AWS-specific features
        if "custom_domain" not in settings_override:
            settings_override["custom_domain"] = getattr(
                settings, "AWS_S3_CUSTOM_DOMAIN", None
            )

        if "signature_version" not in settings_override:
            settings_override["signature_version"] = getattr(
                settings, "AWS_S3_SIGNATURE_VERSION", "s3v4"
            )

        if "object_parameters" not in settings_override:
            settings_override["object_parameters"] = getattr(
                settings, "AWS_S3_OBJECT_PARAMETERS", {}
            )

        super().__init__(**settings_override)

        # Override settings for better R2 compatibility
        if hasattr(settings, "AWS_S3_ENDPOINT_URL") and settings.AWS_S3_ENDPOINT_URL:
            self.endpoint_url = settings.AWS_S3_ENDPOINT_URL
            # For R2, disable region-specific endpoint
            if "r2.cloudflarestorage.com" in self.endpoint_url:
                self.region_name = None
                logger.info("Cloudflare R2 detected - using R2-optimized settings")
            else:
                self.region_name = settings.AWS_S3_REGION_NAME
                logger.info(
                    f"Using S3-compatible storage with region: {self.region_name}"
                )

    def url(self, name, parameters=None, expire=None, http_method=None):
        """
        Generate public URL for the file.

        For R2 with public buckets, we prefer using the custom domain
        to avoid signing overhead and provide cleaner URLs.
        """
        # If we have a custom domain, build a simple URL
        custom_domain = getattr(self, "custom_domain", None)
        if custom_domain:
            # Clean the name (remove leading 'media/' if present)
            clean_name = (
                name.replace("media/", "", 1) if name.startswith("media/") else name
            )
            url = f"https://{custom_domain}/media/{clean_name}"
            return url

        # Otherwise, use the default S3 URL generation
        return super().url(name, parameters, expire, http_method)
