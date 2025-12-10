# AGENTS.md

## Commands
- **Install**: `make install` (uses uv)
- **Run tests**: `make test`
- **Single test**: `DJANGO_SETTINGS_MODULE=config.settings.test uv run python manage.py test apps.authn.tests.test_views_mobile.LoginViewTests.test_method`
- **Lint**: `make lint` / **Fix**: `make lint-fix`
- **Format**: `make format` / **Check**: `make format-check`
- **Coverage**: `make coverage`

## Code Style
- **Python 3.13**, line length 88, double quotes, 4-space indent (ruff)
- **Imports**: stdlib -> third-party (Django, DRF) -> first-party (`apps.*`, `config.*`) -> local
- **No type hints** (pyright disabled) - use docstrings instead
- **Naming**: PascalCase classes, snake_case functions/variables, UPPER_SNAKE_CASE constants

## Architecture
- **Service layer**: Business logic in `*Service` classes (e.g., `AuthService`), instantiated as singletons
- **Models**: Inherit from `apps.common.models.BaseModel` (provides `id`, `public_id`, `created_at`, `updated_at`)
- **Responses**: Use `apps.common.responses` helpers (`success_response`, `error_response`, `validation_error_response`, etc.)
- **Tests**: Use `django.test.TestCase`, `unittest.mock.patch`, `APIRequestFactory`

## Response Envelope
All APIs return: `{"message": "...", "data": {...}, "errors": null, "meta": null}`

## Workflow
- **Always run `make lint` and `make test` after any code changes**
- **New APIs**: Add detailed OpenAPI spec using `drf-spectacular` decorators (`@extend_schema`) with examples, request/response schemas, and descriptions
