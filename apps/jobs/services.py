"""
Service for managing job applications.
"""

import logging

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.jobs.models import Job, JobApplication
from apps.notifications.services import notification_service

logger = logging.getLogger(__name__)


class JobApplicationService:
    """
    Service for handling job application business logic.
    """

    @transaction.atomic
    def apply_to_job(self, handyman, job: Job) -> JobApplication:
        """
        Create a job application from a handyman to a job.

        Args:
            handyman: User (handyman) applying
            job: Job to apply to

        Returns:
            JobApplication: Created application

        Raises:
            ValidationError: If application is invalid
        """
        # Validate job is open
        if job.status != "open":
            raise ValidationError("This job is not accepting applications.")

        # Validate handyman has handyman role
        if not handyman.has_role("handyman"):
            raise ValidationError("You must have a handyman role to apply.")

        # Validate handyman has profile
        if not hasattr(handyman, "handyman_profile"):
            raise ValidationError("You must complete your handyman profile first.")

        # Validate phone is verified
        handyman_profile = handyman.handyman_profile
        if not handyman_profile.is_phone_verified:
            raise ValidationError("You must verify your phone number to apply.")

        # Check if already applied
        if JobApplication.objects.filter(job=job, handyman=handyman).exists():
            raise ValidationError("You have already applied to this job.")

        # Create application
        application = JobApplication.objects.create(
            job=job,
            handyman=handyman,
            status="pending",
        )

        # Create notification for homeowner
        notification_service.create_and_send_notification(
            user=job.homeowner,
            notification_type="job_application_received",
            title=f"New application for {job.title}",
            body=f"{handyman_profile.display_name} has applied to your job.",
            target_role="homeowner",
            data={
                "job_id": str(job.public_id),
                "application_id": str(application.public_id),
            },
        )

        logger.info(
            f"Created application {application.public_id} for job {job.public_id}"
        )

        return application

    @transaction.atomic
    def approve_application(
        self, homeowner, application: JobApplication
    ) -> JobApplication:
        """
        Approve a job application.

        Args:
            homeowner: User (homeowner) approving
            application: Application to approve

        Returns:
            JobApplication: Approved application

        Raises:
            ValidationError: If approval is invalid
        """
        job = application.job

        # Validate homeowner owns the job
        if job.homeowner != homeowner:
            raise ValidationError(
                "You can only approve applications for your own jobs."
            )

        # Validate application is pending
        if application.status != "pending":
            raise ValidationError("Only pending applications can be approved.")

        # Approve the application
        application.status = "approved"
        application.save()

        # Update job status to in_progress
        job.status = "in_progress"
        job.save()

        # Auto-reject all other pending applications
        other_applications = JobApplication.objects.filter(
            job=job, status="pending"
        ).exclude(pk=application.pk)

        for other_app in other_applications:
            other_app.status = "rejected"
            other_app.save()

            # Notify rejected applicants
            notification_service.create_and_send_notification(
                user=other_app.handyman,
                notification_type="application_rejected",
                title="Application not selected",
                body=f"Your application for {job.title} was not selected. The position has been filled.",
                target_role="handyman",
                data={
                    "job_id": str(job.public_id),
                    "application_id": str(other_app.public_id),
                },
            )

        # Notify approved handyman
        notification_service.create_and_send_notification(
            user=application.handyman,
            notification_type="application_approved",
            title="Application approved!",
            body=f"Congratulations! Your application for {job.title} was approved.",
            target_role="handyman",
            data={
                "job_id": str(job.public_id),
                "application_id": str(application.public_id),
            },
        )

        logger.info(
            f"Approved application {application.public_id}, rejected {other_applications.count()} others"
        )

        return application

    @transaction.atomic
    def reject_application(
        self, homeowner, application: JobApplication
    ) -> JobApplication:
        """
        Reject a job application.

        Args:
            homeowner: User (homeowner) rejecting
            application: Application to reject

        Returns:
            JobApplication: Rejected application

        Raises:
            ValidationError: If rejection is invalid
        """
        job = application.job

        # Validate homeowner owns the job
        if job.homeowner != homeowner:
            raise ValidationError("You can only reject applications for your own jobs.")

        # Validate application is pending
        if application.status != "pending":
            raise ValidationError("Only pending applications can be rejected.")

        # Reject the application
        application.status = "rejected"
        application.save()

        # Notify rejected handyman
        notification_service.create_and_send_notification(
            user=application.handyman,
            notification_type="application_rejected",
            title="Application not selected",
            body=f"Your application for {job.title} was not selected.",
            target_role="handyman",
            data={
                "job_id": str(job.public_id),
                "application_id": str(application.public_id),
            },
        )

        logger.info(f"Rejected application {application.public_id}")

        return application

    @transaction.atomic
    def withdraw_application(
        self, handyman, application: JobApplication
    ) -> JobApplication:
        """
        Withdraw a job application.

        Args:
            handyman: User (handyman) withdrawing
            application: Application to withdraw

        Returns:
            JobApplication: Withdrawn application

        Raises:
            ValidationError: If withdrawal is invalid
        """
        job = application.job

        # Validate handyman owns the application
        if application.handyman != handyman:
            raise ValidationError("You can only withdraw your own applications.")

        # Validate application is pending
        if application.status != "pending":
            raise ValidationError("Only pending applications can be withdrawn.")

        # Withdraw the application
        application.status = "withdrawn"
        application.save()

        # Notify homeowner
        handyman_profile = handyman.handyman_profile
        notification_service.create_and_send_notification(
            user=job.homeowner,
            notification_type="application_withdrawn",
            title="Application withdrawn",
            body=f"{handyman_profile.display_name} has withdrawn their application for {job.title}.",
            target_role="homeowner",
            data={
                "job_id": str(job.public_id),
                "application_id": str(application.public_id),
            },
        )

        logger.info(f"Withdrew application {application.public_id}")

        return application


# Global job application service instance
job_application_service = JobApplicationService()
