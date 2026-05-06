import pytest

from django.db import IntegrityError

from apps.companies.models import Company, Department, Employee
from apps.users.models import CustomUser, Roles


def make_user(email, role=Roles.STUDENT):
    return CustomUser.objects.create_user(
        email=email, full_name="Test User", password="pass1234", role=role
    )


@pytest.mark.django_db
class TestCompanyModel:
    def test_creation(self):
        company = Company.objects.create(name="Acme Corp", ruc="20123456789")
        assert company.pk is not None
        assert str(company) == "Acme Corp (20123456789)"

    def test_ruc_unique(self):
        Company.objects.create(name="Alpha", ruc="20111111111")
        with pytest.raises(IntegrityError):
            Company.objects.create(name="Beta", ruc="20111111111")

    def test_soft_delete_hides_from_alive_manager(self):
        company = Company.objects.create(name="Gone Corp", ruc="20000000001")
        pk = company.pk
        company.delete()
        assert Company.objects.filter(pk=pk).count() == 0
        assert Company.all_objects.filter(pk=pk).count() == 1

    def test_timestamps_set(self):
        company = Company.objects.create(name="Time Corp", ruc="20000000002")
        assert company.created_at is not None
        assert company.updated_at is not None


@pytest.mark.django_db
class TestDepartmentModel:
    def setup_method(self):
        self.company = Company.objects.create(name="Corp A", ruc="20222222221")

    def test_creation_and_str(self):
        dept = Department.objects.create(company=self.company, name="Engineering")
        assert str(dept) == "Engineering — Corp A"

    def test_name_unique_per_company(self):
        Department.objects.create(company=self.company, name="Sales")
        with pytest.raises(IntegrityError):
            Department.objects.create(company=self.company, name="Sales")

    def test_same_name_different_company(self):
        other = Company.objects.create(name="Corp B", ruc="20333333331")
        Department.objects.create(company=self.company, name="Finance")
        dept2 = Department.objects.create(company=other, name="Finance")
        assert dept2.pk is not None

    def test_soft_delete(self):
        dept = Department.objects.create(company=self.company, name="IT")
        pk = dept.pk
        dept.delete()
        assert Department.objects.filter(pk=pk).count() == 0
        assert Department.all_objects.filter(pk=pk).count() == 1


@pytest.mark.django_db
class TestEmployeeModel:
    def setup_method(self):
        self.company = Company.objects.create(name="TechCorp", ruc="20444444441")
        self.user = make_user("emp@test.com")

    def test_creation_and_str(self):
        emp = Employee.objects.create(user=self.user, company=self.company)
        assert str(emp) == "emp@test.com @ TechCorp"
        assert emp.is_hr_manager is False

    def test_user_company_unique(self):
        Employee.objects.create(user=self.user, company=self.company)
        with pytest.raises(IntegrityError):
            Employee.objects.create(user=self.user, company=self.company)

    def test_hr_manager_flag(self):
        emp = Employee.objects.create(
            user=self.user, company=self.company, is_hr_manager=True
        )
        assert emp.is_hr_manager is True

    def test_department_nullable(self):
        emp = Employee.objects.create(user=self.user, company=self.company)
        assert emp.department is None

    def test_soft_delete(self):
        emp = Employee.objects.create(user=self.user, company=self.company)
        pk = emp.pk
        emp.delete()
        assert Employee.objects.filter(pk=pk).count() == 0
        assert Employee.all_objects.filter(pk=pk).count() == 1

    def test_alive_manager_excludes_deleted(self):
        emp = Employee.objects.create(user=self.user, company=self.company)
        emp.delete()
        # objects manager already filters to alive-only records
        assert Employee.objects.count() == 0
