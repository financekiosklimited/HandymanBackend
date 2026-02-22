"""
Admin interface for chat models.
"""

from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from apps.chat.models import ChatConversation, ChatMessage, ChatMessageAttachment
from apps.common.admin_mixins import CSVExportAdminMixin


class ChatMessageAttachmentInline(TabularInline):
    """Inline admin for chat message attachments."""

    model = ChatMessageAttachment
    extra = 0
    readonly_fields = (
        "public_id",
        "file_preview",
        "thumbnail_preview",
        "file_type",
        "file_name",
        "file_size_display",
        "duration_seconds",
        "created_at",
    )
    fields = (
        "file_preview",
        "thumbnail_preview",
        "file_type",
        "file_name",
        "file_size_display",
        "order",
        "created_at",
    )

    @display(description="File")
    def file_preview(self, obj):
        """Display file preview (image or video link)."""
        if obj.file_type == "image" and obj.file:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.file.url,
            )
        elif obj.file:
            return format_html(
                '<a href="{}" target="_blank">View {}</a>',
                obj.file.url,
                obj.file_type,
            )
        return "-"

    @display(description="Thumbnail")
    def thumbnail_preview(self, obj):
        """Display thumbnail."""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.thumbnail.url,
            )
        return "-"

    @display(description="Size")
    def file_size_display(self, obj):
        """Display file size in KB or MB."""
        if obj.file_size:
            if obj.file_size > 1024 * 1024:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
            return f"{obj.file_size / 1024:.1f} KB"
        return "-"


class ChatMessageInline(TabularInline):
    """Inline admin for chat messages in conversation."""

    model = ChatMessage
    extra = 0
    readonly_fields = (
        "public_id",
        "sender_display",
        "sender_role",
        "message_type",
        "content_preview",
        "is_read",
        "created_at",
    )
    fields = (
        "sender_display",
        "sender_role",
        "message_type",
        "content_preview",
        "is_read",
        "created_at",
    )
    ordering = ("-created_at",)
    max_num = 20
    can_delete = False

    @display(description="Sender")
    def sender_display(self, obj):
        """Display sender email."""
        return obj.sender.email

    @display(description="Content")
    def content_preview(self, obj):
        """Display content preview."""
        if obj.content:
            preview = obj.content[:50]
            if len(obj.content) > 50:
                preview += "..."
            return preview
        return f"[{obj.get_message_type_display()}]"


@admin.register(ChatConversation)
class ChatConversationAdmin(CSVExportAdminMixin, ModelAdmin):
    """Admin interface for ChatConversation model."""

    list_display = (
        "conversation_display",
        "conversation_type_display",
        "job_link",
        "homeowner_link",
        "handyman_link",
        "status_display",
        "message_count",
        "unread_counts",
        "last_message_at",
        "created_at",
    )
    list_filter = ("conversation_type", "status", "last_message_at", "created_at")
    search_fields = (
        "homeowner__email",
        "handyman__email",
        "job__title",
    )
    autocomplete_fields = ("homeowner", "handyman", "job")
    readonly_fields = (
        "public_id",
        "homeowner_unread_count",
        "handyman_unread_count",
        "last_message_at",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"
    list_per_page = 25
    ordering = ("-last_message_at", "-created_at")
    inlines = [ChatMessageInline]

    fieldsets = (
        (
            "Conversation Info",
            {
                "fields": (
                    "public_id",
                    "conversation_type",
                    "job",
                    "status",
                )
            },
        ),
        (
            "Participants",
            {
                "fields": (
                    "homeowner",
                    "handyman",
                )
            },
        ),
        (
            "Statistics",
            {
                "fields": (
                    "homeowner_unread_count",
                    "handyman_unread_count",
                    "last_message_at",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Conversation")
    def conversation_display(self, obj):
        """Display conversation identifier."""
        if obj.job:
            return f"Job: {obj.job.title[:30]}..."
        return f"{obj.homeowner.email} <-> {obj.handyman.email}"

    @display(description="Type")
    def conversation_type_display(self, obj):
        """Display conversation type with icon."""
        icons = {
            "job": "💼",
            "general": "💬",
        }
        icon = icons.get(obj.conversation_type, "💬")
        return f"{icon} {obj.get_conversation_type_display()}"

    @display(description="Job")
    def job_link(self, obj):
        """Display job as clickable link."""
        if obj.job:
            return format_html(
                '<a href="/admin/jobs/job/{}/change/">{}</a>',
                obj.job.pk,
                obj.job.title[:30],
            )
        return "-"

    @display(description="Homeowner")
    def homeowner_link(self, obj):
        """Display homeowner as clickable link."""
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.homeowner.pk,
            obj.homeowner.email,
        )

    @display(description="Handyman")
    def handyman_link(self, obj):
        """Display handyman as clickable link."""
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.handyman.pk,
            obj.handyman.email,
        )

    @display(description="Status")
    def status_display(self, obj):
        """Display status with color."""
        colors = {
            "active": "green",
            "archived": "gray",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @display(description="Messages")
    def message_count(self, obj):
        """Display total message count."""
        return obj.messages.count()

    @display(description="Unread")
    def unread_counts(self, obj):
        """Display unread counts for both parties."""
        return format_html(
            "🏠 {} / 🔧 {}",
            obj.homeowner_unread_count,
            obj.handyman_unread_count,
        )


@admin.register(ChatMessage)
class ChatMessageAdmin(CSVExportAdminMixin, ModelAdmin):
    """Admin interface for ChatMessage model."""

    list_display = (
        "message_preview",
        "conversation_link",
        "sender_link",
        "sender_role_display",
        "message_type_display",
        "has_attachments",
        "read_status",
        "created_at",
    )
    list_filter = ("sender_role", "message_type", "is_read", "read_at", "created_at")
    search_fields = (
        "content",
        "sender__email",
        "conversation__job__title",
    )
    autocomplete_fields = ("conversation", "sender")
    readonly_fields = (
        "public_id",
        "read_at",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"
    list_per_page = 25
    ordering = ("-created_at",)
    inlines = [ChatMessageAttachmentInline]

    fieldsets = (
        (
            "Message Info",
            {
                "fields": (
                    "public_id",
                    "conversation",
                    "sender",
                    "sender_role",
                    "message_type",
                )
            },
        ),
        (
            "Content",
            {"fields": ("content",)},
        ),
        (
            "Read Status",
            {
                "fields": (
                    "is_read",
                    "read_at",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Message")
    def message_preview(self, obj):
        """Display message content preview."""
        if obj.content:
            preview = obj.content[:50]
            if len(obj.content) > 50:
                preview += "..."
            return preview
        return f"[{obj.get_message_type_display()}]"

    @display(description="Conversation")
    def conversation_link(self, obj):
        """Display conversation as clickable link."""
        if obj.conversation.job:
            label = obj.conversation.job.title[:20]
        else:
            label = f"Conv {str(obj.conversation.public_id)[:8]}"
        return format_html(
            '<a href="/admin/chat/chatconversation/{}/change/">{}</a>',
            obj.conversation.pk,
            label,
        )

    @display(description="Sender")
    def sender_link(self, obj):
        """Display sender as clickable link."""
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.sender.pk,
            obj.sender.email,
        )

    @display(description="Role")
    def sender_role_display(self, obj):
        """Display sender role with icon."""
        icons = {
            "homeowner": "🏠",
            "handyman": "🔧",
        }
        icon = icons.get(obj.sender_role, "👤")
        return f"{icon} {obj.get_sender_role_display()}"

    @display(description="Type")
    def message_type_display(self, obj):
        """Display message type with icon."""
        icons = {
            "text": "📝",
            "attachment": "📎",
            "text_with_attachment": "📝📎",
        }
        icon = icons.get(obj.message_type, "📝")
        return f"{icon} {obj.get_message_type_display()}"

    @display(description="Attachments")
    def has_attachments(self, obj):
        """Display whether message has attachments."""
        count = obj.attachments.count()
        if count > 0:
            return f"📎 {count}"
        return "-"

    @display(description="Read")
    def read_status(self, obj):
        """Display read status with icon."""
        if obj.is_read:
            return "✅ Read"
        return "🔵 Unread"


@admin.register(ChatMessageAttachment)
class ChatMessageAttachmentAdmin(ModelAdmin):
    """Admin interface for ChatMessageAttachment model."""

    list_display = (
        "file_preview",
        "message_link",
        "file_type",
        "file_name",
        "file_size_display",
        "duration_seconds",
        "order",
        "created_at",
    )
    list_filter = ("file_type", "created_at")
    search_fields = (
        "file_name",
        "message__content",
        "message__sender__email",
    )
    autocomplete_fields = ("message",)
    readonly_fields = (
        "public_id",
        "file_preview_large",
        "thumbnail_preview_large",
        "created_at",
        "updated_at",
    )
    list_per_page = 25
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Attachment Info",
            {
                "fields": (
                    "public_id",
                    "message",
                    "file_type",
                    "file_name",
                    "file_size",
                    "duration_seconds",
                    "order",
                )
            },
        ),
        (
            "Files",
            {
                "fields": (
                    "file",
                    "file_preview_large",
                    "thumbnail",
                    "thumbnail_preview_large",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Preview")
    def file_preview(self, obj):
        """Display file thumbnail in list."""
        if obj.file_type == "image":
            if obj.thumbnail:
                return format_html(
                    '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                    obj.thumbnail.url,
                )
            if obj.file:
                return format_html(
                    '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                    obj.file.url,
                )
        elif obj.file:
            return format_html(
                '<a href="{}" target="_blank">🎬 Video</a>', obj.file.url
            )
        return "-"

    @display(description="File Preview")
    def file_preview_large(self, obj):
        """Display full file preview."""
        if obj.file_type == "image" and obj.file:
            return format_html(
                '<img src="{}" style="max-height: 300px; max-width: 300px;" />',
                obj.file.url,
            )
        elif obj.file:
            return format_html(
                '<a href="{}" target="_blank">View Video</a>', obj.file.url
            )
        return "-"

    @display(description="Thumbnail Preview")
    def thumbnail_preview_large(self, obj):
        """Display thumbnail preview."""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-height: 150px; max-width: 150px;" />',
                obj.thumbnail.url,
            )
        return "-"

    @display(description="Size")
    def file_size_display(self, obj):
        """Display file size in KB or MB."""
        if obj.file_size:
            if obj.file_size > 1024 * 1024:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
            return f"{obj.file_size / 1024:.1f} KB"
        return "-"

    @display(description="Message")
    def message_link(self, obj):
        """Display message as clickable link."""
        preview = obj.message.content[:30] if obj.message.content else "[Attachment]"
        return format_html(
            '<a href="/admin/chat/chatmessage/{}/change/">{}</a>',
            obj.message.pk,
            preview,
        )
