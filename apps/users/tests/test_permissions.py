from unittest.mock import MagicMock

import pytest

from rest_framework.test import APIRequestFactory

from apps.users.models import CustomUser, Roles
from apps.users.permissions import (
    IsAdmin,
    IsAdminOrReadOnly,
    IsHRManager,
    IsInstructor,
    IsStudent,
)


def make_request(user, method="GET"):
    factory = APIRequestFactory()
    request = getattr(factory, method.lower())("/")
    request.user = user
    return request


def make_user(role, db):
    return CustomUser.objects.create_user(
        email=f"{role.lower()}@example.com",
        full_name=role,
        password="pass12345!",
        role=role,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "permission_class,allowed_role,denied_role",
    [
        (IsAdmin, Roles.ADMIN, Roles.STUDENT),
        (IsInstructor, Roles.INSTRUCTOR, Roles.STUDENT),
        (IsStudent, Roles.STUDENT, Roles.ADMIN),
        (IsHRManager, Roles.HR_MANAGER, Roles.STUDENT),
    ],
)
def test_role_permission_grants_and_denies(
    permission_class, allowed_role, denied_role, db
):
    allowed_user = make_user(allowed_role, db)
    denied_user = make_user(denied_role, db)

    perm = permission_class()
    assert perm.has_permission(make_request(allowed_user), None) is True
    assert perm.has_permission(make_request(denied_user), None) is False


@pytest.mark.django_db
def test_admin_or_readonly_allows_safe_methods_for_any_authenticated(db):
    student = make_user(Roles.STUDENT, db)
    perm = IsAdminOrReadOnly()
    assert perm.has_permission(make_request(student, "GET"), None) is True
    assert perm.has_permission(make_request(student, "HEAD"), None) is True
    assert perm.has_permission(make_request(student, "OPTIONS"), None) is True


@pytest.mark.django_db
def test_admin_or_readonly_blocks_write_for_non_admin(db):
    student = make_user(Roles.STUDENT, db)
    perm = IsAdminOrReadOnly()
    assert perm.has_permission(make_request(student, "POST"), None) is False
    assert perm.has_permission(make_request(student, "PUT"), None) is False
    assert perm.has_permission(make_request(student, "DELETE"), None) is False


@pytest.mark.django_db
def test_admin_or_readonly_allows_write_for_admin(db):
    admin = make_user(Roles.ADMIN, db)
    perm = IsAdminOrReadOnly()
    assert perm.has_permission(make_request(admin, "POST"), None) is True


def test_unauthenticated_user_denied_all_permissions():
    anon = MagicMock()
    anon.is_authenticated = False
    for perm_class in [
        IsAdmin,
        IsInstructor,
        IsStudent,
        IsHRManager,
        IsAdminOrReadOnly,
    ]:
        perm = perm_class()
        assert perm.has_permission(make_request(anon), None) is False
