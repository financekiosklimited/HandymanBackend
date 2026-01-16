"""
Service for managing chat conversations and messages.
"""

import logging
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.chat.models import ChatConversation, ChatMessage, ChatMessageAttachment
from apps.common.constants import (
    ATTACHMENT_TYPE_IMAGE,
    ATTACHMENT_TYPE_VIDEO,
    MAX_CHAT_ATTACHMENTS,
    MAX_IMAGE_SIZE,
    MAX_VIDEO_SIZE,
)
from apps.common.validators import get_file_type_from_mime
from apps.jobs.models import Job
from apps.notifications.services import notification_service

logger = logging.getLogger(__name__)

# Configuration constants
THUMBNAIL_SIZE = (300, 300)
MAX_MESSAGE_LENGTH = 2000


class ChatService:
    """
    Service for chat operations including conversations and messages.
    """

    def get_or_create_job_conversation(self, job, user, user_role):
        """
        Get or create a chat conversation for a job.
        Only allowed when job is in_progress.

        Args:
            job: Job instance
            user: Current user
            user_role: Role of the user (homeowner or handyman)

        Returns:
            tuple: (ChatConversation, created: bool)

        Raises:
            ValueError: If job is not in_progress or user is not authorized
        """
        # Validate job status
        if job.status != "in_progress":
            raise ValueError("Chat is only available for jobs in progress.")

        # Validate user authorization
        if user_role == "homeowner" and job.homeowner != user:
            raise ValueError("You are not authorized to access this chat.")
        if user_role == "handyman" and job.assigned_handyman != user:
            raise ValueError("You are not authorized to access this chat.")

        # Get or create conversation
        conversation, created = ChatConversation.objects.get_or_create(
            job=job,
            conversation_type=ChatConversation.ConversationType.JOB,
            defaults={
                "homeowner": job.homeowner,
                "handyman": job.assigned_handyman,
            },
        )

        if created:
            logger.info(
                f"Created chat conversation {conversation.public_id} for job {job.public_id}"
            )

        return conversation, created

    def get_conversation_by_public_id(self, public_id, user, user_role):
        """
        Get a conversation by public_id with authorization check.

        Args:
            public_id: UUID of the conversation
            user: Current user
            user_role: Role of the user (homeowner or handyman)

        Returns:
            ChatConversation

        Raises:
            ChatConversation.DoesNotExist: If not found or not authorized
        """
        filters = {"public_id": public_id}

        if user_role == "homeowner":
            filters["homeowner"] = user
        else:
            filters["handyman"] = user

        return ChatConversation.objects.get(**filters)

    def get_conversations_for_user(self, user, user_role, conversation_type=None):
        """
        Get all conversations for a user.

        Args:
            user: Current user
            user_role: Role of the user (homeowner or handyman)
            conversation_type: Optional filter by conversation type

        Returns:
            QuerySet of ChatConversation
        """
        if user_role == "homeowner":
            queryset = ChatConversation.objects.filter(homeowner=user)
        else:
            queryset = ChatConversation.objects.filter(handyman=user)

        if conversation_type:
            queryset = queryset.filter(conversation_type=conversation_type)

        return queryset.select_related("job", "homeowner", "handyman").order_by(
            "-last_message_at", "-created_at"
        )

    def get_messages_for_conversation(self, conversation, limit=50, before=None):
        """
        Get messages for a conversation with pagination.

        Args:
            conversation: ChatConversation instance
            limit: Number of messages to return
            before: Get messages before this message public_id

        Returns:
            QuerySet of ChatMessage
        """
        queryset = (
            ChatMessage.objects.filter(conversation=conversation)
            .select_related("sender")
            .prefetch_related("attachments")
        )

        if before:
            try:
                before_message = ChatMessage.objects.get(public_id=before)
                queryset = queryset.filter(created_at__lt=before_message.created_at)
            except ChatMessage.DoesNotExist:
                pass

        # Order by created_at ascending (oldest first)
        return queryset.order_by("created_at")[:limit]

    @transaction.atomic
    def send_message(
        self,
        conversation,
        sender,
        sender_role,
        content="",
        attachments=None,
    ):
        """
        Send a message in a conversation.

        Args:
            conversation: ChatConversation instance
            sender: User sending the message
            sender_role: Role of sender (homeowner or handyman)
            content: Text content of the message
            attachments: List of dicts with keys:
                - file: The uploaded file
                - file_type: 'image' or 'video'
                - thumbnail: Optional thumbnail file (required for videos)
                - duration_seconds: Optional video duration (required for videos)

        Returns:
            ChatMessage

        Raises:
            ValueError: If conversation is archived, content too long,
                        or too many attachments
        """
        # Validate conversation is active
        if conversation.status == ChatConversation.Status.ARCHIVED:
            raise ValueError("Cannot send messages to archived conversations.")

        # For job conversations, check job status
        if (
            conversation.conversation_type == ChatConversation.ConversationType.JOB
            and conversation.job
        ):
            if conversation.job.status != "in_progress":
                raise ValueError("Chat is only available for jobs in progress.")

        # Validate content
        content = content.strip() if content else ""
        attachments = attachments or []

        if not content and not attachments:
            raise ValueError("Message must have content or attachments.")

        if len(content) > MAX_MESSAGE_LENGTH:
            raise ValueError(
                f"Message content cannot exceed {MAX_MESSAGE_LENGTH} characters."
            )

        if len(attachments) > MAX_CHAT_ATTACHMENTS:
            raise ValueError(f"Cannot attach more than {MAX_CHAT_ATTACHMENTS} files.")

        # Validate attachment sizes
        for attachment_data in attachments:
            # Handle new indexed format (dict with file, file_type, thumbnail, duration)
            if isinstance(attachment_data, dict):
                file = attachment_data.get("file")
                file_type = attachment_data.get("file_type", ATTACHMENT_TYPE_IMAGE)
            # Handle legacy tuple format (file, file_type)
            elif isinstance(attachment_data, tuple):
                file, file_type = attachment_data
            else:
                file = attachment_data
                content_type = getattr(file, "content_type", "")
                file_type = (
                    get_file_type_from_mime(content_type) or ATTACHMENT_TYPE_IMAGE
                )

            if file_type == ATTACHMENT_TYPE_VIDEO:
                if file.size > MAX_VIDEO_SIZE:
                    raise ValueError(
                        f"Video size cannot exceed {MAX_VIDEO_SIZE // (1024 * 1024)}MB."
                    )
            else:
                if file.size > MAX_IMAGE_SIZE:
                    raise ValueError(
                        f"Image size cannot exceed {MAX_IMAGE_SIZE // (1024 * 1024)}MB."
                    )

        # Determine message type
        if content and attachments:
            message_type = ChatMessage.MessageType.TEXT_WITH_ATTACHMENT
        elif attachments:
            message_type = ChatMessage.MessageType.ATTACHMENT
        else:
            message_type = ChatMessage.MessageType.TEXT

        # Create message
        message = ChatMessage.objects.create(
            conversation=conversation,
            sender=sender,
            sender_role=sender_role,
            message_type=message_type,
            content=content,
        )

        # Process and save attachments
        for order, attachment_data in enumerate(attachments):
            # Handle new indexed format (dict with file, file_type, thumbnail, duration)
            if isinstance(attachment_data, dict):
                file = attachment_data.get("file")
                file_type = attachment_data.get("file_type", ATTACHMENT_TYPE_IMAGE)
                thumbnail = attachment_data.get("thumbnail")
                duration_seconds = attachment_data.get("duration_seconds")
            # Handle legacy tuple format (file, file_type)
            elif isinstance(attachment_data, tuple):
                file, file_type = attachment_data
                thumbnail = None
                duration_seconds = None
            else:
                file = attachment_data
                content_type = getattr(file, "content_type", "")
                file_type = (
                    get_file_type_from_mime(content_type) or ATTACHMENT_TYPE_IMAGE
                )
                thumbnail = None
                duration_seconds = None

            self._save_message_attachment(
                message, file, file_type, order, thumbnail, duration_seconds
            )

        # Update conversation metadata
        now = timezone.now()
        conversation.last_message_at = now

        # Increment unread count for recipient
        if sender_role == "homeowner":
            conversation.handyman_unread_count = models.F("handyman_unread_count") + 1
        else:
            conversation.homeowner_unread_count = models.F("homeowner_unread_count") + 1

        conversation.save(
            update_fields=[
                "last_message_at",
                "homeowner_unread_count",
                "handyman_unread_count",
                "updated_at",
            ]
        )

        # Refresh to get actual count values
        conversation.refresh_from_db()

        # Send push notification to recipient
        self._send_message_notification(message, conversation, sender_role)

        logger.info(
            f"Sent message {message.public_id} in conversation {conversation.public_id}"
        )

        return message

    def _save_message_attachment(
        self, message, file, file_type, order, thumbnail=None, duration_seconds=None
    ):
        """
        Save an attachment with thumbnail for images.

        Args:
            message: ChatMessage instance
            file: Uploaded file
            file_type: 'image' or 'video'
            order: Attachment order
            thumbnail: Client-provided thumbnail file (for videos)
            duration_seconds: Video duration in seconds
        """
        # Create ChatMessageAttachment
        attachment = ChatMessageAttachment(
            message=message,
            file_type=file_type,
            file_name=getattr(file, "name", ""),
            file_size=getattr(file, "size", 0),
            order=order,
            duration_seconds=duration_seconds,
        )

        # Save the file
        attachment.file.save(file.name, file, save=False)

        # Handle thumbnail
        if file_type == ATTACHMENT_TYPE_VIDEO and thumbnail:
            # Use client-provided thumbnail for videos
            thumb_name = f"thumb_{thumbnail.name}"
            attachment.thumbnail.save(thumb_name, thumbnail, save=False)
        elif file_type == ATTACHMENT_TYPE_IMAGE:
            # Generate thumbnail for images server-side
            try:
                file.seek(0)
                img = Image.open(file)

                # Convert to RGB if necessary (for PNG with transparency)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # Create thumbnail
                img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

                # Save thumbnail to BytesIO
                thumb_io = BytesIO()
                img.save(thumb_io, format="JPEG", quality=85)
                thumb_io.seek(0)

                # Generate thumbnail filename
                thumb_name = f"thumb_{file.name.rsplit('.', 1)[0]}.jpg"
                attachment.thumbnail.save(
                    thumb_name,
                    ContentFile(thumb_io.getvalue()),
                    save=False,
                )
            except Exception as e:
                logger.warning(f"Failed to generate thumbnail: {e}")
                # Continue without thumbnail

        attachment.save()

    def _send_message_notification(self, message, conversation, sender_role):
        """
        Send push notification for new message.

        Args:
            message: ChatMessage instance
            conversation: ChatConversation instance
            sender_role: Role of the sender
        """
        # Determine recipient
        if sender_role == "homeowner":
            recipient = conversation.handyman
            recipient_role = "handyman"
            sender_name = self._get_display_name(conversation.homeowner, "homeowner")
        else:
            recipient = conversation.homeowner
            recipient_role = "homeowner"
            sender_name = self._get_display_name(conversation.handyman, "handyman")

        # Prepare notification content
        title = f"New message from {sender_name}"
        if message.content:
            body = (
                message.content[:100] + "..."
                if len(message.content) > 100
                else message.content
            )
        else:
            body = "Sent an attachment"

        # Prepare data payload
        data = {
            "type": "chat_message",
            "conversation_id": str(conversation.public_id),
            "message_id": str(message.public_id),
        }

        if conversation.job:
            data["job_id"] = str(conversation.job.public_id)

        # Send notification
        try:
            notification_service.create_and_send_notification(
                user=recipient,
                notification_type="chat_message_received",
                title=title,
                body=body,
                target_role=recipient_role,
                data=data,
                triggered_by=message.sender,
            )
        except Exception as e:
            logger.error(f"Failed to send chat notification: {e}")

    def _get_display_name(self, user, role):
        """
        Get display name for a user based on their role.

        Args:
            user: User instance
            role: User role (homeowner or handyman)

        Returns:
            str: Display name
        """
        try:
            if role == "homeowner":
                profile = user.homeowner_profile
            else:
                profile = user.handyman_profile

            if profile and profile.display_name:
                return profile.display_name
        except Exception:
            pass

        return user.email.split("@")[0]

    @transaction.atomic
    def mark_messages_as_read(self, conversation, user, user_role):
        """
        Mark all unread messages in a conversation as read for a user.

        Args:
            conversation: ChatConversation instance
            user: Current user
            user_role: Role of the user

        Returns:
            int: Number of messages marked as read
        """
        # Determine which messages to mark
        if user_role == "homeowner":
            # Homeowner reads handyman's messages
            unread_messages = ChatMessage.objects.filter(
                conversation=conversation,
                sender_role=ChatMessage.SenderRole.HANDYMAN,
                is_read=False,
            )
        else:
            # Handyman reads homeowner's messages
            unread_messages = ChatMessage.objects.filter(
                conversation=conversation,
                sender_role=ChatMessage.SenderRole.HOMEOWNER,
                is_read=False,
            )

        now = timezone.now()
        count = unread_messages.update(is_read=True, read_at=now)

        # Reset unread count for this user
        if user_role == "homeowner":
            conversation.homeowner_unread_count = 0
        else:
            conversation.handyman_unread_count = 0

        conversation.save(
            update_fields=[
                "homeowner_unread_count",
                "handyman_unread_count",
                "updated_at",
            ]
        )

        logger.info(
            f"Marked {count} messages as read in conversation {conversation.public_id}"
        )

        return count

    def get_total_unread_count(self, user, user_role, conversation_type=None):
        """
        Get total unread message count across all conversations.

        Args:
            user: Current user
            user_role: Role of the user
            conversation_type: Optional filter by conversation type

        Returns:
            int: Total unread count
        """
        if user_role == "homeowner":
            queryset = ChatConversation.objects.filter(homeowner=user)
            count_field = "homeowner_unread_count"
        else:
            queryset = ChatConversation.objects.filter(handyman=user)
            count_field = "handyman_unread_count"

        if conversation_type:
            queryset = queryset.filter(conversation_type=conversation_type)

        result = queryset.aggregate(total=Sum(count_field))
        return result["total"] or 0

    def archive_conversation(self, conversation):
        """
        Archive a conversation (e.g., when job is completed/cancelled).

        Args:
            conversation: ChatConversation instance

        Returns:
            ChatConversation
        """
        if conversation.status != ChatConversation.Status.ARCHIVED:
            conversation.status = ChatConversation.Status.ARCHIVED
            conversation.save(update_fields=["status", "updated_at"])
            logger.info(f"Archived conversation {conversation.public_id}")

        return conversation

    def get_job_for_chat(self, job_public_id, user, user_role):
        """
        Get a job for chat access with authorization check.

        Args:
            job_public_id: UUID of the job
            user: Current user
            user_role: Role of the user

        Returns:
            Job

        Raises:
            Job.DoesNotExist: If not found or not authorized
        """
        filters = {"public_id": job_public_id}

        if user_role == "homeowner":
            filters["homeowner"] = user
        else:
            filters["assigned_handyman"] = user

        return Job.objects.get(**filters)

    def get_user_for_general_chat(self, user_public_id, user_role):
        """
        Get target user for general chat with role validation.

        Args:
            user_public_id: UUID of the target user
            user_role: Role of the current user (homeowner or handyman)

        Returns:
            User: Target user

        Raises:
            User.DoesNotExist: If user not found or doesn't have the required role
        """
        # If current user is homeowner, target must have handyman role
        # If current user is handyman, target must have homeowner role
        if user_role == "homeowner":
            required_role = "handyman"
        else:
            required_role = "homeowner"

        return User.objects.get(
            public_id=user_public_id,
            roles__role=required_role,
        )

    def get_or_create_general_conversation(self, user, user_role, target_user):
        """
        Get or create a general chat conversation with another user.

        Args:
            user: Current user
            user_role: Role of the current user (homeowner or handyman)
            target_user: User to chat with

        Returns:
            tuple: (ChatConversation, created: bool)
        """
        # Determine homeowner and handyman based on roles
        if user_role == "homeowner":
            homeowner = user
            handyman = target_user
        else:
            homeowner = target_user
            handyman = user

        # Get or create conversation
        conversation, created = ChatConversation.objects.get_or_create(
            conversation_type=ChatConversation.ConversationType.GENERAL,
            homeowner=homeowner,
            handyman=handyman,
        )

        if created:
            logger.info(
                f"Created general chat conversation {conversation.public_id} "
                f"between homeowner {homeowner.public_id} and handyman {handyman.public_id}"
            )

        return conversation, created

    def get_job_chat_unread_count(self, job, user, user_role):
        """
        Get unread count for a specific job's chat conversation.

        Args:
            job: Job instance
            user: Current user
            user_role: Role of the user (homeowner or handyman)

        Returns:
            int: Unread count for the job's conversation, or 0 if no conversation exists
        """
        try:
            conversation = ChatConversation.objects.get(
                job=job,
                conversation_type=ChatConversation.ConversationType.JOB,
            )

            if user_role == "homeowner":
                return conversation.homeowner_unread_count
            else:
                return conversation.handyman_unread_count
        except ChatConversation.DoesNotExist:
            return 0


# Global chat service instance
chat_service = ChatService()
