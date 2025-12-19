from django.contrib import admin
from django.db import models
from django.utils import timezone
from django.utils.html import format_html
from django_jsonform.widgets import JSONFormWidget
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.notifications.models import Notification, UserDevice


@admin.register(UserDevice)
class UserDeviceAdmin(ModelAdmin):
    """
    Admin interface for UserDevice model with Unfold styling.
    """

    list_display = (
        "device_token_short",
        "user_link",
        "device_type_display",
        "status_display",
        "last_used_at",
        "created_at",
    )
    list_filter = ("device_type", "is_active", "created_at")
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "device_token",
    )
    autocomplete_fields = ("user",)
    readonly_fields = (
        "public_id",
        "device_token",
        "created_at",
        "updated_at",
        "last_used_at",
    )
    date_hierarchy = "created_at"
    list_per_page = 25
    actions = ["activate_devices", "deactivate_devices", "send_test_notification"]
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Device Information",
            {
                "fields": (
                    "public_id",
                    "user",
                    "device_token",
                    "device_type",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "is_active",
                    "last_used_at",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @display(description="Device Token")
    def device_token_short(self, obj):
        """Display truncated device token."""
        token = obj.device_token
        if len(token) > 30:
            return f"{token[:15]}...{token[-15:]}"
        return token

    @display(description="User")
    def user_link(self, obj):
        """Display user email as clickable link."""
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.user.pk,
            obj.user.email,
        )

    @display(description="Device Type")
    def device_type_display(self, obj):
        """Display device type with icon."""
        icons = {
            "ios": "📱",
            "android": "🤖",
            "web": "🌐",
        }
        icon = icons.get(obj.device_type, "📱")
        return f"{icon} {obj.get_device_type_display()}"

    @display(description="Status")
    def status_display(self, obj):
        """Display status with color coding."""
        if obj.is_active:
            return "✅ Active"
        return "⭕ Inactive"

    @admin.action(description="Activate selected devices")
    def activate_devices(self, request, queryset):
        """Activate selected devices."""
        updated = queryset.update(is_active=True, updated_at=timezone.now())
        self.message_user(
            request,
            f"Successfully activated {updated} device(s).",
        )

    @admin.action(description="Deactivate selected devices")
    def deactivate_devices(self, request, queryset):
        """Deactivate selected devices."""
        updated = queryset.update(is_active=False, updated_at=timezone.now())
        self.message_user(
            request,
            f"Successfully deactivated {updated} device(s).",
        )

    @admin.action(description="Send test push notification")
    def send_test_notification(self, request, queryset):
        """Send test push notification to selected devices."""
        from apps.notifications.firebase_service import firebase_service

        success_count = 0
        failure_count = 0

        # Only send to active devices
        active_devices = queryset.filter(is_active=True)

        for device in active_devices:
            sent = firebase_service.send_notification(
                device_token=device.device_token,
                title="SolutionBank Test",
                body="Push notifications are working correctly.",
                data={"test": "true"},
            )

            if sent:
                success_count += 1
                # Update last_used_at
                device.last_used_at = timezone.now()
                device.save(update_fields=["last_used_at"])
            else:
                failure_count += 1

        if success_count > 0:
            self.message_user(
                request,
                f"Successfully sent test notification to {success_count} device(s).",
            )

        if failure_count > 0:
            self.message_user(
                request,
                f"Failed to send to {failure_count} device(s). Check Firebase configuration.",
                level="warning",
            )


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    """
    Admin interface for Notification model with Unfold styling.
    """

    list_display = (
        "title",
        "user_link",
        "type_display",
        "read_status_display",
        "created_at",
    )
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "title",
        "body",
    )
    autocomplete_fields = ("user",)
    readonly_fields = ("public_id", "created_at", "updated_at", "read_at")
    date_hierarchy = "created_at"
    list_per_page = 25
    actions = ["mark_as_read", "mark_as_unread"]
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Notification Content",
            {
                "fields": (
                    "public_id",
                    "user",
                    "notification_type",
                    "title",
                    "body",
                )
            },
        ),
        (
            "Data Payload",
            {
                "fields": ("data",),
                "classes": ("collapse",),
                "description": "JSON data for deep linking in the mobile app",
            },
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

    formfield_overrides = {
        models.JSONField: {
            "widget": JSONFormWidget(schema={"type": "object"}),
        },
    }

    @display(description="User")
    def user_link(self, obj):
        """Display user email as clickable link."""
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.user.pk,
            obj.user.email,
        )

    @display(description="Type")
    def type_display(self, obj):
        """Display notification type with icon."""
        icons = {
            "job_application_received": "📩",
            "application_approved": "✅",
            "application_rejected": "❌",
            "application_withdrawn": "↩️",
        }
        icon = icons.get(obj.notification_type, "🔔")
        return f"{icon} {obj.get_notification_type_display()}"

    @display(description="Read Status")
    def read_status_display(self, obj):
        """Display read status with icon."""
        if obj.is_read:
            return "✅ Read"
        return "🔵 Unread"

    @admin.action(description="Mark selected as read")
    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read."""
        unread = queryset.filter(is_read=False)
        updated = unread.update(
            is_read=True,
            read_at=timezone.now(),
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f"Successfully marked {updated} notification(s) as read.",
        )

    @admin.action(description="Mark selected as unread")
    def mark_as_unread(self, request, queryset):
        """Mark selected notifications as unread."""
        read = queryset.filter(is_read=True)
        updated = read.update(
            is_read=False,
            read_at=None,
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f"Successfully marked {updated} notification(s) as unread.",
        )
