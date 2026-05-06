import pytest

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.courses.models import Course, Lesson
from apps.quizzes.models import Attempt, AttemptAnswer, Question, Quiz
from apps.users.models import CustomUser, Roles


def make_user(email, role=Roles.INSTRUCTOR):
    return CustomUser.objects.create_user(
        email=email, full_name="Test", password="pass1234", role=role
    )


def make_course(instructor, slug="c1"):
    return Course.objects.create(
        title="Course", slug=slug, instructor=instructor, is_published=True
    )


def make_quiz(course, **kwargs):
    return Quiz.objects.create(title="Quiz", course=course, **kwargs)


@pytest.mark.django_db
class TestQuizModel:
    def setup_method(self):
        self.instructor = make_user("inst@t.com")
        self.course = make_course(self.instructor)

    def test_creation_defaults(self):
        quiz = make_quiz(self.course)
        assert quiz.is_active is True
        assert float(quiz.passing_score) == 60.0
        assert quiz.max_attempts is None
        assert quiz.time_limit_minutes is None

    def test_str(self):
        quiz = make_quiz(self.course)
        assert str(quiz) == "Quiz"

    def test_clean_lesson_wrong_course(self):
        other_course = make_course(self.instructor, slug="c2")
        lesson = Lesson.objects.create(
            course=other_course, title="L", order=1, is_published=True
        )
        quiz = Quiz(course=self.course, lesson=lesson, title="Bad")
        with pytest.raises(ValidationError, match="does not belong"):
            quiz.clean()

    def test_clean_lesson_correct_course_ok(self):
        lesson = Lesson.objects.create(
            course=self.course, title="L", order=1, is_published=True
        )
        quiz = Quiz(course=self.course, lesson=lesson, title="Good")
        quiz.clean()  # should not raise


@pytest.mark.django_db
class TestAttemptModel:
    def setup_method(self):
        self.instructor = make_user("inst@t.com")
        self.student = make_user("stu@t.com", role=Roles.STUDENT)
        self.course = make_course(self.instructor)
        self.quiz = make_quiz(self.course)

    def test_unique_attempt_number(self):
        Attempt.objects.create(quiz=self.quiz, student=self.student, attempt_number=1)
        with pytest.raises(IntegrityError):
            Attempt.objects.create(
                quiz=self.quiz, student=self.student, attempt_number=1
            )

    def test_different_attempt_numbers_allowed(self):
        Attempt.objects.create(quiz=self.quiz, student=self.student, attempt_number=1)
        a2 = Attempt.objects.create(
            quiz=self.quiz, student=self.student, attempt_number=2
        )
        assert a2.pk is not None

    def test_str(self):
        a = Attempt.objects.create(
            quiz=self.quiz, student=self.student, attempt_number=1
        )
        assert "Quiz" in str(a)
        assert "#1" in str(a)


@pytest.mark.django_db
class TestAttemptAnswerModel:
    def setup_method(self):
        self.instructor = make_user("inst@t.com")
        self.student = make_user("stu@t.com", role=Roles.STUDENT)
        self.course = make_course(self.instructor)
        self.quiz = make_quiz(self.course)
        self.question = Question.objects.create(
            quiz=self.quiz, text="Q1", order=1, points=10
        )
        self.attempt = Attempt.objects.create(
            quiz=self.quiz, student=self.student, attempt_number=1
        )

    def test_unique_attempt_question(self):
        AttemptAnswer.objects.create(attempt=self.attempt, question=self.question)
        with pytest.raises(IntegrityError):
            AttemptAnswer.objects.create(attempt=self.attempt, question=self.question)
