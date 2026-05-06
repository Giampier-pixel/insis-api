import pytest

from apps.users.models import CustomUser, UserProfile


@pytest.mark.django_db
def test_email_normalized_to_lowercase():
    user = CustomUser.objects.create_user(
        email="Test.User@Example.COM",
        full_name="Test User",
        password="strongpass123",
    )
    assert user.email == "test.user@example.com"


@pytest.mark.django_db
def test_user_profile_created_on_user_save():
    user = CustomUser.objects.create_user(
        email="profiletest@example.com",
        full_name="Profile Test",
        password="strongpass123",
    )
    assert UserProfile.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_soft_delete_user():
    user = CustomUser.objects.create_user(
        email="softdelete@example.com",
        full_name="Soft Delete",
        password="strongpass123",
    )
    pk = user.pk
    user.delete()
    assert CustomUser.objects.filter(pk=pk).count() == 0
    assert CustomUser.all_objects.filter(pk=pk).count() == 1


@pytest.mark.django_db
def test_create_superuser():
    superuser = CustomUser.objects.create_superuser(
        email="admin@example.com",
        full_name="Admin User",
        password="superpassword123",
    )
    assert superuser.is_staff is True
    assert superuser.is_superuser is True
