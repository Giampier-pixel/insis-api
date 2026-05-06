import pytest

from django.db import IntegrityError

from apps.assignments.models import AssignmentTarget, CompletionRecord, CourseAssignment
from apps.companies.models import Company, Department, Employee
from apps.courses.models import Course
from apps.users.models import CustomUser, Roles


def make_user(email, role=Roles.HR_MANAGER):
    return CustomUser.objects.create_user(
        email=email, full_name="Test", password="pass1234", role=role
    )


def make_company():
    return Company.objects.create(name="Acme", ruc="12345678901")


def make_dept(company):
    return Department.objects.create(company=company, name="Eng")


def make_employee(company, dept=None, role=Roles.STUDENT):
    user = CustomUser.objects.create_user(
        email=f"emp_{id(company)}@t.com",
        full_name="Emp",
        password="pass",
        role=role,
    )
    return Employee.objects.create(user=user, company=company, department=dept)


def make_course(slug="c1"):
    inst = make_user(f"inst_{slug}@t.com", role=Roles.INSTRUCTOR)
    return Course.objects.create(
        title="C", slug=slug, instructor=inst, is_published=True
    )


def make_assignment(course, company, hr, scope=CourseAssignment.Scope.COMPANY):
    return CourseAssignment.objects.create(
        course=course, company=company, assigned_by=hr, scope=scope
    )


@pytest.mark.django_db
class TestCourseAssignmentModel:
    def setup_method(self):
        self.hr = make_user("hr@t.com")
        self.company = make_company()
        self.course = make_course()

    def test_creation_defaults(self):
        a = make_assignment(self.course, self.company, self.hr)
        assert a.is_active is True
        assert a.is_mandatory is True
        assert a.scope == CourseAssignment.Scope.COMPANY
        assert str(a) == f"{self.company.name} — {self.course.title} (COMPANY)"

    def test_scope_choices(self):
        for scope in CourseAssignment.Scope:
            a = CourseAssignment.objects.create(
                course=self.course,
                company=self.company,
                assigned_by=self.hr,
                scope=scope,
            )
            assert a.scope == scope


@pytest.mark.django_db
class TestAssignmentTargetModel:
    def setup_method(self):
        self.hr = make_user("hr@t.com")
        self.company = make_company()
        self.course = make_course()
        self.assignment = make_assignment(self.course, self.company, self.hr)
        self.employee = make_employee(self.company)

    def test_unique_assignment_employee(self):
        AssignmentTarget.objects.create(
            assignment=self.assignment, employee=self.employee
        )
        with pytest.raises(IntegrityError):
            AssignmentTarget.objects.create(
                assignment=self.assignment, employee=self.employee
            )


@pytest.mark.django_db
class TestCompletionRecordModel:
    def setup_method(self):
        self.hr = make_user("hr@t.com")
        self.company = make_company()
        self.course = make_course()
        self.assignment = make_assignment(self.course, self.company, self.hr)
        self.employee = make_employee(self.company)
        self.target = AssignmentTarget.objects.create(
            assignment=self.assignment, employee=self.employee
        )

    def test_creation(self):
        cr = CompletionRecord.objects.create(
            target=self.target,
            employee=self.employee,
            assignment=self.assignment,
            company_id=self.company.pk,
        )
        assert cr.completed is False
        assert cr.company_id == self.company.pk

    def test_unique_employee_assignment(self):
        CompletionRecord.objects.create(
            target=self.target,
            employee=self.employee,
            assignment=self.assignment,
            company_id=self.company.pk,
        )
        # A second target for a different employee but same assignment+employee pair
        with pytest.raises(IntegrityError):
            CompletionRecord.objects.create(
                target=self.target,
                employee=self.employee,
                assignment=self.assignment,
                company_id=self.company.pk,
            )
