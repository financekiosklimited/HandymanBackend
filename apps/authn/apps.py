"""App configuration for authn app."""

import importlib

from django.apps import AppConfig


class AuthnConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.authn"

    def ready(self):
        """Import schema extensions to register them with Spectacular."""
        try:
            importlib.import_module("apps.authn.schema")
        except ImportError:
            # Schema extras are optional in certain runtimes (e.g., stripped migrations)
            pass
