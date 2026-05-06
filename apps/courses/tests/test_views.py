import pytest

from rest_framework.test import APIClient

from apps.courses.models import Category, Course, CourseReview, Lesson
from apps.users.models import CustomUser, Roles


def make_user(email, role=Roles.STUDENT, password="pass1234"):
    return CustomUser.objects.create_user(
        email=email, full_name="Test User", password=password, role=role
    )


def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_course(instructor, slug, published=True, **kwargs):
    return Course.objects.create(
        title=f"Course {slug}",
        slug=slug,
        instructor=instructor,
        is_published=published,
        **kwargs,
    )


# ------------------------------------------------------------------ categories


@pytest.mark.django_db
class TestCategoryViewSet:
    def test_public_list(self):
        Category.objects.create(name="Tech")
        resp = APIClient().get("/api/v1/categories/")
        assert resp.status_code == 200

    def test_admin_can_create(self):
        admin = make_user("admin@t.com", role=Roles.ADMIN)
        resp = auth_client(admin).post("/api/v1/categories/", {"name": "Science"})
        assert resp.status_code == 201
        assert resp.data["slug"] == "science"

    def test_student_cannot_create(self):
        student = make_user("stu@t.com")
        resp = auth_client(student).post("/api/v1/categories/", {"name": "Art"})
        assert resp.status_code == 403


# --------------------------------------------------------- courses list / create


@pytest.mark.django_db
class TestCourseListCreate:
    def setup_method(self):
        self.instructor = make_user("inst@t.com", role=Roles.INSTRUCTOR)
        self.admin = make_user("admin@t.com", role=Roles.ADMIN)
        self.student = make_user("stu@t.com", role=Roles.STUDENT)

    def test_public_list_only_published(self):
        make_course(self.instructor, "pub", published=True)
        make_course(self.instructor, "draft", published=False)
        resp = APIClient().get("/api/v1/courses/")
        slugs = [c["slug"] for c in resp.data["results"]]
        assert "pub" in slugs
        assert "draft" not in slugs

    def test_instructor_sees_own_drafts(self):
        make_course(self.instructor, "pub2", published=True)
        make_course(self.instructor, "draft2", published=False)
        resp = auth_client(self.instructor).get("/api/v1/courses/")
        slugs = [c["slug"] for c in resp.data["results"]]
        assert "draft2" in slugs

    def test_instructor_cannot_see_other_drafts(self):
        other = make_user("other@t.com", role=Roles.INSTRUCTOR)
        make_course(other, "other-draft", published=False)
        resp = auth_client(self.instructor).get("/api/v1/courses/")
        slugs = [c["slug"] for c in resp.data["results"]]
        assert "other-draft" not in slugs

    def test_admin_sees_all(self):
        make_course(self.instructor, "pub3", published=True)
        make_course(self.instructor, "draft3", published=False)
        resp = auth_client(self.admin).get("/api/v1/courses/")
        slugs = [c["slug"] for c in resp.data["results"]]
        assert "draft3" in slugs

    def test_instructor_can_create(self):
        resp = auth_client(self.instructor).post(
            "/api/v1/courses/",
            {"title": "New Course", "slug": "new-course"},
        )
        assert resp.status_code == 201
        assert resp.data["slug"] == "new-course"

    def test_slug_auto_generated_from_title(self):
        resp = auth_client(self.instructor).post(
            "/api/v1/courses/",
            {"title": "Auto Slug Course"},
        )
        assert resp.status_code == 201
        assert resp.data["slug"] == "auto-slug-course"

    def test_student_cannot_create_course(self):
        resp = auth_client(self.student).post(
            "/api/v1/courses/",
            {"title": "Hack", "slug": "hack"},
        )
        assert resp.status_code == 403

    def test_annotations_present(self):
        make_course(self.instructor, "ann-course")
        resp = APIClient().get("/api/v1/courses/")
        course = resp.data["results"][0]
        assert "avg_rating" in course
        assert "lesson_count" in course
        assert "review_count" in course


# -------------------------------------------------- course detail / update / delete


@pytest.mark.django_db
class TestCourseDetail:
    def setup_method(self):
        self.instructor = make_user("inst2@t.com", role=Roles.INSTRUCTOR)
        self.other_inst = make_user("other2@t.com", role=Roles.INSTRUCTOR)
        self.admin = make_user("admin2@t.com", role=Roles.ADMIN)
        self.course = make_course(self.instructor, "detail-course")

    def test_public_retrieve(self):
        resp = APIClient().get(f"/api/v1/courses/{self.course.slug}/")
        assert resp.status_code == 200
        assert "lessons" in resp.data
        assert "reviews" in resp.data

    def test_owner_can_update(self):
        resp = auth_client(self.instructor).patch(
            f"/api/v1/courses/{self.course.slug}/",
            {"title": "Updated Title"},
        )
        assert resp.status_code == 200

    def test_other_instructor_cannot_update(self):
        resp = auth_client(self.other_inst).patch(
            f"/api/v1/courses/{self.course.slug}/",
            {"title": "Hack"},
        )
        assert resp.status_code == 403

    def test_admin_can_update(self):
        resp = auth_client(self.admin).patch(
            f"/api/v1/courses/{self.course.slug}/",
            {"title": "Admin Updated"},
        )
        assert resp.status_code == 200

    def test_admin_can_delete(self):
        resp = auth_client(self.admin).delete(f"/api/v1/courses/{self.course.slug}/")
        assert resp.status_code == 204
        self.course.refresh_from_db()
        assert self.course.deleted_at is not None

    def test_instructor_cannot_delete(self):
        resp = auth_client(self.instructor).delete(
            f"/api/v1/courses/{self.course.slug}/"
        )
        assert resp.status_code == 403

    def test_deleted_course_not_accessible(self):
        self.course.delete()
        resp = APIClient().get(f"/api/v1/courses/{self.course.slug}/")
        assert resp.status_code == 404


# ------------------------------------------------------------------ lessons


@pytest.mark.django_db
class TestLessons:
    def setup_method(self):
        self.instructor = make_user("inst3@t.com", role=Roles.INSTRUCTOR)
        self.other_inst = make_user("other3@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu2@t.com")
        self.course = make_course(self.instructor, "lesson-test")

    def test_instructor_add_lesson(self):
        resp = auth_client(self.instructor).post(
            f"/api/v1/courses/{self.course.slug}/lessons/",
            {"title": "Lesson 1", "order": 1},
        )
        assert resp.status_code == 201

    def test_other_instructor_cannot_add_lesson(self):
        resp = auth_client(self.other_inst).post(
            f"/api/v1/courses/{self.course.slug}/lessons/",
            {"title": "Hack", "order": 1},
        )
        assert resp.status_code == 403

    def test_student_can_list_published_lessons(self):
        Lesson.objects.create(
            course=self.course, title="Pub", order=1, is_published=True
        )
        Lesson.objects.create(
            course=self.course, title="Draft", order=2, is_published=False
        )
        resp = auth_client(self.student).get(
            f"/api/v1/courses/{self.course.slug}/lessons/"
        )
        assert resp.status_code == 200
        titles = [lesson["title"] for lesson in resp.data]
        assert "Pub" in titles
        assert "Draft" not in titles

    def test_owner_sees_all_lessons(self):
        Lesson.objects.create(
            course=self.course, title="Pub", order=1, is_published=True
        )
        Lesson.objects.create(
            course=self.course, title="Draft", order=2, is_published=False
        )
        resp = auth_client(self.instructor).get(
            f"/api/v1/courses/{self.course.slug}/lessons/"
        )
        titles = [lesson["title"] for lesson in resp.data]
        assert "Draft" in titles

    def test_instructor_update_lesson(self):
        lesson = Lesson.objects.create(course=self.course, title="Old", order=1)
        resp = auth_client(self.instructor).patch(
            f"/api/v1/courses/{self.course.slug}/lessons/{lesson.pk}/",
            {"title": "Updated"},
        )
        assert resp.status_code == 200
        assert resp.data["title"] == "Updated"

    def test_unauthenticated_cannot_list_lessons(self):
        resp = APIClient().get(f"/api/v1/courses/{self.course.slug}/lessons/")
        assert resp.status_code == 401


# ------------------------------------------------------------------ reviews


@pytest.mark.django_db
class TestReviews:
    def setup_method(self):
        self.instructor = make_user("inst4@t.com", role=Roles.INSTRUCTOR)
        self.student = make_user("stu3@t.com", role=Roles.STUDENT)
        self.course = make_course(self.instructor, "review-test")

    def test_public_list_reviews(self):
        resp = APIClient().get(f"/api/v1/courses/{self.course.slug}/reviews/")
        assert resp.status_code == 200

    def test_student_can_post_review(self):
        resp = auth_client(self.student).post(
            f"/api/v1/courses/{self.course.slug}/reviews/",
            {"rating": 5, "comment": "Excellent!"},
        )
        assert resp.status_code == 201
        assert resp.data["rating"] == 5

    def test_instructor_cannot_review(self):
        resp = auth_client(self.instructor).post(
            f"/api/v1/courses/{self.course.slug}/reviews/",
            {"rating": 5},
        )
        assert resp.status_code == 403

    def test_duplicate_review_rejected(self):
        CourseReview.objects.create(course=self.course, student=self.student, rating=4)
        resp = auth_client(self.student).post(
            f"/api/v1/courses/{self.course.slug}/reviews/",
            {"rating": 3},
        )
        assert resp.status_code == 400

    def test_review_appears_in_list(self):
        CourseReview.objects.create(
            course=self.course, student=self.student, rating=5, comment="Great"
        )
        resp = APIClient().get(f"/api/v1/courses/{self.course.slug}/reviews/")
        assert len(resp.data) == 1
        assert resp.data[0]["rating"] == 5


# ------------------------------------------------------------------ filters


@pytest.mark.django_db
class TestCourseFilters:
    def setup_method(self):
        self.instructor = make_user("inst5@t.com", role=Roles.INSTRUCTOR)
        self.cat = Category.objects.create(name="Web Dev")

    def test_filter_by_category(self):
        make_course(self.instructor, "with-cat", category=self.cat)
        make_course(self.instructor, "no-cat")
        resp = APIClient().get(f"/api/v1/courses/?category={self.cat.pk}")
        slugs = [c["slug"] for c in resp.data["results"]]
        assert "with-cat" in slugs
        assert "no-cat" not in slugs

    def test_filter_by_level(self):
        make_course(self.instructor, "adv-course", level=Course.Level.ADVANCED)
        make_course(self.instructor, "beg-course", level=Course.Level.BEGINNER)
        resp = APIClient().get("/api/v1/courses/?level=ADVANCED")
        slugs = [c["slug"] for c in resp.data["results"]]
        assert "adv-course" in slugs
        assert "beg-course" not in slugs

    def test_filter_free_courses(self):
        make_course(self.instructor, "free-c", price=0)
        make_course(self.instructor, "paid-c", price=29.99)
        resp = APIClient().get("/api/v1/courses/?is_free=true")
        slugs = [c["slug"] for c in resp.data["results"]]
        assert "free-c" in slugs
        assert "paid-c" not in slugs

    def test_search_by_title(self):
        make_course(
            self.instructor,
            "django-rest",
        )
        Course.objects.filter(slug="django-rest").update(title="Django REST Framework")
        make_course(self.instructor, "vue-course")
        Course.objects.filter(slug="vue-course").update(title="Vue.js Basics")
        resp = APIClient().get("/api/v1/courses/?search=Django")
        slugs = [c["slug"] for c in resp.data["results"]]
        assert "django-rest" in slugs
        assert "vue-course" not in slugs
