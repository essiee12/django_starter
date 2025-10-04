"""
Django settings
"""

import os
import sys
import environ
import pathlib

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    BACKEND_DOMAIN=(str),
    BACKEND_URL=(str),
    BACKEND_SLUG=(str),
    # Django
    ADMIN_URL=(str, "admin"),
    DJANGO_SECRET_KEY=(str),
    CACHE_PREFIX=(str, ""),
    # Directories
    DJANGO_STATIC_DIR=(str, "/static"),
    DJANGO_STATIC_URL=(str, "/static/"),
    DJANGO_MEDIA_URL=(str, "/media/"),
    DJANGO_MEDIA_ROOT=(str, "/media"),
    DJANGO_ALLOWED_HOSTS=(list, []),
    USE_DOCKER=(str, "yes"),
    # Sentry settings
    SENTRY_DSN=(str, ""),
    SENTRY_TRACE_SAMPLING_RATE=(int, 0.1),
    # Email settings
    EMAIL_HOST=(str, "host"),
    EMAIL_HOST_USER=(str, "host_user"),
    EMAIL_HOST_PASSWORD=(str, "host_password"),
    EMAIL_RECIPIENT_LIST=(list, []),
)

BACKEND_DOMAIN = env("BACKEND_DOMAIN")
BACKEND_URL = env("BACKEND_URL")
BACKEND_SLUG = env("BACKEND_SLUG")

SECRET_KEY = env("DJANGO_SECRET_KEY")

STATIC_ROOT = env("DJANGO_STATIC_DIR")
STATIC_URL = env("DJANGO_STATIC_URL")

MEDIA_URL = env("DJANGO_MEDIA_URL")
MEDIA_ROOT = env("DJANGO_MEDIA_ROOT")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

ADMIN_URL = env("ADMIN_URL")
DEBUG = env("DJANGO_DEBUG")

RUNNING_TESTS = "test" in sys.argv
ENABLE_DEBUG_TOOLBAR = DEBUG and not RUNNING_TESTS

ROOT_DIR = pathlib.Path(__file__).resolve(strict=True).parent.parent.parent

ROOT_APP_NAME = os.path.basename(environ.Path(__file__) - 2)

ALL_APP_NAMES = [
    app.name
    for app in ROOT_DIR.iterdir()
    if app.is_dir() and (ROOT_APP_NAME in app.name)
]

# Directory to dump common files (like exports)
COMMON_DIR = "/common"

# General settings
APPEND_SLASH = False

# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sitemaps",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "django_extensions",
    "django_celery_beat",
    "django_ckeditor_5",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt.token_blacklist",
    "drf_yasg",
    "django_filters",
    "django_json_widget",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "dj_rest_auth.registration",
]


USER_APPS = ["base", "users"]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + USER_APPS
if ENABLE_DEBUG_TOOLBAR:
    INSTALLED_APPS += ("debug_toolbar",)

INTERNAL_IPS = []
if ENABLE_DEBUG_TOOLBAR:
    INTERNAL_IPS += ["127.0.0.1", "10.0.2.2"]
    if env("USE_DOCKER") == "yes":
        import socket

        hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
        INTERNAL_IPS += [ip[:-1] + "1" for ip in ips]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]


if ENABLE_DEBUG_TOOLBAR:
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware") # pragma: no cover
elif not DEBUG:
    MIDDLEWARE.insert(0, "django.middleware.cache.UpdateCacheMiddleware") # pragma: no cover
    MIDDLEWARE.append("django.middleware.cache.FetchFromCacheMiddleware") # pragma: no cover


CSRF_TRUSTED_ORIGINS = [f"https://*{BACKEND_DOMAIN}"]
ROOT_URLCONF = f"{ROOT_APP_NAME}.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(ROOT_DIR / "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = f"{ROOT_APP_NAME}.wsgi.application"

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {
        "info_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/logs/info.log",
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,  # Save 5 files
        },
        "sentry": {
            "level": "ERROR",
            "class": "sentry_sdk.integrations.logging.EventHandler",
            "formatter": "verbose",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": dict(
        map(
            lambda app_name: (
                app_name,
                {
                    "handlers": ["info_file", "sentry", "console"],
                    "propagate": True,
                    "level": "INFO",
                },
            ),
            ALL_APP_NAMES + ["django"],
        )
    ),
}


# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Cache settings
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/1",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": env("CACHE_PREFIX"),
    }
}
CACHE_MIDDLEWARE_SECONDS = 0

# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Celery settings
CELERY_BROKER_URL = "redis://redis:6379"
CELERY_RESULT_BACKEND = "redis://redis:6379"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_SERIALIZER = "json"


# Django debug toolbar settings
# Always show toolbar in dev
def show_toolbar(request):
    """Show debug toolbar"""
    from django.conf import settings

    return settings.DEBUG


DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": ["debug_toolbar.panels.redirects.RedirectsPanel"],
    "SHOW_TEMPLATE_CONTEXT": True,
    "SHOW_TOOLBAR_CALLBACK": show_toolbar,
}


# Sentry settings
def traces_sampler(sampling_context):
    """Sentry sample traces"""
    try:
        # Don't sample ping method
        if (
            sampling_context["transaction_context"]["op"] == "http.server"
            and sampling_context["wsgi_environ"]["RAW_URI"] == "/ping"
        ):
            return 0
    except KeyError:
        # Handle the case where 'wsgi_environ' key is not present
        pass

    return SENTRY_TRACE_SAMPLING_RATE


SENTRY_DSN = env("SENTRY_DSN")
SENTRY_TRACE_SAMPLING_RATE = env("SENTRY_TRACE_SAMPLING_RATE")

sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[DjangoIntegration(), RedisIntegration()],
    traces_sampler=traces_sampler,
    environment=BACKEND_SLUG,
)
sentry_sdk.set_tag("backend", BACKEND_SLUG)

STATICFILES_DIRS = [str(ROOT_DIR / "static")]

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Social Auth Settings
SOCIALACCOUNT_ADAPTER = "users.adapters.SocialAccountAdapter"

SITE_ID = 1

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# Use email-only authentication and modern signup configuration
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
