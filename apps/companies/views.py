import csv
import io

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.crypto import get_random_string

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.companies.models import Company, Department, Employee
from apps.companies.serializers import (
    CompanySerializer,
    CompanyStatsSerializer,
    DepartmentSerializer,
    EmployeeBulkImportSerializer,
    EmployeeCreateSerializer,
    EmployeeSerializer,
)
from apps.users.models import Roles
from apps.users.permissions import IsAdmin

User = get_user_model()


def _is_hr_of_company(user, company):
    return Employee.objects.filter(
        user=user, company=company, is_hr_manager=True
    ).exists()


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Company.objects.none()
        user = self.request.user
        if user.role == Roles.HR_MANAGER:
            return Company.objects.filter(
                employees__user=user, employees__is_hr_manager=True
            ).distinct()
        return Company.objects.all()

    def get_permissions(self):
        if self.action in ("create", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        if request.user.role not in (Roles.ADMIN, Roles.HR_MANAGER):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        company = self.get_object()
        if request.user.role != Roles.ADMIN and not _is_hr_of_company(
            request.user, company
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(self.get_serializer(company).data)

    @action(detail=True, methods=["get", "post"], url_path="departments")
    def departments(self, request, pk=None):
        company = self.get_object()
        is_admin = request.user.role == Roles.ADMIN
        is_hr = _is_hr_of_company(request.user, company)
        if not (is_admin or is_hr):
            return Response(status=status.HTTP_403_FORBIDDEN)

        if request.method == "GET":
            serializer = DepartmentSerializer(company.departments.all(), many=True)
            return Response(serializer.data)

        serializer = DepartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(company=company)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"departments/(?P<dept_pk>[^/.]+)",
    )
    def department_detail(self, request, pk=None, dept_pk=None):
        from django.shortcuts import get_object_or_404

        company = self.get_object()
        is_admin = request.user.role == Roles.ADMIN
        is_hr = _is_hr_of_company(request.user, company)
        if not (is_admin or is_hr):
            return Response(status=status.HTTP_403_FORBIDDEN)

        department = get_object_or_404(Department, pk=dept_pk, company=company)

        if request.method == "DELETE":
            department.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = DepartmentSerializer(department, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="stats")
    def stats(self, request, pk=None):
        company = self.get_object()
        is_admin = request.user.role == Roles.ADMIN
        is_hr = _is_hr_of_company(request.user, company)
        if not (is_admin or is_hr):
            return Response(status=status.HTTP_403_FORBIDDEN)

        data = {
            "total_employees": company.employees.count(),
            "total_departments": company.departments.count(),
            "hr_managers": company.employees.filter(is_hr_manager=True).count(),
        }
        return Response(CompanyStatsSerializer(data).data)


class EmployeeViewSet(viewsets.GenericViewSet):
    serializer_class = EmployeeSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Employee.objects.none()
        user = self.request.user
        if user.role == Roles.ADMIN:
            return Employee.objects.all().select_related(
                "user", "company", "department"
            )
        if user.role == Roles.HR_MANAGER:
            company_ids = Employee.objects.filter(
                user=user, is_hr_manager=True
            ).values_list("company_id", flat=True)
            return Employee.objects.filter(company_id__in=company_ids).select_related(
                "user", "company", "department"
            )
        return Employee.objects.none()

    def _hr_company(self, user):
        emp = (
            Employee.objects.filter(user=user, is_hr_manager=True)
            .select_related("company")
            .first()
        )
        return emp.company if emp else None

    def list(self, request):
        if request.user.role not in (Roles.ADMIN, Roles.HR_MANAGER):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        from django.shortcuts import get_object_or_404

        if request.user.role not in (Roles.ADMIN, Roles.HR_MANAGER):
            return Response(status=status.HTTP_403_FORBIDDEN)
        employee = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(self.get_serializer(employee).data)

    def create(self, request):
        if request.user.role not in (Roles.ADMIN, Roles.HR_MANAGER):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = EmployeeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vdata = serializer.validated_data

        if request.user.role == Roles.HR_MANAGER:
            company = self._hr_company(request.user)
            if company is None:
                return Response(
                    {"detail": "You are not an HR Manager of any company."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            company_id = request.data.get("company")
            if not company_id:
                return Response(
                    {"company": ["This field is required."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                company = Company.objects.get(pk=company_id)
            except Company.DoesNotExist:
                return Response(
                    {"company": ["Company not found."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        department = vdata.get("department")
        if department and department.company_id != company.pk:
            return Response(
                {"department": ["Department does not belong to this company."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user, created = User.objects.get_or_create(
                email=vdata["email"],
                defaults={
                    "full_name": vdata["full_name"],
                    "role": (
                        Roles.HR_MANAGER
                        if vdata.get("is_hr_manager")
                        else Roles.STUDENT
                    ),
                },
            )
            if created:
                user.set_password(get_random_string(20))
                user.save(update_fields=["password"])

            if Employee.objects.filter(user=user, company=company).exists():
                return Response(
                    {"detail": "Employee already exists in this company."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            employee = Employee.objects.create(
                user=user,
                company=company,
                department=department,
                is_hr_manager=vdata.get("is_hr_manager", False),
            )

        return Response(
            EmployeeSerializer(employee).data, status=status.HTTP_201_CREATED
        )

    def partial_update(self, request, pk=None):
        from django.shortcuts import get_object_or_404

        if request.user.role not in (Roles.ADMIN, Roles.HR_MANAGER):
            return Response(status=status.HTTP_403_FORBIDDEN)

        employee = get_object_or_404(self.get_queryset(), pk=pk)

        if request.user.role == Roles.HR_MANAGER and not _is_hr_of_company(
            request.user, employee.company
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = EmployeeSerializer(employee, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        from django.shortcuts import get_object_or_404

        if request.user.role not in (Roles.ADMIN, Roles.HR_MANAGER):
            return Response(status=status.HTTP_403_FORBIDDEN)

        employee = get_object_or_404(self.get_queryset(), pk=pk)

        if request.user.role == Roles.HR_MANAGER and not _is_hr_of_company(
            request.user, employee.company
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        employee.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        if request.user.role not in (Roles.ADMIN, Roles.HR_MANAGER):
            return Response(status=status.HTTP_403_FORBIDDEN)

        if request.user.role == Roles.ADMIN:
            company_id = request.data.get("company")
            if not company_id:
                return Response(
                    {"company": ["This field is required."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                company = Company.objects.get(pk=company_id)
            except Company.DoesNotExist:
                return Response(
                    {"company": ["Company not found."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            company = self._hr_company(request.user)
            if company is None:
                return Response(
                    {"detail": "You are not an HR Manager of any company."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = EmployeeBulkImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        csv_file = serializer.validated_data["file"]

        decoded = csv_file.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))
        if not {"email", "full_name"}.issubset(set(reader.fieldnames or [])):
            return Response(
                {"detail": "CSV must contain 'email' and 'full_name' headers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_count = 0
        errors = []
        with transaction.atomic():
            for i, row in enumerate(reader, start=2):
                email = row.get("email", "").lower().strip()
                full_name = row.get("full_name", "").strip()
                dept_name = row.get("department", "").strip()
                is_hr = row.get("is_hr_manager", "").strip().lower() in (
                    "true",
                    "1",
                    "yes",
                )

                if not email or not full_name:
                    errors.append(
                        {"row": i, "error": "email and full_name are required."}
                    )
                    continue

                department = None
                if dept_name:
                    department, _ = Department.objects.get_or_create(
                        company=company, name=dept_name
                    )

                user, _ = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "full_name": full_name,
                        "role": Roles.HR_MANAGER if is_hr else Roles.STUDENT,
                    },
                )
                _, emp_created = Employee.objects.get_or_create(
                    user=user,
                    company=company,
                    defaults={"department": department, "is_hr_manager": is_hr},
                )
                if emp_created:
                    created_count += 1

        return Response(
            {"created": created_count, "errors": errors},
            status=status.HTTP_201_CREATED,
        )
