# settings/localtest.py
from .settings import *

# Use cache in testing
CACHES["default"]["KEY_PREFIX"] = "test_"

MEDIA_ROOT = "/tempmedia"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
