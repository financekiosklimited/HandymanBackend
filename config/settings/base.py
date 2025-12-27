"""
Base Django settings for sb project.
"""

from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment configuration
env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
    JWT_ALG=(str, "RS256"),
    JWT_NBF_LEEWAY=(int, 5),
    ACCESS_TOKEN_EXPIRE_MIN=(int, 15),
    REFRESH_TOKEN_EXPIRE_MIN=(int, 43200),  # 30 days
    EMAIL_USE_TLS=(bool, True),
    EMAIL_USE_SSL=(bool, False),
    AWS_S3_SIGNATURE_VERSION=(str, "s3v4"),
)

# Take environment variables from .env file
environ.Env.read_env(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# Application definition
DJANGO_APPS = [
    "unfold",  # Unfold admin theme - must be before django.contrib.admin
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "django_filters",
    "django_jsonform",
    "storages",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.authn",
    "apps.profiles",
    "apps.common",
    "apps.waitlist",
    "apps.jobs",
    "apps.notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": env.db()
    if env("DATABASE_URL", default=None)
    else {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", default="sb"),
        "USER": env("DB_USER", default="postgres"),
        "PASSWORD": env("DB_PASSWORD", default="postgres"),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5432"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static and media storage
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Django 5+ uses STORAGES; configure both static and media explicitly so uploads
# use Cloudflare R2/S3 via the custom backend instead of the local filesystem.
STORAGES = {
    "default": {
        "BACKEND": "apps.common.storage.MediaStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# S3/R2 Configuration
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default=None)
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default=None)
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default=None)
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="auto")  # 'auto' for R2
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None)
AWS_S3_SIGNATURE_VERSION = env("AWS_S3_SIGNATURE_VERSION", default="s3v4")

# File upload settings
AWS_DEFAULT_ACL = None  # R2 doesn't support ACLs by default
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",  # 1 day cache
}
AWS_QUERYSTRING_AUTH = False  # Don't add auth query params to URLs

# Media URL
# For Cloudflare R2, use the custom domain or public bucket URL
# For AWS S3, use the standard S3 URL
if AWS_S3_CUSTOM_DOMAIN:
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
elif AWS_STORAGE_BUCKET_NAME and AWS_S3_ENDPOINT_URL:
    # Extract account ID from R2 endpoint or use bucket name
    MEDIA_URL = env(
        "MEDIA_URL", default=f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"
    )
elif AWS_STORAGE_BUCKET_NAME:
    MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/"
else:
    MEDIA_URL = "/media/"

# CORS/CSRF
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env("EMAIL_USE_TLS")
EMAIL_USE_SSL = env("EMAIL_USE_SSL")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")

# JWT Settings
JWT_PRIVATE_KEY = env("JWT_PRIVATE_KEY", default=None)
JWT_PRIVATE_KEY_PATH = env("JWT_PRIVATE_KEY_PATH", default=None)
JWT_PUBLIC_KEY = env("JWT_PUBLIC_KEY", default=None)
JWT_PUBLIC_KEY_PATH = env("JWT_PUBLIC_KEY_PATH", default=None)
JWT_ALGORITHM = env("JWT_ALG")
JWT_AUDIENCE = env("JWT_AUDIENCE", default=None)
JWT_NBF_LEEWAY = env("JWT_NBF_LEEWAY")
ACCESS_TOKEN_EXPIRE_MINUTES = env("ACCESS_TOKEN_EXPIRE_MIN")
REFRESH_TOKEN_EXPIRE_MINUTES = env("REFRESH_TOKEN_EXPIRE_MIN")

# Twilio Configuration (Phone Verification via Verify API)
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default=None)
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", default=None)
TWILIO_VERIFY_SERVICE_SID = env("TWILIO_VERIFY_SERVICE_SID", default=None)

# Firebase Configuration (Push Notifications)
FIREBASE_CREDENTIALS_PATH = env("FIREBASE_CREDENTIALS_PATH", default=None)
FIREBASE_CREDENTIALS_JSON = env("FIREBASE_CREDENTIALS_JSON", default=None)


# DRF Configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.authn.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Web throttles - DRF format: num/period (s=second, m=minute, h=hour, d=day)
        "web:register": "5/min",
        "web:login": "10/min",
        "web:activate_role": "10/min",
        "web:verify_email": "10/min",
        "web:resend_email": "3/min",
        "web:refresh": "30/min",
        "web:forgot_password": "5/min",
        "web:verify_password_reset": "5/min",
        "web:reset_password": "5/min",
        "web:change_password": "5/min",
        # Mobile throttles (same rates)
        "mobile:register": "5/min",
        "mobile:login": "10/min",
        "mobile:activate_role": "10/min",
        "mobile:verify_email": "10/min",
        "mobile:resend_email": "3/min",
        "mobile:refresh": "30/min",
        "mobile:forgot_password": "5/min",
        "mobile:verify_password_reset": "5/min",
        "mobile:reset_password": "5/min",
        "mobile:change_password": "5/min",
        # Phone verification throttles
        "mobile:phone_send": "3/min",
        "mobile:phone_verify": "10/min",
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "EXCEPTION_HANDLER": "apps.common.exceptions.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# Spectacular settings
SPECTACULAR_SETTINGS = {
    "TITLE": "SolutionBank API",
    "DESCRIPTION": """
    Authentication: JWT Bearer Token with RS256 signatures
    Platform Support: Web and Mobile platforms with separate endpoints
    Role-based Access: Homeowner, Handyman, and Admin roles with guards

    Getting Started:
    1. Register a new account via /auth/register
    2. Verify email using the 6-digit code sent to your inbox
    3. Activate role (homeowner or handyman) via /auth/activate-role
    4. Access profiles and other protected endpoints

    Using Authentication:
    1. Get your JWT token from any auth endpoint
    2. Click the Authorize button above
    3. Paste your token (without "Bearer " prefix)
    4. Test protected endpoints with proper authorization
    """,
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1/",
    "COMPONENT_SPLIT_REQUEST": True,
    "SECURITY": [{"bearerAuth": []}],
    "ENUM_NAME_OVERRIDES": {
        "InitialRoleEnum": "apps.authn.serializers.RegisterSerializer.initial_role",
    },
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": False,
        "defaultModelsExpandDepth": 1,
        "defaultModelExpandDepth": 1,
        "displayRequestDuration": True,
        "docExpansion": "list",
        "filter": True,
        "operationsSorter": "method",
        "showExtensions": True,
        "showCommonExtensions": True,
        "tagsSorter": "alpha",
        "supportedSubmitMethods": ["get", "post", "put", "delete", "patch"],
        "tryItOutEnabled": True,
    },
}

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Unfold Admin Configuration
UNFOLD = {
    "DASHBOARD_CALLBACK": "apps.common.dashboard.dashboard_callback",
    "SITE_TITLE": "SolutionBank Admin",
    "SITE_HEADER": "SolutionBank",
    "SITE_URL": "/",
    "SITE_SYMBOL": "speed",  # Material icon symbol for sidebar
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "COLORS": {
        "primary": {
            "50": "239 246 255",
            "100": "219 234 254",
            "200": "191 219 254",
            "300": "147 197 253",
            "400": "96 165 250",
            "500": "59 130 246",
            "600": "37 99 235",
            "700": "29 78 216",
            "800": "30 64 175",
            "900": "30 58 138",
            "950": "23 37 84",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Dashboard",
                "separator": True,
                "items": [
                    {
                        "title": "Overview",
                        "icon": "dashboard",
                        "link": lambda request: "/admin/",
                    },
                ],
            },
            {
                "title": "Jobs",
                "separator": True,
                "items": [
                    {
                        "title": "Disputes Dashboard",
                        "icon": "gavel",
                        "link": lambda request: "/admin/jobs/jobdispute/dashboard/",
                    },
                    {
                        "title": "Job Listings",
                        "icon": "work",
                        "link": lambda request: "/admin/jobs/job/",
                    },
                    {
                        "title": "Job Applications",
                        "icon": "assignment",
                        "link": lambda request: "/admin/jobs/jobapplication/",
                    },
                    {
                        "title": "Job Categories",
                        "icon": "category",
                        "link": lambda request: "/admin/jobs/jobcategory/",
                    },
                ],
            },
            {
                "title": "Users & Profiles",
                "separator": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": lambda request: "/admin/accounts/user/",
                    },
                    {
                        "title": "Homeowner Profiles",
                        "icon": "person_outline",
                        "link": lambda request: "/admin/profiles/homeownerprofile/",
                    },
                    {
                        "title": "Handyman Profiles",
                        "icon": "build",
                        "link": lambda request: "/admin/profiles/handymanprofile/",
                    },
                ],
            },
            {
                "title": "Notifications",
                "separator": False,
                "items": [
                    {
                        "title": "Send Broadcast",
                        "icon": "campaign",
                        "link": lambda request: "/admin/notifications/broadcastnotification/send/",
                    },
                    {
                        "title": "Broadcast History",
                        "icon": "history",
                        "link": lambda request: "/admin/notifications/broadcastnotification/",
                    },
                    {
                        "title": "All Notifications",
                        "icon": "notifications",
                        "link": lambda request: "/admin/notifications/notification/",
                    },
                    {
                        "title": "User Devices",
                        "icon": "smartphone",
                        "link": lambda request: "/admin/notifications/userdevice/",
                    },
                ],
            },
            {
                "title": "Reference Data",
                "separator": True,
                "items": [
                    {
                        "title": "Cities",
                        "icon": "location_city",
                        "link": lambda request: "/admin/jobs/city/",
                    },
                    {
                        "title": "Country Phone Codes",
                        "icon": "phone",
                        "link": lambda request: "/admin/common/countryphonecode/",
                    },
                    {
                        "title": "Handyman Categories",
                        "icon": "category",
                        "link": lambda request: "/admin/profiles/handymancategory/",
                    },
                ],
            },
            {
                "title": "Waitlist",
                "separator": False,
                "items": [
                    {
                        "title": "Entries",
                        "icon": "hourglass_bottom",
                        "link": lambda request: "/admin/waitlist/waitlistentry/",
                    },
                ],
            },
            {
                "title": "System",
                "separator": False,
                "items": [
                    {
                        "title": "Groups",
                        "icon": "group",
                        "link": lambda request: "/admin/auth/group/",
                    },
                ],
            },
        ],
    },
}
