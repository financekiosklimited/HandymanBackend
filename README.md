# Solutionbank Backend API

## 🚀 Quick Setup Tutorial

**Prerequisites:**
- Python 3.13+
- PostgreSQL (running locally or Docker)
- uv package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/solution-bank/backend.git solutionbank-backend
cd solutionbank-backend

# Copy environment template and configure
cp .env.example .env
# Edit .env file with your local settings (see Configuration section)
```

### 2. One-Command Setup

```bash
# This will: create venv, install deps, create DB, run migrations
make setup
```

Or step by step:
```bash
# Install dependencies
make install

# Create database (ensure PostgreSQL is running)
make create-db

# Run migrations
make migrate

# Create superuser (optional)
make createsuperuser
```

### 3. Start Development Server

```bash
make run
# Server will be available at http://localhost:8000
```

### 4. Verify Installation

```bash
# Check database connection
make check-postgres

# Test API endpoint
curl http://localhost:8000/health/
# Should return: {"message": "ok", "data": null, "errors": null, "meta": null}
```

## 🛠 Tech Stack

- **Python 3.13.7** with **uv** package manager
- **Django 5.2** + **Django REST Framework**
- **PostgreSQL 18** database
- **RS256 JWT** authentication with custom service
- **S3** for media storage via django-storages + boto3
- **WhiteNoise** for static files

## 📋 Configuration

### Environment Variables (.env file)

**Required for local development:**

```bash
# Database (PostgreSQL must be running)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sb
DB_USER=postgres
DB_PASSWORD=your_postgres_password

# Django Core
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000

# JWT (keys are pre-generated in secrets/ folder)
JWT_PRIVATE_KEY_PATH=secrets/jwt_private.pem
JWT_PUBLIC_KEY_PATH=secrets/jwt_public.pem
JWT_ALG=RS256

# Email (for development, use local SMTP or disable)
EMAIL_HOST=localhost
EMAIL_PORT=1025
EMAIL_USE_TLS=False
```

**Optional (for S3 media storage):**
```bash
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1
```

## 🧪 Development Commands

```bash
# Available commands
make help

# Development workflow
make run              # Start dev server
make shell            # Django shell
make test             # Run tests
make migrate          # Apply migrations
make makemigrations   # Create new migrations
make createsuperuser  # Create admin user

# Database
make check-postgres   # Test DB connection
make create-db        # Create database

# Utilities
make clean           # Clean temp files
make fresh-setup     # Complete clean setup
```

## 🔑 API Documentation

### Key Endpoints

#### Authentication (Web Platform)
```
POST /api/v1/web/auth/register      # Register new user
POST /api/v1/web/auth/login         # Login user
POST /api/v1/web/auth/login/google  # Google OAuth login
POST /api/v1/web/auth/activate-role # Activate user role
POST /api/v1/web/auth/refresh       # Refresh token
POST /api/v1/web/auth/logout        # Logout user
POST /api/v1/web/auth/email/verify  # Verify email OTP
POST /api/v1/web/auth/password/forgot   # Request password reset
POST /api/v1/web/auth/password/reset    # Reset password
```

#### Profiles (Role-based)
```
GET/PUT /api/v1/web/customer/profile    # Customer profile
GET/PUT /api/v1/web/handyman/profile    # Handyman profile
GET/PUT /api/v1/mobile/customer/profile # Mobile customer profile
GET/PUT /api/v1/mobile/handyman/profile # Mobile handyman profile
```

#### Health & Schema
```
GET /health/                    # Health check
GET /api/schema/               # OpenAPI schema (JSON)
GET /api/schema/swagger/       # Interactive API docs
```

## 🏗 Features & Architecture

### Authentication & Authorization
- **RS256 JWT** with access/refresh token pairs
- **Platform-bound tokens** (web/mobile) with strict guards
- **Role-based access control** (admin/handyman/customer)
- **Email verification** with 6-digit OTP (24h TTL)
- **Password reset** with 2-step verification
- **Google OAuth** integration ready

### API Design
- **Versioned**: `/api/v1/`
- **Platform namespaces**: `/web/` and `/mobile/`
- **Role-scoped endpoints**: `/{platform}/{role}/profile`
- **Consistent JSON envelope**: `{"message", "data", "errors", "meta"}`
- **Rate limiting** per platform and endpoint

### JWT Token Structure
```json
{
  "sub": "user-public-uuid",
  "roles": ["customer", "handyman"],
  "plat": "web|mobile|admin",
  "type": "access|refresh",
  "active_role": "customer|handyman|admin|null",
  "email_verified": true,
  "jti": "unique-token-id",
  "exp": 1234567890,
  "aud": "sb-api"
}
```

## 📁 Project Structure

```
sb/
├── apps/                    # Django applications
│   ├── accounts/           # User models & profiles
│   ├── authn/             # JWT authentication service
│   ├── common/            # Shared utilities & base classes
│   ├── profiles/          # Profile serializers & views
│   └── storage/           # S3 storage configuration
├── config/                 # Django project configuration
│   ├── settings/          # Environment-specific settings
│   │   ├── base.py       # Base settings
│   │   ├── dev.py        # Development settings
│   │   └── prod.py       # Production settings
│   ├── urls.py           # Main URL configuration
│   ├── wsgi.py           # WSGI application
│   └── asgi.py           # ASGI application
├── interfaces/api/         # API endpoint definitions
│   ├── web/              # Web platform endpoints
│   └── mobile/           # Mobile platform endpoints
├── secrets/               # JWT keys and certificates
│   ├── jwt_private.pem   # RS256 private key
│   └── jwt_public.pem    # RS256 public key
├── .env.example          # Environment variables template
├── .env                  # Local environment (gitignored)
├── Makefile              # Development commands
├── pyproject.toml        # Python dependencies & config
└── manage.py             # Django management script
```
