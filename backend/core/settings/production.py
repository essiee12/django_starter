# settings/production.py
from .settings import *

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

STATIC_ROOT = "/staticfiles"

MEDIA_ROOT = "/media"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False

CORS_ORIGIN_ALLOW_ALL = False
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB
