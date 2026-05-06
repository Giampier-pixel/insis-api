from rest_framework.permissions import BasePermission

from apps.users.models import Roles


class IsHRManagerOfCompany(BasePermission):
    """Require an HR manager Employee record for the target company."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Roles.HR_MANAGER
        )

    def has_object_permission(self, request, view, obj):
        from apps.companies.models import Company, Employee

        if isinstance(obj, Company):
            company = obj
        elif hasattr(obj, "company"):
            company = obj.company
        else:
            return False
        return Employee.objects.filter(
            user=request.user, company=company, is_hr_manager=True
        ).exists()
