"""
Management command to delete all dummy data.

Usage:
    python manage.py delete_dummy_data
    python manage.py delete_dummy_data --yes  # Skip confirmation

This will delete all records where is_dummy=True:
    - Jobs (cascade deletes JobImage)
    - Users (cascade deletes UserRole, profiles)

Note: Files in S3 storage are NOT deleted to speed up the process.
"""

from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.jobs.models import Job, JobImage


class Command(BaseCommand):
    help = "Delete all dummy data (is_dummy=True)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        # Count dummy data
        dummy_users = User.objects.filter(is_dummy=True)
        dummy_jobs = Job.objects.filter(is_dummy=True)

        user_count = dummy_users.count()
        job_count = dummy_jobs.count()

        # Count images that will be cascade deleted
        image_count = JobImage.objects.filter(job__is_dummy=True).count()

        if user_count == 0 and job_count == 0:
            self.stdout.write(self.style.WARNING("No dummy data found."))
            return

        # Show summary
        self.stdout.write("Found dummy data:")
        self.stdout.write(f"  - Users: {user_count}")
        self.stdout.write(f"  - Jobs: {job_count}")
        self.stdout.write(f"  - Job Images: {image_count}")

        # Confirm deletion
        if not options["yes"]:
            self.stdout.write("")
            confirm = input("Are you sure you want to delete all dummy data? [y/N]: ")
            if confirm.lower() != "y":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        self.stdout.write("\nDeleting...")

        # Delete jobs (cascade deletes JobImage records)
        dummy_jobs.delete()
        self.stdout.write(
            self.style.SUCCESS(f"  Deleted {job_count} jobs (and {image_count} images)")
        )

        # Delete users (cascade deletes UserRole, profiles)
        dummy_users.delete()
        self.stdout.write(
            self.style.SUCCESS(f"  Deleted {user_count} users (and profiles)")
        )

        self.stdout.write(
            "\n" + self.style.SUCCESS("Done! All dummy data has been removed.")
        )
        self.stdout.write(
            self.style.WARNING("Note: S3 files are NOT deleted (orphaned).")
        )
