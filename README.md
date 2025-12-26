# SolutionBank Backend API

Django REST API for a home services marketplace connecting homeowners with handymen.

## Quick Start

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/solution-bank/backend.git
cd backend
cp .env.example .env
make setup

# Run server
make run  # http://localhost:8000
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

**Required:**
- `DJANGO_SECRET_KEY` - Django secret key
- `DATABASE_URL` - PostgreSQL connection string (or individual DB settings)
- `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` - RSA keys for JWT auth
- `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_PASSWORD` - SMTP settings

**Optional:**
- `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_VERIFY_SERVICE_SID` - Phone verification
- `FIREBASE_CREDENTIALS_JSON` - Push notifications (JSON string, not base64)
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_STORAGE_BUCKET_NAME` - S3 storage

## Commands

```bash
make run              # Start dev server
make shell            # Django shell
make migrate          # Apply migrations
make makemigrations   # Create migrations
make createsuperuser  # Create admin user
make test             # Run tests
make coverage         # Test with coverage report
make format           # Format code (ruff)
make lint             # Lint code (ruff)
make dummy-generate   # Generate demo data
make clean            # Clean temp files
```

## Tech Stack

- Django 5.2 + Django REST Framework
- PostgreSQL database
- RS256 JWT authentication
- Twilio (phone verification), Firebase (push notifications)
- AWS S3 / Cloudflare R2 (file storage)

## Features

- **Multi-platform APIs** - Web and mobile endpoints
- **Role-based access** - Admin, handyman, homeowner
- **Job marketplace** - Post jobs, browse, apply
- **Guest browsing** - Unauthenticated job/handyman access
- **Notifications** - In-app + push notifications
- **Verification** - Email and phone verification

## API Structure

**Web API** (`/api/v1/web/`) - (not used currently)
- `/auth/` - Login, register, email verification, password reset
- `/homeowner/profile/`, `/handyman/profile/` - Profile management
- `/waitlist/` - Pre-launch signup

**Mobile API** (`/api/v1/mobile/`)
- `/auth/` - All web auth + phone verification
- `/country-codes/`, `/job-categories/`, `/cities/` - Lookups
- `/guest/jobs/`, `/guest/handymen/` - Unauthenticated browsing
- `/homeowner/` - Jobs, applications, notifications, devices
- `/handyman/` - Jobs, applications, notifications, devices

**Documentation**
- Admin: `/admin/`
- Swagger: `/api/schema/swagger/`
- Schema: `/api/schema/`

## Architecture

```
apps/
├── accounts      # User model & roles
├── authn         # JWT auth, email/phone verification
├── profiles      # Homeowner & handyman profiles
├── jobs          # Job marketplace
├── notifications # In-app & push notifications
├── common        # Shared utilities
└── waitlist      # Pre-launch signup

config/           # Django settings & URLs
```
