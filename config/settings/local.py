"""
Django local development settings for INSIS API project.

DEBUG=True, MySQL via docker-compose, console email backend.
"""

from decouple import config

from .base import *

# ============================================================
# Debug
# ============================================================
DEBUG = True

# ============================================================
# Database — MySQL local via docker-compose
# ============================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": config("DB_NAME", default="insis_db"),
        "USER": config("DB_USER", default="insis_user"),
        "PASSWORD": config("DB_PASSWORD", default="insis_dev_password"),
        "HOST": config("DB_HOST", default="db"),
        "PORT": config("DB_PORT", default="3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ============================================================
# CORS (frontend local)
# ============================================================
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://localhost:5173",
    cast=lambda v: [s.strip() for s in v.split(",")],
)

# ============================================================
# Email — console backend (prints to stdout)
# ============================================================
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
