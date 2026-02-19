"""Mobile API views for Stripe KYC, wallet, and payment authorization."""

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.authn.permissions import (
    EmailVerifiedPermission,
    PhoneVerifiedPermission,
    PlatformGuardPermission,
    RoleGuardPermission,
)
from apps.common.openapi import (
    FORBIDDEN_EXAMPLE,
    NOT_FOUND_EXAMPLE,
    UNAUTHORIZED_EXAMPLE,
    VALIDATION_ERROR_EXAMPLE,
    pagination_meta_example,
)
from apps.common.responses import success_response, validation_error_response
from apps.jobs.models import Job, JobApplication
from apps.payments.serializers import (
    ConnectOnboardingLinkResponseSerializer,
    IdentitySessionResponseSerializer,
    JobPaymentStatusResponseSerializer,
    KycStatusResponseSerializer,
    PaymentAuthorizationResponseSerializer,
    WalletBalanceResponseSerializer,
    WithdrawalCreateSerializer,
    WithdrawalDetailResponseSerializer,
    WithdrawalListResponseSerializer,
    WithdrawalSerializer,
)
from apps.payments.services import job_payment_service, kyc_service, withdrawal_service


class HandymanConnectOnboardingLinkView(APIView):
    """Create/recreate Stripe Connect onboarding link."""

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_kyc_connect_onboarding_link_create",
        request=None,
        responses={
            200: ConnectOnboardingLinkResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        description=(
            "Create or regenerate Stripe Connect onboarding link for handyman account verification. "
            "Requires authenticated handyman with verified email."
        ),
        summary="Create onboarding link",
        tags=["Mobile Handyman KYC"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Onboarding link created successfully",
                    "data": {
                        "url": "https://connect.stripe.com/setup/e/acct_123",
                        "expires_at": 1735689600,
                        "account_id": "acct_123",
                    },
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
    def post(self, request):
        try:
            payload = kyc_service.create_connect_onboarding_link(request.user)
            return success_response(
                payload, message="Onboarding link created successfully"
            )
        except Exception as exc:
            return validation_error_response({"detail": str(exc)})


class HandymanIdentitySessionView(APIView):
    """Create Stripe Identity verification session."""

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_kyc_identity_session_create",
        request=None,
        responses={
            200: IdentitySessionResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        description=(
            "Create Stripe Identity verification session for handyman identity check. "
            "Requires authenticated handyman with verified email."
        ),
        summary="Create identity session",
        tags=["Mobile Handyman KYC"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Identity verification session created successfully",
                    "data": {
                        "verification_session_id": "vs_123",
                        "status": "pending",
                        "url": "https://verify.stripe.com/session/vs_123",
                    },
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
    def post(self, request):
        try:
            payload = kyc_service.create_identity_verification_session(request.user)
            return success_response(
                payload,
                message="Identity verification session created successfully",
            )
        except Exception as exc:
            return validation_error_response({"detail": str(exc)})


class HandymanKycStatusView(APIView):
    """Get consolidated KYC status."""

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_kyc_status_retrieve",
        responses={
            200: KycStatusResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        description=(
            "Retrieve KYC status from Stripe Connect and Stripe Identity for handyman account. "
            "Returns eligibility for payment assignment and withdrawals."
        ),
        summary="Get KYC status",
        tags=["Mobile Handyman KYC"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "KYC status retrieved successfully",
                    "data": {
                        "identity_status": "verified",
                        "charges_enabled": True,
                        "payouts_enabled": True,
                        "details_submitted": True,
                        "requirements_due": [],
                        "is_eligible": True,
                    },
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
        payload = kyc_service.get_kyc_status(request.user)
        return success_response(payload, message="KYC status retrieved successfully")


class HandymanWalletBalanceView(APIView):
    """Get wallet balance snapshot."""

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
        PhoneVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_wallet_balance_retrieve",
        responses={
            200: WalletBalanceResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        description=(
            "Get available and pending wallet balance from Stripe connected account. "
            "Requires handyman role and phone verification."
        ),
        summary="Get wallet balance",
        tags=["Mobile Handyman Wallet"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Wallet balance retrieved successfully",
                    "data": {
                        "currency": "cad",
                        "available_amount": "120.50",
                        "pending_amount": "45.00",
                    },
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
        payload = withdrawal_service.get_wallet_balance(request.user)
        payload.pop("available_cents", None)
        payload.pop("pending_cents", None)
        return success_response(
            payload, message="Wallet balance retrieved successfully"
        )


class HandymanWithdrawListCreateView(APIView):
    """List and create withdrawal requests."""

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
        PhoneVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_handyman_wallet_withdrawals_list",
        responses={
            200: WithdrawalListResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        description=(
            "List withdrawal requests for authenticated handyman with pagination. "
            "Requires KYC-enabled handyman wallet access."
        ),
        summary="List withdrawals",
        tags=["Mobile Handyman Wallet"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Withdrawals retrieved successfully",
                    "data": [
                        {
                            "public_id": "123e4567-e89b-12d3-a456-426614174000",
                            "amount": "50.00",
                            "currency": "cad",
                            "method": "instant",
                            "instant_fee": "0.50",
                            "status": "processing",
                            "failure_code": "",
                            "failure_message": "",
                            "requested_at": "2026-02-19T08:00:00Z",
                            "processed_at": None,
                            "created_at": "2026-02-19T08:00:00Z",
                        }
                    ],
                    "errors": None,
                    "meta": pagination_meta_example(total_count=1),
                },
                response_only=True,
                status_codes=["200"],
            ),
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
        ],
    )
    def get(self, request):
        queryset = request.user.withdrawal_requests.select_related(
            "connected_account"
        ).order_by("-created_at")

        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        total_count = queryset.count()
        total_pages = (total_count + page_size - 1) // page_size if total_count else 1

        start = (page - 1) * page_size
        end = start + page_size
        serializer = WithdrawalSerializer(queryset[start:end], many=True)

        meta = {
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_count": total_count,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            }
        }
        return success_response(
            serializer.data,
            message="Withdrawals retrieved successfully",
            meta=meta,
        )

    @extend_schema(
        operation_id="mobile_handyman_wallet_withdrawals_create",
        request=WithdrawalCreateSerializer,
        responses={
            201: WithdrawalDetailResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        description=(
            "Create withdrawal request for available wallet balance. "
            "Supports standard and instant payout methods."
        ),
        summary="Create withdrawal",
        tags=["Mobile Handyman Wallet"],
        examples=[
            OpenApiExample(
                "Instant Withdraw Request",
                value={"amount": 50.0, "method": "instant"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Withdrawal requested successfully",
                    "data": {
                        "public_id": "123e4567-e89b-12d3-a456-426614174001",
                        "amount": "50.00",
                        "currency": "cad",
                        "method": "instant",
                        "instant_fee": "0.50",
                        "status": "processing",
                        "failure_code": "",
                        "failure_message": "",
                        "requested_at": "2026-02-19T08:10:00Z",
                        "processed_at": None,
                        "created_at": "2026-02-19T08:10:00Z",
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
        ],
    )
    def post(self, request):
        serializer = WithdrawalCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            withdrawal = withdrawal_service.create_withdrawal(
                handyman=request.user,
                amount=serializer.validated_data["amount"],
                method=serializer.validated_data["method"],
            )
            return success_response(
                WithdrawalSerializer(withdrawal).data,
                message="Withdrawal requested successfully",
                status_code=201,
            )
        except Exception as exc:
            return validation_error_response({"detail": str(exc)})


class HomeownerApplicationPaymentAuthorizationView(APIView):
    """Authorize payment for a selected job application."""

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
        PhoneVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_homeowner_applications_payment_authorization_create",
        request=None,
        responses={
            200: PaymentAuthorizationResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Create or reuse Stripe PaymentIntent authorization for a homeowner job application. "
            "Uses manual capture and destination charge strategy."
        ),
        summary="Authorize application payment",
        tags=["Mobile Homeowner Payments"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Payment authorization prepared successfully",
                    "data": {
                        "job_payment_public_id": "123e4567-e89b-12d3-a456-426614174000",
                        "payment_intent_id": "pi_123",
                        "client_secret": "pi_123_secret_abc",
                        "status": "requires_confirmation",
                        "authorized_amount": "130.00",
                        "currency": "cad",
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def post(self, request, public_id):
        application = get_object_or_404(
            JobApplication.objects.select_related("job", "handyman"),
            public_id=public_id,
            job__homeowner=request.user,
        )

        try:
            result = job_payment_service.authorize_for_application(
                homeowner=request.user,
                application=application,
            )
            payment = result["job_payment"]
            data = {
                "job_payment_public_id": payment.public_id,
                "payment_intent_id": payment.payment_intent_id,
                "client_secret": result.get("client_secret", ""),
                "status": payment.status,
                "authorized_amount": str(payment.authorized_amount_cents / 100),
                "currency": payment.currency,
            }
            return success_response(
                data, message="Payment authorization prepared successfully"
            )
        except Exception as exc:
            return validation_error_response({"detail": str(exc)})


class HomeownerDirectOfferPaymentAuthorizationView(APIView):
    """Authorize payment for direct-offer jobs."""

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
        PhoneVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_homeowner_direct_offers_payment_authorization_create",
        request=None,
        responses={
            200: PaymentAuthorizationResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Create or reuse Stripe PaymentIntent authorization for a direct-offer job. "
            "Authorization is required before handyman can accept the offer."
        ),
        summary="Authorize direct-offer payment",
        tags=["Mobile Homeowner Payments"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Payment authorization prepared successfully",
                    "data": {
                        "job_payment_public_id": "123e4567-e89b-12d3-a456-426614174002",
                        "payment_intent_id": "pi_456",
                        "client_secret": "pi_456_secret_xyz",
                        "status": "requires_confirmation",
                        "authorized_amount": "260.00",
                        "currency": "cad",
                    },
                    "errors": None,
                    "meta": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            VALIDATION_ERROR_EXAMPLE,
            UNAUTHORIZED_EXAMPLE,
            FORBIDDEN_EXAMPLE,
            NOT_FOUND_EXAMPLE,
        ],
    )
    def post(self, request, public_id):
        job = get_object_or_404(
            Job,
            public_id=public_id,
            homeowner=request.user,
            is_direct_offer=True,
        )

        try:
            result = job_payment_service.authorize_for_direct_offer(
                homeowner=request.user,
                job=job,
            )
            payment = result["job_payment"]
            data = {
                "job_payment_public_id": payment.public_id,
                "payment_intent_id": payment.payment_intent_id,
                "client_secret": result.get("client_secret", ""),
                "status": payment.status,
                "authorized_amount": str(payment.authorized_amount_cents / 100),
                "currency": payment.currency,
            }
            return success_response(
                data, message="Payment authorization prepared successfully"
            )
        except Exception as exc:
            return validation_error_response({"detail": str(exc)})


class HomeownerJobPaymentStatusView(APIView):
    """Get payment status for homeowner job."""

    permission_classes = [
        IsAuthenticated,
        PlatformGuardPermission,
        RoleGuardPermission,
        EmailVerifiedPermission,
        PhoneVerifiedPermission,
    ]

    @extend_schema(
        operation_id="mobile_homeowner_jobs_payment_status_retrieve",
        responses={
            200: JobPaymentStatusResponseSerializer,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description=(
            "Retrieve Stripe payment status observability for a homeowner job. "
            "Includes authorization, capturable, captured, and refund-ready indicators."
        ),
        summary="Get job payment status",
        tags=["Mobile Homeowner Payments"],
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Payment status retrieved successfully",
                    "data": {
                        "status": "authorized",
                        "payment_intent_id": "pi_123",
                        "authorized_amount": "130.00",
                        "captured_amount": "0.00",
                        "capturable_amount": "130.00",
                        "platform_fee": "10.00",
                        "currency": "cad",
                        "last_failure_code": "",
                        "last_failure_message": "",
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
    def get(self, request, public_id):
        job = get_object_or_404(Job, public_id=public_id, homeowner=request.user)
        payload = job_payment_service.get_payment_status(job)
        return success_response(
            payload, message="Payment status retrieved successfully"
        )
