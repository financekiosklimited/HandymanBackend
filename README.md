# SolutionBank Backend API

## Quick Start

### Prerequisites
- Python 3.13+
- PostgreSQL
- uv package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Installation

1. **Clone and configure**
   ```bash
   git clone https://github.com/solution-bank/backend.git solutionbank-backend
   cd solutionbank-backend
   cp .env.example .env
   # Edit .env with your database credentials
   ```

2. **One-command setup**
   ```bash
   make setup
   # Creates venv, installs dependencies, creates database, runs migrations
   ```

3. **Start development server**
   ```bash
   make run
   # Server available at http://localhost:8000
   ```

4. **Create admin user (optional)**
   ```bash
   make createsuperuser
   ```

## Configuration

### Environment Variables (.env)

```bash
# Django Core
DJANGO_SECRET_KEY=your-super-secret-key-here
DEBUG=True
DJANGO_ENVIRONMENT=dev
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Database Configuration
# Option 1: Use DATABASE_URL (recommended for production)
# DATABASE_URL=postgresql://user:password@host:port/database

# Option 2: Individual database settings
DB_HOST=localhost
DB_PORT=5432
DB_NAME=solutionbank
DB_USER=postgres
DB_PASSWORD=

# JWT Configuration
# Option 1: Inline keys
JWT_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----...-----END PRIVATE KEY-----
JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----...-----END PUBLIC KEY-----
# Option 2: File paths (pre-generated keys in secrets/ folder)
# JWT_PRIVATE_KEY_PATH=secrets/jwt_private.pem
# JWT_PUBLIC_KEY_PATH=secrets/jwt_public.pem
JWT_ALG=RS256
JWT_AUDIENCE=sb-api
JWT_NBF_LEEWAY=5
ACCESS_TOKEN_EXPIRE_MIN=15
REFRESH_TOKEN_EXPIRE_MIN=43200

# Email Configuration (SMTP)
EMAIL_HOST=localhost
EMAIL_PORT=1025
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=False
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=noreply@example.com

# S3 Configuration (for file storage - Cloudflare R2 or AWS S3)
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=auto
AWS_S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
AWS_S3_CUSTOM_DOMAIN=<bucket-name>.r2.dev  # Or your custom domain
AWS_S3_SIGNATURE_VERSION=s3v4

# Twilio Configuration (Phone Verification via Verify API)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_VERIFY_SERVICE_SID=VAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Firebase Configuration (Push Notifications)
# Option 1: Path to Firebase service account JSON file
FIREBASE_CREDENTIALS_PATH=secrets/firebase-credentials.json
# Option 2: Base64 encoded JSON string of service account credentials
# FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}

# Logging Configuration (Optional)
# DJANGO_LOG_FILE=logs/django.log
```

## Admin Panel

### Access
- **URL**: http://localhost:8000/admin/

### Creating Admin User
```bash
# Interactive superuser creation
make createsuperuser

# Or using Django directly
uv run python manage.py createsuperuser
```

## Testing & Coverage

The project uses Django's test framework with Coverage.py for measuring test coverage.

### Running Tests
```bash
make test              # Run all tests
make coverage          # Run tests with coverage report
make coverage-html     # Generate interactive HTML coverage report
make coverage-xml      # Generate XML coverage report (for CI)
```

## Development

### Common Commands
```bash
make help              # Show all available commands
make run               # Start development server
make shell             # Django shell
make test              # Run tests
make coverage          # Run tests with coverage report
make coverage-html     # Generate HTML coverage report
make migrate           # Apply database migrations
make makemigrations    # Create new migrations
make check-postgres    # Test database connection
make lint              # Run linting checks (ruff)
make lint-fix          # Run linting and auto-fix issues
make format            # Format code with ruff
make format-check      # Check code formatting
make dummy-generate    # Generate dummy data for demo
make dummy-delete      # Delete all dummy data
make clean             # Clean temporary files
```

### API Documentation
- **Health Check**: http://localhost:8000/health/
- **Swagger UI**: http://localhost:8000/api/schema/swagger/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## Architecture

### Tech Stack
- **Django 5.2** + **Django REST Framework**
- **PostgreSQL** database
- **RS256 JWT** authentication
- **Unfold** modern admin theme

### Key Features
- **Platform-specific APIs** - Separate endpoints for web (`/web/`) and mobile (`/mobile/`)
- **Role-based access control** - Admin, handyman, and homeowner roles with granular permissions
- **Authentication & Verification**
  - Email verification with OTP
  - Phone verification via Twilio Verify API (mobile only)
  - Google OAuth integration (planned)
- **Job Marketplace**
  - Homeowners can post jobs with categories, locations, budgets, and images
  - Handymen can browse, apply to, and manage job applications
  - Guest browsing for unauthenticated users
  - Location-based filtering with Canadian cities
- **Notifications System**
  - In-app notifications for job applications and status updates
  - Push notifications via Firebase Cloud Messaging
  - Admin broadcast notifications with targeting
  - Device token management
- **File Storage** - S3-compatible storage (AWS S3 or Cloudflare R2) for images
- **Consistent API responses** - Standardized JSON envelope format
- **Pre-launch waitlist** - Early access signup and management

### Application Architecture

#### Core Apps
- **`accounts`** - User management, custom User model with email-based authentication
- **`authn`** - Authentication flows (JWT tokens, email/phone verification, password reset)
- **`profiles`** - Homeowner and handyman profile management with role-based access
- **`jobs`** - Job marketplace (posting, browsing, applications, categories, cities)
- **`notifications`** - Push notifications (Firebase), in-app notifications, device management
- **`common`** - Shared utilities (BaseModel, response formatters, validators)
- **`waitlist`** - Pre-launch waitlist signup and management

#### API Structure
```
/api/v1/web/          # Web platform endpoints
├── auth/            # Authentication (login, register, verify, password reset)
├── profiles/        # Profile management
└── waitlist/        # Waitlist signup

/api/v1/mobile/      # Mobile platform endpoints
├── auth/            # Authentication + phone verification
├── profiles/        # Profile management
├── country-codes/   # Country phone codes lookup
├── job-categories/  # Job categories list
├── cities/          # Cities list
├── guest/jobs/      # Unauthenticated job browsing
├── homeowner/
│   ├── jobs/        # Job posting and management
│   ├── applications/ # Application review and approval
│   ├── notifications/ # In-app notifications
│   └── devices/     # Device token registration
└── handyman/
    ├── jobs/        # Job browsing and details
    ├── applications/ # Apply to jobs, manage applications
    ├── notifications/ # In-app notifications
    └── devices/     # Device token registration

/admin/              # Django admin interface (with Unfold theme)
/health/             # Health check endpoint
/api/schema/         # OpenAPI schema
/api/schema/swagger/ # Swagger UI documentation
```

### Project Structure
```
apps/                  # Django applications
├── accounts/         # User models & authentication
├── authn/           # JWT authentication service
├── common/          # Shared utilities (BaseModel, responses)
├── profiles/        # Homeowner & handyman profiles
├── jobs/            # Job marketplace (posting, applications)
├── notifications/   # Push & in-app notifications
└── waitlist/        # Pre-launch waitlist functionality

config/              # Django configuration
├── settings/        # Environment-specific settings (base, dev, prod, test)
├── urls.py         # URL routing
└── asgi.py/wsgi.py # ASGI/WSGI applications

secrets/            # JWT keys & Firebase credentials
staticfiles/        # Collected static files
templates/          # Django templates (admin customizations)
```
