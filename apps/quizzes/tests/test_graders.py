import pytest

from apps.courses.models import Course
from apps.quizzes.graders import grade_attempt
from apps.quizzes.models import Attempt, Option, Question, Quiz
from apps.users.models import CustomUser, Roles


def make_user(email, role=Roles.STUDENT):
    return CustomUser.objects.create_user(
        email=email, full_name="Test", password="pass1234", role=role
    )


def make_quiz(instructor, passing_score=60.0, max_attempts=None):
    course = Course.objects.create(
        title="C", slug=f"c-{id(instructor)}", instructor=instructor, is_published=True
    )
    return Quiz.objects.create(
        title="Q", course=course, passing_score=passing_score, max_attempts=max_attempts
    )


def make_question(quiz, points=10, q_type=Question.Type.SINGLE):
    return Question.objects.create(
        quiz=quiz, text="Question?", order=1, points=points, type=q_type
    )


def make_options(question, correct_count=1, total=4):
    options = []
    for i in range(total):
        opt = Option.objects.create(
            question=question,
            text=f"Option {i}",
            is_correct=(i < correct_count),
            order=i,
        )
        options.append(opt)
    return options


@pytest.mark.django_db
class TestGradeAttempt:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu@t.com")

    def test_all_correct_gives_100(self):
        quiz = make_quiz(self.instructor, passing_score=60.0)
        q = make_question(quiz, points=10)
        opts = make_options(q, correct_count=1)
        attempt = Attempt.objects.create(
            quiz=quiz, student=self.student, attempt_number=1
        )
        attempt = grade_attempt(
            attempt,
            [{"question_id": q.id, "selected_option_ids": [opts[0].id]}],
        )
        assert float(attempt.score) == 100.0
        assert attempt.passed is True
        assert attempt.finished_at is not None

    def test_all_wrong_gives_0(self):
        quiz = make_quiz(self.instructor, passing_score=60.0)
        q = make_question(quiz, points=10)
        opts = make_options(q, correct_count=1)
        attempt = Attempt.objects.create(
            quiz=quiz, student=self.student, attempt_number=1
        )
        attempt = grade_attempt(
            attempt,
            [{"question_id": q.id, "selected_option_ids": [opts[1].id]}],
        )
        assert float(attempt.score) == 0.0
        assert attempt.passed is False

    def test_partial_score(self):
        quiz = make_quiz(self.instructor, passing_score=60.0)
        q1 = Question.objects.create(quiz=quiz, text="Q1", order=1, points=10)
        q2 = Question.objects.create(quiz=quiz, text="Q2", order=2, points=10)
        o1_correct = Option.objects.create(
            question=q1, text="A", is_correct=True, order=0
        )
        Option.objects.create(question=q1, text="B", is_correct=False, order=1)
        Option.objects.create(question=q2, text="C", is_correct=True, order=0)
        o2_wrong = Option.objects.create(
            question=q2, text="D", is_correct=False, order=1
        )

        attempt = Attempt.objects.create(
            quiz=quiz, student=self.student, attempt_number=1
        )
        attempt = grade_attempt(
            attempt,
            [
                {"question_id": q1.id, "selected_option_ids": [o1_correct.id]},
                {"question_id": q2.id, "selected_option_ids": [o2_wrong.id]},
            ],
        )
        assert float(attempt.score) == 50.0
        assert attempt.passed is False

    def test_multiple_choice_requires_exact_match(self):
        quiz = make_quiz(self.instructor, passing_score=60.0)
        q = Question.objects.create(
            quiz=quiz, text="Multi", order=1, points=10, type=Question.Type.MULTIPLE
        )
        o1 = Option.objects.create(question=q, text="A", is_correct=True, order=0)
        Option.objects.create(question=q, text="B", is_correct=True, order=1)
        Option.objects.create(question=q, text="C", is_correct=False, order=2)

        attempt = Attempt.objects.create(
            quiz=quiz, student=self.student, attempt_number=1
        )
        # Select only one of two correct — should be wrong
        attempt = grade_attempt(
            attempt,
            [{"question_id": q.id, "selected_option_ids": [o1.id]}],
        )
        assert float(attempt.score) == 0.0

    def test_multiple_choice_all_correct(self):
        quiz = make_quiz(self.instructor, passing_score=60.0)
        q = Question.objects.create(
            quiz=quiz, text="Multi", order=1, points=10, type=Question.Type.MULTIPLE
        )
        o1 = Option.objects.create(question=q, text="A", is_correct=True, order=0)
        o2 = Option.objects.create(question=q, text="B", is_correct=True, order=1)
        Option.objects.create(question=q, text="C", is_correct=False, order=2)

        attempt = Attempt.objects.create(
            quiz=quiz, student=self.student, attempt_number=1
        )
        attempt = grade_attempt(
            attempt,
            [{"question_id": q.id, "selected_option_ids": [o1.id, o2.id]}],
        )
        assert float(attempt.score) == 100.0

    def test_no_questions_gives_0(self):
        quiz = make_quiz(self.instructor, passing_score=60.0)
        attempt = Attempt.objects.create(
            quiz=quiz, student=self.student, attempt_number=1
        )
        attempt = grade_attempt(attempt, [])
        assert float(attempt.score) == 0.0
        assert attempt.passed is False

    def test_points_earned_stored(self):
        quiz = make_quiz(self.instructor, passing_score=60.0)
        q = make_question(quiz, points=15)
        opts = make_options(q, correct_count=1)
        attempt = Attempt.objects.create(
            quiz=quiz, student=self.student, attempt_number=1
        )
        grade_attempt(
            attempt,
            [{"question_id": q.id, "selected_option_ids": [opts[0].id]}],
        )
        aa = attempt.answers.first()
        assert aa.points_earned == 15
        assert aa.is_correct is True
