"""Models for Stripe payment, KYC, and payout workflows."""

from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel


class StripeCustomerProfile(BaseModel):
    """Maps a homeowner user to a Stripe customer."""

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="stripe_customer_profile",
    )
    stripe_customer_id = models.CharField(max_length=255, unique=True, db_index=True)
    currency = models.CharField(max_length=3, default="cad")

    class Meta:
        db_table = "stripe_customer_profiles"
        verbose_name = "Stripe Customer Profile"
        verbose_name_plural = "Stripe Customer Profiles"
        indexes = [
            models.Index(fields=["stripe_customer_id"]),
        ]

    def __str__(self):
        return f"Stripe Customer: {self.user.email}"


class StripeConnectedAccount(BaseModel):
    """Maps a handyman user to a Stripe Connect account."""

    ACCOUNT_TYPE_CHOICES = [
        ("express", "Express"),
        ("custom", "Custom"),
        ("standard", "Standard"),
    ]

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="stripe_connected_account",
    )
    stripe_account_id = models.CharField(max_length=255, unique=True, db_index=True)
    account_type = models.CharField(
        max_length=20, choices=ACCOUNT_TYPE_CHOICES, default="express"
    )
    charges_enabled = models.BooleanField(default=False)
    payouts_enabled = models.BooleanField(default=False)
    details_submitted = models.BooleanField(default=False)
    requirements_due = models.JSONField(default=list, blank=True)
    disabled_reason = models.CharField(max_length=255, blank=True)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "stripe_connected_accounts"
        verbose_name = "Stripe Connected Account"
        verbose_name_plural = "Stripe Connected Accounts"
        indexes = [
            models.Index(fields=["stripe_account_id"]),
            models.Index(fields=["charges_enabled", "payouts_enabled"]),
        ]

    def __str__(self):
        return f"Stripe Connected: {self.user.email}"


class HandymanIdentityVerification(BaseModel):
    """Tracks Stripe Identity verification for handyman users."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("requires_input", "Requires Input"),
        ("failed", "Failed"),
    ]

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="identity_verification",
    )
    verification_session_id = models.CharField(
        max_length=255, unique=True, db_index=True
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    last_error_code = models.CharField(max_length=100, blank=True)
    last_error_reason = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "handyman_identity_verifications"
        verbose_name = "Handyman Identity Verification"
        verbose_name_plural = "Handyman Identity Verifications"
        indexes = [
            models.Index(fields=["verification_session_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Identity {self.user.email}: {self.status}"


class JobPayment(BaseModel):
    """Tracks Stripe payment lifecycle for a job."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("requires_payment_method", "Requires Payment Method"),
        ("requires_confirmation", "Requires Confirmation"),
        ("authorized", "Authorized"),
        ("captured", "Captured"),
        ("canceled", "Canceled"),
        ("failed", "Failed"),
        ("partially_refunded", "Partially Refunded"),
        ("refunded", "Refunded"),
        ("disputed", "Disputed"),
    ]

    job = models.OneToOneField(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="payment",
    )
    customer_profile = models.ForeignKey(
        "payments.StripeCustomerProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_payments",
    )
    connected_account = models.ForeignKey(
        "payments.StripeConnectedAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_payments",
    )
    payment_intent_id = models.CharField(max_length=255, unique=True, db_index=True)
    currency = models.CharField(max_length=3, default="cad")

    service_amount_cents = models.PositiveIntegerField(default=0)
    reimbursement_approved_cents = models.PositiveIntegerField(default=0)
    reserve_cents = models.PositiveIntegerField(default=0)
    authorized_amount_cents = models.PositiveIntegerField(default=0)
    capturable_amount_cents = models.PositiveIntegerField(default=0)
    captured_amount_cents = models.PositiveIntegerField(default=0)
    platform_fee_cents = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default="draft")
    last_failure_code = models.CharField(max_length=100, blank=True)
    last_failure_message = models.TextField(blank=True)
    authorized_at = models.DateTimeField(null=True, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "job_payments"
        verbose_name = "Job Payment"
        verbose_name_plural = "Job Payments"
        indexes = [
            models.Index(fields=["payment_intent_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["job"]),
        ]

    def __str__(self):
        return f"Payment for {self.job.title} ({self.status})"


class PaymentRefund(BaseModel):
    """Tracks Stripe refunds related to a job payment."""

    SOURCE_CHOICES = [
        ("dispute", "Dispute"),
        ("admin", "Admin"),
        ("chargeback", "Chargeback"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("succeeded", "Succeeded"),
        ("failed", "Failed"),
        ("canceled", "Canceled"),
    ]

    job_payment = models.ForeignKey(
        "payments.JobPayment",
        on_delete=models.CASCADE,
        related_name="refunds",
    )
    stripe_refund_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    amount_cents = models.PositiveIntegerField(default=0)
    reason = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="admin")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    failure_reason = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payment_refunds"
        verbose_name = "Payment Refund"
        verbose_name_plural = "Payment Refunds"
        indexes = [
            models.Index(fields=["job_payment"]),
            models.Index(fields=["source", "status"]),
        ]

    def __str__(self):
        return f"Refund {self.amount_cents} ({self.status})"


class WithdrawalRequest(BaseModel):
    """Tracks manual/instant payout requests for handyman users."""

    METHOD_CHOICES = [
        ("standard", "Standard"),
        ("instant", "Instant"),
    ]

    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("processing", "Processing"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("canceled", "Canceled"),
    ]

    handyman = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="withdrawal_requests",
    )
    connected_account = models.ForeignKey(
        "payments.StripeConnectedAccount",
        on_delete=models.PROTECT,
        related_name="withdrawal_requests",
    )
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="cad")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="standard")
    instant_fee_cents = models.PositiveIntegerField(default=0)
    stripe_payout_id = models.CharField(
        max_length=255, null=True, blank=True, db_index=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="requested"
    )
    failure_code = models.CharField(max_length=100, blank=True)
    failure_message = models.TextField(blank=True)
    requested_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "withdrawal_requests"
        verbose_name = "Withdrawal Request"
        verbose_name_plural = "Withdrawal Requests"
        indexes = [
            models.Index(fields=["handyman", "status"]),
            models.Index(fields=["stripe_payout_id"]),
        ]

    def __str__(self):
        return f"Withdrawal {self.handyman.email} ({self.status})"


class StripeEventLog(BaseModel):
    """Deduplicated Stripe webhook event log."""

    PROCESSING_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processed", "Processed"),
        ("failed", "Failed"),
    ]

    stripe_event_id = models.CharField(max_length=255, unique=True, db_index=True)
    event_type = models.CharField(max_length=150, db_index=True)
    payload_json = models.JSONField(default=dict)
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default="pending",
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "stripe_event_logs"
        verbose_name = "Stripe Event Log"
        verbose_name_plural = "Stripe Event Logs"
        indexes = [
            models.Index(fields=["stripe_event_id"]),
            models.Index(fields=["event_type", "processing_status"]),
        ]

    def __str__(self):
        return f"{self.event_type} ({self.processing_status})"
