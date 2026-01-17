"""
Management command to delete all dummy data.

Usage:
    python manage.py delete_dummy_data
    python manage.py delete_dummy_data --yes  # Skip confirmation

This will delete all records where is_dummy=True:
    - Jobs (cascade deletes attachments, tasks, applications, work sessions,
            daily reports, reviews, etc.)
    - Users (cascade deletes UserRole, profiles)

Note: Files in S3 storage are NOT deleted to speed up the process.
"""

from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.jobs.models import (
    DailyReport,
    DailyReportTask,
    Job,
    JobApplication,
    JobApplicationAttachment,
    JobApplicationMaterial,
    JobAttachment,
    JobTask,
    Review,
    WorkSession,
    WorkSessionMedia,
)


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

        # Count all related data that will be cascade deleted
        job_attachment_count = JobAttachment.objects.filter(job__is_dummy=True).count()
        job_task_count = JobTask.objects.filter(job__is_dummy=True).count()

        application_count = JobApplication.objects.filter(job__is_dummy=True).count()
        application_material_count = JobApplicationMaterial.objects.filter(
            application__job__is_dummy=True
        ).count()
        application_attachment_count = JobApplicationAttachment.objects.filter(
            application__job__is_dummy=True
        ).count()

        work_session_count = WorkSession.objects.filter(job__is_dummy=True).count()
        work_session_media_count = WorkSessionMedia.objects.filter(
            work_session__job__is_dummy=True
        ).count()

        daily_report_count = DailyReport.objects.filter(job__is_dummy=True).count()
        daily_report_task_count = DailyReportTask.objects.filter(
            daily_report__job__is_dummy=True
        ).count()

        review_count = Review.objects.filter(job__is_dummy=True).count()

        if user_count == 0 and job_count == 0:
            self.stdout.write(self.style.WARNING("No dummy data found."))
            return

        # Show summary
        self.stdout.write("Found dummy data:")
        self.stdout.write(f"  - Users: {user_count}")
        self.stdout.write(f"  - Jobs: {job_count}")
        self.stdout.write(f"    - Job Attachments: {job_attachment_count}")
        self.stdout.write(f"    - Job Tasks: {job_task_count}")
        self.stdout.write(f"    - Job Applications: {application_count}")
        self.stdout.write(
            f"      - Application Materials: {application_material_count}"
        )
        self.stdout.write(
            f"      - Application Attachments: {application_attachment_count}"
        )
        self.stdout.write(f"    - Work Sessions: {work_session_count}")
        self.stdout.write(f"      - Session Media: {work_session_media_count}")
        self.stdout.write(f"    - Daily Reports: {daily_report_count}")
        self.stdout.write(f"      - Report Tasks: {daily_report_task_count}")
        self.stdout.write(f"    - Reviews: {review_count}")

        # Calculate total records
        total_records = (
            user_count
            + job_count
            + job_attachment_count
            + job_task_count
            + application_count
            + application_material_count
            + application_attachment_count
            + work_session_count
            + work_session_media_count
            + daily_report_count
            + daily_report_task_count
            + review_count
        )
        self.stdout.write(f"\n  Total records to delete: {total_records}")

        # Confirm deletion
        if not options["yes"]:
            self.stdout.write("")
            confirm = input("Are you sure you want to delete all dummy data? [y/N]: ")
            if confirm.lower() != "y":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        self.stdout.write("\nDeleting...")

        # Delete jobs first (cascade deletes all related records)
        dummy_jobs.delete()
        self.stdout.write(
            self.style.SUCCESS(f"  Deleted {job_count} jobs and all related records:")
        )
        self.stdout.write(f"    - {job_attachment_count} attachments")
        self.stdout.write(f"    - {job_task_count} tasks")
        self.stdout.write(f"    - {application_count} applications")
        self.stdout.write(f"    - {work_session_count} work sessions")
        self.stdout.write(f"    - {daily_report_count} daily reports")
        self.stdout.write(f"    - {review_count} reviews")

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
