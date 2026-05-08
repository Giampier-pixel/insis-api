from django.db.models import Count, Q

from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.courses.models import Course
from apps.courses.serializers import (
    CourseDetailSerializer,
    CourseListSerializer,
    CourseWriteSerializer,
)
from apps.users.models import Roles
from apps.users.permissions import IsAdmin, IsInstructor


def _is_owner(user, course):
    return course.instructor_id == user.pk


class CourseViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description", "instructor__full_name"]
    ordering_fields = ["created_at", "title"]
    ordering = ["-created_at"]

    def _annotated_qs(self):
        return (
            Course.objects.select_related("instructor")
            .annotate(
                quiz_count=Count(
                    "quizzes",
                    filter=Q(quizzes__is_active=True),
                    distinct=True,
                ),
                enrolled_count=Count(
                    "enrollments",
                    filter=Q(
                        enrollments__deleted_at__isnull=True,
                        enrollments__is_active=True,
                    ),
                    distinct=True,
                ),
            )
        )

    def get_queryset(self):
        user = self.request.user
        qs = self._annotated_qs()
        if not user.is_authenticated or user.role == Roles.STUDENT:
            return qs.filter(is_published=True)
        if user.role == Roles.INSTRUCTOR:
            return qs.filter(Q(is_published=True) | Q(instructor=user)).distinct()
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "partial_update"):
            return CourseWriteSerializer
        if self.action == "retrieve":
            return CourseDetailSerializer
        return CourseListSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        if self.action in ("create", "partial_update", "destroy"):
            return [IsAuthenticated()]
        return [IsAdmin()]

    def perform_create(self, serializer):
        if self.request.user.role == Roles.INSTRUCTOR:
            serializer.save(instructor=self.request.user)
        else:
            serializer.save()

    def partial_update(self, request, *args, **kwargs):
        course = self.get_object()
        if request.user.role != Roles.ADMIN and not _is_owner(request.user, course):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = CourseWriteSerializer(
            course,
            data=request.data,
            partial=True,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            CourseListSerializer(
                self._annotated_qs().get(slug=course.slug),
                context=self.get_serializer_context(),
            ).data
        )

    def destroy(self, request, *args, **kwargs):
        course = self.get_object()
        if request.user.role != Roles.ADMIN and not _is_owner(request.user, course):
            return Response(status=status.HTTP_403_FORBIDDEN)
        course.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="quizzes")
    def quizzes(self, request, slug=None):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        course = self.get_object()

        from apps.enrollments.models import Enrollment
        from apps.quizzes.models import Quiz
        from apps.quizzes.serializers import QuizListSerializer

        if request.user.role == Roles.STUDENT:
            if not Enrollment.objects.filter(
                student=request.user, course=course, is_active=True
            ).exists():
                return Response(
                    {"detail": "You must be enrolled to access course quizzes."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        qs = (
            Quiz.objects.filter(course=course, is_active=True)
            .annotate(question_count=Count("questions"))
            .order_by("id")
        )
        return Response(
            QuizListSerializer(qs, many=True, context=self.get_serializer_context()).data
        )
