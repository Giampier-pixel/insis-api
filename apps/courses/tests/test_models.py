import pytest

from django.db import IntegrityError

from apps.courses.models import Category, Course, CourseReview, Lesson, Tag
from apps.users.models import CustomUser, Roles


def make_user(email, role=Roles.INSTRUCTOR):
    return CustomUser.objects.create_user(
        email=email, full_name="Test User", password="pass1234", role=role
    )


def make_course(instructor, slug="test-course", published=True):
    return Course.objects.create(
        title="Test Course",
        slug=slug,
        instructor=instructor,
        is_published=published,
    )


@pytest.mark.django_db
class TestCategoryModel:
    def test_creation_and_slug_auto(self):
        cat = Category.objects.create(name="Data Science")
        assert cat.slug == "data-science"
        assert str(cat) == "Data Science"

    def test_name_unique(self):
        Category.objects.create(name="Python")
        with pytest.raises(IntegrityError):
            Category.objects.create(name="Python")

    def test_slug_unique(self):
        Category.objects.create(name="Go Lang", slug="go-lang")
        with pytest.raises(IntegrityError):
            Category.objects.create(name="GoLang", slug="go-lang")


@pytest.mark.django_db
class TestTagModel:
    def test_creation_and_slug_auto(self):
        tag = Tag.objects.create(name="Django")
        assert tag.slug == "django"
        assert str(tag) == "Django"

    def test_name_unique(self):
        Tag.objects.create(name="REST")
        with pytest.raises(IntegrityError):
            Tag.objects.create(name="REST")


@pytest.mark.django_db
class TestCourseModel:
    def setup_method(self):
        self.instructor = make_user("inst@test.com")

    def test_creation(self):
        course = make_course(self.instructor)
        assert str(course) == "Test Course"
        assert course.price == 0

    def test_slug_unique(self):
        make_course(self.instructor, slug="unique-slug")
        with pytest.raises(IntegrityError):
            make_course(self.instructor, slug="unique-slug")

    def test_soft_delete(self):
        course = make_course(self.instructor, slug="to-delete")
        pk = course.pk
        course.delete()
        assert Course.objects.filter(pk=pk).count() == 0
        assert Course.all_objects.filter(pk=pk).count() == 1

    def test_default_level_beginner(self):
        course = make_course(self.instructor, slug="level-course")
        assert course.level == Course.Level.BEGINNER

    def test_tags_m2m(self):
        course = make_course(self.instructor, slug="tagged-course")
        tag = Tag.objects.create(name="ML")
        course.tags.add(tag)
        assert course.tags.count() == 1


@pytest.mark.django_db
class TestLessonModel:
    def setup_method(self):
        instructor = make_user("inst2@test.com")
        self.course = make_course(instructor, slug="lesson-course")

    def test_creation_and_str(self):
        lesson = Lesson.objects.create(course=self.course, title="Intro", order=1)
        assert str(lesson) == "Test Course — Intro"

    def test_soft_delete(self):
        lesson = Lesson.objects.create(course=self.course, title="To Delete", order=1)
        pk = lesson.pk
        lesson.delete()
        assert Lesson.objects.filter(pk=pk).count() == 0
        assert Lesson.all_objects.filter(pk=pk).count() == 1

    def test_ordering_by_order_field(self):
        Lesson.objects.create(course=self.course, title="Third", order=3)
        Lesson.objects.create(course=self.course, title="First", order=1)
        Lesson.objects.create(course=self.course, title="Second", order=2)
        titles = list(
            Lesson.objects.filter(course=self.course).values_list("title", flat=True)
        )
        assert titles == ["First", "Second", "Third"]


@pytest.mark.django_db
class TestCourseReviewModel:
    def setup_method(self):
        instructor = make_user("inst3@test.com")
        self.course = make_course(instructor, slug="review-course")
        self.student = make_user("stu@test.com", role=Roles.STUDENT)

    def test_creation_and_str(self):
        review = CourseReview.objects.create(
            course=self.course, student=self.student, rating=4
        )
        assert "stu@test.com" in str(review)
        assert "4/5" in str(review)

    def test_unique_per_course_and_student(self):
        CourseReview.objects.create(course=self.course, student=self.student, rating=5)
        with pytest.raises(IntegrityError):
            CourseReview.objects.create(
                course=self.course, student=self.student, rating=3
            )

    def test_rating_validator_enforced(self):
        from django.core.exceptions import ValidationError

        review = CourseReview(course=self.course, student=self.student, rating=6)
        with pytest.raises(ValidationError):
            review.full_clean()
