"""
Service for managing job applications.
"""

import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.common.validators import get_file_type_from_mime
from apps.jobs.models import (
    DailyReport,
    DailyReportTask,
    Job,
    JobApplication,
    JobApplicationAttachment,
    JobApplicationMaterial,
    JobDispute,
    JobTask,
    Review,
    WorkSession,
    WorkSessionMedia,
)
from apps.notifications.services import notification_service

logger = logging.getLogger(__name__)


class JobApplicationService:
    """
    Service for handling job application business logic.
    """

    @transaction.atomic
    def apply_to_job(
        self,
        handyman,
        job: Job,
        predicted_hours=None,
        estimated_total_price=None,
        negotiation_reasoning="",
        materials_data=None,
        attachments=None,
    ) -> JobApplication:
        """
        Create a job application from a handyman to a job.

        Args:
            handyman: User (handyman) applying
            job: Job to apply to
            predicted_hours: Predicted total hours needed (required)
            estimated_total_price: Estimated total price from handyman (required)
            negotiation_reasoning: Detailed reasoning of negotiation (optional)
            materials_data: List of material dicts with name, price, description (optional)
            attachments: List of file objects (optional)

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
            predicted_hours=predicted_hours,
            estimated_total_price=estimated_total_price,
            negotiation_reasoning=negotiation_reasoning or "",
        )

        # Create materials
        materials_data = materials_data or []
        for material_data in materials_data:
            JobApplicationMaterial.objects.create(
                application=application,
                name=material_data["name"],
                price=material_data["price"],
                description=material_data.get("description", ""),
            )

        # Create attachments
        attachments = attachments or []
        for attachment_data in attachments:
            # Handle new indexed format (dict with file, file_type, thumbnail, duration)
            if isinstance(attachment_data, dict):
                file = attachment_data.get("file")
                file_type = attachment_data.get("file_type", "image")
                thumbnail = attachment_data.get("thumbnail")
                duration_seconds = attachment_data.get("duration_seconds")
            else:
                # Legacy: plain file object
                file = attachment_data
                content_type = getattr(file, "content_type", "")
                file_type = get_file_type_from_mime(content_type) or "image"
                thumbnail = None
                duration_seconds = None

            JobApplicationAttachment.objects.create(
                application=application,
                file=file,
                file_type=file_type,
                file_name=getattr(file, "name", ""),
                file_size=getattr(file, "size", 0),
                thumbnail=thumbnail,
                duration_seconds=duration_seconds,
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
            triggered_by=handyman,
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
        application.save(update_fields=["status", "updated_at"])

        # Update job status to in_progress and set assigned handyman
        job.status = "in_progress"
        job.assigned_handyman = application.handyman
        job.save(
            update_fields=["status", "assigned_handyman", "updated_at", "status_at"]
        )

        # Auto-reject all other pending applications
        other_applications = JobApplication.objects.filter(
            job=job, status="pending"
        ).exclude(pk=application.pk)

        for other_app in other_applications:
            other_app.status = "rejected"
            other_app.save(update_fields=["status", "updated_at"])

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
                triggered_by=homeowner,
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
            triggered_by=homeowner,
        )

        # Notify homeowner about job start with assigned handyman
        notification_service.create_and_send_notification(
            user=job.homeowner,
            notification_type="application_approved",
            title="Handyman assigned",
            body=f"{application.handyman.handyman_profile.display_name} is now assigned to {job.title}.",
            target_role="homeowner",
            data={
                "job_id": str(job.public_id),
                "application_id": str(application.public_id),
                "handyman_id": str(application.handyman.public_id),
            },
            triggered_by=homeowner,
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
            triggered_by=homeowner,
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
            triggered_by=handyman,
        )

        logger.info(f"Withdrew application {application.public_id}")

        return application

    @transaction.atomic
    def update_application(
        self,
        handyman,
        application: JobApplication,
        predicted_hours=None,
        estimated_total_price=None,
        negotiation_reasoning=None,
        materials_data=None,
        attachments=None,
        attachments_to_remove=None,
    ) -> JobApplication:
        """
        Update a job application.

        Args:
            handyman: User (handyman) updating
            application: Application to update
            predicted_hours: Updated predicted hours (optional)
            estimated_total_price: Updated price (optional)
            negotiation_reasoning: Updated reasoning (optional)
            materials_data: Updated materials list (optional, replaces existing)
            attachments: New attachments to add (optional)
            attachments_to_remove: List of attachment public_ids to remove (optional)

        Returns:
            JobApplication: Updated application

        Raises:
            ValidationError: If update is invalid
        """
        # Validate handyman owns the application
        if application.handyman != handyman:
            raise ValidationError("You can only update your own applications.")

        # Validate application is pending
        if application.status != "pending":
            raise ValidationError("Only pending applications can be updated.")

        # Update application fields if provided
        if predicted_hours is not None:
            application.predicted_hours = predicted_hours

        if estimated_total_price is not None:
            application.estimated_total_price = estimated_total_price

        if negotiation_reasoning is not None:
            application.negotiation_reasoning = negotiation_reasoning

        application.save(
            update_fields=[
                "predicted_hours",
                "estimated_total_price",
                "negotiation_reasoning",
                "updated_at",
            ]
        )

        # Update materials if provided (replace all)
        if materials_data is not None:
            # Delete existing materials
            application.materials.all().delete()
            # Create new materials
            for material_data in materials_data:
                JobApplicationMaterial.objects.create(
                    application=application,
                    name=material_data["name"],
                    price=material_data["price"],
                    description=material_data.get("description", ""),
                )

        # Remove attachments if specified
        if attachments_to_remove:
            JobApplicationAttachment.objects.filter(
                application=application,
                public_id__in=attachments_to_remove,
            ).delete()

        # Add new attachments
        if attachments:
            for attachment_data in attachments:
                # Handle new indexed format (dict with file, file_type, thumbnail, duration)
                if isinstance(attachment_data, dict):
                    file = attachment_data.get("file")
                    file_type = attachment_data.get("file_type", "image")
                    thumbnail = attachment_data.get("thumbnail")
                    duration_seconds = attachment_data.get("duration_seconds")
                else:
                    # Legacy: plain file object
                    file = attachment_data
                    content_type = getattr(file, "content_type", "")
                    file_type = get_file_type_from_mime(content_type) or "image"
                    thumbnail = None
                    duration_seconds = None

                JobApplicationAttachment.objects.create(
                    application=application,
                    file=file,
                    file_type=file_type,
                    file_name=getattr(file, "name", ""),
                    file_size=getattr(file, "size", 0),
                    thumbnail=thumbnail,
                    duration_seconds=duration_seconds,
                )

        logger.info(f"Updated application {application.public_id}")

        return application


# Global job application service instance
job_application_service = JobApplicationService()


# ========================
# Ongoing Job Services
# ========================


class WorkSessionService:
    """Business logic for work sessions."""

    @transaction.atomic
    def start_session(
        self,
        handyman,
        job,
        started_at,
        start_latitude,
        start_longitude,
        start_photo,
        start_accuracy=None,
    ):
        if job.assigned_handyman != handyman:
            raise ValidationError("You are not assigned to this job.")

        if job.status not in ("in_progress", "pending_completion"):
            raise ValidationError("Job is not active for work sessions.")

        has_active = WorkSession.objects.filter(
            job=job, handyman=handyman, status="in_progress"
        ).exists()
        if has_active:
            raise ValidationError("You already have an active session for this job.")

        session = WorkSession.objects.create(
            job=job,
            handyman=handyman,
            started_at=started_at,
            start_latitude=start_latitude,
            start_longitude=start_longitude,
            start_accuracy=start_accuracy,
            start_photo=start_photo,
            status="in_progress",
        )

        notification_service.create_and_send_notification(
            user=job.homeowner,
            notification_type="work_session_started",
            title=f"Work started for {job.title}",
            body=f"{handyman.handyman_profile.display_name} started a session.",
            target_role="homeowner",
            data={"job_id": str(job.public_id), "session_id": str(session.public_id)},
            triggered_by=handyman,
        )

        logger.info("Work session %s started", session.public_id)
        return session

    @transaction.atomic
    def stop_session(
        self,
        session,
        ended_at,
        end_latitude,
        end_longitude,
        end_photo,
        end_accuracy=None,
    ):
        if session.status != "in_progress":
            raise ValidationError("Session is not active.")

        if ended_at <= session.started_at:
            raise ValidationError("End time must be after start time.")

        session.ended_at = ended_at
        session.end_latitude = end_latitude
        session.end_longitude = end_longitude
        session.end_accuracy = end_accuracy
        session.end_photo = end_photo
        session.status = "completed"
        session.save(
            update_fields=[
                "ended_at",
                "end_latitude",
                "end_longitude",
                "end_accuracy",
                "end_photo",
                "status",
                "updated_at",
            ]
        )

        notification_service.create_and_send_notification(
            user=session.job.homeowner,
            notification_type="work_session_ended",
            title=f"Work session ended for {session.job.title}",
            body="A work session has been completed.",
            target_role="homeowner",
            data={
                "job_id": str(session.job.public_id),
                "session_id": str(session.public_id),
            },
            triggered_by=session.handyman,
        )

        logger.info("Work session %s stopped", session.public_id)
        return session

    @transaction.atomic
    def add_media(
        self,
        work_session,
        media_type,
        file,
        file_size,
        description="",
        task=None,
        thumbnail=None,
        duration_seconds=None,
    ):
        # Validate task belongs to the job if provided
        if task is not None and task.job_id != work_session.job_id:
            raise ValidationError("Task does not belong to this job.")

        media = WorkSessionMedia.objects.create(
            work_session=work_session,
            media_type=media_type,
            file=file,
            thumbnail=thumbnail,
            description=description,
            task=task,
            file_size=file_size,
            duration_seconds=duration_seconds,
        )

        notification_service.create_and_send_notification(
            user=work_session.job.homeowner,
            notification_type="work_session_media_uploaded",
            title=f"New media for {work_session.job.title}",
            body="A new photo or video was added to the session.",
            target_role="homeowner",
            data={
                "job_id": str(work_session.job.public_id),
                "session_id": str(work_session.public_id),
                "media_id": str(media.public_id),
            },
            triggered_by=work_session.handyman,
        )

        logger.info("Media %s uploaded for session %s", media.public_id, work_session)
        return media


class DailyReportService:
    """Business logic for daily reports."""

    @transaction.atomic
    def submit_report(
        self,
        handyman,
        job,
        report_date,
        summary,
        total_work_duration,
        task_entries=None,
    ):
        if job.assigned_handyman != handyman:
            raise ValidationError("You are not assigned to this job.")

        if job.status not in ("in_progress", "pending_completion"):
            raise ValidationError("Job is not active for reporting.")

        exists = DailyReport.objects.filter(job=job, report_date=report_date).exists()
        if exists:
            raise ValidationError("A report for this date already exists.")

        report = DailyReport.objects.create(
            job=job,
            handyman=handyman,
            report_date=report_date,
            summary=summary,
            total_work_duration=total_work_duration,
            review_deadline=timezone.now() + timedelta(days=3),
        )

        tasks = task_entries or []
        for entry in tasks:
            task = entry.get("task")
            if not isinstance(task, JobTask):
                continue
            # Validate task belongs to this job
            if task.job_id != job.id:
                raise ValidationError(
                    f"Task '{task.title}' does not belong to this job."
                )
            DailyReportTask.objects.create(
                daily_report=report,
                task=task,
                notes=entry.get("notes", ""),
                marked_complete=entry.get("marked_complete", False),
            )
            if entry.get("marked_complete"):
                task.is_completed = True
                task.completed_by = handyman
                task.completed_at = timezone.now()
                task.save(
                    update_fields=[
                        "is_completed",
                        "completed_by",
                        "completed_at",
                        "updated_at",
                    ]
                )

        notification_service.create_and_send_notification(
            user=job.homeowner,
            notification_type="daily_report_submitted",
            title=f"Daily report for {job.title}",
            body="A new daily report is ready for review.",
            target_role="homeowner",
            data={"job_id": str(job.public_id), "report_id": str(report.public_id)},
            triggered_by=handyman,
        )

        logger.info("Daily report %s submitted", report.public_id)
        return report

    @transaction.atomic
    def review_report(self, homeowner, report, decision, comment=""):
        if report.job.homeowner != homeowner:
            raise ValidationError("You can only review your own job reports.")

        if report.status != "pending":
            raise ValidationError("Only pending reports can be reviewed.")

        if decision not in ("approved", "rejected"):
            raise ValidationError("Invalid decision.")

        report.status = decision
        report.homeowner_comment = comment
        report.reviewed_by = homeowner
        report.reviewed_at = timezone.now()
        report.save(
            update_fields=[
                "status",
                "homeowner_comment",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ]
        )

        notification_type = (
            "daily_report_approved"
            if decision == "approved"
            else "daily_report_rejected"
        )

        notification_service.create_and_send_notification(
            user=report.handyman,
            notification_type=notification_type,
            title=f"Daily report {decision}",
            body=f"Your report for {report.report_date} was {decision}.",
            target_role="handyman",
            data={
                "job_id": str(report.job.public_id),
                "report_id": str(report.public_id),
            },
            triggered_by=homeowner,
        )

        logger.info("Daily report %s reviewed as %s", report.public_id, decision)
        return report

    @transaction.atomic
    def update_report(
        self,
        handyman,
        report,
        summary=None,
        total_work_duration=None,
        task_entries=None,
    ):
        if report.handyman != handyman:
            raise ValidationError("You can only edit your own reports.")

        if report.status not in ("pending", "rejected"):
            raise ValidationError("Only pending or rejected reports can be edited.")

        if report.status == "rejected":
            report.status = "pending"
            report.reviewed_by = None
            report.reviewed_at = None
            report.homeowner_comment = ""
            report.save(
                update_fields=[
                    "status",
                    "reviewed_by",
                    "reviewed_at",
                    "homeowner_comment",
                    "updated_at",
                ]
            )

        if summary is not None:
            report.summary = summary

        if total_work_duration is not None:
            report.total_work_duration = total_work_duration

        report.save(update_fields=["summary", "total_work_duration", "updated_at"])

        if task_entries is not None:
            existing_tasks = list(report.tasks_worked.all())
            existing_task_ids = {et.task_id for et in existing_tasks}

            new_task_ids = set()
            for entry in task_entries:
                task = entry.get("task")
                if isinstance(task, JobTask):
                    new_task_ids.add(task.id)

                    if task.id in existing_task_ids:
                        existing_entry = next(
                            et for et in existing_tasks if et.task_id == task.id
                        )
                        if existing_entry.notes != entry.get(
                            "notes", ""
                        ) or existing_entry.marked_complete != entry.get(
                            "marked_complete", False
                        ):
                            existing_entry.notes = entry.get("notes", "")
                            existing_entry.marked_complete = entry.get(
                                "marked_complete", False
                            )
                            existing_entry.save(
                                update_fields=["notes", "marked_complete", "updated_at"]
                            )
                    else:
                        DailyReportTask.objects.create(
                            daily_report=report,
                            task=task,
                            notes=entry.get("notes", ""),
                            marked_complete=entry.get("marked_complete", False),
                        )

                    if entry.get("marked_complete"):
                        task.is_completed = True
                        task.completed_by = handyman
                        task.completed_at = timezone.now()
                        task.save(
                            update_fields=[
                                "is_completed",
                                "completed_by",
                                "completed_at",
                                "updated_at",
                            ]
                        )
                    else:
                        task.is_completed = False
                        task.completed_by = None
                        task.completed_at = None
                        task.save(
                            update_fields=[
                                "is_completed",
                                "completed_by",
                                "completed_at",
                                "updated_at",
                            ]
                        )

            for existing_entry in existing_tasks:
                if existing_entry.task_id not in new_task_ids:
                    task = existing_entry.task
                    task.is_completed = False
                    task.completed_by = None
                    task.completed_at = None
                    task.save(
                        update_fields=[
                            "is_completed",
                            "completed_by",
                            "completed_at",
                            "updated_at",
                        ]
                    )
                    existing_entry.delete()

        notification_service.create_and_send_notification(
            user=report.job.homeowner,
            notification_type="daily_report_updated",
            title=f"Daily report updated for {report.job.title}",
            body=f"The daily report for {report.report_date} has been updated.",
            target_role="homeowner",
            data={
                "job_id": str(report.job.public_id),
                "report_id": str(report.public_id),
            },
            triggered_by=handyman,
        )

        logger.info("Daily report %s updated", report.public_id)
        return report


class JobCompletionService:
    """Business logic for job completion flow."""

    @transaction.atomic
    def request_completion(self, handyman, job):
        if job.assigned_handyman != handyman:
            raise ValidationError("You are not assigned to this job.")

        if job.status != "in_progress":
            raise ValidationError("Completion can only be requested in progress.")

        job.status = "pending_completion"
        job.completion_requested_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "completion_requested_at",
                "updated_at",
                "status_at",
            ]
        )

        notification_service.create_and_send_notification(
            user=job.homeowner,
            notification_type="job_completion_requested",
            title=f"Completion requested for {job.title}",
            body="Handyman requested to mark the job as completed.",
            target_role="homeowner",
            data={"job_id": str(job.public_id)},
            triggered_by=handyman,
        )

        logger.info("Job %s completion requested", job.public_id)
        return job

    @transaction.atomic
    def approve_completion(self, homeowner, job):
        if job.homeowner != homeowner:
            raise ValidationError("You can only approve your own job.")

        if job.status != "pending_completion":
            raise ValidationError("Job is not awaiting completion approval.")

        job.status = "completed"
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "completed_at", "updated_at", "status_at"])

        notification_service.create_and_send_notification(
            user=job.assigned_handyman,
            notification_type="job_completion_approved",
            title="Job completed",
            body=f"{job.title} was marked completed.",
            target_role="handyman",
            data={"job_id": str(job.public_id)},
            triggered_by=homeowner,
        )

        logger.info("Job %s completion approved", job.public_id)
        return job

    @transaction.atomic
    def reject_completion(self, homeowner, job, reason=""):
        if job.homeowner != homeowner:
            raise ValidationError("You can only reject your own job.")

        if job.status != "pending_completion":
            raise ValidationError("Job is not awaiting completion approval.")

        job.status = "in_progress"
        job.completion_requested_at = None
        job.save(
            update_fields=[
                "status",
                "completion_requested_at",
                "updated_at",
                "status_at",
            ]
        )

        notification_service.create_and_send_notification(
            user=job.assigned_handyman,
            notification_type="job_completion_rejected",
            title="Completion rejected",
            body=reason or "Homeowner rejected the completion request.",
            target_role="handyman",
            data={"job_id": str(job.public_id)},
            triggered_by=homeowner,
        )

        logger.info("Job %s completion rejected", job.public_id)
        return job


class DisputeService:
    """Business logic for disputes."""

    @transaction.atomic
    def open_dispute(self, homeowner, job, reason, disputed_reports=None):
        if job.homeowner != homeowner:
            raise ValidationError("You can only dispute your own job.")

        if job.status not in ("pending_completion", "completed", "in_progress"):
            raise ValidationError("Job is not eligible for dispute.")

        dispute = JobDispute.objects.create(
            job=job,
            initiated_by=homeowner,
            reason=reason,
            resolution_deadline=timezone.now() + timedelta(days=3),
        )

        reports = disputed_reports or []
        if reports:
            dispute.disputed_reports.set(reports)

        notification_service.create_and_send_notification(
            user=job.assigned_handyman,
            notification_type="job_dispute_opened",
            title=f"Dispute opened for {job.title}",
            body="Homeowner opened a dispute.",
            target_role="handyman",
            data={"job_id": str(job.public_id), "dispute_id": str(dispute.public_id)},
            triggered_by=homeowner,
        )

        logger.info("Dispute %s opened", dispute.public_id)
        return dispute

    @transaction.atomic
    def resolve_dispute(
        self,
        admin_user,
        dispute,
        status,
        refund_percentage=None,
        admin_notes="",
    ):
        if status not in (
            "resolved_full_refund",
            "resolved_partial_refund",
            "resolved_pay_handyman",
            "cancelled",
        ):
            raise ValidationError("Invalid resolution status.")

        dispute.status = status
        dispute.resolved_by = admin_user
        dispute.resolved_at = timezone.now()
        dispute.admin_notes = admin_notes
        dispute.refund_percentage = refund_percentage
        dispute.save(
            update_fields=[
                "status",
                "resolved_by",
                "resolved_at",
                "admin_notes",
                "refund_percentage",
                "updated_at",
            ]
        )

        notification_service.create_and_send_notification(
            user=dispute.job.homeowner,
            notification_type="job_dispute_resolved",
            title="Dispute resolved",
            body="Your dispute has been resolved.",
            target_role="homeowner",
            data={
                "job_id": str(dispute.job.public_id),
                "dispute_id": str(dispute.public_id),
            },
            triggered_by=admin_user,
        )
        if dispute.job.assigned_handyman:
            notification_service.create_and_send_notification(
                user=dispute.job.assigned_handyman,
                notification_type="job_dispute_resolved",
                title="Dispute resolved",
                body="A dispute was resolved for your job.",
                target_role="handyman",
                data={
                    "job_id": str(dispute.job.public_id),
                    "dispute_id": str(dispute.public_id),
                },
                triggered_by=admin_user,
            )

        logger.info("Dispute %s resolved as %s", dispute.public_id, status)
        return dispute


class ReviewService:
    """Business logic for job reviews."""

    REVIEW_WINDOW_DAYS = 14

    def can_review(self, user, job, reviewer_type) -> tuple[bool, str]:
        """
        Check if user can review this job.

        Args:
            user: User attempting to review
            job: Job to review
            reviewer_type: "homeowner" or "handyman"

        Returns:
            tuple[bool, str]: (can_review, error_message)
        """
        # Check job is completed
        if job.status != "completed":
            return False, "Reviews can only be submitted for completed jobs."

        # Check reviewer is the correct party
        if reviewer_type == "homeowner":
            if job.homeowner != user:
                return False, "You can only review jobs you posted."
        elif reviewer_type == "handyman":
            if job.assigned_handyman != user:
                return False, "You can only review jobs you were assigned to."
        else:
            return False, "Invalid reviewer type."

        # Check within review window
        if not self.is_within_review_window(job):
            return False, "The 14-day review window has expired."

        # Check if already reviewed
        existing_review = Review.objects.filter(
            job=job, reviewer_type=reviewer_type
        ).first()
        if existing_review:
            return False, "You have already reviewed this job."

        return True, ""

    def is_within_review_window(self, job) -> bool:
        """Check if job is still within the 14-day review window."""
        if job.completed_at is None:
            return False
        review_deadline = job.completed_at + timedelta(days=self.REVIEW_WINDOW_DAYS)
        return timezone.now() <= review_deadline

    def can_edit_review(self, user, review) -> tuple[bool, str]:
        """
        Check if user can edit this review.

        Args:
            user: User attempting to edit
            review: Review to edit

        Returns:
            tuple[bool, str]: (can_edit, error_message)
        """
        # Check user owns the review
        if review.reviewer != user:
            return False, "You can only edit your own reviews."

        # Check within review window
        if not self.is_within_review_window(review.job):
            return False, "The 14-day edit window has expired."

        return True, ""

    @transaction.atomic
    def create_review(
        self, user, job, reviewer_type: str, rating: int, comment: str = ""
    ) -> Review:
        """
        Create a review and update profile rating.

        Args:
            user: User creating the review
            job: Job to review
            reviewer_type: "homeowner" or "handyman"
            rating: Rating from 1 to 5
            comment: Optional comment

        Returns:
            Review: Created review

        Raises:
            ValidationError: If review is invalid
        """
        can_review, error = self.can_review(user, job, reviewer_type)
        if not can_review:
            raise ValidationError(error)

        # Determine reviewer and reviewee
        if reviewer_type == "homeowner":
            reviewer = job.homeowner
            reviewee = job.assigned_handyman
        else:
            reviewer = job.assigned_handyman
            reviewee = job.homeowner

        review = Review.objects.create(
            job=job,
            reviewer=reviewer,
            reviewee=reviewee,
            reviewer_type=reviewer_type,
            rating=rating,
            comment=comment,
        )

        # Update profile rating
        self.update_profile_rating(reviewee, reviewer_type)

        # Send notification (only when homeowner reviews handyman)
        if reviewer_type == "homeowner":
            homeowner_profile = reviewer.homeowner_profile
            notification_service.create_and_send_notification(
                user=reviewee,
                notification_type="review_received",
                title="New review received",
                body=f"{homeowner_profile.display_name} left you a {rating}-star review for {job.title}",
                target_role="handyman",
                data={
                    "job_id": str(job.public_id),
                    "review_id": str(review.public_id),
                },
                triggered_by=reviewer,
            )

        logger.info(
            "Review %s created by %s for job %s",
            review.public_id,
            reviewer_type,
            job.public_id,
        )
        return review

    @transaction.atomic
    def update_review(self, user, review, rating: int, comment: str = "") -> Review:
        """
        Update an existing review.

        Args:
            user: User updating the review
            review: Review to update
            rating: New rating from 1 to 5
            comment: New comment

        Returns:
            Review: Updated review

        Raises:
            ValidationError: If update is invalid
        """
        can_edit, error = self.can_edit_review(user, review)
        if not can_edit:
            raise ValidationError(error)

        review.rating = rating
        review.comment = comment
        review.save(update_fields=["rating", "comment", "updated_at"])

        # Update profile rating
        self.update_profile_rating(review.reviewee, review.reviewer_type)

        logger.info("Review %s updated", review.public_id)
        return review

    def update_profile_rating(self, reviewee, reviewer_type: str):
        """
        Recalculate and update profile average rating and review_count.

        Args:
            reviewee: User who received the review
            reviewer_type: "homeowner" or "handyman" (who gave the review)
        """
        from django.db.models import Avg, Count

        # Get all reviews received by this user from the specified reviewer type
        reviews = Review.objects.filter(reviewee=reviewee, reviewer_type=reviewer_type)
        stats = reviews.aggregate(avg_rating=Avg("rating"), count=Count("id"))

        avg_rating = stats["avg_rating"]
        review_count = stats["count"]

        # Update the appropriate profile
        if reviewer_type == "homeowner":
            # Homeowners review handymen -> update handyman profile
            if hasattr(reviewee, "handyman_profile"):
                profile = reviewee.handyman_profile
                profile.rating = avg_rating
                profile.review_count = review_count
                profile.save(update_fields=["rating", "review_count", "updated_at"])
        else:
            # Handymen review homeowners -> update homeowner profile
            if hasattr(reviewee, "homeowner_profile"):
                profile = reviewee.homeowner_profile
                profile.rating = avg_rating
                profile.review_count = review_count
                profile.save(update_fields=["rating", "review_count", "updated_at"])

    def get_review_for_job(self, job, reviewer_type: str):
        """
        Get review for a job by reviewer type.

        Args:
            job: Job to get review for
            reviewer_type: "homeowner" or "handyman"

        Returns:
            Review or None
        """
        return Review.objects.filter(job=job, reviewer_type=reviewer_type).first()

    def get_reviews_received(self, user, reviewer_type: str):
        """
        Get all reviews received by a user from a specific reviewer type.

        Args:
            user: User to get reviews for
            reviewer_type: "homeowner" or "handyman" (who gave the reviews)

        Returns:
            QuerySet of reviews
        """
        return Review.objects.filter(
            reviewee=user, reviewer_type=reviewer_type
        ).select_related("job", "reviewer")


work_session_service = WorkSessionService()
daily_report_service = DailyReportService()
job_completion_service = JobCompletionService()
dispute_service = DisputeService()
review_service = ReviewService()


class ReimbursementService:
    """Business logic for job reimbursements."""

    @transaction.atomic
    def submit_reimbursement(
        self, handyman, job, name, category, amount, attachments, notes=""
    ):
        """Submit a new reimbursement request."""
        from apps.jobs.models import JobReimbursement, JobReimbursementAttachment

        # Validate handyman is assigned to job
        if job.assigned_handyman != handyman:
            raise ValidationError("You are not assigned to this job.")

        # Validate job is in progress or pending completion
        if job.status not in ("in_progress", "pending_completion"):
            raise ValidationError("Job is not active for reimbursement requests.")

        # Create reimbursement
        reimbursement = JobReimbursement.objects.create(
            job=job,
            handyman=handyman,
            name=name,
            category=category,
            amount=amount,
            notes=notes,
        )

        # Create attachments
        for attachment_data in attachments:
            # Handle new indexed format (dict with file, file_type, thumbnail, duration)
            if isinstance(attachment_data, dict):
                file = attachment_data.get("file")
                file_type = attachment_data.get("file_type", "image")
                thumbnail = attachment_data.get("thumbnail")
                duration_seconds = attachment_data.get("duration_seconds")
            else:
                # Legacy: plain file object
                file = attachment_data
                content_type = getattr(file, "content_type", "")
                file_type = get_file_type_from_mime(content_type) or "image"
                thumbnail = None
                duration_seconds = None

            JobReimbursementAttachment.objects.create(
                reimbursement=reimbursement,
                file=file,
                file_type=file_type,
                file_name=getattr(file, "name", ""),
                file_size=getattr(file, "size", 0),
                thumbnail=thumbnail,
                duration_seconds=duration_seconds,
            )

        # Send notification to homeowner
        notification_service.create_and_send_notification(
            user=job.homeowner,
            notification_type="reimbursement_submitted",
            title=f"Reimbursement request for {job.title}",
            body=f"{handyman.handyman_profile.display_name} submitted a reimbursement request of ${amount}.",
            target_role="homeowner",
            data={
                "job_id": str(job.public_id),
                "reimbursement_id": str(reimbursement.public_id),
            },
            triggered_by=handyman,
        )

        logger.info(
            "Reimbursement %s submitted for job %s",
            reimbursement.public_id,
            job.public_id,
        )
        return reimbursement

    @transaction.atomic
    def review_reimbursement(self, homeowner, reimbursement, decision, comment=""):
        """Approve or reject a reimbursement request."""
        job = reimbursement.job

        # Validate homeowner owns the job
        if job.homeowner != homeowner:
            raise ValidationError(
                "You can only review reimbursements for your own jobs."
            )

        # Validate reimbursement is pending
        if reimbursement.status != "pending":
            raise ValidationError("Only pending reimbursements can be reviewed.")

        # Validate decision
        if decision not in ("approved", "rejected"):
            raise ValidationError("Invalid decision.")

        # Update reimbursement
        reimbursement.status = decision
        reimbursement.homeowner_comment = comment
        reimbursement.reviewed_by = homeowner
        reimbursement.reviewed_at = timezone.now()
        reimbursement.save(
            update_fields=[
                "status",
                "homeowner_comment",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ]
        )

        # Send notification to handyman
        notification_type = (
            "reimbursement_approved"
            if decision == "approved"
            else "reimbursement_rejected"
        )
        notification_service.create_and_send_notification(
            user=reimbursement.handyman,
            notification_type=notification_type,
            title=f"Reimbursement {decision}",
            body=f"Your reimbursement request for {job.title} was {decision}.",
            target_role="handyman",
            data={
                "job_id": str(job.public_id),
                "reimbursement_id": str(reimbursement.public_id),
            },
            triggered_by=homeowner,
        )

        logger.info(
            "Reimbursement %s reviewed as %s", reimbursement.public_id, decision
        )
        return reimbursement

    @transaction.atomic
    def update_reimbursement(
        self,
        handyman,
        reimbursement,
        name=None,
        category=None,
        amount=None,
        notes=None,
        attachments=None,
        attachments_to_remove=None,
    ):
        """Update a pending reimbursement request."""
        from apps.jobs.models import JobReimbursementAttachment

        # Validate handyman owns the reimbursement
        if reimbursement.handyman != handyman:
            raise ValidationError("You can only edit your own reimbursements.")

        # Validate reimbursement is pending
        if reimbursement.status != "pending":
            raise ValidationError("Only pending reimbursements can be edited.")

        # Update fields if provided
        if name is not None:
            reimbursement.name = name
        if category is not None:
            reimbursement.category = category
        if amount is not None:
            reimbursement.amount = amount
        if notes is not None:
            reimbursement.notes = notes

        reimbursement.save(
            update_fields=["name", "category", "amount", "notes", "updated_at"]
        )

        # Remove attachments if specified
        if attachments_to_remove:
            JobReimbursementAttachment.objects.filter(
                reimbursement=reimbursement,
                public_id__in=attachments_to_remove,
            ).delete()

        # Add new attachments
        if attachments:
            for attachment_data in attachments:
                # Handle new indexed format (dict with file, file_type, thumbnail, duration)
                if isinstance(attachment_data, dict):
                    file = attachment_data.get("file")
                    file_type = attachment_data.get("file_type", "image")
                    thumbnail = attachment_data.get("thumbnail")
                    duration_seconds = attachment_data.get("duration_seconds")
                else:
                    # Legacy: plain file object
                    file = attachment_data
                    content_type = getattr(file, "content_type", "")
                    file_type = get_file_type_from_mime(content_type) or "image"
                    thumbnail = None
                    duration_seconds = None

                JobReimbursementAttachment.objects.create(
                    reimbursement=reimbursement,
                    file=file,
                    file_type=file_type,
                    file_name=getattr(file, "name", ""),
                    file_size=getattr(file, "size", 0),
                    thumbnail=thumbnail,
                    duration_seconds=duration_seconds,
                )

        # Ensure at least one attachment remains
        if reimbursement.attachments.count() == 0:
            raise ValidationError("At least one attachment is required.")

        logger.info("Reimbursement %s updated", reimbursement.public_id)
        return reimbursement


reimbursement_service = ReimbursementService()


class DirectOfferService:
    """
    Service for handling direct job offer business logic.
    Direct offers are private job listings sent to a specific handyman.
    """

    DEFAULT_OFFER_EXPIRY_DAYS = 7
    MIN_OFFER_EXPIRY_DAYS = 1
    MAX_OFFER_EXPIRY_DAYS = 30

    @transaction.atomic
    def create_direct_offer(
        self,
        homeowner,
        target_handyman,
        title: str,
        description: str,
        estimated_budget,
        category,
        city,
        address: str,
        postal_code: str = "",
        latitude=None,
        longitude=None,
        tasks_data=None,
        attachments=None,
        offer_expires_in_days: int = None,
    ) -> Job:
        """
        Create a direct job offer to a specific handyman.

        Args:
            homeowner: User creating the offer
            target_handyman: User (handyman) to receive the offer
            title: Job title
            description: Job description
            estimated_budget: Estimated budget
            category: JobCategory instance
            city: City instance
            address: Job address
            postal_code: Postal code (optional)
            latitude: Latitude (optional)
            longitude: Longitude (optional)
            tasks_data: List of task dicts with title, description (optional)
            attachments: List of attachment data (optional)
            offer_expires_in_days: Days until offer expires (default: 7)

        Returns:
            Job: Created direct offer job

        Raises:
            ValidationError: If creation is invalid
        """
        from apps.common.validators import get_file_type_from_mime

        # Validate homeowner has homeowner role
        if not homeowner.has_role("homeowner"):
            raise ValidationError("You must have a homeowner role to create offers.")

        # Validate homeowner has verified phone
        if not hasattr(homeowner, "homeowner_profile"):
            raise ValidationError("You must complete your homeowner profile first.")

        homeowner_profile = homeowner.homeowner_profile
        if not homeowner_profile.is_phone_verified:
            raise ValidationError(
                "You must verify your phone number to create direct offers."
            )

        # Validate target handyman
        if not target_handyman.has_role("handyman"):
            raise ValidationError("Target user must have a handyman role.")

        if not hasattr(target_handyman, "handyman_profile"):
            raise ValidationError("Target handyman has not completed their profile.")

        # Cannot send offer to yourself
        if homeowner == target_handyman:
            raise ValidationError("You cannot send a direct offer to yourself.")

        # Calculate expiration
        if offer_expires_in_days is None:
            offer_expires_in_days = self.DEFAULT_OFFER_EXPIRY_DAYS

        if not (
            self.MIN_OFFER_EXPIRY_DAYS
            <= offer_expires_in_days
            <= self.MAX_OFFER_EXPIRY_DAYS
        ):
            raise ValidationError(
                f"Offer expiry must be between {self.MIN_OFFER_EXPIRY_DAYS} "
                f"and {self.MAX_OFFER_EXPIRY_DAYS} days."
            )

        offer_expires_at = timezone.now() + timedelta(days=offer_expires_in_days)

        # Create the job as a direct offer
        job = Job.objects.create(
            homeowner=homeowner,
            title=title,
            description=description,
            estimated_budget=estimated_budget,
            category=category,
            city=city,
            address=address,
            postal_code=postal_code or "",
            latitude=latitude,
            longitude=longitude,
            status="draft",  # Direct offers start as draft
            is_direct_offer=True,
            target_handyman=target_handyman,
            offer_status="pending",
            offer_expires_at=offer_expires_at,
        )

        # Create tasks
        tasks_data = tasks_data or []
        for idx, task_data in enumerate(tasks_data):
            JobTask.objects.create(
                job=job,
                title=task_data.get("title", ""),
                description=task_data.get("description", ""),
                order=idx,
            )

        # Create attachments
        from apps.jobs.models import JobAttachment

        attachments = attachments or []
        for idx, attachment_data in enumerate(attachments):
            if isinstance(attachment_data, dict):
                file = attachment_data.get("file")
                file_type = attachment_data.get("file_type", "image")
                thumbnail = attachment_data.get("thumbnail")
                duration_seconds = attachment_data.get("duration_seconds")
            else:
                file = attachment_data
                content_type = getattr(file, "content_type", "")
                file_type = get_file_type_from_mime(content_type) or "image"
                thumbnail = None
                duration_seconds = None

            JobAttachment.objects.create(
                job=job,
                file=file,
                file_type=file_type,
                file_name=getattr(file, "name", ""),
                file_size=getattr(file, "size", 0),
                thumbnail=thumbnail,
                duration_seconds=duration_seconds,
                order=idx,
            )

        # Send notification to target handyman
        notification_service.create_and_send_notification(
            user=target_handyman,
            notification_type="direct_offer_received",
            title="New job offer!",
            body=f"{homeowner_profile.display_name} wants to hire you for: {title}",
            target_role="handyman",
            data={
                "job_id": str(job.public_id),
                "offer_type": "direct_offer",
            },
            triggered_by=homeowner,
        )

        logger.info(
            f"Created direct offer {job.public_id} from {homeowner.email} "
            f"to {target_handyman.email}"
        )

        return job

    @transaction.atomic
    def accept_offer(self, handyman, job: Job) -> Job:
        """
        Accept a direct job offer.

        Args:
            handyman: User (handyman) accepting the offer
            job: Job (direct offer) to accept

        Returns:
            Job: Updated job with in_progress status

        Raises:
            ValidationError: If acceptance is invalid
        """
        # Validate this is a direct offer
        if not job.is_direct_offer:
            raise ValidationError("This job is not a direct offer.")

        # Validate handyman is the target
        if job.target_handyman != handyman:
            raise ValidationError("You are not the target of this offer.")

        # Validate offer is pending
        if job.offer_status != "pending":
            raise ValidationError(
                f"This offer cannot be accepted. Current status: {job.offer_status}"
            )

        # Check if offer has expired
        if job.offer_expires_at and timezone.now() > job.offer_expires_at:
            raise ValidationError("This offer has expired.")

        # Accept the offer
        job.offer_status = "accepted"
        job.offer_responded_at = timezone.now()
        job.status = "in_progress"
        job.assigned_handyman = handyman
        job.save(
            update_fields=[
                "offer_status",
                "offer_responded_at",
                "status",
                "status_at",
                "assigned_handyman",
                "updated_at",
            ]
        )

        # Notify homeowner
        handyman_profile = handyman.handyman_profile
        notification_service.create_and_send_notification(
            user=job.homeowner,
            notification_type="direct_offer_accepted",
            title="Offer accepted!",
            body=f"{handyman_profile.display_name} has accepted your job offer: {job.title}",
            target_role="homeowner",
            data={
                "job_id": str(job.public_id),
                "handyman_id": str(handyman.public_id),
            },
            triggered_by=handyman,
        )

        logger.info(f"Direct offer {job.public_id} accepted by {handyman.email}")

        return job

    @transaction.atomic
    def reject_offer(self, handyman, job: Job, rejection_reason: str = "") -> Job:
        """
        Reject a direct job offer.

        Args:
            handyman: User (handyman) rejecting the offer
            job: Job (direct offer) to reject
            rejection_reason: Optional reason for rejection

        Returns:
            Job: Updated job with rejected status

        Raises:
            ValidationError: If rejection is invalid
        """
        # Validate this is a direct offer
        if not job.is_direct_offer:
            raise ValidationError("This job is not a direct offer.")

        # Validate handyman is the target
        if job.target_handyman != handyman:
            raise ValidationError("You are not the target of this offer.")

        # Validate offer is pending
        if job.offer_status != "pending":
            raise ValidationError(
                f"This offer cannot be rejected. Current status: {job.offer_status}"
            )

        # Reject the offer
        job.offer_status = "rejected"
        job.offer_responded_at = timezone.now()
        job.offer_rejection_reason = rejection_reason or ""
        job.save(
            update_fields=[
                "offer_status",
                "offer_responded_at",
                "offer_rejection_reason",
                "updated_at",
            ]
        )

        # Notify homeowner
        handyman_profile = handyman.handyman_profile
        notification_service.create_and_send_notification(
            user=job.homeowner,
            notification_type="direct_offer_rejected",
            title="Offer declined",
            body=f"{handyman_profile.display_name} has declined your job offer: {job.title}",
            target_role="homeowner",
            data={
                "job_id": str(job.public_id),
                "handyman_id": str(handyman.public_id),
            },
            triggered_by=handyman,
        )

        logger.info(f"Direct offer {job.public_id} rejected by {handyman.email}")

        return job

    @transaction.atomic
    def cancel_offer(self, homeowner, job: Job) -> Job:
        """
        Cancel a direct job offer (by homeowner).

        Args:
            homeowner: User (homeowner) cancelling the offer
            job: Job (direct offer) to cancel

        Returns:
            Job: Updated job with cancelled status

        Raises:
            ValidationError: If cancellation is invalid
        """
        # Validate this is a direct offer
        if not job.is_direct_offer:
            raise ValidationError("This job is not a direct offer.")

        # Validate homeowner owns the job
        if job.homeowner != homeowner:
            raise ValidationError("You can only cancel your own offers.")

        # Validate offer is pending
        if job.offer_status != "pending":
            raise ValidationError(
                f"This offer cannot be cancelled. Current status: {job.offer_status}"
            )

        # Cancel the offer
        job.offer_status = "expired"  # Use expired for cancelled by homeowner
        job.status = "cancelled"
        job.save(
            update_fields=[
                "offer_status",
                "status",
                "status_at",
                "updated_at",
            ]
        )

        # Notify target handyman
        notification_service.create_and_send_notification(
            user=job.target_handyman,
            notification_type="direct_offer_cancelled",
            title="Offer cancelled",
            body=f"The job offer for '{job.title}' has been cancelled by the homeowner.",
            target_role="handyman",
            data={
                "job_id": str(job.public_id),
            },
            triggered_by=homeowner,
        )

        logger.info(f"Direct offer {job.public_id} cancelled by {homeowner.email}")

        return job

    @transaction.atomic
    def convert_to_public(self, homeowner, job: Job) -> Job:
        """
        Convert a rejected/expired direct offer to a public job listing.

        Args:
            homeowner: User (homeowner) converting the offer
            job: Job (direct offer) to convert

        Returns:
            Job: Updated job as public listing

        Raises:
            ValidationError: If conversion is invalid
        """
        # Validate this is a direct offer
        if not job.is_direct_offer:
            raise ValidationError("This job is not a direct offer.")

        # Validate homeowner owns the job
        if job.homeowner != homeowner:
            raise ValidationError("You can only convert your own offers.")

        # Validate offer status allows conversion
        if job.offer_status not in ("rejected", "expired"):
            raise ValidationError(
                "Only rejected or expired offers can be converted to public listings."
            )

        # Convert to public job
        job.is_direct_offer = False
        job.offer_status = "converted"
        job.status = "open"
        # Keep target_handyman for reference but clear assignment
        job.assigned_handyman = None
        job.save(
            update_fields=[
                "is_direct_offer",
                "offer_status",
                "status",
                "status_at",
                "assigned_handyman",
                "updated_at",
            ]
        )

        logger.info(
            f"Direct offer {job.public_id} converted to public listing by {homeowner.email}"
        )

        return job

    def expire_pending_offers(self) -> int:
        """
        Expire all pending offers that have passed their expiration date.
        This should be called by a scheduled task/cron job.

        Returns:
            int: Number of offers expired
        """
        expired_offers = Job.objects.filter(
            is_direct_offer=True,
            offer_status="pending",
            offer_expires_at__lt=timezone.now(),
        )

        count = expired_offers.count()

        for job in expired_offers:
            job.offer_status = "expired"
            job.save(update_fields=["offer_status", "updated_at"])

            # Notify homeowner
            notification_service.create_and_send_notification(
                user=job.homeowner,
                notification_type="direct_offer_expired",
                title="Offer expired",
                body=f"Your job offer '{job.title}' has expired without a response.",
                target_role="homeowner",
                data={
                    "job_id": str(job.public_id),
                },
                triggered_by=None,
            )

            # Notify handyman
            notification_service.create_and_send_notification(
                user=job.target_handyman,
                notification_type="direct_offer_expired",
                title="Offer expired",
                body=f"The job offer '{job.title}' has expired.",
                target_role="handyman",
                data={
                    "job_id": str(job.public_id),
                },
                triggered_by=None,
            )

        if count > 0:
            logger.info(f"Expired {count} pending direct offers")

        return count


direct_offer_service = DirectOfferService()
