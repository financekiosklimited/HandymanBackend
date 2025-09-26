from django.apps import AppConfig


class AuthnConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.authn"

    def ready(self):
        # Import schema extensions to register them
        try:
            from . import schema  # noqa: F401
        except ImportError:
            pass
