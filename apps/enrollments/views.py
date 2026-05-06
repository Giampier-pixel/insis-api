from drf_spectacular.utils import extend_schema

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.courses.models import Lesson
from apps.enrollments.models import Enrollment, LessonProgress
from apps.enrollments.serializers import (
    CompleteLessonSerializer,
    EnrollmentCreateSerializer,
    EnrollmentDetailSerializer,
    EnrollmentSerializer,
    LessonProgressSerializer,
)
from apps.users.models import Roles


class EnrollmentViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EnrollmentSerializer

    def _annotated_qs(self):
        return Enrollment.objects.select_related("student", "course").annotate(
            total_lessons=Count(
                "course__lessons",
                filter=Q(
                    course__lessons__deleted_at__isnull=True,
                    course__lessons__is_published=True,
                ),
                distinct=True,
            ),
            completed_lessons=Count(
                "lesson_progresses",
                filter=Q(lesson_progresses__completed=True),
                distinct=True,
            ),
        )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Enrollment.objects.none()
        user = self.request.user
        qs = self._annotated_qs()
        if user.role == Roles.ADMIN:
            return qs
        if user.role == Roles.INSTRUCTOR:
            return qs.filter(course__instructor=user)
        return qs.filter(student=user)

    # GET /enrollments/
    def list(self, request):
        qs = self.get_queryset().order_by("-enrolled_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                EnrollmentSerializer(page, many=True).data
            )
        return Response(EnrollmentSerializer(qs, many=True).data)

    # POST /enrollments/
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
        enrollment = Enrollment.objects.create(
            student=request.user,
            course=course,
            source=Enrollment.Source.DIRECT,
        )
        return Response(
            EnrollmentSerializer(self._annotated_qs().get(pk=enrollment.pk)).data,
            status=status.HTTP_201_CREATED,
        )

    # GET /enrollments/{id}/
    def retrieve(self, request, pk=None):
        enrollment = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(EnrollmentDetailSerializer(enrollment).data)

    # DELETE /enrollments/{id}/
    def destroy(self, request, pk=None):
        enrollment = get_object_or_404(
            Enrollment.objects.filter(student=request.user), pk=pk
        )
        enrollment.is_active = False
        enrollment.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    # POST /enrollments/{id}/complete-lesson/
    @extend_schema(
        tags=["enrollments"],
        request=CompleteLessonSerializer,
        responses={200: LessonProgressSerializer},
        description=(
            "Mark a lesson as completed for the authenticated student's enrollment."
        ),
    )
    @action(detail=True, methods=["post"], url_path="complete-lesson")
    def complete_lesson(self, request, pk=None):
        enrollment = get_object_or_404(
            Enrollment.objects.filter(student=request.user, is_active=True), pk=pk
        )
        serializer = CompleteLessonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson_id = serializer.validated_data["lesson_id"]
        time_spent = serializer.validated_data["time_spent_seconds"]

        lesson = get_object_or_404(
            Lesson.objects.all(), pk=lesson_id, course=enrollment.course
        )

        with transaction.atomic():
            progress, created = LessonProgress.objects.get_or_create(
                enrollment=enrollment,
                lesson=lesson,
                defaults={
                    "completed": True,
                    "completed_at": timezone.now(),
                    "time_spent_seconds": time_spent,
                },
            )
            if not created and not progress.completed:
                progress.completed = True
                progress.completed_at = timezone.now()
                progress.time_spent_seconds = time_spent
                progress.save(
                    update_fields=[
                        "completed",
                        "completed_at",
                        "time_spent_seconds",
                    ]
                )

        return Response(LessonProgressSerializer(progress).data)

    # GET /enrollments/{id}/progress/
    @action(detail=True, methods=["get"], url_path="progress")
    def progress(self, request, pk=None):
        enrollment = get_object_or_404(self.get_queryset(), pk=pk)
        all_lessons = Lesson.objects.filter(
            course=enrollment.course, is_published=True
        ).order_by("order")
        lesson_progress_map = {
            lp.lesson_id: lp
            for lp in enrollment.lesson_progresses.select_related("lesson").all()
        }
        total = all_lessons.count()
        done = sum(1 for lp in lesson_progress_map.values() if lp.completed)
        pct = round((done / total) * 100, 1) if total > 0 else 0

        lessons_data = []
        for lesson in all_lessons:
            lp = lesson_progress_map.get(lesson.id)
            lessons_data.append(
                {
                    "lesson_id": lesson.id,
                    "lesson_title": lesson.title,
                    "lesson_order": lesson.order,
                    "completed": lp.completed if lp else False,
                    "completed_at": lp.completed_at if lp else None,
                    "time_spent_seconds": lp.time_spent_seconds if lp else 0,
                }
            )

        return Response(
            {
                "enrollment_id": enrollment.id,
                "course_slug": enrollment.course.slug,
                "total_lessons": total,
                "completed_lessons": done,
                "progress_pct": pct,
                "completed": enrollment.completed,
                "completed_at": enrollment.completed_at,
                "lessons": lessons_data,
            }
        )

    # GET /enrollments/my-certificates/
    @action(detail=False, methods=["get"], url_path="my-certificates")
    def my_certificates(self, request):
        qs = (
            self._annotated_qs()
            .filter(
                student=request.user,
                completed=True,
                is_active=True,
            )
            .order_by("-completed_at")
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                EnrollmentSerializer(page, many=True).data
            )
        return Response(EnrollmentSerializer(qs, many=True).data)
