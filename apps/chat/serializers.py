"""
Serializers for chat API.
"""

from rest_framework import serializers

from apps.chat.models import ChatConversation, ChatMessage, ChatMessageAttachment
from apps.common.constants import MAX_CHAT_ATTACHMENTS
from apps.common.serializers import (
    AttachmentInputSerializer,
    create_list_response_serializer,
    create_response_serializer,
)

# ========================
# Nested Info Serializers
# ========================


class ChatParticipantSerializer(serializers.Serializer):
    """
    Serializer for chat participant info.
    """

    public_id = serializers.UUIDField(help_text="User's public ID")
    display_name = serializers.CharField(
        allow_null=True, help_text="User's display name"
    )
    avatar_url = serializers.URLField(allow_null=True, help_text="User's avatar URL")


class ChatJobSerializer(serializers.Serializer):
    """
    Serializer for job info in chat context.
    """

    public_id = serializers.UUIDField(help_text="Job's public ID")
    title = serializers.CharField(help_text="Job title")
    status = serializers.CharField(help_text="Job status")


# ========================
# Attachment Serializers
# ========================


class ChatMessageAttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer for chat message attachments (images/videos).
    """

    file_url = serializers.SerializerMethodField(help_text="Full file URL")
    thumbnail_url = serializers.SerializerMethodField(
        help_text="Thumbnail URL (video thumbnail or image itself)"
    )

    class Meta:
        model = ChatMessageAttachment
        fields = [
            "public_id",
            "file_url",
            "file_type",
            "file_name",
            "file_size",
            "thumbnail_url",
            "duration_seconds",
            "order",
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        """Get the full file URL."""
        return obj.file_url

    def get_thumbnail_url(self, obj):
        """Get the thumbnail URL."""
        return obj.thumbnail_url


# ========================
# Message Serializers
# ========================


class ChatMessageSerializer(serializers.ModelSerializer):
    """
    Serializer for chat messages (response).
    """

    attachments = ChatMessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "public_id",
            "sender_role",
            "message_type",
            "content",
            "attachments",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


class LastMessageSerializer(serializers.Serializer):
    """
    Serializer for last message preview in conversation list.
    """

    content = serializers.CharField(
        allow_blank=True, help_text="Message content preview"
    )
    sender_role = serializers.CharField(help_text="Sender role (homeowner/handyman)")
    message_type = serializers.CharField(help_text="Message type")
    created_at = serializers.DateTimeField(help_text="Message timestamp")


class SendMessageSerializer(serializers.Serializer):
    """
    Serializer for sending a chat message (request).
    """

    content = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        help_text="Message text content (max 2000 characters)",
    )
    attachments = AttachmentInputSerializer(
        many=True,
        required=False,
        help_text=f"List of attachments (max {MAX_CHAT_ATTACHMENTS}). "
        "Use indexed format: attachments[0].file, attachments[0].thumbnail, "
        "attachments[0].duration_seconds. For videos, thumbnail and duration_seconds are required.",
    )

    def validate_attachments(self, value):
        """Validate attachments list count."""
        if not value:
            return []

        if len(value) > MAX_CHAT_ATTACHMENTS:
            raise serializers.ValidationError(
                f"Maximum {MAX_CHAT_ATTACHMENTS} attachments allowed."
            )

        return value

    def validate(self, data):
        """Validate that message has content or attachments."""
        content = data.get("content", "").strip()
        attachments = data.get("attachments", [])

        if not content and not attachments:
            raise serializers.ValidationError(
                "Message must have content or at least one attachment."
            )

        return data


# ========================
# Conversation Serializers
# ========================


class ConversationListSerializer(serializers.Serializer):
    """
    Serializer for conversation in list view.
    """

    public_id = serializers.UUIDField(help_text="Conversation's public ID")
    conversation_type = serializers.CharField(
        help_text="Conversation type (job/general)"
    )
    job = ChatJobSerializer(
        allow_null=True, help_text="Job info (for job conversations)"
    )
    other_party = ChatParticipantSerializer(help_text="The other participant's info")
    last_message = LastMessageSerializer(
        allow_null=True, help_text="Last message preview"
    )
    unread_count = serializers.IntegerField(help_text="Number of unread messages")
    status = serializers.CharField(help_text="Conversation status")
    last_message_at = serializers.DateTimeField(
        allow_null=True, help_text="Timestamp of last message"
    )
    created_at = serializers.DateTimeField(help_text="Conversation created timestamp")


class ConversationDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for conversation detail view.
    """

    job = ChatJobSerializer(allow_null=True, read_only=True)
    homeowner = ChatParticipantSerializer(read_only=True)
    handyman = ChatParticipantSerializer(read_only=True)

    class Meta:
        model = ChatConversation
        fields = [
            "public_id",
            "conversation_type",
            "job",
            "homeowner",
            "handyman",
            "status",
            "homeowner_unread_count",
            "handyman_unread_count",
            "last_message_at",
            "created_at",
        ]
        read_only_fields = fields


# ========================
# Count Serializers
# ========================


class UnreadCountSerializer(serializers.Serializer):
    """
    Serializer for unread count response.
    """

    unread_count = serializers.IntegerField(
        help_text="Total unread message count across all conversations"
    )


class MarkAsReadResponseSerializer(serializers.Serializer):
    """
    Serializer for mark as read response.
    """

    messages_read = serializers.IntegerField(
        help_text="Number of messages marked as read"
    )


# ========================
# Response Envelope Serializers
# ========================


ConversationListResponseSerializer = create_list_response_serializer(
    ConversationListSerializer, "ConversationListResponse"
)

ConversationDetailResponseSerializer = create_response_serializer(
    ConversationDetailSerializer, "ConversationDetailResponse"
)

MessageListResponseSerializer = create_list_response_serializer(
    ChatMessageSerializer, "MessageListResponse"
)

MessageResponseSerializer = create_response_serializer(
    ChatMessageSerializer, "MessageResponse"
)

UnreadCountResponseSerializer = create_response_serializer(
    UnreadCountSerializer, "UnreadCountResponse"
)

MarkAsReadResponseSerializer = create_response_serializer(
    MarkAsReadResponseSerializer, "MarkAsReadResponse"
)
