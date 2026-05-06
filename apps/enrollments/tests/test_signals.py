from unittest.mock import MagicMock, patch

import pytest

from apps.courses.models import Course, Lesson
from apps.enrollments.models import Enrollment, LessonProgress
from apps.users.models import CustomUser, Roles


def make_user(email, role=Roles.STUDENT):
    return CustomUser.objects.create_user(
        email=email, full_name="Test", password="pass1234", role=role
    )


def make_course(instructor, slug="sig-course"):
    return Course.objects.create(
        title="Sig Course", slug=slug, instructor=instructor, is_published=True
    )


@pytest.mark.django_db
class TestEnrollmentSignal:
    def test_confirmation_task_called_on_create(self):
        instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        student = make_user("stu@t.com")
        course = make_course(instructor)

        mock_task = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "apps.notifications.tasks": MagicMock(
                    send_enrollment_confirmation=mock_task
                )
            },
        ):
            enrollment = Enrollment.objects.create(student=student, course=course)
            mock_task.delay.assert_called_once_with(enrollment.id)

    def test_no_task_on_update(self):
        instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        student = make_user("stu@t.com")
        course = make_course(instructor)
        enrollment = Enrollment.objects.create(student=student, course=course)

        mock_task = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "apps.notifications.tasks": MagicMock(
                    send_enrollment_confirmation=mock_task
                )
            },
        ):
            enrollment.is_active = False
            enrollment.save(update_fields=["is_active"])
            mock_task.delay.assert_not_called()


@pytest.mark.django_db
class TestLessonProgressSignal:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu@t.com")
        self.course = make_course(self.instructor)
        self.enrollment = Enrollment.objects.create(
            student=self.student, course=self.course
        )

    def test_course_completes_when_all_lessons_done(self):
        l1 = Lesson.objects.create(
            course=self.course, title="L1", order=1, is_published=True
        )
        l2 = Lesson.objects.create(
            course=self.course, title="L2", order=2, is_published=True
        )
        LessonProgress.objects.create(
            enrollment=self.enrollment, lesson=l1, completed=True
        )
        assert not Enrollment.objects.get(pk=self.enrollment.pk).completed

        LessonProgress.objects.create(
            enrollment=self.enrollment, lesson=l2, completed=True
        )
        self.enrollment.refresh_from_db()
        assert self.enrollment.completed is True

    def test_incomplete_lesson_does_not_trigger_completion(self):
        l1 = Lesson.objects.create(
            course=self.course, title="L1", order=1, is_published=True
        )
        LessonProgress.objects.create(
            enrollment=self.enrollment, lesson=l1, completed=False
        )
        self.enrollment.refresh_from_db()
        assert self.enrollment.completed is False

    def test_unpublished_lessons_ignored_in_completion(self):
        l1 = Lesson.objects.create(
            course=self.course, title="L1", order=1, is_published=True
        )
        Lesson.objects.create(
            course=self.course, title="Draft", order=2, is_published=False
        )
        LessonProgress.objects.create(
            enrollment=self.enrollment, lesson=l1, completed=True
        )
        self.enrollment.refresh_from_db()
        assert self.enrollment.completed is True
