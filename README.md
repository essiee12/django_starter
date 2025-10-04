# Django Starter Template

A batteries-included Django 5 starter that focuses on API-first applications with production-ready defaults. It ships with a custom user model, JWT authentication, Celery workers, Docker-based deployment, and a streamlined local developer workflow powered by [uv](https://github.com/astral-sh/uv).

## Highlights
- **Layered architecture** - versioned API under `api/v1`, modular settings (`base.py`, `settings.py`, `localtest.py`, `production.py`), and reusable `base`/`users` apps.
- **Auth & user management** - email-first custom `User` model, JWT (SimpleJWT) integration, OTP verification hooks, and Google OAuth (allauth) ready to wire into routing.
- **Async & scheduling** - Celery configured with Redis for both broker and result backend, sample periodic tasks, and Django Celery Beat baked in.
- **Content & rich text** - CKEditor 5 integration with authenticated upload endpoint that rewrites URLs against `BACKEND_URL`.
- **Observability & operations** - Sentry SDK, file/console logging, health/config endpoints, cache middleware, and environment-driven settings.
- **Developer experience** - `uv` for dependency management, `runserver_plus` auto-reload via `watchmedo`, debug toolbar in development, and formatting helpers.

## Ideal Use Cases
- SaaS/back-office products that need secure CRUD APIs and background jobs out of the box.
- Greenfield Django projects that want production-ready Docker & Nginx deployment defaults.
- Teams standardising on JWT-based auth with optional social login and OTP flows.
- Projects that plan to send transactional emails and process files asynchronously.

## Tech Stack at a Glance
- Python 3.13, Django 5.2, Django REST Framework, SimpleJWT, django-allauth
- PostgreSQL, Redis, Celery + Celery Beat
- drf-yasg & drf-spectacular for OpenAPI/Swagger
- Sentry SDK, django-environ, django-celery-beat, django-ckeditor-5
- Docker & Docker Compose, uv (package/dependency manager)

## Project Layout
```
backend/
├── core/                 # Global settings, Celery app, JWT config, project URLs
├── base/                 # Reusable mixins, pagination, Config model, health views, exceptions, tests
├── users/                # Custom user model, serializers, viewsets, admin customizations, tests and tasks
├── static/               # Static files (CSS, JS, images)
├── templates/            # Global templates (emails, admin overrides, etc.)
│
compose/
├── local/                # Dockerfile & scripts for local development (watchmedo, runserver_plus)
└── production/           # Dockerfiles & entrypoints for gunicorn/nginx/celery
│
envs/                     # Shell-friendly environment variable templates
local.yml                 # Docker Compose for local development
production.yml            # Docker Compose for production deployment
```

## Requirements
- Python 3.13 (matches `pyproject.toml`)
- [uv](https://github.com/astral-sh/uv) >= 0.8 (recommended) or pip
- PostgreSQL 15+ and Redis 7+ (if you run services outside Docker)
- Docker & Docker Compose (for containerised workflows)
- Make sure the host has `watchmedo` (installed via `watchdog`) if you use the provided scripts

## Configuration

The stack expects environment variables to be defined through the files in `envs/` (all values are simple `KEY=value` pairs so they work both for Docker Compose and for direct shell usage).

### Local profiles
- `envs/local/django` — Django-specific flags (`DJANGO_SECRET_KEY`, domains, SMTP, etc.).
- `envs/local/postgres` — Credentials for the Postgres container.

Docker Compose automatically loads both files, so in most cases no manual export is required. If you want to run a command outside of Compose, you can source them manually:
```bash
set -a
source envs/local/postgres
source envs/local/django
set +a
```

### Production
`envs/production/readme.md` walks through creating `.envs/.production/.config` and `.envs/.production/.keys`. Those files are mounted by `production.yml` and should never be committed to version control.

## Local Development (Docker Compose)
1. Ensure `data/` directories exist for bind mounts:
   ```bash
   mkdir -p data/{logs,common,media,backups}
   ```
2. Build and start the stack:
   ```bash
   docker compose -f local.yml up --build
   ```
   - Django app: http://localhost:8000
   - Postgres & Redis run inside the compose stack.
3. Run database migrations and create a superuser (one-off commands always go through the Django service container):
   ```bash
   docker compose -f local.yml run --rm django uv run manage.py migrate
   docker compose -f local.yml run --rm django uv run manage.py createsuperuser
   ```
4. Tail logs during development:
   ```bash
   docker compose -f local.yml logs -f django
   ```
5. (Optional) Run Celery worker/beat using the provided profile:
   ```bash
   docker compose -f local.yml --profile celery up --build
   ```
6. Stop everything with `docker compose -f local.yml down`

### One-off commands cheat sheet
- Start an interactive shell: `docker compose -f local.yml run --rm django uv run manage.py shell`
- Collect static files: `docker compose -f local.yml run --rm django uv run manage.py collectstatic`
- Open the Django shell-plus debugger: `docker compose -f local.yml run --rm django uv run manage.py shell_plus`

Containers rely on the same env files under `envs/local/`; edit them before `up`.

## Tests & Code Quality
- Run Django tests:
  ```bash
  docker compose -f local.yml run --rm django uv run manage.py test
  ```
- Run coverage:
  ```bash
  docker compose -f local.yml run --rm django uv run coverage run manage.py test
  docker compose -f local.yml run --rm django uv run coverage html
  ```
- Format and prune imports:
  ```bash
  docker compose -f local.yml run --rm django uv run black .
  docker compose -f local.yml run --rm django uv run \
    autoflake --imports=django,requests,urllib3 --in-place --remove-unused-variables $(find backend -name '*.py')
  ```
  (The helper script `compose/local/django/formatcode` wraps the commands.)

## API & UI Endpoints
- `GET /ping` - lightweight health check.
- `GET /iconfig` - diff-style settings viewer (superuser only).
- Admin panel at `/<ADMIN_URL>/` (defaults to `/admin/`).
- Swagger UI at `/api/v1/docs/` (requires authentication; log in via admin or session first).
- CKEditor upload endpoint at `/ckeditor5/image_upload/` (honours `BACKEND_URL`).

### Users API (`api/v1/users/` namespace)
- `POST /api/v1/users/login/` - email/password login returning JWT pair and user profile.
- `POST /api/v1/users/token/refresh/` - refresh access tokens.
- `GET /api/v1/users/details/` - current user profile (requires auth).
- `POST /api/v1/users/` - register a new user and trigger OTP email via Celery (implement `users.tasks.send_otp_to_user_mail`).
- `POST /api/v1/users/otp-request/` & `POST /api/v1/users/otp-verification/` - OTP flow for email verification/login.
- `POST /api/v1/users/password-change/` & `POST /api/v1/users/forgot-password/` - password management endpoints.
- `POST /api/v1/users/logout/` - blacklist refresh tokens.
- Google social login view (`users.views.GoogleLoginView`) is ready to be routed when you configure OAuth credentials.

## Core Modules
- `core.settings` - env-driven settings, Redis cache, JWT defaults (`core/jwt.py`), Sentry setup, and CKEditor config.
- `base` app - reusable model mixins (`BaseModel`, `BaseUserModel` with ShortUUID primary keys), DRF viewset base classes, custom pagination, `Config` model for feature flags, and shared exception handler.
- `users` app - custom `User` model, admin forms with avatar previews, DRF serializers/viewsets for auth flows, OTP utilities, and hooks for Celery-powered email delivery.

## Observability & Ops
- Logs stream to console and rotate into `/logs` inside containers (5 MB per file, 5 backups).
- Sentry instrumentation is wired; set `SENTRY_DSN` & `SENTRY_TRACE_SAMPLING_RATE` to enable.
- Redis cache is enabled by default; tweak `CACHE_PREFIX` to avoid key collisions across environments.
- Health endpoints (`/ping`, `/iconfig`) assist load balancers and operational debugging.

## Deployment (Docker Compose)
1. Prepare production env files under `.envs/.production/` (see `envs/production/readme.md`).
2. Build images and launch:
   ```bash
   docker compose -f production.yml up --build -d
   ```
   - `django` runs Gunicorn and collects static files.
   - `nginx` exposes port `APP_PORT` (set in env file) and serves static/media.
   - `celery` & `celery-beat` services can be enabled when you need workers.
3. Volumes:
   - Database data sits in `django_template_production_postgres_data`.
   - Static files mount to `./data/django_template_production_staticfiles` for Nginx.
   - Media, logs, and common state (`/common`) reuse the host `data/` directory.
4. Review `compose/production/nginx/nginx.conf`; `BACKEND_DOMAIN` is templated at runtime via `envsubst`.

## Maintenance Tips
- Rebuild requirements after dependency changes with `uv lock` / `uv sync` (or regenerate `uv.lock`).
- Use `python manage.py diffsettings` (surfaced via `/iconfig`) to inspect configuration drifts.
- Persist Celery beat schedules in the shared `/common` volume to avoid losing periodic task state across restarts.
- ShortUUID primary keys are opaque strings-ensure API clients treat them as immutable identifiers.

Happy shipping!
