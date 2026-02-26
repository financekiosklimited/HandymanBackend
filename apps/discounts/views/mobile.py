"""
Mobile API views for Discounts.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.common.openapi import (
    UNAUTHORIZED_EXAMPLE,
    VALIDATION_ERROR_EXAMPLE,
)
from apps.common.responses import (
    error_response,
    success_response,
    validation_error_response,
)

from ..models import Discount
from ..serializers import (
    DiscountListSerializer,
    DiscountValidateSerializer,
    DiscountValidationResponseSerializer,
)
from ..services import discount_service


class DiscountListView(APIView):
    """
    GET /api/v1/mobile/discounts/

    List active discounts. Optionally filter by target role.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="mobile_discounts_list",
        summary="List active discounts",
        description=(
            "Returns a list of currently active discounts. "
            "If authenticated, discounts are filtered by user's role. "
            "Unauthenticated users see all discounts for marketing purposes."
        ),
        parameters=[
            OpenApiParameter(
                name="role",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by target role (homeowner, handyman, or both)",
                required=False,
                examples=[
                    OpenApiExample("Homeowner", value="homeowner"),
                    OpenApiExample("Handyman", value="handyman"),
                ],
            ),
        ],
        responses={
            200: DiscountListSerializer(many=True),
            401: OpenApiTypes.OBJECT,
        },
        tags=["Mobile Discounts"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Discounts retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "name": "First Job Special",
                            "code": "FIRST20",
                            "description": "Get 20% off your first job posting",
                            "terms_and_conditions": (
                                "This discount applies to the platform fee only, "
                                "not the job value. Valid for one-time use per user."
                            ),
                            "discount_type": "percentage",
                            "discount_value": "20.00",
                            "discount_display": "20% OFF",
                            "target_role": "homeowner",
                            "color": "#0C9A5C",
                            "icon": "sparkles",
                            "badge_text": "POPULAR",
                            "expiry_text": "Ends in 5 days",
                            "ends_in_days": 5,
                        },
                    ],
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
        ],
    )
    def get(self, request):
        """Get list of active discounts."""
        # Get role filter from query param or user's role
        role = request.query_params.get("role")

        if not role and request.user.is_authenticated:
            # Use user's actual role if authenticated
            if hasattr(request.user, "role"):
                role = request.user.role

        # Get active discounts
        discounts = discount_service.get_active_discounts(role=role)

        serializer = DiscountListSerializer(discounts, many=True)

        return success_response(
            data=serializer.data,
            message="Discounts retrieved successfully",
        )


class DiscountValidateView(APIView):
    """
    POST /api/v1/mobile/discounts/validate/

    Validate a discount code for the current user.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="mobile_discount_validate",
        summary="Validate discount code",
        description=(
            "Validates a discount code for the authenticated user. "
            "Checks if code exists, is active, within date range, "
            "applies to user's role, and user has remaining uses. "
            "Requires phone verification for homeowners."
        ),
        request=DiscountValidateSerializer,
        responses={
            200: DiscountValidationResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        tags=["Mobile Discounts"],
        examples=[
            OpenApiExample(
                "Valid Code Request",
                value={
                    "code": "FIRST20",
                    "target_role": "homeowner",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Valid Code Response",
                value={
                    "message": "Discount code is valid",
                    "data": {
                        "valid": True,
                        "discount": {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "name": "First Job Special",
                            "code": "FIRST20",
                            "description": "Get 20% off your first job posting",
                            "terms_and_conditions": (
                                "This discount applies to the platform fee only, "
                                "not the job value."
                            ),
                            "discount_type": "percentage",
                            "discount_value": "20.00",
                            "discount_display": "20% OFF",
                            "target_role": "homeowner",
                            "color": "#0C9A5C",
                            "icon": "sparkles",
                            "badge_text": "POPULAR",
                            "expiry_text": "Ends in 5 days",
                            "ends_in_days": 5,
                        },
                        "remaining_uses": 1,
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Invalid Code Response",
                value={
                    "message": "Discount validation failed",
                    "data": {
                        "valid": False,
                        "message": "You have already used this discount.",
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
        ],
    )
    def post(self, request):
        """Validate a discount code."""
        serializer = DiscountValidateSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        code = serializer.validated_data["code"]
        target_role = serializer.validated_data["target_role"]

        # Validate the discount code
        result = discount_service.validate_discount_code(
            code=code,
            user=request.user,
            target_role=target_role,
        )

        if result["valid"]:
            discount_serializer = DiscountListSerializer(result["discount"])
            return success_response(
                data={
                    "valid": True,
                    "discount": discount_serializer.data,
                    "remaining_uses": result["remaining_uses"],
                },
                message="Discount code is valid",
            )
        else:
            return success_response(
                data={
                    "valid": False,
                    "message": result["message"],
                },
                message="Discount validation failed",
            )


class DiscountDetailView(APIView):
    """
    GET /api/v1/mobile/discounts/{code}/

    Get details of a specific discount by code.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="mobile_discount_detail",
        summary="Get discount details",
        description=(
            "Returns details of a specific discount by its code. "
            "Useful for showing discount info before application."
        ),
        parameters=[
            OpenApiParameter(
                name="code",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Discount code (case insensitive)",
            ),
        ],
        responses={
            200: DiscountListSerializer,
            404: OpenApiTypes.OBJECT,
        },
        tags=["Mobile Discounts"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Discount retrieved successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "First Job Special",
                        "code": "FIRST20",
                        "description": "Get 20% off your first job posting",
                        "terms_and_conditions": (
                            "This discount applies to the platform fee only, "
                            "not the job value."
                        ),
                        "discount_type": "percentage",
                        "discount_value": "20.00",
                        "discount_display": "20% OFF",
                        "target_role": "homeowner",
                        "color": "#0C9A5C",
                        "icon": "sparkles",
                        "badge_text": "POPULAR",
                        "expiry_text": "Ends in 5 days",
                        "ends_in_days": 5,
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def get(self, request, code):
        """Get discount details by code."""
        try:
            discount = Discount.objects.get(code=code.upper())
        except Discount.DoesNotExist:
            return error_response(
                message="Discount not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = DiscountListSerializer(discount)

        return success_response(
            data=serializer.data,
            message="Discount retrieved successfully",
        )
