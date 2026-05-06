from unittest.mock import MagicMock, patch

import pytest

from apps.users.models import CustomUser, UserProfile


@pytest.mark.django_db
def test_create_user_profile_signal_fires():
    user = CustomUser.objects.create_user(
        email="signal_test@example.com",
        full_name="Signal Test",
        password="pass12345!",
    )
    assert UserProfile.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_create_user_profile_not_duplicated_on_update():
    user = CustomUser.objects.create_user(
        email="nodedup@example.com",
        full_name="No Dup",
        password="pass12345!",
    )
    user.full_name = "Updated Name"
    user.save()
    assert UserProfile.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_welcome_email_task_called_on_register():
    mock_task = MagicMock()
    with patch.dict(
        "sys.modules",
        {"apps.notifications.tasks": MagicMock(send_welcome_email=mock_task)},
    ):
        user = CustomUser.objects.create_user(
            email="welcome@example.com",
            full_name="Welcome User",
            password="pass12345!",
        )
    mock_task.delay.assert_called_once_with(user.id)


@pytest.mark.django_db
def test_welcome_email_not_sent_on_update():
    user = CustomUser.objects.create_user(
        email="noemail_update@example.com",
        full_name="No Email Update",
        password="pass12345!",
    )
    mock_task = MagicMock()
    with patch.dict(
        "sys.modules",
        {"apps.notifications.tasks": MagicMock(send_welcome_email=mock_task)},
    ):
        user.full_name = "Changed"
        user.save()
    mock_task.delay.assert_not_called()


@pytest.mark.django_db
def test_welcome_email_silenced_when_notifications_missing():
    # Sin apps.notifications instalado, no debe lanzar excepción
    user = CustomUser.objects.create_user(
        email="noimport@example.com",
        full_name="No Import",
        password="pass12345!",
    )
    assert user.pk is not None
