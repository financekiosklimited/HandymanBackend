# SolutionBank Deployment Guide

Deploy the Django backend on Coolify.

## Quick Start

1. **Create PostgreSQL database** in Coolify (Resources → PostgreSQL)
2. **Create application** from Git repository (Dockerfile, port 8000)
3. **Configure environment variables** (see below)
4. **Deploy**

---

## Environment Variables

### Required

```bash
# Django
DJANGO_ENVIRONMENT=production
DEBUG=False
DJANGO_SECRET_KEY=<generated-key>

# Domains
DJANGO_ALLOWED_HOSTS=your-domain.com,app.coolify.io
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://app.coolify.io
CORS_ALLOWED_ORIGINS=https://your-frontend.com

# Database
DATABASE_URL=postgresql://user:password@host:5432/database

# JWT
JWT_ALG=RS256
JWT_AUDIENCE=sb-api
JWT_NBF_LEEWAY=5
ACCESS_TOKEN_EXPIRE_MIN=15
REFRESH_TOKEN_EXPIRE_MIN=43200
JWT_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----
[private key]
-----END PRIVATE KEY-----
JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----
[public key]
-----END PUBLIC KEY-----

# Email
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=465
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=<api-key>
EMAIL_USE_SSL=True
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

### Optional

```bash
# SSL (production)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Firebase (push notifications)
FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}

# Twilio (phone verification)
TWILIO_ACCOUNT_SID=ACxxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_VERIFY_SERVICE_SID=VAxxx

# S3 Storage (files)
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_STORAGE_BUCKET_NAME=bucket-name
AWS_S3_ENDPOINT_URL=https://xxx.r2.cloudflarestorage.com
```

---

## Configuration

### Application Settings
- **Build Pack**: Dockerfile
- **Port**: 8000
- **Health Check**: `/health/` (GET, status 200)

### Post-Deployment Command
```bash
UV_NO_SYNC=1 uv run --frozen python manage.py migrate --noinput
```

---

## Post-Deployment

### Create Superuser

```bash
# Interactive
docker exec -it <container> uv run --frozen python manage.py createsuperuser

# Non-interactive
DJANGO_SUPERUSER_USERNAME=admin \
DJANGO_SUPERUSER_EMAIL=admin@example.com \
DJANGO_SUPERUSER_PASSWORD=<password> \
UV_NO_SYNC=1 uv run --frozen python manage.py createsuperuser --noinput
```

### Verify

```bash
# Health check
curl https://your-domain.com/health/

# Admin panel
https://your-domain.com/admin/

# API docs
https://your-domain.com/api/schema/swagger/
```

---

## Tech Stack

- **Base Image**: `ghcr.io/astral-sh/uv:python3.13-bookworm-slim`
- **Python**: 3.13
- **Package Manager**: uv
- **Server**: Gunicorn (workers: `2*CPU+1`)
- **Database**: PostgreSQL

---

## Performance

### Gunicorn Workers
```dockerfile
# Fixed workers
--workers 4

# Environment variable
--workers ${GUNICORN_WORKERS:-4}
```

### Database Pooling
Add `DATABASES['default']['CONN_MAX_AGE'] = 600` in settings.

---

## Monitoring

- **Logs**: Coolify → Application → Logs
- **Health**: `/health/` endpoint
- **Uptime**: Use external monitoring (UptimeRobot, Pingdom)

---

## Scheduled Tasks

Configure scheduled tasks in Coolify: **Projects → Application → Scheduled Tasks**

### Process Overdue Reports

Auto-approves daily reports that pass review deadline (3 days).

| Field | Value |
|-------|-------|
| **Name** | Process Overdue Reports |
| **Command** | `uv run python manage.py process_overdue_reports` |
| **Frequency** | `0 * * * *` |

### Process Overdue Disputes

Auto-resolves disputes (pay handyman) that pass resolution deadline (3 days).

| Field | Value |
|-------|-------|
| **Name** | Process Overdue Disputes |
| **Command** | `uv run python manage.py process_overdue_disputes` |
| **Frequency** | `0 * * * *` |
---

## Backups

Coolify handles PostgreSQL backups automatically. Manual:

```bash
# Backup
docker exec <postgres> pg_dump -U postgres solutionbank > backup.sql

# Restore
docker exec -i <postgres> psql -U postgres solutionbank < backup.sql
```

---

**Last Updated:** 2025-12-27
