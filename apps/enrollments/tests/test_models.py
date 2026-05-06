import pytest

from django.db import IntegrityError

from apps.courses.models import Course, Lesson
from apps.enrollments.models import Enrollment, LessonProgress
from apps.users.models import CustomUser, Roles


def make_user(email, role=Roles.STUDENT):
    return CustomUser.objects.create_user(
        email=email, full_name="Test User", password="pass1234", role=role
    )


def make_course(instructor, slug="test-course"):
    return Course.objects.create(
        title="Test Course", slug=slug, instructor=instructor, is_published=True
    )


def make_enrollment(student, course):
    return Enrollment.objects.create(student=student, course=course)


@pytest.mark.django_db
class TestEnrollmentModel:
    def setup_method(self):
        self.student = make_user("student@t.com")
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.course = make_course(self.instructor)

    def test_creation(self):
        enrollment = make_enrollment(self.student, self.course)
        assert enrollment.source == Enrollment.Source.DIRECT
        assert enrollment.is_active is True
        assert enrollment.completed is False
        assert enrollment.completed_at is None
        assert str(enrollment) == f"{self.student.email} → {self.course.title}"

    def test_unique_student_course(self):
        make_enrollment(self.student, self.course)
        with pytest.raises(IntegrityError):
            make_enrollment(self.student, self.course)

    def test_mark_completed(self):
        enrollment = make_enrollment(self.student, self.course)
        assert not enrollment.completed
        enrollment.mark_completed()
        enrollment.refresh_from_db()
        assert enrollment.completed is True
        assert enrollment.completed_at is not None

    def test_mark_completed_idempotent(self):
        enrollment = make_enrollment(self.student, self.course)
        enrollment.mark_completed()
        first_completed_at = enrollment.completed_at
        enrollment.mark_completed()
        assert enrollment.completed_at == first_completed_at

    def test_soft_delete(self):
        enrollment = make_enrollment(self.student, self.course)
        pk = enrollment.pk
        enrollment.delete()
        assert Enrollment.objects.filter(pk=pk).count() == 0
        assert Enrollment.all_objects.filter(pk=pk).count() == 1


@pytest.mark.django_db
class TestLessonProgressModel:
    def setup_method(self):
        self.student = make_user("student@t.com")
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.course = make_course(self.instructor)
        self.enrollment = make_enrollment(self.student, self.course)
        self.lesson = Lesson.objects.create(
            course=self.course, title="L1", order=1, is_published=True
        )

    def test_creation(self):
        lp = LessonProgress.objects.create(
            enrollment=self.enrollment, lesson=self.lesson
        )
        assert lp.completed is False
        assert lp.time_spent_seconds == 0
        assert str(lp) == f"{self.enrollment} — {self.lesson.title}"

    def test_unique_enrollment_lesson(self):
        LessonProgress.objects.create(enrollment=self.enrollment, lesson=self.lesson)
        with pytest.raises(IntegrityError):
            LessonProgress.objects.create(
                enrollment=self.enrollment, lesson=self.lesson
            )
