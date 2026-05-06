from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.assignments.models import CourseAssignment
from apps.assignments.serializers import (
    AssignDepartmentSerializer,
    AssignmentCreateSerializer,
    AssignmentSerializer,
    AssignmentTargetSerializer,
)
from apps.companies.models import Employee
from apps.users.models import Roles


def _hr_company_ids(user):
    return list(
        Employee.objects.filter(user=user, is_hr_manager=True).values_list(
            "company_id", flat=True
        )
    )


def _can_manage(user, assignment):
    if user.role == Roles.ADMIN:
        return True
    if user.role == Roles.HR_MANAGER:
        return Employee.objects.filter(
            user=user, company=assignment.company, is_hr_manager=True
        ).exists()
    return False


def _queue_materialization(assignment_id, **kwargs):
    try:
        from apps.assignments.tasks import materialize_assignment_targets

        materialize_assignment_targets.delay(assignment_id, **kwargs)
    except Exception:
        pass


class CourseAssignmentViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AssignmentSerializer

    def get_queryset(self):
        return self._base_qs()

    def _base_qs(self):
        if getattr(self, "swagger_fake_view", False):
            return CourseAssignment.objects.none()
        user = self.request.user
        qs = CourseAssignment.objects.select_related("course", "company", "assigned_by")
        if user.role == Roles.ADMIN:
            return qs
        if user.role == Roles.HR_MANAGER:
            return qs.filter(company_id__in=_hr_company_ids(user))
        return qs.none()

    def _annotated_qs(self):
        return self._base_qs().annotate(
            total_targets=Count("targets", distinct=True),
            completed_targets=Count(
                "targets",
                filter=Q(targets__completion_record__completed=True),
                distinct=True,
            ),
        )

    # GET /assignments/
    def list(self, request):
        if request.user.role not in (Roles.ADMIN, Roles.HR_MANAGER):
            return Response(status=status.HTTP_403_FORBIDDEN)
        qs = self._annotated_qs().filter(is_active=True).order_by("-created_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                AssignmentSerializer(page, many=True).data
            )
        return Response(AssignmentSerializer(qs, many=True).data)

    # POST /assignments/
    def create(self, request):
        if request.user.role not in (Roles.ADMIN, Roles.HR_MANAGER):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = AssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = serializer.validated_data["company"]

        if request.user.role == Roles.HR_MANAGER:
            if company.pk not in _hr_company_ids(request.user):
                return Response(
                    {"detail": "You are not HR Manager of this company."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        assignment = serializer.save(assigned_by=request.user)

        scope = assignment.scope
        department_id = request.data.get("department_id")
        employee_id = request.data.get("employee_id")

        if scope == CourseAssignment.Scope.COMPANY:
            _queue_materialization(assignment.pk)
        elif scope == CourseAssignment.Scope.DEPARTMENT and department_id:
            _queue_materialization(assignment.pk, department_id=int(department_id))
        elif scope == CourseAssignment.Scope.INDIVIDUAL and employee_id:
            _queue_materialization(assignment.pk, employee_id=int(employee_id))

        return Response(
            AssignmentSerializer(self._annotated_qs().get(pk=assignment.pk)).data,
            status=status.HTTP_201_CREATED,
        )

    # GET /assignments/{id}/
    def retrieve(self, request, pk=None):
        assignment = get_object_or_404(self._annotated_qs(), pk=pk)
        if not _can_manage(request.user, assignment):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(AssignmentSerializer(assignment).data)

    # DELETE /assignments/{id}/
    def destroy(self, request, pk=None):
        assignment = get_object_or_404(self._base_qs(), pk=pk)
        if not _can_manage(request.user, assignment):
            return Response(status=status.HTTP_403_FORBIDDEN)
        assignment.is_active = False
        assignment.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    # POST /assignments/{id}/assign-department/
    @action(detail=True, methods=["post"], url_path="assign-department")
    def assign_department(self, request, pk=None):
        assignment = get_object_or_404(self._base_qs().filter(is_active=True), pk=pk)
        if not _can_manage(request.user, assignment):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = AssignDepartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        department = serializer.validated_data["department"]

        if department.company_id != assignment.company_id:
            return Response(
                {"detail": "Department does not belong to this company."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _queue_materialization(assignment.pk, department_id=department.pk)

        try:
            from apps.notifications.tasks import send_bulk_assignment_emails

            send_bulk_assignment_emails.delay(assignment.pk, department.pk)
        except Exception:
            pass

        return Response(
            {"detail": "Department assignment queued.", "department_id": department.pk},
            status=status.HTTP_202_ACCEPTED,
        )

    # GET /assignments/{id}/targets/
    @action(detail=True, methods=["get"], url_path="targets")
    def targets(self, request, pk=None):
        assignment = get_object_or_404(self._base_qs(), pk=pk)
        if not _can_manage(request.user, assignment):
            return Response(status=status.HTTP_403_FORBIDDEN)
        qs = assignment.targets.select_related(
            "employee__user", "completion_record"
        ).order_by("employee__user__full_name")
        return Response(AssignmentTargetSerializer(qs, many=True).data)
