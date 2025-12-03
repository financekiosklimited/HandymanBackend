"""
Common serializers for API responses with envelope format.
"""

from rest_framework import serializers

from apps.common.models import CountryPhoneCode


class ResponseEnvelopeSerializer(serializers.Serializer):
    """
    Base envelope serializer for wrapping all API responses.
    """

    message = serializers.CharField(help_text="Response message")
    data = serializers.JSONField(
        allow_null=True, required=False, help_text="Response data"
    )
    errors = serializers.DictField(
        allow_null=True, required=False, help_text="Error details if any"
    )
    meta = serializers.DictField(
        allow_null=True, required=False, help_text="Additional metadata"
    )


def create_response_serializer(data_serializer, serializer_name=None):
    """
    Factory function to create a response envelope serializer wrapping a data serializer.

    Args:
        data_serializer: The serializer class for the 'data' field
        serializer_name: Optional name for the generated serializer class

    Returns:
        A new serializer class with envelope format
    """
    if serializer_name is None:
        serializer_name = f"{data_serializer.__name__}Response"

    class Meta:
        ref_name = serializer_name

    attrs = {
        "message": serializers.CharField(help_text="Response message"),
        "data": data_serializer(help_text="Response data"),
        "errors": serializers.DictField(
            allow_null=True, required=False, help_text="Error details if any"
        ),
        "meta": serializers.DictField(
            allow_null=True, required=False, help_text="Additional metadata"
        ),
        "Meta": Meta,
    }

    return type(serializer_name, (serializers.Serializer,), attrs)


def create_list_response_serializer(data_serializer, serializer_name=None):
    """
    Factory function to create a response envelope serializer wrapping a list of data.

    Args:
        data_serializer: The serializer class for items in the 'data' list
        serializer_name: Optional name for the generated serializer class

    Returns:
        A new serializer class with envelope format for list responses
    """
    if serializer_name is None:
        serializer_name = f"{data_serializer.__name__}ListResponse"

    class Meta:
        ref_name = serializer_name

    attrs = {
        "message": serializers.CharField(help_text="Response message"),
        "data": data_serializer(many=True, help_text="List of response data"),
        "errors": serializers.DictField(
            allow_null=True, required=False, help_text="Error details if any"
        ),
        "meta": serializers.DictField(
            allow_null=True, required=False, help_text="Additional metadata"
        ),
        "Meta": Meta,
    }

    return type(serializer_name, (serializers.Serializer,), attrs)


class CountryPhoneCodeSerializer(serializers.ModelSerializer):
    """
    Serializer for country phone codes.
    """

    class Meta:
        model = CountryPhoneCode
        fields = [
            "country_code",
            "country_name",
            "dial_code",
            "flag_emoji",
        ]


# Response envelope for country codes list
CountryPhoneCodeListResponseEnvelope = create_list_response_serializer(
    CountryPhoneCodeSerializer, "CountryPhoneCodeListResponse"
)
