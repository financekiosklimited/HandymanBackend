"""
Serializers for Discount API.
"""

from rest_framework import serializers

from .models import Discount, UserDiscountUsage


class DiscountListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing active discounts.
    Used on homepages to show available discounts.
    """

    discount_display = serializers.CharField(
        source="get_discount_display", read_only=True
    )
    expiry_text = serializers.CharField(source="get_expiry_text", read_only=True)
    ends_in_days = serializers.IntegerField(source="get_ends_in_days", read_only=True)

    class Meta:
        model = Discount
        fields = [
            "public_id",
            "name",
            "code",
            "description",
            "terms_and_conditions",
            "discount_type",
            "discount_value",
            "discount_display",
            "target_role",
            "color",
            "icon",
            "badge_text",
            "expiry_text",
            "ends_in_days",
        ]


class DiscountValidateSerializer(serializers.Serializer):
    """
    Serializer for validating a discount code.
    """

    code = serializers.CharField(required=True, max_length=50)
    target_role = serializers.ChoiceField(
        choices=["homeowner", "handyman"],
        required=True,
        help_text="Role of the user validating the code",
    )

    def validate_code(self, value):
        """Ensure code is uppercase."""
        return value.upper()


class DiscountValidationResponseSerializer(serializers.Serializer):
    """
    Serializer for discount validation response.
    """

    valid = serializers.BooleanField()
    discount = DiscountListSerializer(required=False)
    message = serializers.CharField(required=False)
    remaining_uses = serializers.IntegerField(required=False)


class UserDiscountUsageSerializer(serializers.ModelSerializer):
    """
    Serializer for user discount usage records.
    """

    discount_name = serializers.CharField(source="discount.name", read_only=True)
    discount_code = serializers.CharField(source="discount.code", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True, default=None)

    class Meta:
        model = UserDiscountUsage
        fields = [
            "public_id",
            "discount_name",
            "discount_code",
            "job_title",
            "usage_number",
            "used_at",
        ]
