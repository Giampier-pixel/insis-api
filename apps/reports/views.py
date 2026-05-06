from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.reports.data import (
    company_summary,
    completion_by_department,
    employee_ranking,
    overdue_assignments,
)
from apps.reports.models import ReportExportJob
from apps.reports.serializers import (
    ReportExportJobCreateSerializer,
    ReportExportJobSerializer,
    ReportQuerySerializer,
)
from apps.users.models import Roles


def _queue_export(job_id):
    try:
        from apps.reports.tasks import generate_report_export

        generate_report_export.delay(job_id)
    except Exception:
        pass


class ReportExportJobViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ReportExportJobSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ReportExportJob.objects.none()
        user = self.request.user
        qs = ReportExportJob.objects.select_related("company", "requested_by")
        if user.role == Roles.ADMIN:
            return qs
        if user.role == Roles.HR_MANAGER:
            return qs.filter(requested_by=user)
        return qs.none()

    def create(self, request):
        if request.user.role not in (Roles.ADMIN, Roles.HR_MANAGER):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = ReportExportJobCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        job = serializer.save(requested_by=request.user)
        _queue_export(job.pk)
        return Response(
            ReportExportJobSerializer(job, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk=None):
        job = self.get_object()
        return Response(
            ReportExportJobSerializer(job, context={"request": request}).data
        )

    def list(self, request):
        if request.user.role not in (Roles.ADMIN, Roles.HR_MANAGER):
            return Response(status=status.HTTP_403_FORBIDDEN)
        qs = self.get_queryset()
        company = request.query_params.get("company")
        if company:
            qs = qs.filter(company_id=company)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                ReportExportJobSerializer(
                    page,
                    many=True,
                    context={"request": request},
                ).data
            )
        return Response(
            ReportExportJobSerializer(
                qs,
                many=True,
                context={"request": request},
            ).data
        )


class ReportsViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ReportQuerySerializer

    def _company(self, request):
        serializer = ReportQuerySerializer(
            data=request.query_params,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data["company"]

    @action(detail=False, methods=["get"], url_path="company-summary")
    def company_summary(self, request):
        return Response(company_summary(self._company(request)))

    @action(detail=False, methods=["get"], url_path="completion-by-department")
    def completion_by_department(self, request):
        return Response(completion_by_department(self._company(request)))

    @action(detail=False, methods=["get"], url_path="employee-ranking")
    def employee_ranking(self, request):
        return Response(employee_ranking(self._company(request)))

    @action(detail=False, methods=["get"], url_path="overdue-assignments")
    def overdue_assignments(self, request):
        return Response(overdue_assignments(self._company(request)))
