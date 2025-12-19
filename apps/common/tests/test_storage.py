"""Tests for storage backends."""

from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.common.storage import MediaStorage


class MediaStorageTests(TestCase):
    """Test cases for MediaStorage."""

    @patch("storages.backends.s3boto3.S3Boto3Storage.__init__")
    def test_init_with_defaults(self, mock_super_init):
        """Test initialization with default settings."""
        mock_super_init.return_value = None
        with override_settings(
            AWS_S3_CUSTOM_DOMAIN="cdn.example.com",
            AWS_S3_SIGNATURE_VERSION="s3v4",
            AWS_S3_OBJECT_PARAMETERS={"CacheControl": "max-age=86400"},
            AWS_S3_ENDPOINT_URL=None,
        ):
            storage = MediaStorage()
            mock_super_init.assert_called_once()
            args, kwargs = mock_super_init.call_args
            self.assertEqual(kwargs["custom_domain"], "cdn.example.com")
            self.assertEqual(kwargs["signature_version"], "s3v4")
            self.assertEqual(
                kwargs["object_parameters"], {"CacheControl": "max-age=86400"}
            )

    @patch("storages.backends.s3boto3.S3Boto3Storage.__init__")
    def test_init_r2_detection(self, mock_super_init):
        """Test R2 detection and optimization."""
        mock_super_init.return_value = None
        with override_settings(
            AWS_S3_ENDPOINT_URL="https://accountid.r2.cloudflarestorage.com",
            AWS_S3_REGION_NAME="us-east-1",
        ):
            storage = MediaStorage()
            self.assertIsNone(storage.region_name)
            self.assertEqual(
                storage.endpoint_url, "https://accountid.r2.cloudflarestorage.com"
            )

    @patch("storages.backends.s3boto3.S3Boto3Storage.__init__")
    def test_init_other_s3_detection(self, mock_super_init):
        """Test non-R2 S3 initialization."""
        mock_super_init.return_value = None
        with override_settings(
            AWS_S3_ENDPOINT_URL="https://s3.amazonaws.com",
            AWS_S3_REGION_NAME="us-west-2",
        ):
            storage = MediaStorage()
            self.assertEqual(storage.region_name, "us-west-2")

    @patch("storages.backends.s3boto3.S3Boto3Storage.__init__")
    def test_url_custom_domain(self, mock_super_init):
        """Test URL generation with custom domain."""
        mock_super_init.return_value = None
        storage = MediaStorage(custom_domain="cdn.example.com")
        storage.custom_domain = "cdn.example.com"

        url = storage.url("test.jpg")
        self.assertEqual(url, "https://cdn.example.com/media/test.jpg")

        # Test cleaning 'media/' prefix
        url = storage.url("media/test.jpg")
        self.assertEqual(url, "https://cdn.example.com/media/test.jpg")

    @patch("storages.backends.s3boto3.S3Boto3Storage.url")
    @patch("storages.backends.s3boto3.S3Boto3Storage.__init__")
    def test_url_no_custom_domain(self, mock_super_init, mock_super_url):
        """Test URL generation without custom domain."""
        mock_super_init.return_value = None
        mock_super_url.return_value = "https://s3.amazonaws.com/bucket/media/test.jpg"

        storage = MediaStorage()
        storage.custom_domain = None

        url = storage.url("test.jpg")
        self.assertEqual(url, "https://s3.amazonaws.com/bucket/media/test.jpg")
        mock_super_url.assert_called_once_with("test.jpg", None, None, None)
