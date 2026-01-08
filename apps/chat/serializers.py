"""
Serializers for chat API.
"""

from rest_framework import serializers

from apps.chat.models import ChatConversation, ChatMessage, ChatMessageImage
from apps.common.serializers import (
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
# Image Serializers
# ========================


class ChatMessageImageSerializer(serializers.ModelSerializer):
    """
    Serializer for chat message images.
    """

    image_url = serializers.SerializerMethodField(help_text="Full image URL")
    thumbnail_url = serializers.SerializerMethodField(help_text="Thumbnail URL")

    class Meta:
        model = ChatMessageImage
        fields = ["public_id", "image_url", "thumbnail_url", "order"]
        read_only_fields = fields

    def get_image_url(self, obj):
        """Get the full image URL."""
        if obj.image:
            return obj.image.url
        return None

    def get_thumbnail_url(self, obj):
        """Get the thumbnail URL."""
        if obj.thumbnail:
            return obj.thumbnail.url
        # Fallback to full image if no thumbnail
        if obj.image:
            return obj.image.url
        return None


# ========================
# Message Serializers
# ========================


class ChatMessageSerializer(serializers.ModelSerializer):
    """
    Serializer for chat messages (response).
    """

    images = ChatMessageImageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "public_id",
            "sender_role",
            "message_type",
            "content",
            "images",
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
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        max_length=5,
        help_text="List of images (max 5, each max 10MB)",
    )

    def validate(self, data):
        """Validate that message has content or images."""
        content = data.get("content", "").strip()
        images = data.get("images", [])

        if not content and not images:
            raise serializers.ValidationError(
                "Message must have content or at least one image."
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
