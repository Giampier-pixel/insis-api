import pytest

from rest_framework.test import APIClient

from apps.assignments.models import AssignmentTarget, CourseAssignment
from apps.companies.models import Company, Department, Employee
from apps.courses.models import Course
from apps.users.models import CustomUser, Roles


def make_user(email, role=Roles.STUDENT, password="pass1234"):
    return CustomUser.objects.create_user(
        email=email, full_name="T", password=password, role=role
    )


def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_company(ruc="12345678901"):
    return Company.objects.create(name="Acme", ruc=ruc)


def make_dept(company, name="Eng"):
    return Department.objects.create(company=company, name=name)


def make_employee(company, dept=None, role=Roles.STUDENT, suffix=""):
    user = make_user(f"emp{suffix}@t.com", role=role)
    return Employee.objects.create(user=user, company=company, department=dept)


def make_hr_employee(company, suffix=""):
    user = make_user(f"hr{suffix}@t.com", role=Roles.HR_MANAGER)
    return Employee.objects.create(user=user, company=company, is_hr_manager=True)


def make_course(slug="c1"):
    inst = make_user(f"inst_{slug}@t.com", role=Roles.INSTRUCTOR)
    return Course.objects.create(
        title="C", slug=slug, instructor=inst, is_published=True
    )


def make_assignment(course, company, hr_user, scope=CourseAssignment.Scope.COMPANY):
    return CourseAssignment.objects.create(
        course=course, company=company, assigned_by=hr_user, scope=scope
    )


# ------------------------------------------------------------------ list


@pytest.mark.django_db
class TestAssignmentList:
    def setup_method(self):
        self.company = make_company()
        self.hr_emp = make_hr_employee(self.company)
        self.hr = self.hr_emp.user
        self.admin = make_user("admin@t.com", role=Roles.ADMIN)
        self.course = make_course()

    def test_hr_sees_own_company(self):
        make_assignment(self.course, self.company, self.hr)
        other_co = make_company("99999999999")
        other_hr = make_user("otherhr@t.com", role=Roles.HR_MANAGER)
        make_assignment(self.course, other_co, other_hr)
        resp = auth_client(self.hr).get("/api/v1/assignments/")
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_admin_sees_all(self):
        make_assignment(self.course, self.company, self.hr)
        other_co = make_company("88888888888")
        other_hr = make_user("otherhr2@t.com", role=Roles.HR_MANAGER)
        make_assignment(self.course, other_co, other_hr)
        resp = auth_client(self.admin).get("/api/v1/assignments/")
        assert resp.status_code == 200
        assert resp.data["count"] == 2

    def test_student_403(self):
        stu = make_user("stu@t.com")
        resp = auth_client(stu).get("/api/v1/assignments/")
        assert resp.status_code == 403

    def test_includes_completion_pct(self):
        make_assignment(self.course, self.company, self.hr)
        resp = auth_client(self.hr).get("/api/v1/assignments/")
        assert "completion_pct" in resp.data["results"][0]

    def test_cancelled_not_in_list(self):
        a = make_assignment(self.course, self.company, self.hr)
        a.is_active = False
        a.save(update_fields=["is_active"])
        resp = auth_client(self.hr).get("/api/v1/assignments/")
        assert resp.data["count"] == 0


# ------------------------------------------------------------------ create


@pytest.mark.django_db
class TestAssignmentCreate:
    def setup_method(self):
        self.company = make_company()
        self.hr_emp = make_hr_employee(self.company)
        self.hr = self.hr_emp.user
        self.admin = make_user("admin@t.com", role=Roles.ADMIN)
        self.course = make_course()

    def test_hr_creates_for_own_company(self):
        resp = auth_client(self.hr).post(
            "/api/v1/assignments/",
            {"course": self.course.id, "company": self.company.id, "scope": "COMPANY"},
        )
        assert resp.status_code == 201
        assert resp.data["scope"] == "COMPANY"

    def test_hr_cannot_create_for_other_company(self):
        other = make_company("77777777777")
        resp = auth_client(self.hr).post(
            "/api/v1/assignments/",
            {"course": self.course.id, "company": other.id, "scope": "COMPANY"},
        )
        assert resp.status_code == 403

    def test_admin_creates_for_any_company(self):
        resp = auth_client(self.admin).post(
            "/api/v1/assignments/",
            {"course": self.course.id, "company": self.company.id, "scope": "COMPANY"},
        )
        assert resp.status_code == 201

    def test_student_cannot_create(self):
        stu = make_user("stu@t.com")
        resp = auth_client(stu).post(
            "/api/v1/assignments/",
            {"course": self.course.id, "company": self.company.id, "scope": "COMPANY"},
        )
        assert resp.status_code == 403


# ------------------------------------------------------------------ destroy


@pytest.mark.django_db
class TestAssignmentDestroy:
    def setup_method(self):
        self.company = make_company()
        self.hr_emp = make_hr_employee(self.company)
        self.hr = self.hr_emp.user
        self.admin = make_user("admin@t.com", role=Roles.ADMIN)
        self.course = make_course()
        self.assignment = make_assignment(self.course, self.company, self.hr)

    def test_hr_can_cancel(self):
        resp = auth_client(self.hr).delete(f"/api/v1/assignments/{self.assignment.id}/")
        assert resp.status_code == 204
        self.assignment.refresh_from_db()
        assert self.assignment.is_active is False

    def test_other_hr_cannot_cancel(self):
        other_co = make_company("66666666666")
        other_hr_emp = make_hr_employee(other_co, suffix="2")
        resp = auth_client(other_hr_emp.user).delete(
            f"/api/v1/assignments/{self.assignment.id}/"
        )
        assert resp.status_code in (403, 404)

    def test_admin_can_cancel(self):
        resp = auth_client(self.admin).delete(
            f"/api/v1/assignments/{self.assignment.id}/"
        )
        assert resp.status_code == 204


# ------------------------------------------------------------------ assign-department


@pytest.mark.django_db
class TestAssignDepartment:
    def setup_method(self):
        self.company = make_company()
        self.dept = make_dept(self.company)
        self.hr_emp = make_hr_employee(self.company)
        self.hr = self.hr_emp.user
        self.course = make_course()
        self.assignment = make_assignment(
            self.course, self.company, self.hr, scope=CourseAssignment.Scope.DEPARTMENT
        )

    def test_valid_department_accepted(self):
        resp = auth_client(self.hr).post(
            f"/api/v1/assignments/{self.assignment.id}/assign-department/",
            {"department": self.dept.id},
        )
        assert resp.status_code == 202

    def test_department_from_other_company_rejected(self):
        other_co = make_company("55555555555")
        other_dept = make_dept(other_co, name="OtherDept")
        resp = auth_client(self.hr).post(
            f"/api/v1/assignments/{self.assignment.id}/assign-department/",
            {"department": other_dept.id},
        )
        assert resp.status_code == 400

    def test_inactive_assignment_404(self):
        self.assignment.is_active = False
        self.assignment.save(update_fields=["is_active"])
        resp = auth_client(self.hr).post(
            f"/api/v1/assignments/{self.assignment.id}/assign-department/",
            {"department": self.dept.id},
        )
        assert resp.status_code == 404


# ------------------------------------------------------------------ targets


@pytest.mark.django_db
class TestTargetsList:
    def setup_method(self):
        self.company = make_company()
        self.dept = make_dept(self.company)
        self.hr_emp = make_hr_employee(self.company)
        self.hr = self.hr_emp.user
        self.course = make_course()
        self.assignment = make_assignment(self.course, self.company, self.hr)
        self.emp = make_employee(self.company, self.dept, suffix="t")

    def test_hr_can_view_targets(self):
        AssignmentTarget.objects.create(assignment=self.assignment, employee=self.emp)
        resp = auth_client(self.hr).get(
            f"/api/v1/assignments/{self.assignment.id}/targets/"
        )
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_student_cannot_view_targets(self):
        stu = make_user("stu@t.com")
        resp = auth_client(stu).get(
            f"/api/v1/assignments/{self.assignment.id}/targets/"
        )
        # Student's queryset returns none(), so the assignment is not found
        assert resp.status_code in (403, 404)
