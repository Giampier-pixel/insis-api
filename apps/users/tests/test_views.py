import pytest

from rest_framework.test import APIClient

from apps.users.models import CustomUser, Roles


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def registered_user(db):
    user = CustomUser.objects.create_user(
        email="existing@example.com",
        full_name="Existing User",
        password="testpass123!",
    )
    return user


def get_tokens(client, email, password):
    response = client.post(
        "/api/v1/auth/login/",
        {"email": email, "password": password},
        format="json",
    )
    return response.data


@pytest.mark.django_db
def test_register_success(client):
    response = client.post(
        "/api/v1/auth/register/",
        {
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "newpass123!",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["email"] == "newuser@example.com"


@pytest.mark.django_db
def test_register_duplicate_email(client, registered_user):
    response = client.post(
        "/api/v1/auth/register/",
        {
            "email": "existing@example.com",
            "full_name": "Another User",
            "password": "testpass123!",
        },
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_register_role_cannot_be_set(client):
    response = client.post(
        "/api/v1/auth/register/",
        {
            "email": "hacker@example.com",
            "full_name": "Hacker",
            "password": "testpass123!",
            "role": "ADMIN",
        },
        format="json",
    )
    assert response.status_code == 201
    user = CustomUser.objects.get(email="hacker@example.com")
    assert user.role == Roles.STUDENT


@pytest.mark.django_db
def test_login_success(client, registered_user):
    response = client.post(
        "/api/v1/auth/login/",
        {"email": "existing@example.com", "password": "testpass123!"},
        format="json",
    )
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_login_wrong_password(client, registered_user):
    response = client.post(
        "/api/v1/auth/login/",
        {"email": "existing@example.com", "password": "wrongpassword"},
        format="json",
    )
    assert response.status_code in (400, 401)


@pytest.mark.django_db
def test_logout_blacklists_token(client, registered_user):
    tokens = get_tokens(client, "existing@example.com", "testpass123!")
    access = tokens["access"]
    refresh = tokens["refresh"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = client.post(
        "/api/v1/auth/logout/",
        {"refresh": refresh},
        format="json",
    )
    assert response.status_code in (200, 205)

    client.credentials()
    refresh_response = client.post(
        "/api/v1/auth/token/refresh/",
        {"refresh": refresh},
        format="json",
    )
    assert refresh_response.status_code in (400, 401)


@pytest.mark.django_db
def test_me_authenticated(client, registered_user):
    tokens = get_tokens(client, "existing@example.com", "testpass123!")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    response = client.get("/api/v1/auth/me/")
    assert response.status_code == 200
    assert response.data["email"] == "existing@example.com"


@pytest.mark.django_db
def test_me_unauthenticated(client):
    response = client.get("/api/v1/auth/me/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_patch_me(client, registered_user):
    tokens = get_tokens(client, "existing@example.com", "testpass123!")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    response = client.patch(
        "/api/v1/auth/me/",
        {"full_name": "Updated Name"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["full_name"] == "Updated Name"


@pytest.mark.django_db
def test_change_password_success(client, registered_user):
    tokens = get_tokens(client, "existing@example.com", "testpass123!")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    response = client.post(
        "/api/v1/auth/change-password/",
        {"current_password": "testpass123!", "new_password": "newsecurepass456!"},
        format="json",
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_change_password_wrong_current(client, registered_user):
    tokens = get_tokens(client, "existing@example.com", "testpass123!")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    response = client.post(
        "/api/v1/auth/change-password/",
        {"current_password": "wrongcurrent!", "new_password": "newsecurepass456!"},
        format="json",
    )
    assert response.status_code == 400
