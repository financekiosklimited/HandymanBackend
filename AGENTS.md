# Repository Guidelines

## Project Structure & Module Organization
SolutionBank is a Django 5 project rooted in `manage.py`. Core domain logic lives under `apps/`, with each app (e.g., `accounts`, `authn`, `profiles`, `storage`) exposing Django models, serializers, and REST views. Shared utilities sit in `apps/common`. Runtime configuration resides in `config/` (`settings/dev.py` for local work, `settings/prod.py` for deployment). Static assets are collected into `staticfiles/`, and `main.py` offers the `uvicorn` entrypoint for ASGI hosting.

## Build, Test, and Development Commands
- `make setup` — create the virtualenv, install dependencies with `uv`, create the database, and run migrations.
- `make run` — start the Django development server against `config.settings.dev`.
- `make migrate` / `make makemigrations` — apply or generate schema changes after updating models.
- `make test` — run the Django test suite via `uv run python manage.py test`.
- `make check-postgres` — quickly confirm credentials in `.env` before running database tasks.

## Coding Style & Naming Conventions
Follow idiomatic Django + PEP 8 style: four-space indentation, `snake_case` for modules/functions, `CamelCase` for models and serializers, and descriptive `snake_case` field names. Keep view names aligned with route purpose (e.g., `ProfileDetailView`). Prefer explicit imports within each app. Optional type hints are welcome but keep them practical; Pyright runs with relaxed settings, so lint proactively before raising PRs.

## Testing Guidelines
Locate or create tests alongside the relevant app (`apps/<app>/tests.py`). Name methods `test_<condition>_<expected>` and group related cases inside `Test` classes. Use Django’s `APITestCase` or `TestCase` helpers for database interaction, and mock external services (e.g., S3, auth providers). Run `make test` before every PR; add targeted tests for new views, signals, and serializers to guard regressions.

## Commit & Pull Request Guidelines
Use Conventional Commit prefixes observed in history (`feat:`, `fix:`, `chore:`) and keep summaries under ~70 characters. Reference ticket IDs or issue numbers where available. For pull requests, include: purpose, key changes, migration notes, deployment considerations, and screenshots for admin/UI tweaks. Confirm `make test` passes and mention any follow-up work in the description.

## Environment & Configuration Tips
Store secrets in `.env`; never commit them. Local development assumes PostgreSQL credentials from `.env`. Toggle runtime modes via `DJANGO_SETTINGS_MODULE` if you need non-default settings. For ASGI deployments, point your process manager at `main.py` or `config.asgi:application`, ensure static files are collected, and configure S3 credentials for `django-storages` before enabling file uploads.
