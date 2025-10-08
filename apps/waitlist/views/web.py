"""Web-facing API views for waitlist operations."""

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.common.responses import (
    created_response,
    success_response,
    validation_error_response,
)

from ..serializers import WaitlistEntryResponseSerializer, WaitlistEntrySerializer


class WaitlistSignupView(APIView):
    """Handle waitlist signups initiated via web experiences."""

    permission_classes = [AllowAny]

    @extend_schema(
        request=WaitlistEntrySerializer,
        responses={201: WaitlistEntryResponseSerializer, 200: WaitlistEntryResponseSerializer},
        summary="Join waitlist",
        description="Create or update a waitlist entry for the provided email and user type.",
        tags=["Waitlist"],
    )
    def post(self, request):
        """Add or refresh a waitlist entry."""

        serializer = WaitlistEntrySerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        entry = serializer.save()
        response_serializer = WaitlistEntrySerializer(entry)

        if getattr(serializer, "_created", False):
            return created_response(
                data=response_serializer.data,
                message="Joined waitlist successfully",
            )

        return success_response(
            data=response_serializer.data,
            message="Waitlist entry updated",
        )
