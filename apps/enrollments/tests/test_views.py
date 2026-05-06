import pytest

from rest_framework.test import APIClient

from apps.courses.models import Course, Lesson
from apps.enrollments.models import Enrollment, LessonProgress
from apps.users.models import CustomUser, Roles


def make_user(email, role=Roles.STUDENT, password="pass1234"):
    return CustomUser.objects.create_user(
        email=email, full_name="Test User", password=password, role=role
    )


def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_course(instructor, slug="course-1", published=True):
    return Course.objects.create(
        title=f"Course {slug}", slug=slug, instructor=instructor, is_published=published
    )


def make_enrollment(student, course, **kwargs):
    return Enrollment.objects.create(student=student, course=course, **kwargs)


def make_lesson(course, order=1, published=True):
    return Lesson.objects.create(
        course=course, title=f"Lesson {order}", order=order, is_published=published
    )


# ------------------------------------------------------------------ list


@pytest.mark.django_db
class TestEnrollmentList:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.admin = make_user("admin@t.com", role=Roles.ADMIN)
        self.s1 = make_user("s1@t.com")
        self.s2 = make_user("s2@t.com")
        self.course = make_course(self.instructor)

    def test_student_sees_only_own(self):
        make_enrollment(self.s1, self.course)
        course2 = make_course(self.instructor, slug="c2")
        make_enrollment(self.s2, course2)
        resp = auth_client(self.s1).get("/api/v1/enrollments/")
        assert resp.status_code == 200
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["student_email"] == self.s1.email

    def test_admin_sees_all(self):
        make_enrollment(self.s1, self.course)
        course2 = make_course(self.instructor, slug="c2")
        make_enrollment(self.s2, course2)
        resp = auth_client(self.admin).get("/api/v1/enrollments/")
        assert resp.status_code == 200
        assert resp.data["count"] == 2

    def test_instructor_sees_own_course_enrollments(self):
        other_instructor = make_user("other@t.com", role=Roles.INSTRUCTOR)
        other_course = make_course(other_instructor, slug="other")
        make_enrollment(self.s1, self.course)
        make_enrollment(self.s2, other_course)
        resp = auth_client(self.instructor).get("/api/v1/enrollments/")
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_unauthenticated_401(self):
        resp = APIClient().get("/api/v1/enrollments/")
        assert resp.status_code == 401


# ------------------------------------------------------------------ create


@pytest.mark.django_db
class TestEnrollmentCreate:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu@t.com")
        self.course = make_course(self.instructor)

    def test_student_can_enroll(self):
        resp = auth_client(self.student).post(
            "/api/v1/enrollments/", {"course": self.course.id}
        )
        assert resp.status_code == 201
        assert resp.data["course"] == self.course.id
        assert resp.data["source"] == "DIRECT"

    def test_instructor_cannot_enroll(self):
        resp = auth_client(self.instructor).post(
            "/api/v1/enrollments/", {"course": self.course.id}
        )
        assert resp.status_code == 403

    def test_admin_cannot_enroll(self):
        admin = make_user("admin@t.com", role=Roles.ADMIN)
        resp = auth_client(admin).post(
            "/api/v1/enrollments/", {"course": self.course.id}
        )
        assert resp.status_code == 403

    def test_duplicate_enrollment_400(self):
        make_enrollment(self.student, self.course)
        resp = auth_client(self.student).post(
            "/api/v1/enrollments/", {"course": self.course.id}
        )
        assert resp.status_code == 400

    def test_unauthenticated_401(self):
        resp = APIClient().post("/api/v1/enrollments/", {"course": self.course.id})
        assert resp.status_code == 401


# ------------------------------------------------------------------ retrieve


@pytest.mark.django_db
class TestEnrollmentRetrieve:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu@t.com")
        self.course = make_course(self.instructor)
        self.enrollment = make_enrollment(self.student, self.course)

    def test_student_can_retrieve_own(self):
        resp = auth_client(self.student).get(
            f"/api/v1/enrollments/{self.enrollment.id}/"
        )
        assert resp.status_code == 200
        assert resp.data["id"] == self.enrollment.id

    def test_student_cannot_retrieve_other(self):
        other = make_user("other@t.com")
        resp = auth_client(other).get(f"/api/v1/enrollments/{self.enrollment.id}/")
        assert resp.status_code == 404

    def test_admin_can_retrieve_any(self):
        admin = make_user("admin@t.com", role=Roles.ADMIN)
        resp = auth_client(admin).get(f"/api/v1/enrollments/{self.enrollment.id}/")
        assert resp.status_code == 200


# ------------------------------------------------------------------ destroy


@pytest.mark.django_db
class TestEnrollmentDestroy:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu@t.com")
        self.course = make_course(self.instructor)
        self.enrollment = make_enrollment(self.student, self.course)

    def test_student_can_unenroll(self):
        resp = auth_client(self.student).delete(
            f"/api/v1/enrollments/{self.enrollment.id}/"
        )
        assert resp.status_code == 204
        self.enrollment.refresh_from_db()
        assert self.enrollment.is_active is False

    def test_student_cannot_unenroll_other(self):
        other = make_user("other@t.com")
        resp = auth_client(other).delete(f"/api/v1/enrollments/{self.enrollment.id}/")
        assert resp.status_code == 404


# ------------------------------------------------------------------ complete_lesson


@pytest.mark.django_db
class TestCompleteLesson:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu@t.com")
        self.course = make_course(self.instructor)
        self.enrollment = make_enrollment(self.student, self.course)
        self.lesson = make_lesson(self.course, order=1)

    def test_complete_lesson_creates_progress(self):
        resp = auth_client(self.student).post(
            f"/api/v1/enrollments/{self.enrollment.id}/complete-lesson/",
            {"lesson_id": self.lesson.id, "time_spent_seconds": 120},
        )
        assert resp.status_code == 200
        assert resp.data["completed"] is True
        assert resp.data["time_spent_seconds"] == 120
        assert LessonProgress.objects.filter(
            enrollment=self.enrollment, lesson=self.lesson, completed=True
        ).exists()

    def test_complete_lesson_idempotent(self):
        LessonProgress.objects.create(
            enrollment=self.enrollment,
            lesson=self.lesson,
            completed=True,
            completed_at=None,
        )
        resp = auth_client(self.student).post(
            f"/api/v1/enrollments/{self.enrollment.id}/complete-lesson/",
            {"lesson_id": self.lesson.id, "time_spent_seconds": 60},
        )
        assert resp.status_code == 200
        assert LessonProgress.objects.filter(enrollment=self.enrollment).count() == 1

    def test_wrong_lesson_returns_404(self):
        other_course = make_course(self.instructor, slug="other")
        other_lesson = make_lesson(other_course, order=1)
        resp = auth_client(self.student).post(
            f"/api/v1/enrollments/{self.enrollment.id}/complete-lesson/",
            {"lesson_id": other_lesson.id},
        )
        assert resp.status_code == 404

    def test_inactive_enrollment_returns_404(self):
        self.enrollment.is_active = False
        self.enrollment.save(update_fields=["is_active"])
        resp = auth_client(self.student).post(
            f"/api/v1/enrollments/{self.enrollment.id}/complete-lesson/",
            {"lesson_id": self.lesson.id},
        )
        assert resp.status_code == 404

    def test_completes_course_when_all_lessons_done(self):
        lesson2 = make_lesson(self.course, order=2)
        auth_client(self.student).post(
            f"/api/v1/enrollments/{self.enrollment.id}/complete-lesson/",
            {"lesson_id": self.lesson.id},
        )
        auth_client(self.student).post(
            f"/api/v1/enrollments/{self.enrollment.id}/complete-lesson/",
            {"lesson_id": lesson2.id},
        )
        self.enrollment.refresh_from_db()
        assert self.enrollment.completed is True
        assert self.enrollment.completed_at is not None


# ------------------------------------------------------------------ progress


@pytest.mark.django_db
class TestProgress:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu@t.com")
        self.course = make_course(self.instructor)
        self.enrollment = make_enrollment(self.student, self.course)
        self.l1 = make_lesson(self.course, order=1)
        self.l2 = make_lesson(self.course, order=2)

    def test_progress_zero_initially(self):
        resp = auth_client(self.student).get(
            f"/api/v1/enrollments/{self.enrollment.id}/progress/"
        )
        assert resp.status_code == 200
        assert resp.data["total_lessons"] == 2
        assert resp.data["completed_lessons"] == 0
        assert resp.data["progress_pct"] == 0
        assert len(resp.data["lessons"]) == 2

    def test_progress_after_one_lesson(self):
        LessonProgress.objects.create(
            enrollment=self.enrollment,
            lesson=self.l1,
            completed=True,
            completed_at=None,
        )
        resp = auth_client(self.student).get(
            f"/api/v1/enrollments/{self.enrollment.id}/progress/"
        )
        assert resp.data["completed_lessons"] == 1
        assert resp.data["progress_pct"] == 50.0

    def test_unpublished_lessons_excluded(self):
        make_lesson(self.course, order=3)  # published by default
        unpublished = Lesson.objects.create(
            course=self.course, title="Draft", order=4, is_published=False
        )
        resp = auth_client(self.student).get(
            f"/api/v1/enrollments/{self.enrollment.id}/progress/"
        )
        lesson_ids = [lesson["lesson_id"] for lesson in resp.data["lessons"]]
        assert unpublished.id not in lesson_ids


# ------------------------------------------------------------------ my_certificates


@pytest.mark.django_db
class TestMyCertificates:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu@t.com")
        self.course1 = make_course(self.instructor, slug="c1")
        self.course2 = make_course(self.instructor, slug="c2")

    def test_only_completed_returned(self):
        e1 = make_enrollment(self.student, self.course1, completed=True)
        e1.completed_at = e1.enrolled_at
        e1.save(update_fields=["completed_at"])
        make_enrollment(self.student, self.course2)  # not completed

        resp = auth_client(self.student).get("/api/v1/enrollments/my-certificates/")
        assert resp.status_code == 200
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["id"] == e1.id

    def test_inactive_completed_excluded(self):
        e1 = make_enrollment(
            self.student, self.course1, completed=True, is_active=False
        )
        e1.completed_at = e1.enrolled_at
        e1.save(update_fields=["completed_at"])

        resp = auth_client(self.student).get("/api/v1/enrollments/my-certificates/")
        assert resp.data["count"] == 0

    def test_unauthenticated_401(self):
        resp = APIClient().get("/api/v1/enrollments/my-certificates/")
        assert resp.status_code == 401
