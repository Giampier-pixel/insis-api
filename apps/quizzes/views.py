from drf_spectacular.utils import extend_schema

from django.db import transaction
from django.db.models import (
    Avg,
    Case,
    Count,
    ExpressionWrapper,
    FloatField,
    Max,
    Min,
    Q,
    Value,
    When,
)
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.quizzes.graders import grade_attempt
from apps.quizzes.models import Attempt, Question, Quiz
from apps.quizzes.serializers import (
    AttemptDetailSerializer,
    AttemptSerializer,
    QuestionSerializer,
    QuestionWriteSerializer,
    QuizDetailSerializer,
    QuizListSerializer,
    QuizWriteSerializer,
    SubmitSerializer,
)
from apps.users.models import Roles


def _is_enrolled(user, course):
    from apps.enrollments.models import Enrollment

    return Enrollment.objects.filter(
        student=user, course=course, is_active=True
    ).exists()


def _can_access_quiz(user, quiz):
    if user.role == Roles.ADMIN:
        return True
    if user.role == Roles.INSTRUCTOR and quiz.course.instructor_id == user.pk:
        return True
    return user.role == Roles.STUDENT and _is_enrolled(user, quiz.course)


def _is_course_owner(user, course):
    return user.role == Roles.ADMIN or (
        user.role == Roles.INSTRUCTOR and course.instructor_id == user.pk
    )


class QuizViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = QuizListSerializer

    def get_queryset(self):
        return Quiz.objects.select_related("course", "lesson").all()

    # GET /quizzes/{id}/
    def retrieve(self, request, pk=None):
        quiz = get_object_or_404(self.get_queryset(), pk=pk)
        if not _can_access_quiz(request.user, quiz):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(
            QuizDetailSerializer(quiz, context=self.get_serializer_context()).data
        )

    # POST /quizzes/
    def create(self, request):
        serializer = QuizWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.validated_data["course"]
        if not _is_course_owner(request.user, course):
            return Response(
                {"detail": "You can only create quizzes for your own courses."},
                status=status.HTTP_403_FORBIDDEN,
            )
        quiz = serializer.save()
        return Response(QuizListSerializer(quiz).data, status=status.HTTP_201_CREATED)

    # GET /quizzes/{id}/questions/ & POST /quizzes/{id}/questions/
    @action(detail=True, methods=["get", "post"], url_path="questions")
    def questions(self, request, pk=None):
        quiz = get_object_or_404(self.get_queryset(), pk=pk)

        if request.method == "GET":
            if not _can_access_quiz(request.user, quiz):
                return Response(status=status.HTTP_403_FORBIDDEN)
            qs = quiz.questions.prefetch_related("options").order_by("order")
            return Response(QuestionSerializer(qs, many=True).data)

        # POST
        if not _is_course_owner(request.user, quiz.course):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = QuestionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = serializer.save(quiz=quiz)
        return Response(
            QuestionSerializer(question).data, status=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"questions/(?P<question_id>\d+)",
    )
    def question_update(self, request, pk=None, question_id=None):
        quiz = get_object_or_404(self.get_queryset(), pk=pk)
        if not _is_course_owner(request.user, quiz.course):
            return Response(status=status.HTTP_403_FORBIDDEN)
        question = get_object_or_404(Question.objects.all(), pk=question_id, quiz=quiz)
        serializer = QuestionWriteSerializer(question, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        question = serializer.save()
        return Response(QuestionSerializer(question).data)

    # POST /quizzes/{id}/start/
    @extend_schema(
        tags=["quizzes"],
        request=None,
        responses={201: AttemptSerializer, 200: AttemptSerializer},
        description="Start a quiz attempt for an enrolled student.",
    )
    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request, pk=None):
        quiz = get_object_or_404(Quiz.objects.filter(is_active=True), pk=pk)

        if request.user.role != Roles.STUDENT:
            return Response(
                {"detail": "Only students can start quiz attempts."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not _is_enrolled(request.user, quiz.course):
            return Response(
                {"detail": "You must be enrolled in the course to take this quiz."},
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            existing = Attempt.objects.select_for_update().filter(
                quiz=quiz, student=request.user
            )
            count = existing.count()

            if quiz.max_attempts and count >= quiz.max_attempts:
                return Response(
                    {"detail": f"Maximum attempts ({quiz.max_attempts}) reached."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            in_progress = existing.filter(finished_at__isnull=True).first()
            if in_progress:
                return Response(AttemptSerializer(in_progress).data)

            attempt = Attempt.objects.create(
                quiz=quiz,
                student=request.user,
                attempt_number=count + 1,
            )

        return Response(AttemptSerializer(attempt).data, status=status.HTTP_201_CREATED)

    # POST /quizzes/{id}/submit/
    @extend_schema(
        tags=["quizzes"],
        request=SubmitSerializer,
        responses={200: AttemptDetailSerializer},
        description="Submit answers for the active quiz attempt and grade it.",
    )
    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        quiz = get_object_or_404(Quiz.objects.filter(is_active=True), pk=pk)

        if request.user.role != Roles.STUDENT:
            return Response(
                {"detail": "Only students can submit quiz attempts."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not _is_enrolled(request.user, quiz.course):
            return Response(status=status.HTTP_403_FORBIDDEN)

        attempt = Attempt.objects.filter(
            quiz=quiz, student=request.user, finished_at__isnull=True
        ).first()
        if not attempt:
            return Response(
                {"detail": "No active attempt found. Call /start/ first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quiz.time_limit_minutes:
            elapsed = (timezone.now() - attempt.started_at).total_seconds() / 60
            if elapsed > quiz.time_limit_minutes:
                return Response(
                    {"detail": "Time limit exceeded."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = SubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attempt = grade_attempt(attempt, serializer.validated_data["answers"])
        return Response(AttemptDetailSerializer(attempt).data)

    # GET /quizzes/{id}/attempts/
    @action(detail=True, methods=["get"], url_path="attempts")
    def attempts(self, request, pk=None):
        quiz = get_object_or_404(self.get_queryset(), pk=pk)
        if not _can_access_quiz(request.user, quiz):
            return Response(status=status.HTTP_403_FORBIDDEN)

        if request.user.role in (Roles.INSTRUCTOR, Roles.ADMIN):
            qs = Attempt.objects.filter(quiz=quiz, finished_at__isnull=False)
        else:
            qs = Attempt.objects.filter(
                quiz=quiz, student=request.user, finished_at__isnull=False
            )
        return Response(AttemptSerializer(qs.order_by("-started_at"), many=True).data)

    # GET /quizzes/{id}/results/{attempt_id}/
    @action(
        detail=True,
        methods=["get"],
        url_path=r"results/(?P<attempt_id>\d+)",
    )
    def results(self, request, pk=None, attempt_id=None):
        quiz = get_object_or_404(self.get_queryset(), pk=pk)
        attempt = get_object_or_404(
            Attempt.objects.filter(finished_at__isnull=False), pk=attempt_id, quiz=quiz
        )
        # Only attempt owner, instructor of course, or admin
        if (
            request.user.role not in (Roles.INSTRUCTOR, Roles.ADMIN)
            and attempt.student_id != request.user.pk
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if request.user.role == Roles.INSTRUCTOR and not _is_course_owner(
            request.user, quiz.course
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(AttemptDetailSerializer(attempt).data)

    # GET /quizzes/{id}/stats/
    @action(detail=True, methods=["get"], url_path="stats")
    def stats(self, request, pk=None):
        quiz = get_object_or_404(self.get_queryset(), pk=pk)
        if not _is_course_owner(request.user, quiz.course):
            return Response(status=status.HTTP_403_FORBIDDEN)

        agg = Attempt.objects.filter(quiz=quiz, finished_at__isnull=False).aggregate(
            total_attempts=Count("id"),
            unique_students=Count("student", distinct=True),
            avg_score=Avg("score"),
            pass_rate=Avg(
                Case(
                    When(passed=True, then=Value(1.0)),
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            ),
            highest_score=Max("score"),
            lowest_score=Min("score"),
        )

        hardest = list(
            Question.objects.filter(quiz=quiz)
            .annotate(
                total_answers=Count("attempt_answers"),
                wrong_answers=Count(
                    "attempt_answers",
                    filter=Q(attempt_answers__is_correct=False),
                ),
                error_rate=ExpressionWrapper(
                    Count(
                        "attempt_answers",
                        filter=Q(attempt_answers__is_correct=False),
                    )
                    * 100.0
                    / Count("attempt_answers"),
                    output_field=FloatField(),
                ),
            )
            .filter(total_answers__gt=0)
            .order_by("-error_rate")
            .values("id", "text", "total_answers", "wrong_answers", "error_rate")[:5]
        )

        pass_rate = agg["pass_rate"]
        return Response(
            {
                "total_attempts": agg["total_attempts"],
                "unique_students": agg["unique_students"],
                "avg_score": (
                    round(float(agg["avg_score"]), 2) if agg["avg_score"] else None
                ),
                "pass_rate": (
                    round(float(pass_rate) * 100, 1) if pass_rate is not None else None
                ),
                "highest_score": (
                    float(agg["highest_score"])
                    if agg["highest_score"] is not None
                    else None
                ),
                "lowest_score": (
                    float(agg["lowest_score"])
                    if agg["lowest_score"] is not None
                    else None
                ),
                "hardest_questions": hardest,
            }
        )
