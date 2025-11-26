"""
Management command to test S3/R2 storage configuration.
"""

from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.management.base import BaseCommand
from PIL import Image as PILImage

from apps.common.storage import MediaStorage


class Command(BaseCommand):
    help = "Test S3/Cloudflare R2 storage configuration"

    def handle(self, *args, **options):
        self.stdout.write("Testing S3/R2 storage configuration...\n")

        # Initialize storage
        storage = MediaStorage()

        try:
            # Test 1: Check configuration
            self.stdout.write("1. Checking configuration...")
            self.stdout.write(f"   Bucket: {storage.bucket_name}")
            self.stdout.write(
                f"   Endpoint: {getattr(storage, 'endpoint_url', 'Default AWS S3')}"
            )
            self.stdout.write(
                f"   Region: {getattr(storage, 'region_name', 'Default')}"
            )
            self.stdout.write(self.style.SUCCESS("   ✓ Configuration loaded\n"))

            # Test 2: Create a test image
            self.stdout.write("2. Creating test image...")
            image_io = BytesIO()
            pil_image = PILImage.new("RGB", (100, 100), color="red")
            pil_image.save(image_io, format="JPEG")
            image_io.seek(0)

            test_file = InMemoryUploadedFile(
                image_io,
                field_name="test",
                name="test-storage-upload.jpg",
                content_type="image/jpeg",
                size=len(image_io.getvalue()),
                charset=None,
            )
            self.stdout.write(self.style.SUCCESS("   ✓ Test image created\n"))

            # Test 3: Upload file
            self.stdout.write("3. Uploading test file to storage...")
            file_path = "test/storage-test.jpg"
            saved_path = storage.save(file_path, test_file)
            self.stdout.write(self.style.SUCCESS(f"   ✓ File uploaded: {saved_path}\n"))

            # Test 4: Check if file exists
            self.stdout.write("4. Verifying file exists...")
            if storage.exists(saved_path):
                self.stdout.write(self.style.SUCCESS("   ✓ File exists in storage\n"))
            else:
                self.stdout.write(self.style.ERROR("   ✗ File not found in storage\n"))
                return

            # Test 5: Get file URL
            self.stdout.write("5. Getting file URL...")
            file_url = storage.url(saved_path)
            self.stdout.write(f"   URL: {file_url}")
            self.stdout.write(self.style.SUCCESS("   ✓ URL generated\n"))

            # Test 6: Get file size
            self.stdout.write("6. Checking file metadata...")
            file_size = storage.size(saved_path)
            self.stdout.write(f"   Size: {file_size} bytes")
            self.stdout.write(self.style.SUCCESS("   ✓ Metadata accessible\n"))

            # Test 7: Delete file
            self.stdout.write("7. Cleaning up (deleting test file)...")
            storage.delete(saved_path)
            if not storage.exists(saved_path):
                self.stdout.write(self.style.SUCCESS("   ✓ Test file deleted\n"))
            else:
                self.stdout.write(self.style.WARNING("   ! Test file still exists\n"))

            # Success!
            self.stdout.write(
                self.style.SUCCESS(
                    "\n✓ All tests passed! S3/R2 storage is configured correctly.\n"
                )
            )
            self.stdout.write("Your storage is ready to use for file uploads.\n")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n✗ Storage test failed: {str(e)}\n"))
            self.stdout.write("\nTroubleshooting tips:")
            self.stdout.write("1. Check your .env file has all required variables:")
            self.stdout.write("   - AWS_ACCESS_KEY_ID")
            self.stdout.write("   - AWS_SECRET_ACCESS_KEY")
            self.stdout.write("   - AWS_STORAGE_BUCKET_NAME")
            self.stdout.write("   - AWS_S3_ENDPOINT_URL (for R2)")
            self.stdout.write("   - AWS_S3_REGION_NAME")
            self.stdout.write("\n2. Verify your credentials are correct")
            self.stdout.write("3. Check your bucket exists and is accessible")
            self.stdout.write("4. For R2: Verify endpoint URL format")
            self.stdout.write("   https://<account-id>.r2.cloudflarestorage.com")
            self.stdout.write(
                "\nSee docs/CLOUDFLARE_R2_SETUP.md for detailed setup instructions.\n"
            )
            raise
