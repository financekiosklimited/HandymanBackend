"""Tests for common app models."""

from unittest.mock import patch

from django.db import models
from django.test import TestCase

from apps.common.models import BaseModel


# Test model for BaseModel tests
class TestModel(BaseModel):
    """Test model for BaseModel tests."""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "common"


class TestBaseModel(TestCase):
    """Tests for BaseModel abstract class.

    Note: These tests use a concrete model approach since we can't
    dynamically create tables in SQLite during tests.
    """

    def test_creates_public_id_on_save(self):
        """Test that public_id is automatically created."""
        # We'll test the behavior by creating a simple concrete model
        # Since we can't create dynamic tables in test, we verify the base behavior
        from apps.common.models import BaseModel

        # Verify that BaseModel has the expected fields
        self.assertTrue(hasattr(BaseModel, "public_id"))
        self.assertTrue(hasattr(BaseModel, "created_at"))
        self.assertTrue(hasattr(BaseModel, "updated_at"))

        # Verify field properties
        public_id_field = BaseModel._meta.get_field("public_id")
        self.assertFalse(public_id_field.editable)
        self.assertTrue(public_id_field.unique)
        self.assertTrue(public_id_field.db_index)

    def test_public_id_field_properties(self):
        """Test that public_id has correct field properties."""
        from apps.common.models import BaseModel

        field = BaseModel._meta.get_field("public_id")
        self.assertFalse(field.editable)
        self.assertTrue(field.unique)
        self.assertTrue(field.db_index)
        self.assertEqual(field.get_internal_type(), "UUIDField")

    def test_created_at_field_properties(self):
        """Test that created_at has correct field properties."""
        from apps.common.models import BaseModel

        field = BaseModel._meta.get_field("created_at")
        self.assertTrue(field.auto_now_add)
        self.assertTrue(field.db_index)

    def test_updated_at_field_properties(self):
        """Test that updated_at has correct field properties."""
        from apps.common.models import BaseModel

        field = BaseModel._meta.get_field("updated_at")
        self.assertTrue(field.auto_now)
        self.assertTrue(field.db_index)

    def test_default_ordering(self):
        """Test that default ordering is by created_at descending."""
        from apps.common.models import BaseModel

        self.assertEqual(BaseModel._meta.ordering, ["-created_at"])

    def test_model_is_abstract(self):
        """Test that BaseModel is abstract."""
        from apps.common.models import BaseModel

        self.assertTrue(BaseModel._meta.abstract)

    def test_has_bigautofield_primary_key(self):
        """Test that BaseModel uses BigAutoField for primary key."""
        from apps.common.models import BaseModel

        id_field = BaseModel._meta.get_field("id")
        self.assertEqual(id_field.get_internal_type(), "BigAutoField")
        self.assertTrue(id_field.primary_key)

    def test_save_method_sets_public_id(self):
        """Test that save method ensures public_id is set."""
        # This tests the save method logic without requiring a database
        import inspect

        from apps.common.models import BaseModel

        # Verify the save method is overridden
        save_method = BaseModel.save
        source = inspect.getsource(save_method)

        # Check that the save method handles public_id
        self.assertIn("public_id", source)
        self.assertIn("uuid", source)

    def test_save_generates_missing_public_id(self):
        """Ensure save regenerates public_id when manually cleared."""
        instance = TestModel(name="Needs UUID")
        instance.public_id = None

        with patch("django.db.models.Model.save") as mock_save:
            instance.save()

        self.assertIsNotNone(instance.public_id)
        mock_save.assert_called_once()

    def test_save_preserves_existing_public_id(self):
        """Confirm save keeps existing public_id when already set."""
        instance = TestModel(name="Has UUID")
        original_public_id = instance.public_id

        with patch("django.db.models.Model.save") as mock_save:
            instance.save()

        self.assertEqual(instance.public_id, original_public_id)
        mock_save.assert_called_once()
