# SolutionBank Backend API

## 🚀 Quick Start

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

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=solutionbank
DB_USER=postgres
DB_PASSWORD=your_password

# Django Core
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000

# JWT (pre-generated keys in secrets/ folder)
JWT_PRIVATE_KEY_PATH=secrets/jwt_private.pem
JWT_PUBLIC_KEY_PATH=secrets/jwt_public.pem
JWT_ALG=RS256

# Email
EMAIL_HOST=localhost
EMAIL_PORT=1025
EMAIL_USE_TLS=False
```

## 🔑 Admin Panel

### Access
- **URL**: http://localhost:8000/admin/

### Creating Admin User
```bash
# Interactive superuser creation
make createsuperuser

# Or using Django directly
uv run python manage.py createsuperuser
```

## 🧪 Testing & Coverage

The project uses Django's test framework with Coverage.py for measuring test coverage.

### Running Tests
```bash
make test              # Run all tests
make coverage          # Run tests with coverage report
make coverage-html     # Generate interactive HTML coverage report
make coverage-xml      # Generate XML coverage report (for CI)
```

## 🛠 Development

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
```

### API Documentation
- **Health Check**: http://localhost:8000/health/
- **Swagger UI**: http://localhost:8000/api/schema/swagger/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## 🏗 Architecture

### Tech Stack
- **Django 5.2** + **Django REST Framework**
- **PostgreSQL** database
- **RS256 JWT** authentication
- **Unfold** modern admin theme

### Key Features
- Platform-specific APIs (`/web/`, `/mobile/`)
- Role-based access control (admin/handyman/homeowner)
- Email verification with OTP
- Google OAuth integration
- Consistent JSON response format
- Pre-launch waitlist management

### Application Architecture

#### Core Apps
- **`accounts`** - User management, authentication models, custom User model
- **`authn`** - JWT token management, email verification, password reset flows
- **`profiles`** - Homeowner and handyman profile management with role-based access
- **`common`** - Shared utilities, BaseModel abstract class, response formatters
- **`waitlist`** - Pre-launch waitlist signup and management

#### API Structure
```
/api/v1/web/          # Web platform endpoints
├── auth/            # Authentication (login, register, verify)
├── profiles/        # Profile management
└── waitlist/        # Waitlist signup

/api/v1/mobile/      # Mobile platform endpoints
├── auth/            # Authentication flows
└── profiles/        # Profile management

/admin/              # Django admin interface
/health/             # Health check endpoint
```

### Project Structure
```
apps/                  # Django applications
├── accounts/         # User models & authentication
├── authn/           # JWT authentication service
├── common/          # Shared utilities (BaseModel, responses)
├── profiles/        # Homeowner & handyman profiles
└── waitlist/        # Pre-launch waitlist functionality

config/              # Django configuration
├── settings/        # Environment-specific settings
├── urls.py         # URL routing
└── asgi.py/wsgi.py # ASGI/WSGI applications

secrets/            # JWT private/public keys
staticfiles/        # Collected static files
```
