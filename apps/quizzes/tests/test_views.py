import pytest

from rest_framework.test import APIClient

from apps.courses.models import Course
from apps.enrollments.models import Enrollment
from apps.quizzes.models import Attempt, Option, Question, Quiz
from apps.users.models import CustomUser, Roles


def make_user(email, role=Roles.STUDENT, password="pass1234"):
    return CustomUser.objects.create_user(
        email=email, full_name="Test", password=password, role=role
    )


def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_course(instructor, slug="c1"):
    return Course.objects.create(
        title="Course", slug=slug, instructor=instructor, is_published=True
    )


def make_quiz(course, **kwargs):
    return Quiz.objects.create(title="Quiz", course=course, **kwargs)


def make_question(quiz, points=10, q_type=Question.Type.SINGLE, order=1):
    return Question.objects.create(
        quiz=quiz, text="Q?", order=order, points=points, type=q_type
    )


def make_options(question, correct_count=1):
    opts = []
    for i in range(4):
        opts.append(
            Option.objects.create(
                question=question,
                text=f"Opt {i}",
                is_correct=(i < correct_count),
                order=i,
            )
        )
    return opts


def enroll(student, course):
    return Enrollment.objects.create(student=student, course=course)


# ------------------------------------------------------------------ retrieve


@pytest.mark.django_db
class TestQuizRetrieve:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu@t.com")
        self.course = make_course(self.instructor)
        self.quiz = make_quiz(self.course)
        self.question = make_question(self.quiz)
        make_options(self.question)

    def test_student_sees_no_is_correct(self):
        enroll(self.student, self.course)
        resp = auth_client(self.student).get(f"/api/v1/quizzes/{self.quiz.id}/")
        assert resp.status_code == 200
        for opt in resp.data["questions"][0]["options"]:
            assert "is_correct" not in opt

    def test_instructor_sees_is_correct(self):
        resp = auth_client(self.instructor).get(f"/api/v1/quizzes/{self.quiz.id}/")
        assert resp.status_code == 200
        for opt in resp.data["questions"][0]["options"]:
            assert "is_correct" in opt

    def test_unenrolled_student_gets_403(self):
        resp = auth_client(self.student).get(f"/api/v1/quizzes/{self.quiz.id}/")
        assert resp.status_code == 403

    def test_unauthenticated_401(self):
        resp = APIClient().get(f"/api/v1/quizzes/{self.quiz.id}/")
        assert resp.status_code == 401


# ------------------------------------------------------------------ create


@pytest.mark.django_db
class TestQuizCreate:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.course = make_course(self.instructor)

    def test_instructor_can_create(self):
        resp = auth_client(self.instructor).post(
            "/api/v1/quizzes/",
            {"course": self.course.id, "title": "New Quiz", "passing_score": "70.00"},
        )
        assert resp.status_code == 201
        assert resp.data["title"] == "New Quiz"

    def test_other_instructor_cannot_create(self):
        other = make_user("other@t.com", role=Roles.INSTRUCTOR)
        resp = auth_client(other).post(
            "/api/v1/quizzes/",
            {"course": self.course.id, "title": "Hack Quiz", "passing_score": "60.00"},
        )
        assert resp.status_code == 403

    def test_student_cannot_create(self):
        student = make_user("stu@t.com")
        resp = auth_client(student).post(
            "/api/v1/quizzes/",
            {"course": self.course.id, "title": "Quiz", "passing_score": "60.00"},
        )
        assert resp.status_code == 403

    def test_passing_score_out_of_range(self):
        resp = auth_client(self.instructor).post(
            "/api/v1/quizzes/",
            {"course": self.course.id, "title": "Quiz", "passing_score": "150"},
        )
        assert resp.status_code == 400


# ------------------------------------------------------------------ start


@pytest.mark.django_db
class TestQuizStart:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu@t.com")
        self.course = make_course(self.instructor)
        self.quiz = make_quiz(self.course, max_attempts=2)
        enroll(self.student, self.course)

    def test_enrolled_student_can_start(self):
        resp = auth_client(self.student).post(f"/api/v1/quizzes/{self.quiz.id}/start/")
        assert resp.status_code == 201
        assert resp.data["attempt_number"] == 1

    def test_start_returns_in_progress_if_exists(self):
        auth_client(self.student).post(f"/api/v1/quizzes/{self.quiz.id}/start/")
        resp = auth_client(self.student).post(f"/api/v1/quizzes/{self.quiz.id}/start/")
        # Returns 200 with existing attempt (not a new one)
        assert resp.status_code == 200
        assert resp.data["attempt_number"] == 1
        assert Attempt.objects.filter(quiz=self.quiz, student=self.student).count() == 1

    def test_max_attempts_enforced(self):
        # Consume both attempts
        for i in range(1, 3):
            Attempt.objects.create(
                quiz=self.quiz,
                student=self.student,
                attempt_number=i,
                finished_at=None,
            )
            attempt = Attempt.objects.get(
                quiz=self.quiz, student=self.student, attempt_number=i
            )
            attempt.finished_at = attempt.started_at
            attempt.save(update_fields=["finished_at"])

        resp = auth_client(self.student).post(f"/api/v1/quizzes/{self.quiz.id}/start/")
        assert resp.status_code == 400
        assert "Maximum" in resp.data["detail"]

    def test_unenrolled_student_403(self):
        other = make_user("other@t.com")
        resp = auth_client(other).post(f"/api/v1/quizzes/{self.quiz.id}/start/")
        assert resp.status_code == 403

    def test_instructor_cannot_start(self):
        resp = auth_client(self.instructor).post(
            f"/api/v1/quizzes/{self.quiz.id}/start/"
        )
        assert resp.status_code == 403


# ------------------------------------------------------------------ submit


@pytest.mark.django_db
class TestQuizSubmit:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu@t.com")
        self.course = make_course(self.instructor)
        self.quiz = make_quiz(self.course, passing_score=60.0)
        enroll(self.student, self.course)
        self.question = make_question(self.quiz, points=10)
        self.opts = make_options(self.question)

    def _start(self):
        resp = auth_client(self.student).post(f"/api/v1/quizzes/{self.quiz.id}/start/")
        assert resp.status_code == 201
        return resp.data["id"]

    def test_submit_correct_answer(self):
        self._start()
        resp = auth_client(self.student).post(
            f"/api/v1/quizzes/{self.quiz.id}/submit/",
            {
                "answers": [
                    {
                        "question_id": self.question.id,
                        "selected_option_ids": [self.opts[0].id],
                    }
                ]
            },
            format="json",
        )
        assert resp.status_code == 200
        assert float(resp.data["score"]) == 100.0
        assert resp.data["passed"] is True

    def test_submit_wrong_answer(self):
        self._start()
        resp = auth_client(self.student).post(
            f"/api/v1/quizzes/{self.quiz.id}/submit/",
            {
                "answers": [
                    {
                        "question_id": self.question.id,
                        "selected_option_ids": [self.opts[1].id],
                    }
                ]
            },
            format="json",
        )
        assert resp.status_code == 200
        assert float(resp.data["score"]) == 0.0
        assert resp.data["passed"] is False

    def test_no_active_attempt_400(self):
        resp = auth_client(self.student).post(
            f"/api/v1/quizzes/{self.quiz.id}/submit/",
            {"answers": []},
            format="json",
        )
        assert resp.status_code == 400

    def test_submit_closes_attempt(self):
        self._start()
        auth_client(self.student).post(
            f"/api/v1/quizzes/{self.quiz.id}/submit/",
            {"answers": []},
            format="json",
        )
        attempt = Attempt.objects.get(quiz=self.quiz, student=self.student)
        assert attempt.finished_at is not None


# ------------------------------------------------------------------ attempts


@pytest.mark.django_db
class TestAttemptsList:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu@t.com")
        self.course = make_course(self.instructor)
        self.quiz = make_quiz(self.course)
        enroll(self.student, self.course)

    def _finish_attempt(self, num):
        from django.utils import timezone

        a = Attempt.objects.create(
            quiz=self.quiz,
            student=self.student,
            attempt_number=num,
            finished_at=timezone.now(),
            score=80,
            passed=True,
        )
        return a

    def test_student_sees_own_attempts(self):
        self._finish_attempt(1)
        resp = auth_client(self.student).get(
            f"/api/v1/quizzes/{self.quiz.id}/attempts/"
        )
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_in_progress_not_in_list(self):
        Attempt.objects.create(quiz=self.quiz, student=self.student, attempt_number=1)
        resp = auth_client(self.student).get(
            f"/api/v1/quizzes/{self.quiz.id}/attempts/"
        )
        assert len(resp.data) == 0


# ------------------------------------------------------------------ results


@pytest.mark.django_db
class TestResults:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu@t.com")
        self.course = make_course(self.instructor)
        self.quiz = make_quiz(self.course, passing_score=60.0)
        enroll(self.student, self.course)
        self.question = make_question(self.quiz)
        self.opts = make_options(self.question)

    def _do_submit(self):
        auth_client(self.student).post(f"/api/v1/quizzes/{self.quiz.id}/start/")
        auth_client(self.student).post(
            f"/api/v1/quizzes/{self.quiz.id}/submit/",
            {
                "answers": [
                    {
                        "question_id": self.question.id,
                        "selected_option_ids": [self.opts[0].id],
                    }
                ]
            },
            format="json",
        )
        return Attempt.objects.get(quiz=self.quiz, student=self.student)

    def test_student_can_view_own_result(self):
        attempt = self._do_submit()
        resp = auth_client(self.student).get(
            f"/api/v1/quizzes/{self.quiz.id}/results/{attempt.id}/"
        )
        assert resp.status_code == 200
        assert "answers" in resp.data

    def test_other_student_cannot_view(self):
        attempt = self._do_submit()
        other = make_user("other@t.com")
        enroll(other, self.course)
        resp = auth_client(other).get(
            f"/api/v1/quizzes/{self.quiz.id}/results/{attempt.id}/"
        )
        assert resp.status_code == 403

    def test_instructor_can_view_any_result(self):
        attempt = self._do_submit()
        resp = auth_client(self.instructor).get(
            f"/api/v1/quizzes/{self.quiz.id}/results/{attempt.id}/"
        )
        assert resp.status_code == 200


# ------------------------------------------------------------------ stats


@pytest.mark.django_db
class TestStats:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu@t.com")
        self.course = make_course(self.instructor)
        self.quiz = make_quiz(self.course, passing_score=60.0)
        enroll(self.student, self.course)

    def test_instructor_can_view_stats(self):
        resp = auth_client(self.instructor).get(
            f"/api/v1/quizzes/{self.quiz.id}/stats/"
        )
        assert resp.status_code == 200
        assert "total_attempts" in resp.data
        assert "pass_rate" in resp.data
        assert "hardest_questions" in resp.data

    def test_student_cannot_view_stats(self):
        resp = auth_client(self.student).get(f"/api/v1/quizzes/{self.quiz.id}/stats/")
        assert resp.status_code == 403

    def test_stats_aggregate_correctly(self):
        from django.utils import timezone

        Attempt.objects.create(
            quiz=self.quiz,
            student=self.student,
            attempt_number=1,
            finished_at=timezone.now(),
            score=80,
            passed=True,
        )
        resp = auth_client(self.instructor).get(
            f"/api/v1/quizzes/{self.quiz.id}/stats/"
        )
        assert resp.data["total_attempts"] == 1
        assert resp.data["avg_score"] == 80.0
        assert resp.data["pass_rate"] == 100.0
