"""
Django production settings for INSIS API project.

DEBUG=False, Cloud SQL via Auth Proxy, SMTP email, GCS storage.
"""

from decouple import Csv, config

from .base import *  # noqa: F401, F403

# ============================================================
# Debug
# ============================================================
DEBUG = False

# ============================================================
# Security
# ============================================================
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False  # Cloud Run handles TLS termination
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ============================================================
# Database — Cloud SQL via Auth Proxy (Unix socket)
# ============================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT", default="3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ============================================================
# Email — SMTP real
# ============================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")

# ============================================================
# Static files — WhiteNoise
# ============================================================
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ============================================================
# CORS (producción)
# ============================================================
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

# ============================================================
# GCS (reports)
# ============================================================
USE_GCS = config("USE_GCS", default=True, cast=bool)
GCS_BUCKET_NAME = config("GCS_BUCKET_NAME", default="insis-reports")
