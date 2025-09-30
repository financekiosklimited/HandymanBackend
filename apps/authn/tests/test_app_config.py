"""Tests for app configuration and schema utilities."""

import importlib
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.authn.apps import AuthnConfig
from apps.authn.schema import JWTAuthenticationExtension


class AuthnConfigTests(SimpleTestCase):
    """Ensure app config gracefully handles optional schema import."""

    def test_ready_handles_import_error(self):
        config = AuthnConfig("apps.authn", importlib.import_module("apps.authn"))

        with patch("apps.authn.apps.importlib.import_module", side_effect=ImportError("boom")) as mock_import:
            config.ready()

        mock_import.assert_called_once_with("apps.authn.schema")


class JWTAuthenticationExtensionTests(SimpleTestCase):
    """Validate security definition returned by schema extension."""

    def test_get_security_definition(self):
        extension = JWTAuthenticationExtension(target=None)
        definition = extension.get_security_definition(auto_schema=None)

        self.assertEqual(definition["type"], "http")
        self.assertEqual(definition["scheme"], "bearer")
        self.assertEqual(definition.get("bearerFormat"), "JWT")
