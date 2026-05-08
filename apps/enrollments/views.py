from django.db.models import Count, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.enrollments.models import Certificate, Enrollment
from apps.enrollments.serializers import (
    CertificateSerializer,
    EnrollmentCreateSerializer,
    EnrollmentSerializer,
)
from apps.users.models import Roles


class EnrollmentViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EnrollmentSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Enrollment.objects.none()
        user = self.request.user
        qs = Enrollment.objects.select_related("student", "course")
        if user.role == Roles.ADMIN:
            return qs
        if user.role == Roles.INSTRUCTOR:
            return qs.filter(course__instructor=user)
        return qs.filter(student=user)

    def list(self, request):
        qs = self.get_queryset().order_by("-enrolled_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                EnrollmentSerializer(page, many=True, context={"request": request}).data
            )
        return Response(EnrollmentSerializer(qs, many=True, context={"request": request}).data)

    def create(self, request):
        if request.user.role != Roles.STUDENT:
            return Response(
                {"detail": "Only students can enroll."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = EnrollmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.validated_data["course"]

        if Enrollment.objects.filter(student=request.user, course=course).exists():
            return Response(
                {"detail": "Already enrolled in this course."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        enrollment = Enrollment.objects.create(student=request.user, course=course)
        return Response(
            EnrollmentSerializer(
                Enrollment.objects.get(pk=enrollment.pk),
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk=None):
        enrollment = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(EnrollmentSerializer(enrollment, context={"request": request}).data)

    def destroy(self, request, pk=None):
        enrollment = get_object_or_404(
            Enrollment.objects.filter(student=request.user), pk=pk
        )
        enrollment.is_active = False
        enrollment.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CertificateViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CertificateSerializer

    def get_queryset(self):
        return Certificate.objects.select_related("course", "student").filter(
            student=self.request.user
        )

    def list(self, request):
        qs = self.get_queryset().order_by("-generated_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                CertificateSerializer(page, many=True, context={"request": request}).data
            )
        return Response(
            CertificateSerializer(qs, many=True, context={"request": request}).data
        )

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        cert = get_object_or_404(self.get_queryset(), pk=pk, is_ready=True)
        if not cert.pdf_file:
            return Response(
                {"detail": "Certificate PDF not yet generated."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(
            cert.pdf_file.open("rb"),
            as_attachment=True,
            filename=f"certificado_{cert.course.slug}.pdf",
            content_type="application/pdf",
        )
