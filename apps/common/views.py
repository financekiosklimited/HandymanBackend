"""
Common views for the application.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .models import CountryPhoneCode
from .responses import success_response
from .serializers import (
    CountryPhoneCodeListResponseEnvelope,
    CountryPhoneCodeSerializer,
    ResponseEnvelopeSerializer,
)


@extend_schema(
    summary="Health check",
    description="Health check endpoint for deployment monitoring.",
    tags=["Common"],
    responses={200: ResponseEnvelopeSerializer},
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint for deployment monitoring.
    """
    return success_response(message="ok", data=None, meta=None)


class CountryPhoneCodeListView(APIView):
    """List active country phone codes."""

    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: CountryPhoneCodeListResponseEnvelope},
        description="Get list of active country phone codes for phone number input.",
        summary="List country phone codes",
        tags=["Common"],
    )
    def get(self, request):
        """Get list of active country phone codes."""
        queryset = CountryPhoneCode.objects.filter(is_active=True)
        serializer = CountryPhoneCodeSerializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message="Country codes retrieved successfully",
        )
