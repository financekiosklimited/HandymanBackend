# Repository Guidelines

## Project Structure & Module Organization
- Django 5 entrypoint is `manage.py`; reusable apps live under `apps/` (e.g., `accounts`, `authn`, `profiles`, `storage`).
- Shared utilities (email, mixins, enums) sit in `apps/common/`; ASGI startup is in `main.py`.
- Tests live beside their feature code (e.g., `apps/authn/tests/test_services.py`); settings variants are under `config/settings/` (`dev.py`, `prod.py`, `test.py`).
- Static assets collect into `staticfiles/`; runtime scripts and infra helpers stay at the project root.

## Build, Test, and Development Commands
- `make setup` — bootstrap the `uv` virtualenv, install dependencies, and run migrations.
- `make run` — start the local server with `config.settings.dev`.
- `make test` — run the full Django test suite using the SQLite-backed test settings.
- `make migrate` / `make makemigrations` — generate and apply schema changes.
- `make check-postgres` — verify `.env` credentials before talking to Postgres services.

## Coding Style & Naming Conventions
- Follow PEP 8 with four-space indentation and `snake_case` for modules, functions, and fields.
- Use `CamelCase` for models, serializers, and class-based views (e.g., `ProfileDetailView`).
- Run `make lint` (Ruff) before committing; prefer explicit imports within each app and keep business logic out of views when possible.
- Rely on structured logging via `logging.getLogger(__name__)` (see `apps/common/email.py`); avoid bare `print` in production code.

## Testing Guidelines
- Use Django `TestCase` or DRF `APITestCase`; name tests `test_<condition>_<expected>` inside `Test...` classes.
- Mock external systems (auth providers, S3, SMTP) and cover serializers, services, signals, and REST endpoints.
- The default test settings disable logging noise and use an in-memory database; run `make test` before every commit.

## Commit & Pull Request Guidelines
- Adopt Conventional Commit prefixes (`feat:`, `fix:`, `chore:`) with subjects under ~70 characters.
- Reference tickets where available, describe migrations or breaking changes, and confirm `make test`/`make lint` results.
- PRs should outline purpose, key changes, data/backfill steps, and include screenshots for any UI/admin impact.

## Security & Configuration Tips
- Keep secrets in `.env`; never commit credentials or generated keys.
- Switch environments by exporting `DJANGO_SETTINGS_MODULE` (e.g., `config.settings.dev`).
- Collect static files prior to deployment and configure S3 credentials for `django-storages` when targeting production.
