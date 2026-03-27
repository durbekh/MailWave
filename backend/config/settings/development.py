"""
Development settings for MailWave project.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Use console email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Add browsable API renderer in development
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# Disable throttling in development
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405

# CORS - allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Use SQLite for quick local development if PostgreSQL is unavailable
import os
if os.environ.get("USE_SQLITE", "False") == "True":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        }
    }

# Simpler static file storage for development
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# Create logs directory if needed
import os
os.makedirs(BASE_DIR / "logs", exist_ok=True)  # noqa: F405
