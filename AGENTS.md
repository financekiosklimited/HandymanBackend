# Repository Guidelines

## Project Structure & Module Organization
Core Django apps live under `apps/`, each owning models, serializers, and services for its domain; extend the closest app (e.g., `apps/authn` for token flows). Project configuration and ASGI/WSGI entrypoints reside in `config/`, with environment tweaks in `config/settings/{base,dev,prod}.py`. Platform routers stay in `interfaces/api/{web,mobile}`, while shared utilities go in `apps/common`. Use `manage.py` for one-off commands, the `Makefile` for workflows, and never edit material under `secrets/` directly.

## Build, Test, and Development Commands
Initialize with `make setup` to create the uv environment, install dependencies, create the database, and run migrations. `make run` serves http://localhost:8000; `make shell` opens a Django REPL. Pair schema work with `make makemigrations` + `make migrate`, and confirm connectivity via `make check-postgres` before debugging. `make test` runs the suite, `make clean` purges caches, and `make fresh-setup` rebuilds from scratch.

## Coding Style & Naming Conventions
Stick to PEP 8, 4-space indentation, and module docstrings; functions, files, and package names stay `snake_case`, while classes follow `PascalCase` like `HandymanProfile`. Group related logic into `models.py`, `serializers.py`, and `views.py` within each app, leaning on `apps/common` for shared helpers. Static typing is optional, but the `[tool.pyright]` config lets editors or `uv run pyright` provide checks when needed.

## Testing Guidelines
Keep tests beside their app in `apps/<app>/tests.py`; break out a `tests/` package only when the module grows large. Use `django.test.TestCase` for database work and assert both success and failure paths, especially around permissions and JWT flows. Run `make test` before every push and replicate any failing scenario in the suite. Target sustained coverage on critical apps such as authentication and profiles.

## Commit & Pull Request Guidelines
Write imperative, ≤72-character subjects and bundle logically related changes. Adopt Conventional Commit prefixes (`feat`, `fix`, `refactor`, etc.) to keep a coherent changelog, e.g., `feat(authn): add OTP throttle`. Pull requests should highlight the problem, the solution, linked issues, and explicit testing proof (`make test`, manual curl sample, migrations run). Call out new environment variables or secrets so reviewers can configure locally.

## Security & Configuration Tips
Copy `.env.example` to `.env`, keep credentials local, and document any new variables in the README. JWT keys stay in `secrets/jwt_private.pem` and `secrets/jwt_public.pem`; swap paths per environment instead of editing the files. Lock down new integrations by validating settings defaults and avoiding hard-coded secrets in code.
