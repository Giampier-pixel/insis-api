import factory

from django.utils import timezone

from apps.assignments.models import AssignmentTarget, CourseAssignment
from apps.companies.models import Company, Department, Employee
from apps.courses.models import Category, Course, Lesson, Tag
from apps.enrollments.models import Enrollment
from apps.quizzes.models import Attempt, Option, Question, Quiz
from apps.users.models import CustomUser, Roles


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomUser
        django_get_or_create = ("email",)

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    full_name = factory.Faker("name")
    role = Roles.STUDENT
    password = factory.PostGenerationMethodCall("set_password", "pass12345!")


class InstructorFactory(UserFactory):
    role = Roles.INSTRUCTOR


class HRManagerFactory(UserFactory):
    role = Roles.HR_MANAGER


class AdminFactory(UserFactory):
    role = Roles.ADMIN
    is_staff = True
    is_superuser = True


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ("slug",)

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.Sequence(lambda n: f"category-{n}")


class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag
        django_get_or_create = ("slug",)

    name = factory.Sequence(lambda n: f"Tag {n}")
    slug = factory.Sequence(lambda n: f"tag-{n}")


class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course
        django_get_or_create = ("slug",)

    title = factory.Sequence(lambda n: f"Course {n}")
    slug = factory.Sequence(lambda n: f"course-{n}")
    instructor = factory.SubFactory(InstructorFactory)
    category = factory.SubFactory(CategoryFactory)
    is_published = True

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for tag in extracted:
                self.tags.add(tag)


class LessonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Lesson

    course = factory.SubFactory(CourseFactory)
    title = factory.Sequence(lambda n: f"Lesson {n}")
    order = factory.Sequence(lambda n: n)
    is_published = True


class EnrollmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Enrollment
        django_get_or_create = ("student", "course")

    student = factory.SubFactory(UserFactory)
    course = factory.SubFactory(CourseFactory)
    source = Enrollment.Source.DIRECT


class QuizFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Quiz

    course = factory.SubFactory(CourseFactory)
    title = factory.Sequence(lambda n: f"Quiz {n}")
    passing_score = 60
    is_active = True


class QuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Question

    quiz = factory.SubFactory(QuizFactory)
    text = factory.Sequence(lambda n: f"Question {n}?")
    type = Question.Type.SINGLE
    order = factory.Sequence(lambda n: n)
    points = 1


class OptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Option

    question = factory.SubFactory(QuestionFactory)
    text = factory.Sequence(lambda n: f"Option {n}")
    is_correct = False
    order = factory.Sequence(lambda n: n)


class AttemptFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Attempt

    quiz = factory.SubFactory(QuizFactory)
    student = factory.SubFactory(UserFactory)
    attempt_number = factory.Sequence(lambda n: n + 1)


class FinishedAttemptFactory(AttemptFactory):
    finished_at = factory.LazyFunction(timezone.now)
    score = 100
    passed = True


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company
        django_get_or_create = ("ruc",)

    name = factory.Sequence(lambda n: f"Company {n}")
    ruc = factory.Sequence(lambda n: f"20{n:09d}")


class DepartmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Department
        django_get_or_create = ("company", "name")

    company = factory.SubFactory(CompanyFactory)
    name = factory.Sequence(lambda n: f"Department {n}")


class EmployeeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Employee
        django_get_or_create = ("user", "company")

    user = factory.SubFactory(UserFactory)
    company = factory.SubFactory(CompanyFactory)
    department = factory.SubFactory(
        DepartmentFactory,
        company=factory.SelfAttribute("..company"),
    )
    is_hr_manager = False


class HRManagerEmployeeFactory(EmployeeFactory):
    user = factory.SubFactory(HRManagerFactory)
    is_hr_manager = True


class CourseAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseAssignment

    course = factory.SubFactory(CourseFactory)
    company = factory.SubFactory(CompanyFactory)
    assigned_by = factory.SubFactory(HRManagerFactory)
    scope = CourseAssignment.Scope.COMPANY
    is_mandatory = True
    is_active = True


class AssignmentTargetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssignmentTarget
        django_get_or_create = ("assignment", "employee")

    assignment = factory.SubFactory(CourseAssignmentFactory)
    employee = factory.SubFactory(
        EmployeeFactory,
        company=factory.SelfAttribute("..assignment.company"),
    )
