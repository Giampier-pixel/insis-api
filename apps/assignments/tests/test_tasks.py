import pytest

from apps.assignments.models import AssignmentTarget, CompletionRecord, CourseAssignment
from apps.assignments.tasks import materialize_assignment_targets
from apps.companies.models import Company, Department, Employee
from apps.courses.models import Course
from apps.enrollments.models import Enrollment
from apps.users.models import CustomUser, Roles


def make_user(email, role=Roles.STUDENT):
    return CustomUser.objects.create_user(
        email=email, full_name="T", password="pass", role=role
    )


def make_company(ruc="11111111111"):
    return Company.objects.create(name="Co", ruc=ruc)


def make_dept(company, name="Dept"):
    return Department.objects.create(company=company, name=name)


def make_employee(company, dept=None, email_suffix=""):
    user = make_user(f"emp{email_suffix}@t.com")
    return Employee.objects.create(user=user, company=company, department=dept)


def make_course(slug="c1"):
    inst = make_user(f"inst{slug}@t.com", role=Roles.INSTRUCTOR)
    return Course.objects.create(
        title="C", slug=slug, instructor=inst, is_published=True
    )


def make_assignment(course, company, scope=CourseAssignment.Scope.COMPANY):
    hr = make_user("hr@t.com", role=Roles.HR_MANAGER)
    return CourseAssignment.objects.create(
        course=course, company=company, assigned_by=hr, scope=scope
    )


@pytest.mark.django_db
class TestMaterializeTask:
    def setup_method(self):
        self.company = make_company()
        self.dept = make_dept(self.company)
        self.course = make_course()
        self.emp1 = make_employee(self.company, self.dept, "1")
        self.emp2 = make_employee(self.company, self.dept, "2")

    def test_company_scope_creates_targets_for_all(self):
        a = make_assignment(self.course, self.company, CourseAssignment.Scope.COMPANY)
        result = materialize_assignment_targets(a.id)
        assert result["created"] == 2
        assert AssignmentTarget.objects.filter(assignment=a).count() == 2

    def test_creates_enrollments_with_b2b_source(self):
        a = make_assignment(self.course, self.company, CourseAssignment.Scope.COMPANY)
        materialize_assignment_targets(a.id)
        enrollments = Enrollment.objects.filter(course=self.course)
        assert enrollments.count() == 2
        for e in enrollments:
            assert e.source == Enrollment.Source.B2B_ASSIGNMENT

    def test_creates_completion_records(self):
        a = make_assignment(self.course, self.company, CourseAssignment.Scope.COMPANY)
        materialize_assignment_targets(a.id)
        assert CompletionRecord.objects.filter(assignment=a).count() == 2

    def test_completion_record_company_id_denormalized(self):
        a = make_assignment(self.course, self.company, CourseAssignment.Scope.COMPANY)
        materialize_assignment_targets(a.id)
        for cr in CompletionRecord.objects.filter(assignment=a):
            assert cr.company_id == self.company.pk

    def test_idempotent(self):
        a = make_assignment(self.course, self.company, CourseAssignment.Scope.COMPANY)
        materialize_assignment_targets(a.id)
        result2 = materialize_assignment_targets(a.id)
        assert result2["created"] == 0
        assert AssignmentTarget.objects.filter(assignment=a).count() == 2

    def test_department_scope_filters_by_dept(self):
        other_dept = make_dept(self.company, "Other")
        make_employee(self.company, other_dept, "3")
        a = make_assignment(
            self.course, self.company, CourseAssignment.Scope.DEPARTMENT
        )
        result = materialize_assignment_targets(a.id, department_id=self.dept.id)
        assert result["created"] == 2  # only emp1 + emp2 (in self.dept)
        assert AssignmentTarget.objects.filter(assignment=a).count() == 2

    def test_individual_scope(self):
        a = make_assignment(
            self.course, self.company, CourseAssignment.Scope.INDIVIDUAL
        )
        result = materialize_assignment_targets(a.id, employee_id=self.emp1.id)
        assert result["created"] == 1
        assert (
            AssignmentTarget.objects.filter(assignment=a, employee=self.emp1).count()
            == 1
        )

    def test_inactive_assignment_skipped(self):
        a = make_assignment(self.course, self.company)
        a.is_active = False
        a.save(update_fields=["is_active"])
        result = materialize_assignment_targets(a.id)
        assert result["status"] == "not_found"

    def test_enrollment_links_course_assignment(self):
        a = make_assignment(self.course, self.company, CourseAssignment.Scope.COMPANY)
        materialize_assignment_targets(a.id)
        for e in Enrollment.objects.filter(course=self.course):
            assert e.course_assignment_id == a.id


@pytest.mark.django_db
class TestCompletionRecordSignal:
    def test_completion_record_updated_when_enrollment_completed(self):
        company = make_company("22222222222")
        course = make_course("c-signal")
        emp = make_employee(company, email_suffix="sig")
        hr = make_user("hrsig@t.com", role=Roles.HR_MANAGER)
        assignment = CourseAssignment.objects.create(
            course=course,
            company=company,
            assigned_by=hr,
            scope=CourseAssignment.Scope.INDIVIDUAL,
        )
        materialize_assignment_targets(assignment.id, employee_id=emp.id)

        enrollment = Enrollment.objects.get(student=emp.user, course=course)
        enrollment.mark_completed()

        cr = CompletionRecord.objects.get(assignment=assignment, employee=emp)
        assert cr.completed is True
        assert cr.completed_at is not None
