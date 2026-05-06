import pytest
from celery.app.task import Task


@pytest.fixture(autouse=True)
def fast_isolated_tests(settings, monkeypatch):
    settings.PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]
    monkeypatch.setattr(Task, "delay", lambda self, *args, **kwargs: None)
