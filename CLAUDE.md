# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**INSIS API** is a Django 5.2 REST Framework backend for an EdTech B2B/B2C platform (courses, enrollments, quizzes, reports). Stack: MySQL 8.4, Redis, Celery, JWT auth, deployed to Google Cloud Run.

## Development Commands

### Local dev (Docker)
```bash
docker-compose up --build          # Start all 6 services
docker-compose down                # Stop all services
docker-compose logs -f web         # Follow web logs

# Run management commands inside the container
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py makemigrations <app>
```

### Without Docker (requires local MySQL + Redis matching `.env`)
```bash
export DJANGO_SETTINGS_MODULE=config.settings.local
pip install -r requirements.txt -r requirements-dev.txt
python manage.py migrate
python manage.py runserver
```

### Testing
```bash
pytest                             # Run all tests (reuses DB)
pytest apps/users/                 # Run tests for a specific app
pytest -k test_login               # Run a single test by name
coverage run -m pytest && coverage report   # With coverage (target: 80%)
```

### Linting
```bash
flake8 apps/                       # Lint
black apps/                        # Format
isort apps/                        # Sort imports
```

### Celery (local, outside Docker)
```bash
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info
```

## Architecture

### Settings split
- `config/settings/base.py` — shared (DRF, JWT, Celery, pagination, throttling)
- `config/settings/local.py` — DEBUG=True, MySQL via Docker, console email
- `config/settings/production.py` — Cloud SQL (Unix socket), SMTP, GCS, WhiteNoise

Default `DJANGO_SETTINGS_MODULE` is `config.settings.local` (set in `manage.py`).

### URL structure
All APIs are prefixed `/api/v1/`. Schema UI: `/api/v1/schema/swagger-ui/`.

### Apps under `apps/`
- **core** — Abstract base models only (no views, no migrations needed):
  - `TimestampedModel` — `created_at` / `updated_at`
  - `SoftDeleteModel` + `SoftDeleteManager` — logical delete via `deleted_at`; use `objects.alive()` / `objects.dead()`; `hard_delete()` for physical removal
  - `TenantScopedModel` — marker for Company-scoped future models
- **users** — Auth + roles (`CustomUser` + `UserProfile`). Email-based auth (case-insensitive). Roles: `STUDENT`, `INSTRUCTOR`, `ADMIN`, `HR_MANAGER`, `SUPPORT`. `UserProfile` is auto-created on `CustomUser` post-save.

### Planned apps (not yet created)
`companies`, `courses`, `enrollments`, `quizzes`, `assignments`, `reports`, `notifications` — see `TODO.md` for roadmap and `PRD_INSIS_API.md` for requirements.

### Auth endpoints
```
POST /api/v1/auth/register/
POST /api/v1/auth/login/
POST /api/v1/auth/token/refresh/
POST /api/v1/auth/logout/          # Blacklists refresh token
GET|PATCH /api/v1/auth/me/
POST /api/v1/auth/change-password/
```

JWT: 30 min access / 7 day refresh, rotation enabled, blacklist on rotation.

### Permissions
Custom classes in `apps/users/permissions.py`: `IsAdmin`, `IsInstructor`, `IsStudent`, `IsHRManager`, `IsAdminOrReadOnly`. Use these instead of re-implementing role checks.

### Celery
App is in `config/celery.py`. Beat schedule (daily/weekly/monthly) references notification tasks under `apps/notifications/tasks` — not yet implemented. Broker/backend: Redis.

### Docker services
`web` (8081→8080), `db` MySQL (3308→3306), `redis` (6380→6379), `celery_worker`, `celery_beat`, `flower` (5556→5555).

**`entrypoint.sh` waits for DB and Redis but does NOT run migrations.** Always run `migrate` explicitly after container start.

## Key Conventions

- All new models should inherit from `TimestampedModel`. Add `SoftDeleteModel` when logical deletion is needed.
- Use `objects.alive()` in all queryset filters — never raw `filter()` that might return soft-deleted records unintentionally.
- New apps must be added to `INSTALLED_APPS` in `config/settings/base.py` (prefixed `apps.`).
- Tests live in `apps/<name>/tests/`. Shared factories go in `tests/factories.py`.
- Timezone is `America/Lima`; always use timezone-aware datetimes.

## Environment

Copy `.env.example` to `.env` for local dev. All production secrets are injected via Cloud Run / Secret Manager — never hard-code them.
