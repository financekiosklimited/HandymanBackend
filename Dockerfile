# syntax=docker/dockerfile:1.7

# Shared build arguments so Coolify can provide secrets at build-time.
ARG DJANGO_SECRET_KEY
ARG DJANGO_ENVIRONMENT=production
ARG DEBUG=False
ARG DJANGO_ALLOWED_HOSTS=localhost
ARG DATABASE_URL=sqlite:///tmp/db.sqlite3
ARG CSRF_TRUSTED_ORIGINS
ARG CORS_ALLOWED_ORIGINS

# Builder stage: installs system headers, syncs the uv environment, and runs collectstatic.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    wget \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock .python-version ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-group dev

COPY . .

ARG DJANGO_SECRET_KEY
ARG DJANGO_ENVIRONMENT
ARG DEBUG
ARG DJANGO_ALLOWED_HOSTS
ARG DATABASE_URL
ARG CSRF_TRUSTED_ORIGINS
ARG CORS_ALLOWED_ORIGINS

ENV DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
ENV DJANGO_ENVIRONMENT=${DJANGO_ENVIRONMENT}
ENV DEBUG=${DEBUG}
ENV DJANGO_ALLOWED_HOSTS=${DJANGO_ALLOWED_HOSTS}
ENV DATABASE_URL=${DATABASE_URL}
ENV CSRF_TRUSTED_ORIGINS=${CSRF_TRUSTED_ORIGINS}
ENV CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS}

RUN --mount=type=cache,target=/root/.cache/uv \
    UV_NO_SYNC=1 uv run --frozen python manage.py collectstatic --noinput

# Runtime stage: copy the synced virtualenv and source code into a clean image.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local/share/uv /root/.local/share/uv
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:${PATH}"
ENV UV_NO_SYNC=1

ARG DJANGO_SECRET_KEY
ARG DJANGO_ENVIRONMENT
ARG DEBUG
ARG DJANGO_ALLOWED_HOSTS
ARG DATABASE_URL
ARG CSRF_TRUSTED_ORIGINS
ARG CORS_ALLOWED_ORIGINS

ENV DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
ENV DJANGO_ENVIRONMENT=${DJANGO_ENVIRONMENT}
ENV DEBUG=${DEBUG}
ENV DJANGO_ALLOWED_HOSTS=${DJANGO_ALLOWED_HOSTS}
ENV DATABASE_URL=${DATABASE_URL}
ENV CSRF_TRUSTED_ORIGINS=${CSRF_TRUSTED_ORIGINS}
ENV CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS}

EXPOSE 8000

# Use shell form to keep the dynamic Gunicorn worker calculation.
CMD uv run --frozen gunicorn \
    --bind 0.0.0.0:8000 \
    --workers $((2 * $(nproc) + 1)) \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    config.wsgi:application
