"""
Service for managing job applications.
"""

import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.jobs.models import (
    DailyReport,
    DailyReportTask,
    Job,
    JobApplication,
    JobDispute,
    JobTask,
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
        session.status = "completed"
        session.save(
            update_fields=[
                "ended_at",
                "end_latitude",
                "end_longitude",
                "end_accuracy",
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


work_session_service = WorkSessionService()
daily_report_service = DailyReportService()
job_completion_service = JobCompletionService()
dispute_service = DisputeService()
