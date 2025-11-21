# SolutionBank Deployment Guide

Production deployment guide for SolutionBank Django application on Coolify.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Configuration](#environment-configuration)
- [Deployment Steps](#deployment-steps)
- [Database Migrations](#database-migrations)
- [Post-Deployment](#post-deployment)
- [Performance Tuning](#performance-tuning)

---

## Overview

### Technology Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Base Image | `debian:bookworm-slim` | Lightweight Debian base |
| Python | 3.13.7 | Installed via uv |
| Package Manager | uv | Fast Python package manager |
| WSGI Server | Gunicorn | Workers: `2*CPU+1` (auto-scaled) |
| Static Files | WhiteNoise | Compressed manifest storage |
| Database | PostgreSQL | Via Coolify resource |
| Port | 8000 | Internal container port |

### Architecture

```
Internet → Coolify Proxy (SSL) → Gunicorn (port 8000) → Django Application
                                                              ↓
                                                        PostgreSQL DB
```

---

## Prerequisites

Before deploying, ensure you have:

- [ ] Coolify instance running and accessible
- [ ] PostgreSQL database resource created in Coolify
- [ ] Domain name configured (or using Coolify subdomain)
- [ ] Git repository connected to Coolify
- [ ] JWT keys generated (in `secrets/` directory)

---

## Quick Start

### 1. Create PostgreSQL Database

1. Navigate to Coolify Dashboard → **Resources**
2. Click **Add Resource** → **PostgreSQL**
3. Configure database settings:
   - Name: `solutionbank`
   - Version: Latest stable
4. Deploy the database
5. Copy the `DATABASE_URL` connection string

### 2. Create Application

1. Go to **Projects** → **Add Application**
2. Select **Git Repository**
3. Connect your repository
4. Configuration:
   - Build Pack: **Dockerfile**
   - Port: `8000`
   - Health Check: `/health/`

### 3. Configure Environment Variables

Add the environment variables listed in the next section.

### 4. Deploy

Click **Deploy** and monitor the build logs.

---

## Environment Configuration

### Required Variables

#### Django Core

```bash
# Environment
DJANGO_ENVIRONMENT=production
DEBUG=False

# Security
DJANGO_SECRET_KEY=your-generated-secret-key-here

# Domains and CORS
DJANGO_ALLOWED_HOSTS=your-domain.com,app.coolify.io
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://app.coolify.io
CORS_ALLOWED_ORIGINS=https://your-frontend.com
```

**Generate Secret Key:**
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

#### Database

```bash
DATABASE_URL=postgresql://user:password@host:5432/database
```

**Format:** `postgresql://[user]:[password]@[host]:[port]/[database]`

Copy this from your Coolify PostgreSQL resource.

#### JWT Authentication

```bash
# JWT Algorithm
JWT_ALG=RS256
JWT_AUDIENCE=sb-api
JWT_NBF_LEEWAY=5

# Token Expiration (in minutes)
ACCESS_TOKEN_EXPIRE_MIN=15
REFRESH_TOKEN_EXPIRE_MIN=43200

# RSA Keys (multiline)
JWT_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----
[Your private key content here]
-----END PRIVATE KEY-----

JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----
[Your public key content here]
-----END PUBLIC KEY-----
```

**Note:** In Coolify, use the multiline editor for JWT keys. Paste the entire key including headers/footers.

#### Email (Required for user features)

**For Resend (Recommended):**
```bash
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=465
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=your-resend-api-key
EMAIL_USE_SSL=True
EMAIL_USE_TLS=False
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

**For Gmail:**
```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

**Important:** Use App Password for Gmail, not your regular password.

### Optional Variables

#### HTTPS/SSL Configuration

**For HTTPS (Production with SSL):**
```bash
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

**For HTTP (Development/Testing):**
```bash
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
```

**Note:** Only use HTTP mode for development. Production should always use HTTPS.

#### AWS S3 Storage (Optional)

```bash
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1
AWS_S3_SIGNATURE_VERSION=s3v4

# Optional: Custom endpoint
AWS_S3_ENDPOINT_URL=https://s3.custom-domain.com
AWS_S3_CUSTOM_DOMAIN=bucket.s3.amazonaws.com
MEDIA_URL=https://bucket.s3.amazonaws.com/
```

---

## Deployment Steps

### Step 1: Initial Configuration

1. **Set Port Mapping**
   - Container Port: `8000`
   - Protocol: `HTTP`

2. **Configure Health Check**
   - Path: `/health/`
   - Method: `GET`
   - Expected Status: `200`
   - Interval: `30s` (recommended)

### Step 2: Build and Deploy

1. Click **Deploy** in Coolify
2. Monitor build logs for:
   - Python installation via uv
   - Dependency installation
   - Static file collection
   - Container startup

### Step 3: Verify Build

Check build logs for successful completion:
```
✓ Building Docker image
✓ Installing dependencies with uv
✓ Collecting static files
✓ Starting Gunicorn server
```

---

## Database Migrations

Migrations are handled automatically using Coolify's Post-Deployment Commands.

### Configuration

1. Go to Coolify → Application → **Settings** → **Post-Deployment Commands**
2. Add the following command:

```bash
uv run --no-sync python manage.py migrate --noinput
```

This will run migrations automatically after every deployment.

---

## Post-Deployment

### Create Superuser

**Interactive method (via Terminal):**
```bash
docker exec -it <container-id> uv run --no-sync python manage.py createsuperuser
```

**Non-interactive (via environment variables):**
```bash
DJANGO_SUPERUSER_USERNAME=admin \
DJANGO_SUPERUSER_EMAIL=admin@example.com \
DJANGO_SUPERUSER_PASSWORD=secure-password \
uv run --no-sync python manage.py createsuperuser --noinput
```

**Warning:** Never hardcode passwords. Use Coolify secrets for non-interactive creation.

### Verification Checklist

Test these endpoints to verify deployment:

#### 1. Health Check
```bash
curl https://your-domain.com/health/
```
**Expected:**
```json
{"status": "success"}
```

#### 2. Admin Panel
Visit: `https://your-domain.com/admin/`
- Should show login page
- Login with superuser credentials

#### 3. API Documentation
Visit: `https://your-domain.com/api/schema/swagger-ui/`
- Should display Swagger UI
- All endpoints should be listed

#### 4. Application Logs
In Coolify:
1. Go to **Logs**
2. Check for:
   - Gunicorn startup messages
   - No error messages
   - Request logs appearing

---

## Performance Tuning

### Gunicorn Configuration

**Worker calculation:**
```
workers = (2 × CPU_cores) + 1
```

**For CPU-intensive apps:**
- Use fewer workers (CPU count or CPU count + 1)

**For I/O-bound apps:**
- Use more workers (2-4 × CPU count)

**Custom worker count:**
```dockerfile
# Fixed workers
--workers 4

# Environment variable
--workers ${GUNICORN_WORKERS:-4}
```

**Worker timeout:**
```bash
# Default: 120 seconds
# Increase for slow endpoints
--timeout 300
```

### Database Optimization

#### Connection Pooling

**Option 1: Use pgBouncer**
1. Add pgBouncer resource in Coolify
2. Update `DATABASE_URL` to point to pgBouncer
3. Configure pool size based on workers

**Option 2: Django connection pooling**
```python
# In settings/prod.py
DATABASES['default']['CONN_MAX_AGE'] = 600  # 10 minutes
```

#### Query Optimization

```bash
# Enable query logging in development
DEBUG_TOOLBAR = True  # Only in development!

# Analyze slow queries
docker exec -it <container-id> uv run --no-sync python manage.py shell
```
```python
from django.db import connection
from django.conf import settings

# Enable query logging
settings.DEBUG = True
# ... run your code ...
print(len(connection.queries), "queries executed")
for query in connection.queries:
    print(query['sql'])
```

### Caching

**Add Redis for caching:**

1. Add Redis resource in Coolify
2. Install django-redis:
```bash
uv add django-redis
```

3. Configure in settings:
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

4. Add to environment variables:
```bash
REDIS_URL=redis://redis:6379/1
```

### Static Files Optimization

WhiteNoise is already configured with:
- Compression (gzip/brotli)
- Far-future cache headers
- Immutable files

**Additional optimization:**
```python
# In settings/prod.py
WHITENOISE_KEEP_ONLY_HASHED_FILES = True  # Remove non-hashed files
WHITENOISE_MAX_AGE = 31536000  # 1 year cache
```

---

## Security Best Practices

### Pre-Deployment Checklist

- [ ] `DEBUG=False` in production
- [ ] `DJANGO_SECRET_KEY` is unique and strong (50+ characters)
- [ ] `DJANGO_ALLOWED_HOSTS` includes only your domains
- [ ] `CSRF_TRUSTED_ORIGINS` uses `https://` protocol
- [ ] `CORS_ALLOWED_ORIGINS` restricted to frontend domain only
- [ ] SSL/HTTPS enabled (`SECURE_SSL_REDIRECT=True`)
- [ ] Secure cookie flags enabled (`SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`)
- [ ] JWT keys are secure and not committed to git
- [ ] Database password is strong (20+ characters)
- [ ] Email uses App Password, not account password
- [ ] S3 bucket has restrictive permissions (if used)
- [ ] Environment variables stored in Coolify secrets
- [ ] No sensitive data in git repository
- [ ] Application monitoring enabled

### Environment-Specific Settings

| Setting | Development | Production |
|---------|-------------|------------|
| `DEBUG` | `True` | `False` |
| `SECURE_SSL_REDIRECT` | `False` | `True` |
| `SESSION_COOKIE_SECURE` | `False` | `True` |
| `CSRF_COOKIE_SECURE` | `False` | `True` |
| Protocol | HTTP | HTTPS |

---

## Continuous Deployment

### Auto-Deploy on Git Push

1. Go to Coolify → Application → **Settings**
2. Enable **Auto Deploy**
3. Configure branch: `main` or `production`
4. Push to repository triggers automatic deployment

### Manual Deployment

1. Go to Coolify dashboard
2. Select your application
3. Click **Deploy**
4. Monitor build logs

### Deployment Workflow

```
git push → Webhook → Coolify → Build → Deploy → Post-Deploy Commands → Health Check
```

---

## Monitoring and Logs

### Application Logs

**View in Coolify:**
1. Go to Application → **Logs**
2. Filter by:
   - Build logs
   - Runtime logs
   - Error logs

**Via Docker:**
```bash
# Real-time logs
docker logs -f <container-id>

# Last 100 lines
docker logs --tail 100 <container-id>

# Since timestamp
docker logs --since 30m <container-id>
```

### Health Monitoring

**Health check endpoint:** `/health/`

**Monitor uptime:**
- Use external monitoring service (UptimeRobot, Pingdom)
- Set up alerts for downtime
- Monitor response time

---

## Backup and Recovery

### Database Backups

**Automatic backups (Coolify):**
- Coolify handles PostgreSQL backups
- Configure in PostgreSQL resource settings

**Manual backup:**
```bash
# Backup
docker exec <postgres-container> pg_dump -U postgres solutionbank > backup.sql

# Restore
docker exec -i <postgres-container> psql -U postgres solutionbank < backup.sql
```

### Media Files Backup

If using local storage (not recommended for production):
```bash
docker cp <container-id>:/app/media ./media-backup
```

**Recommendation:** Use S3 for media files in production.

---

## Additional Resources

- [Coolify Documentation](https://coolify.io/docs)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Gunicorn Documentation](https://docs.gunicorn.org/en/stable/settings.html)
- [WhiteNoise Documentation](http://whitenoise.evans.io/)
- [PostgreSQL Best Practices](https://wiki.postgresql.org/wiki/Don't_Do_This)

---

## Support

### Getting Help

1. **Check logs** - Most issues show up in logs
2. **Review this guide** - Troubleshooting section covers common issues
3. **Verify environment** - Use the security checklist
4. **Test components** - Database, email, JWT separately

### Reporting Issues

When reporting deployment issues, include:
- Error messages from logs
- Environment variable names (not values!)
- Steps to reproduce
- Expected vs actual behavior

---

**Last Updated:** 2025-11-21
**Version:** 2.0
