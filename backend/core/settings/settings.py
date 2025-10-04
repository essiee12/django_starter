from ..ckeditor5 import *

from ..jwt import *

from .base import *


AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "base.paginators.CustomPagination",
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    "EXCEPTION_HANDLER": "base.exceptions.custom_exception_handler",
    "PAGE_SIZE": 100,
}


AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]


SWAGGER_SETTINGS = {
    "LOGIN_URL": "admin:login",
    "LOGOUT_URL": "admin:logout",
    "DOC_EXPANSION": "list",
    "DEEP_LINKING": True,
    "DEFAULT_MODEL_RENDERING": "example",
    "COMPONENT_SPLIT_REQUEST": True,
}


EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = env("EMAIL_HOST")
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_RECIPIENT_LIST = env("EMAIL_RECIPIENT_LIST")
