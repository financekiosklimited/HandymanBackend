"""
Chat models for bidirectional communication between homeowners and handymen.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import BaseModel


class ChatConversation(BaseModel):
    """
    Unified conversation model for all chat types.
    Supports job-specific chat (current) and general chat (future).
    """

    class ConversationType(models.TextChoices):
        JOB = "job", "Job Chat"
        GENERAL = "general", "General Chat"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    conversation_type = models.CharField(
        max_length=20,
        choices=ConversationType.choices,
        default=ConversationType.JOB,
    )

    # Job reference - required for job chat, null for general
    job = models.OneToOneField(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="chat_conversation",
        null=True,
        blank=True,
    )

    # Participants
    homeowner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="homeowner_conversations",
    )
    handyman = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="handyman_conversations",
    )

    # Status & metadata
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    last_message_at = models.DateTimeField(null=True, blank=True)

    # Denormalized unread counts for performance
    homeowner_unread_count = models.PositiveIntegerField(default=0)
    handyman_unread_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "chat_conversations"
        ordering = ["-last_message_at", "-created_at"]
        verbose_name = "Chat Conversation"
        verbose_name_plural = "Chat Conversations"
        constraints = [
            # Job chat: job is required and unique
            models.UniqueConstraint(
                fields=["job"],
                condition=models.Q(conversation_type="job"),
                name="unique_job_conversation",
            ),
            # General chat: unique per homeowner-handyman pair
            models.UniqueConstraint(
                fields=["homeowner", "handyman"],
                condition=models.Q(conversation_type="general"),
                name="unique_general_conversation",
            ),
        ]
        indexes = [
            models.Index(
                fields=["conversation_type", "homeowner", "-last_message_at"],
                name="chat_conv_homeowner_idx",
            ),
            models.Index(
                fields=["conversation_type", "handyman", "-last_message_at"],
                name="chat_conv_handyman_idx",
            ),
            models.Index(fields=["status"]),
            models.Index(fields=["job"]),
        ]

    def __str__(self):
        if self.conversation_type == self.ConversationType.JOB and self.job:
            return f"Chat for Job: {self.job.title}"
        return f"Chat: {self.homeowner.email} <-> {self.handyman.email}"

    def clean(self):
        """Validate conversation data."""
        super().clean()

        if self.conversation_type == self.ConversationType.JOB and not self.job:
            raise ValidationError({"job": "Job is required for job conversations."})

        if self.conversation_type == self.ConversationType.GENERAL and self.job:
            raise ValidationError(
                {"job": "Job should not be set for general conversations."}
            )

    def save(self, *args, **kwargs):
        """Override save to run validation on full saves."""
        # Skip full_clean when using update_fields (partial updates)
        # This allows F() expressions and other deferred operations
        if not kwargs.get("update_fields"):
            self.full_clean()
        super().save(*args, **kwargs)


class ChatMessage(BaseModel):
    """
    Individual chat message within a conversation.
    """

    class MessageType(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        TEXT_WITH_IMAGE = "text_with_image", "Text with Image"

    class SenderRole(models.TextChoices):
        HOMEOWNER = "homeowner", "Homeowner"
        HANDYMAN = "handyman", "Handyman"

    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_chat_messages",
    )
    sender_role = models.CharField(
        max_length=20,
        choices=SenderRole.choices,
    )

    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
    )
    content = models.TextField(
        blank=True,
        max_length=2000,
        help_text="Text content, can be empty for image-only messages",
    )

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "chat_messages"
        ordering = ["created_at"]
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
        indexes = [
            models.Index(
                fields=["conversation", "created_at"],
                name="chat_msg_conv_created_idx",
            ),
            models.Index(
                fields=["conversation", "is_read"],
                name="chat_msg_conv_read_idx",
            ),
            models.Index(fields=["sender"]),
        ]

    def __str__(self):
        preview = self.content[:50] if self.content else f"[{self.message_type}]"
        return f"{self.sender_role}: {preview}"

    def clean(self):
        """Validate message data."""
        super().clean()

        # Either content or images must be provided
        has_content = bool(self.content and self.content.strip())

        # For new messages, we can't check images yet (they're created after)
        # So we only validate content length
        if has_content and len(self.content) > 2000:
            raise ValidationError(
                {"content": "Message content cannot exceed 2000 characters."}
            )

    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)


class ChatMessageImage(BaseModel):
    """
    Images attached to a chat message.
    Maximum 5 images per message, 10MB each.
    """

    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="chat/images/%Y/%m/")
    thumbnail = models.ImageField(
        upload_to="chat/thumbnails/%Y/%m/",
        blank=True,
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "chat_message_images"
        ordering = ["order"]
        verbose_name = "Chat Message Image"
        verbose_name_plural = "Chat Message Images"
        indexes = [
            models.Index(fields=["message"]),
        ]

    def __str__(self):
        return f"Image {self.order} for message {self.message.public_id}"
