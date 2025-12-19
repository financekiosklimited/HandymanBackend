from django.urls import path

from ..views import mobile as mobile_views

urlpatterns = [
    # Notification endpoints (role-agnostic, accessed via both handyman and homeowner paths)
    path(
        "handyman/notifications/",
        mobile_views.NotificationListView.as_view(),
        name="mobile_handyman_notifications",
    ),
    path(
        "handyman/notifications/<uuid:public_id>/read/",
        mobile_views.NotificationMarkAsReadView.as_view(),
        name="mobile_handyman_notification_read",
    ),
    path(
        "handyman/notifications/read-all/",
        mobile_views.NotificationMarkAllAsReadView.as_view(),
        name="mobile_handyman_notifications_read_all",
    ),
    path(
        "handyman/notifications/unread-count/",
        mobile_views.NotificationUnreadCountView.as_view(),
        name="mobile_handyman_notifications_unread_count",
    ),
    path(
        "homeowner/notifications/",
        mobile_views.NotificationListView.as_view(),
        name="mobile_homeowner_notifications",
    ),
    path(
        "homeowner/notifications/<uuid:public_id>/read/",
        mobile_views.NotificationMarkAsReadView.as_view(),
        name="mobile_homeowner_notification_read",
    ),
    path(
        "homeowner/notifications/read-all/",
        mobile_views.NotificationMarkAllAsReadView.as_view(),
        name="mobile_homeowner_notifications_read_all",
    ),
    path(
        "homeowner/notifications/unread-count/",
        mobile_views.NotificationUnreadCountView.as_view(),
        name="mobile_homeowner_notifications_unread_count",
    ),
    # Device registration endpoints (role-agnostic)
    path(
        "handyman/devices/",
        mobile_views.DeviceRegisterView.as_view(),
        name="mobile_handyman_devices",
    ),
    path(
        "handyman/devices/<uuid:public_id>/",
        mobile_views.DeviceUnregisterView.as_view(),
        name="mobile_handyman_device_unregister",
    ),
    path(
        "homeowner/devices/",
        mobile_views.DeviceRegisterView.as_view(),
        name="mobile_homeowner_devices",
    ),
    path(
        "homeowner/devices/<uuid:public_id>/",
        mobile_views.DeviceUnregisterView.as_view(),
        name="mobile_homeowner_device_unregister",
    ),
]
