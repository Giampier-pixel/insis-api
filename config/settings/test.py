"""
Fast test settings for pytest/coverage.

MySQL migration integrity is verified separately; unit/API tests use SQLite so
the CI quality gate can run quickly and deterministically.
"""

from .local import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test.sqlite3",  # noqa: F405
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
