"""
Django settings module.
"""

import os

# Determine which settings to use
environment = os.environ.get('DJANGO_ENVIRONMENT', 'dev')

if environment == 'production':
    from .prod import *
else:
    from .dev import *