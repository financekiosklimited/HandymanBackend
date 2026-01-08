"""
Mobile URL patterns for chat functionality.
"""

from django.urls import path

from apps.chat.views.mobile_handyman import (
    HandymanConversationListView,
    HandymanConversationMessagesView,
    HandymanConversationReadView,
    HandymanGeneralChatView,
    HandymanJobChatUnreadCountView,
    HandymanJobChatView,
    HandymanUnreadCountView,
)
from apps.chat.views.mobile_homeowner import (
    HomeownerConversationListView,
    HomeownerConversationMessagesView,
    HomeownerConversationReadView,
    HomeownerGeneralChatView,
    HomeownerJobChatUnreadCountView,
    HomeownerJobChatView,
    HomeownerUnreadCountView,
)

urlpatterns = [
    # Homeowner chat endpoints
    path(
        "homeowner/conversations/",
        HomeownerConversationListView.as_view(),
        name="mobile_homeowner_conversations",
    ),
    path(
        "homeowner/conversations/unread-count/",
        HomeownerUnreadCountView.as_view(),
        name="mobile_homeowner_conversations_unread_count",
    ),
    path(
        "homeowner/users/<uuid:user_public_id>/chat/",
        HomeownerGeneralChatView.as_view(),
        name="mobile_homeowner_general_chat",
    ),
    path(
        "homeowner/jobs/<uuid:job_public_id>/chat/",
        HomeownerJobChatView.as_view(),
        name="mobile_homeowner_job_chat",
    ),
    path(
        "homeowner/jobs/<uuid:job_public_id>/chat/unread-count/",
        HomeownerJobChatUnreadCountView.as_view(),
        name="mobile_homeowner_job_chat_unread_count",
    ),
    path(
        "homeowner/conversations/<uuid:conversation_public_id>/messages/",
        HomeownerConversationMessagesView.as_view(),
        name="mobile_homeowner_conversation_messages",
    ),
    path(
        "homeowner/conversations/<uuid:conversation_public_id>/read/",
        HomeownerConversationReadView.as_view(),
        name="mobile_homeowner_conversation_read",
    ),
    # Handyman chat endpoints
    path(
        "handyman/conversations/",
        HandymanConversationListView.as_view(),
        name="mobile_handyman_conversations",
    ),
    path(
        "handyman/conversations/unread-count/",
        HandymanUnreadCountView.as_view(),
        name="mobile_handyman_conversations_unread_count",
    ),
    path(
        "handyman/users/<uuid:user_public_id>/chat/",
        HandymanGeneralChatView.as_view(),
        name="mobile_handyman_general_chat",
    ),
    path(
        "handyman/jobs/<uuid:job_public_id>/chat/",
        HandymanJobChatView.as_view(),
        name="mobile_handyman_job_chat",
    ),
    path(
        "handyman/jobs/<uuid:job_public_id>/chat/unread-count/",
        HandymanJobChatUnreadCountView.as_view(),
        name="mobile_handyman_job_chat_unread_count",
    ),
    path(
        "handyman/conversations/<uuid:conversation_public_id>/messages/",
        HandymanConversationMessagesView.as_view(),
        name="mobile_handyman_conversation_messages",
    ),
    path(
        "handyman/conversations/<uuid:conversation_public_id>/read/",
        HandymanConversationReadView.as_view(),
        name="mobile_handyman_conversation_read",
    ),
]
