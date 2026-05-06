import pytest

from rest_framework.test import APIClient

from apps.companies.models import Company, Department, Employee
from apps.users.models import CustomUser, Roles


def make_user(email, role=Roles.STUDENT, password="pass1234"):
    return CustomUser.objects.create_user(
        email=email, full_name="Test User", password=password, role=role
    )


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestCompanyViewSet:
    def setup_method(self):
        self.admin = make_user("admin@corp.com", role=Roles.ADMIN)
        self.hr = make_user("hr@corp.com", role=Roles.HR_MANAGER)
        self.student = make_user("stu@corp.com", role=Roles.STUDENT)
        self.company = Company.objects.create(name="Test Corp", ruc="20999999991")
        Employee.objects.create(user=self.hr, company=self.company, is_hr_manager=True)

    # --- list ---

    def test_admin_list_companies(self):
        resp = auth_client(self.admin).get("/api/v1/companies/")
        assert resp.status_code == 200

    def test_hr_cannot_list_companies(self):
        resp = auth_client(self.hr).get("/api/v1/companies/")
        assert resp.status_code == 403

    def test_student_cannot_list_companies(self):
        resp = auth_client(self.student).get("/api/v1/companies/")
        assert resp.status_code == 403

    # --- create ---

    def test_admin_creates_company(self):
        resp = auth_client(self.admin).post(
            "/api/v1/companies/", {"name": "New Co", "ruc": "20888888881"}
        )
        assert resp.status_code == 201
        assert resp.data["ruc"] == "20888888881"

    def test_invalid_ruc_rejected(self):
        resp = auth_client(self.admin).post(
            "/api/v1/companies/", {"name": "Bad Co", "ruc": "ABC"}
        )
        assert resp.status_code == 400

    def test_hr_cannot_create_company(self):
        resp = auth_client(self.hr).post(
            "/api/v1/companies/", {"name": "Hack Co", "ruc": "20777777771"}
        )
        assert resp.status_code == 403

    # --- retrieve ---

    def test_admin_retrieve_any_company(self):
        resp = auth_client(self.admin).get(f"/api/v1/companies/{self.company.pk}/")
        assert resp.status_code == 200

    def test_hr_retrieve_own_company(self):
        resp = auth_client(self.hr).get(f"/api/v1/companies/{self.company.pk}/")
        assert resp.status_code == 200

    def test_hr_cannot_retrieve_other_company(self):
        other = Company.objects.create(name="Other Corp", ruc="20666666661")
        resp = auth_client(self.hr).get(f"/api/v1/companies/{other.pk}/")
        assert resp.status_code in (403, 404)

    # --- departments ---

    def test_hr_list_departments(self):
        Department.objects.create(company=self.company, name="HR Dept")
        resp = auth_client(self.hr).get(
            f"/api/v1/companies/{self.company.pk}/departments/"
        )
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_hr_create_department(self):
        resp = auth_client(self.hr).post(
            f"/api/v1/companies/{self.company.pk}/departments/",
            {"name": "Engineering"},
        )
        assert resp.status_code == 201
        assert resp.data["name"] == "Engineering"

    def test_student_cannot_access_departments(self):
        resp = auth_client(self.student).get(
            f"/api/v1/companies/{self.company.pk}/departments/"
        )
        assert resp.status_code in (403, 404)

    # --- stats ---

    def test_hr_get_stats(self):
        resp = auth_client(self.hr).get(f"/api/v1/companies/{self.company.pk}/stats/")
        assert resp.status_code == 200
        assert resp.data["total_employees"] == 1
        assert resp.data["hr_managers"] == 1

    def test_admin_get_stats(self):
        resp = auth_client(self.admin).get(
            f"/api/v1/companies/{self.company.pk}/stats/"
        )
        assert resp.status_code == 200

    # --- soft delete ---

    def test_admin_delete_company(self):
        company = Company.objects.create(name="Delete Me", ruc="20555555551")
        resp = auth_client(self.admin).delete(f"/api/v1/companies/{company.pk}/")
        assert resp.status_code == 204
        company.refresh_from_db()
        assert company.deleted_at is not None

    def test_deleted_company_not_in_list(self):
        company = Company.objects.create(name="Gone", ruc="20444444441")
        company.delete()
        resp = auth_client(self.admin).get("/api/v1/companies/")
        ids = [c["id"] for c in resp.data["results"]]
        assert company.pk not in ids


@pytest.mark.django_db
class TestEmployeeViewSet:
    def setup_method(self):
        self.admin = make_user("admin2@corp.com", role=Roles.ADMIN)
        self.hr = make_user("hr2@corp.com", role=Roles.HR_MANAGER)
        self.student = make_user("stu2@corp.com", role=Roles.STUDENT)
        self.company = Company.objects.create(name="Emp Corp", ruc="20333333331")
        Employee.objects.create(user=self.hr, company=self.company, is_hr_manager=True)

    # --- list ---

    def test_hr_list_own_employees(self):
        resp = auth_client(self.hr).get("/api/v1/employees/")
        assert resp.status_code == 200
        assert len(resp.data) == 1  # the HR manager themselves

    def test_admin_list_all_employees(self):
        resp = auth_client(self.admin).get("/api/v1/employees/")
        assert resp.status_code == 200

    def test_student_cannot_list_employees(self):
        resp = auth_client(self.student).get("/api/v1/employees/")
        assert resp.status_code == 403

    # --- create ---

    def test_hr_create_employee(self):
        resp = auth_client(self.hr).post(
            "/api/v1/employees/",
            {"email": "new@corp.com", "full_name": "New Person"},
        )
        assert resp.status_code == 201
        assert resp.data["email"] == "new@corp.com"

    def test_create_employee_with_department(self):
        dept = Department.objects.create(company=self.company, name="Dev")
        resp = auth_client(self.hr).post(
            "/api/v1/employees/",
            {"email": "dev@corp.com", "full_name": "Dev Person", "department": dept.pk},
        )
        assert resp.status_code == 201
        assert resp.data["department"] == dept.pk

    def test_duplicate_employee_rejected(self):
        emp_user = make_user("dup@corp.com")
        Employee.objects.create(user=emp_user, company=self.company)
        resp = auth_client(self.hr).post(
            "/api/v1/employees/",
            {"email": "dup@corp.com", "full_name": "Dup Person"},
        )
        assert resp.status_code == 400

    def test_student_cannot_create_employee(self):
        resp = auth_client(self.student).post(
            "/api/v1/employees/",
            {"email": "x@corp.com", "full_name": "X"},
        )
        assert resp.status_code == 403

    # --- retrieve ---

    def test_hr_retrieve_own_employee(self):
        emp_user = make_user("emp3@corp.com")
        emp = Employee.objects.create(user=emp_user, company=self.company)
        resp = auth_client(self.hr).get(f"/api/v1/employees/{emp.pk}/")
        assert resp.status_code == 200

    # --- partial update ---

    def test_hr_partial_update_employee(self):
        emp_user = make_user("emp4@corp.com")
        emp = Employee.objects.create(user=emp_user, company=self.company)
        resp = auth_client(self.hr).patch(
            f"/api/v1/employees/{emp.pk}/", {"is_hr_manager": True}
        )
        assert resp.status_code == 200
        assert resp.data["is_hr_manager"] is True

    def test_student_cannot_update_employee(self):
        emp_user = make_user("emp5@corp.com")
        Employee.objects.create(user=emp_user, company=self.company)
        # Student gets 403 before the queryset lookup.
        resp = auth_client(self.student).patch(
            "/api/v1/employees/99999/", {"is_hr_manager": True}
        )
        assert resp.status_code == 403

    # --- bulk import ---

    def test_bulk_import_employees(self):
        import io

        csv_content = (
            "email,full_name,department\n"
            "bulk1@corp.com,Bulk One,Sales\n"
            "bulk2@corp.com,Bulk Two,Sales\n"
        )
        csv_file = io.BytesIO(csv_content.encode())
        csv_file.name = "employees.csv"
        resp = auth_client(self.hr).post(
            "/api/v1/employees/bulk-import/",
            {"file": csv_file},
            format="multipart",
        )
        assert resp.status_code == 201
        assert resp.data["created"] == 2
        assert len(resp.data["errors"]) == 0
        assert Department.objects.filter(company=self.company, name="Sales").exists()

    def test_bulk_import_invalid_format(self):
        import io

        txt_file = io.BytesIO(b"not a csv")
        txt_file.name = "employees.txt"
        resp = auth_client(self.hr).post(
            "/api/v1/employees/bulk-import/",
            {"file": txt_file},
            format="multipart",
        )
        assert resp.status_code == 400

    def test_student_cannot_bulk_import(self):
        import io

        csv_file = io.BytesIO(b"email,full_name\nx@corp.com,X\n")
        csv_file.name = "emp.csv"
        resp = auth_client(self.student).post(
            "/api/v1/employees/bulk-import/",
            {"file": csv_file},
            format="multipart",
        )
        assert resp.status_code == 403
