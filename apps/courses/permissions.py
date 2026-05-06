from rest_framework.permissions import BasePermission

from apps.users.models import Roles


class IsInstructorOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (Roles.ADMIN, Roles.INSTRUCTOR)
        )


class IsCourseOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.role == Roles.ADMIN:
            return True
        return obj.instructor_id == request.user.pk
