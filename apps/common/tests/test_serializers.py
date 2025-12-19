"""Tests for common serializers."""

from django.test import TestCase
from rest_framework import serializers

from apps.common.serializers import (
    create_list_response_serializer,
    create_response_serializer,
)


class DummySerializer(serializers.Serializer):
    """Dummy serializer for testing."""

    name = serializers.CharField()
    value = serializers.IntegerField()


class CreateResponseSerializerTests(TestCase):
    """Test cases for create_response_serializer factory function."""

    def test_create_response_serializer_with_custom_name(self):
        """Test creating response serializer with custom name."""
        ResponseSerializer = create_response_serializer(
            DummySerializer, serializer_name="CustomResponse"
        )

        self.assertEqual(ResponseSerializer.__name__, "CustomResponse")
        self.assertEqual(ResponseSerializer.Meta.ref_name, "CustomResponse")

        # Check that it has envelope fields
        instance = ResponseSerializer()
        self.assertIn("message", instance.fields)
        self.assertIn("data", instance.fields)
        self.assertIn("errors", instance.fields)
        self.assertIn("meta", instance.fields)

    def test_create_response_serializer_auto_name_generation(self):
        """Test auto-generating serializer name when not provided."""
        ResponseSerializer = create_response_serializer(DummySerializer)

        self.assertEqual(ResponseSerializer.__name__, "DummySerializerResponse")
        self.assertEqual(ResponseSerializer.Meta.ref_name, "DummySerializerResponse")


class CreateListResponseSerializerTests(TestCase):
    """Test cases for create_list_response_serializer factory function."""

    def test_create_list_response_serializer_with_custom_name(self):
        """Test creating list response serializer with custom name."""
        ListResponseSerializer = create_list_response_serializer(
            DummySerializer, serializer_name="CustomListResponse"
        )

        self.assertEqual(ListResponseSerializer.__name__, "CustomListResponse")
        self.assertEqual(ListResponseSerializer.Meta.ref_name, "CustomListResponse")

        # Check that it has envelope fields
        instance = ListResponseSerializer()
        self.assertIn("message", instance.fields)
        self.assertIn("data", instance.fields)
        self.assertIn("errors", instance.fields)
        self.assertIn("meta", instance.fields)

        # Check that data field is a list
        self.assertTrue(instance.fields["data"].many)

    def test_create_list_response_serializer_auto_name_generation(self):
        """Test auto-generating list serializer name when not provided."""
        ListResponseSerializer = create_list_response_serializer(DummySerializer)

        self.assertEqual(ListResponseSerializer.__name__, "DummySerializerListResponse")
        self.assertEqual(
            ListResponseSerializer.Meta.ref_name, "DummySerializerListResponse"
        )
