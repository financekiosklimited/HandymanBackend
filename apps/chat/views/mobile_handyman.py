"""
Mobile API views for handyman chat functionality.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.authn.permissions import (
    EmailVerifiedPermission,
    PhoneVerifiedPermission,
    PlatformGuardPermission,
    RoleGuardPermission,
)
from apps.chat.models import ChatConversation
from apps.chat.serializers import (
    ChatMessageSerializer,
    ConversationDetailResponseSerializer,
    ConversationListResponseSerializer,
    MarkAsReadResponseSerializer,
    MessageListResponseSerializer,
    MessageResponseSerializer,
    SendMessageSerializer,
    UnreadCountResponseSerializer,
)
from apps.chat.services import chat_service
from apps.chat.views.mobile_homeowner import (
    serialize_conversation_detail,
    serialize_conversation_for_list,
)
from apps.common.openapi import (
    FORBIDDEN_EXAMPLE,
    NOT_FOUND_EXAMPLE,
    UNAUTHORIZED_EXAMPLE,
    VALIDATION_ERROR_EXAMPLE,
)
from apps.common.responses import (
    created_response,
    not_found_response,
    success_response,
    validation_error_response,
)


class HandymanConversationListView(APIView):
    """
    View for listing handyman's general chat conversations.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
        PhoneVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_conversations_list",
        responses={
            200: ConversationListResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        description=(
            "List general chat conversations for the authenticated handyman. "
            "Returns only general chat conversations (not job chat). "
            "Conversations are sorted by last_message_at (most recent first). "
            "For job-specific chat, use the job chat endpoint. "
            "Requires handyman role and phone verification."
        ),
        summary="List general chat conversations",
        tags=["Mobile Handyman Chat"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Conversations retrieved successfully",
                    "data": [
                        {
                            "public_id": "550e8400-e29b-41d4-a716-446655440000",
                            "conversation_type": "general",
                            "job": None,
                            "other_party": {
                                "public_id": "550e8400-e29b-41d4-a716-446655440003",
                                "display_name": "Jane Doe",
                                "avatar_url": "https://example.com/avatar.jpg",
                            },
                            "last_message": {
                                "content": "Great, see you then!",
                                "sender_role": "homeowner",
                                "message_type": "text",
                                "created_at": "2026-01-08T10:35:00Z",
                            },
                            "unread_count": 1,
                            "status": "active",
                            "last_message_at": "2026-01-08T10:35:00Z",
                            "created_at": "2026-01-07T09:00:00Z",
                        }
                    ],
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
        ],
    )
    def get(self, request):
        """List general chat conversations for the handyman."""
        conversations = chat_service.get_conversations_for_user(
            user=request.user,
            user_role="handyman",
            conversation_type="general",
        )

        data = [
            serialize_conversation_for_list(conv, "handyman") for conv in conversations
        ]

        return success_response(data, message="Conversations retrieved successfully")


class HandymanUnreadCountView(APIView):
    """
    View for getting total unread message count for general chat conversations.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
        PhoneVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_conversations_unread_count",
        responses={
            200: UnreadCountResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        description=(
            "Get total unread message count for general chat conversations. "
            "Useful for displaying badge on chat tab. "
            "For job-specific unread count, use the job chat unread count endpoint. "
            "Requires handyman role and phone verification."
        ),
        summary="Get general chat unread count",
        tags=["Mobile Handyman Chat"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Unread count retrieved successfully",
                    "data": {"unread_count": 3},
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
        ],
    )
    def get(self, request):
        """Get total unread message count for general chat."""
        unread_count = chat_service.get_total_unread_count(
            user=request.user,
            user_role="handyman",
            conversation_type="general",
        )

        return success_response(
            {"unread_count": unread_count},
            message="Unread count retrieved successfully",
        )


class HandymanJobChatView(APIView):
    """
    View for getting or creating a chat conversation for a specific job.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
        PhoneVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_job_chat",
        responses={
            200: ConversationDetailResponseSerializer,
            201: ConversationDetailResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Get or create a chat conversation for a specific job. "
            "Chat is only available when job status is 'in_progress'. "
            "The handyman must be the assigned handyman for the job. "
            "Creates a new conversation if one doesn't exist. "
            "Requires handyman role and phone verification."
        ),
        summary="Get/create job chat",
        tags=["Mobile Handyman Chat"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Conversation retrieved successfully",
                    "data": {
                        "public_id": "550e8400-e29b-41d4-a716-446655440000",
                        "conversation_type": "job",
                        "job": {
                            "public_id": "550e8400-e29b-41d4-a716-446655440001",
                            "title": "Fix kitchen sink",
                            "status": "in_progress",
                        },
                        "homeowner": {
                            "public_id": "550e8400-e29b-41d4-a716-446655440003",
                            "display_name": "Jane Doe",
                            "avatar_url": "https://example.com/avatar.jpg",
                        },
                        "handyman": {
                            "public_id": "550e8400-e29b-41d4-a716-446655440002",
                            "display_name": "John Smith",
                            "avatar_url": "https://example.com/avatar2.jpg",
                        },
                        "status": "active",
                        "homeowner_unread_count": 0,
                        "handyman_unread_count": 0,
                        "last_message_at": None,
                        "created_at": "2026-01-08T10:00:00Z",
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def get(self, request, job_public_id):
        """Get or create chat conversation for a job."""
        try:
            job = chat_service.get_job_for_chat(
                job_public_id=job_public_id,
                user=request.user,
                user_role="handyman",
            )
        except Exception:
            return not_found_response("Job not found")

        try:
            conversation, created = chat_service.get_or_create_job_conversation(
                job=job,
                user=request.user,
                user_role="handyman",
            )
        except ValueError as e:
            return validation_error_response({"detail": str(e)}, message=str(e))

        data = serialize_conversation_detail(conversation)

        if created:
            return created_response(data, message="Conversation created successfully")

        return success_response(data, message="Conversation retrieved successfully")


class HandymanConversationMessagesView(APIView):
    """
    View for listing and sending messages in a conversation.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
        PhoneVerifiedPermission,
    ]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        operation_id="mobile_handyman_conversation_messages_list",
        responses={
            200: MessageListResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        parameters=[
            OpenApiParameter(
                name="before",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description="Get messages before this message public_id (for pagination)",
                required=False,
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Number of messages to return (default 50, max 100)",
                required=False,
            ),
        ],
        description=(
            "List messages in a conversation with cursor-based pagination. "
            "Messages are returned in chronological order (oldest first). "
            "Use 'before' parameter to load older messages. "
            "Requires handyman role and phone verification."
        ),
        summary="List messages",
        tags=["Mobile Handyman Chat"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Messages retrieved successfully",
                    "data": [
                        {
                            "public_id": "550e8400-e29b-41d4-a716-446655440010",
                            "sender_role": "homeowner",
                            "message_type": "text",
                            "content": "Hi, when can you start?",
                            "images": [],
                            "is_read": True,
                            "read_at": "2026-01-08T10:05:00Z",
                            "created_at": "2026-01-08T10:00:00Z",
                        },
                        {
                            "public_id": "550e8400-e29b-41d4-a716-446655440011",
                            "sender_role": "handyman",
                            "message_type": "text",
                            "content": "I'll be there at 2pm tomorrow.",
                            "images": [],
                            "is_read": True,
                            "read_at": "2026-01-08T10:35:00Z",
                            "created_at": "2026-01-08T10:30:00Z",
                        },
                    ],
                    "errors": None,
                    "meta": {"has_more": False},
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def get(self, request, conversation_public_id):
        """List messages in a conversation."""
        try:
            conversation = chat_service.get_conversation_by_public_id(
                public_id=conversation_public_id,
                user=request.user,
                user_role="handyman",
            )
        except ChatConversation.DoesNotExist:
            return not_found_response("Conversation not found")

        before = request.query_params.get("before")
        limit = min(int(request.query_params.get("limit", 50)), 100)

        messages = chat_service.get_messages_for_conversation(
            conversation=conversation,
            limit=limit + 1,  # Get one extra to check if there are more
            before=before,
        )

        messages_list = list(messages)
        has_more = len(messages_list) > limit
        if has_more:
            messages_list = messages_list[:limit]

        serializer = ChatMessageSerializer(messages_list, many=True)

        return success_response(
            serializer.data,
            message="Messages retrieved successfully",
            meta={"has_more": has_more},
        )

    @extend_schema(
        operation_id="mobile_handyman_conversation_messages_create",
        request=SendMessageSerializer,
        responses={
            201: MessageResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Send a message in a conversation. "
            "Can include text content and/or up to 5 images (max 10MB each). "
            "Only allowed when conversation is active and job is in_progress. "
            "Requires handyman role and phone verification."
        ),
        summary="Send message",
        tags=["Mobile Handyman Chat"],
        examples=[
            OpenApiExample(
                "Text Message Request",
                value={"content": "I'll be there at 2pm tomorrow."},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Message sent successfully",
                    "data": {
                        "public_id": "550e8400-e29b-41d4-a716-446655440011",
                        "sender_role": "handyman",
                        "message_type": "text",
                        "content": "I'll be there at 2pm tomorrow.",
                        "images": [],
                        "is_read": False,
                        "read_at": None,
                        "created_at": "2026-01-08T10:30:00Z",
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["201"],
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def post(self, request, conversation_public_id):
        """Send a message in a conversation."""
        try:
            conversation = chat_service.get_conversation_by_public_id(
                public_id=conversation_public_id,
                user=request.user,
                user_role="handyman",
            )
        except ChatConversation.DoesNotExist:
            return not_found_response("Conversation not found")

        serializer = SendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            message = chat_service.send_message(
                conversation=conversation,
                sender=request.user,
                sender_role="handyman",
                content=serializer.validated_data.get("content", ""),
                images=serializer.validated_data.get("images", []),
            )
        except ValueError as e:
            return validation_error_response({"detail": str(e)}, message=str(e))

        response_serializer = ChatMessageSerializer(message)
        return created_response(
            response_serializer.data, message="Message sent successfully"
        )


class HandymanConversationReadView(APIView):
    """
    View for marking all messages in a conversation as read.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
        PhoneVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_conversation_read",
        request=None,
        responses={
            200: MarkAsReadResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Mark all unread messages from the homeowner as read. "
            "Also resets the unread count for the conversation. "
            "Requires handyman role and phone verification."
        ),
        summary="Mark as read",
        tags=["Mobile Handyman Chat"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Messages marked as read",
                    "data": {"messages_read": 2},
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def post(self, request, conversation_public_id):
        """Mark all messages in a conversation as read."""
        try:
            conversation = chat_service.get_conversation_by_public_id(
                public_id=conversation_public_id,
                user=request.user,
                user_role="handyman",
            )
        except ChatConversation.DoesNotExist:
            return not_found_response("Conversation not found")

        count = chat_service.mark_messages_as_read(
            conversation=conversation,
            user=request.user,
            user_role="handyman",
        )

        return success_response(
            {"messages_read": count}, message="Messages marked as read"
        )


class HandymanGeneralChatView(APIView):
    """
    View for getting or creating a general chat conversation with a homeowner.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
        PhoneVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_general_chat",
        responses={
            200: ConversationDetailResponseSerializer,
            201: ConversationDetailResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Get or create a general chat conversation with a homeowner. "
            "General chat is not tied to any specific job. "
            "The target user must have a homeowner role. "
            "Creates a new conversation if one doesn't exist. "
            "Requires handyman role and phone verification."
        ),
        summary="Get/create general chat",
        tags=["Mobile Handyman Chat"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Conversation retrieved successfully",
                    "data": {
                        "public_id": "550e8400-e29b-41d4-a716-446655440000",
                        "conversation_type": "general",
                        "job": None,
                        "homeowner": {
                            "public_id": "550e8400-e29b-41d4-a716-446655440003",
                            "display_name": "Jane Doe",
                            "avatar_url": "https://example.com/avatar.jpg",
                        },
                        "handyman": {
                            "public_id": "550e8400-e29b-41d4-a716-446655440002",
                            "display_name": "John Smith",
                            "avatar_url": "https://example.com/avatar2.jpg",
                        },
                        "status": "active",
                        "homeowner_unread_count": 0,
                        "handyman_unread_count": 0,
                        "last_message_at": None,
                        "created_at": "2026-01-08T10:00:00Z",
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def get(self, request, user_public_id):
        """Get or create general chat conversation with a homeowner."""
        try:
            target_user = chat_service.get_user_for_general_chat(
                user_public_id=user_public_id,
                user_role="handyman",
            )
        except User.DoesNotExist:
            return not_found_response("User not found")

        conversation, created = chat_service.get_or_create_general_conversation(
            user=request.user,
            user_role="handyman",
            target_user=target_user,
        )

        data = serialize_conversation_detail(conversation)

        if created:
            return created_response(data, message="Conversation created successfully")

        return success_response(data, message="Conversation retrieved successfully")


class HandymanJobChatUnreadCountView(APIView):
    """
    View for getting unread message count for a specific job's chat.
    """

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
        PhoneVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_job_chat_unread_count",
        responses={
            200: UnreadCountResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Get unread message count for a specific job's chat conversation. "
            "Returns 0 if no conversation exists for the job. "
            "Requires handyman role and phone verification."
        ),
        summary="Get job chat unread count",
        tags=["Mobile Handyman Chat"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Unread count retrieved successfully",
                    "data": {"unread_count": 3},
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def get(self, request, job_public_id):
        """Get unread message count for a job's chat."""
        try:
            job = chat_service.get_job_for_chat(
                job_public_id=job_public_id,
                user=request.user,
                user_role="handyman",
            )
        except Exception:
            return not_found_response("Job not found")

        unread_count = chat_service.get_job_chat_unread_count(
            job=job,
            user=request.user,
            user_role="handyman",
        )

        return success_response(
            {"unread_count": unread_count},
            message="Unread count retrieved successfully",
        )
