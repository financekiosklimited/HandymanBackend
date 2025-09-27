"""
Django settings module.
"""

import os

# Determine which settings to use
environment = os.environ.get("DJANGO_ENVIRONMENT", "dev")

if environment == "production":
    from .prod import *  # noqa: F403
else:
    from .dev import *  # noqa: F403
