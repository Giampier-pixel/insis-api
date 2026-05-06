from django_filters.rest_framework import DjangoFilterBackend

from django.db.models import Avg, Count, Q

from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.courses.filters import CourseFilter
from apps.courses.models import Category, Course, CourseReview, Lesson, Tag
from apps.courses.permissions import IsInstructorOrAdmin
from apps.courses.serializers import (
    CategorySerializer,
    CourseDetailSerializer,
    CourseListSerializer,
    CourseReviewSerializer,
    CourseWriteSerializer,
    LessonSerializer,
    TagSerializer,
)
from apps.users.models import Roles
from apps.users.permissions import IsAdmin


def _is_owner(user, course):
    return course.instructor_id == user.pk


def _course_queryset(base_qs, user):
    if not user.is_authenticated or user.role == Roles.STUDENT:
        return base_qs.filter(is_published=True)
    if user.role == Roles.INSTRUCTOR:
        return base_qs.filter(Q(is_published=True) | Q(instructor=user)).distinct()
    return base_qs


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAdmin()]


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    http_method_names = ["get", "post", "head", "options"]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsInstructorOrAdmin()]


class CourseViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = CourseFilter
    search_fields = ["title", "description", "instructor__full_name"]
    ordering_fields = ["created_at", "price"]
    ordering = ["-created_at"]

    def _annotated_qs(self):
        return (
            Course.objects.select_related("instructor", "category")
            .prefetch_related("tags")
            .annotate(
                avg_rating=Avg("reviews__rating"),
                review_count=Count("reviews", distinct=True),
                lesson_count=Count(
                    "lessons",
                    filter=Q(lessons__deleted_at__isnull=True),
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
        return _course_queryset(self._annotated_qs(), self.request.user)

    def get_serializer_class(self):
        if self.action in ("create", "partial_update"):
            return CourseWriteSerializer
        if self.action == "retrieve":
            return CourseDetailSerializer
        return CourseListSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        if self.action == "create":
            return [IsInstructorOrAdmin()]
        if self.action == "partial_update":
            return [IsAuthenticated()]
        if self.action in ("lessons", "lesson_update", "reviews", "quizzes"):
            return [AllowAny()]
        return [IsAdmin()]

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

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


    @action(detail=True, methods=["get", "post"], url_path="lessons")
    def lessons(self, request, slug=None):
        course = self.get_object()

        if request.method == "GET":
            if not request.user.is_authenticated:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
            qs = course.lessons.order_by("order")
            if not (
                request.user.role == Roles.ADMIN or _is_owner(request.user, course)
            ):
                qs = qs.filter(is_published=True)
            return Response(LessonSerializer(qs, many=True).data)

        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        if request.user.role not in (Roles.ADMIN, Roles.INSTRUCTOR):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if request.user.role == Roles.INSTRUCTOR and not _is_owner(
            request.user, course
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = LessonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(course=course)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"lessons/(?P<lesson_id>\d+)",
    )
    def lesson_update(self, request, slug=None, lesson_id=None):
        from django.shortcuts import get_object_or_404

        course = self.get_object()
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        if request.user.role not in (Roles.ADMIN, Roles.INSTRUCTOR):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if request.user.role == Roles.INSTRUCTOR and not _is_owner(
            request.user, course
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        lesson = get_object_or_404(Lesson.objects.all(), pk=lesson_id, course=course)
        serializer = LessonSerializer(lesson, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    # reviews

    @action(detail=True, methods=["get", "post"], url_path="reviews")
    def reviews(self, request, slug=None):
        course = self.get_object()

        if request.method == "GET":
            qs = course.reviews.select_related("student").order_by("-created_at")
            return Response(CourseReviewSerializer(qs, many=True).data)

        # POST
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        if request.user.role != Roles.STUDENT:
            return Response(
                {"detail": "Only students can leave reviews."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if CourseReview.objects.filter(course=course, student=request.user).exists():
            return Response(
                {"detail": "You have already reviewed this course."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = CourseReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from apps.enrollments.models import Enrollment

        enrollment = Enrollment.objects.filter(
            student=request.user, course=course
        ).first()
        serializer.save(course=course, student=request.user, enrollment=enrollment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # quizzes

    @action(detail=True, methods=["get"], url_path="quizzes")
    def quizzes(self, request, slug=None):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        course = self.get_object()
        from django.db.models import Count as _Count

        from apps.quizzes.models import Quiz
        from apps.quizzes.serializers import QuizListSerializer

        qs = (
            Quiz.objects.filter(course=course, is_active=True)
            .annotate(question_count=_Count("questions"))
            .order_by("id")
        )
        return Response(
            QuizListSerializer(
                qs, many=True, context=self.get_serializer_context()
            ).data
        )
