from datetime import timedelta
from unittest.mock import patch

import pytest

from django.utils import timezone

from rest_framework.test import APIClient

from apps.assignments.models import AssignmentTarget, CompletionRecord, CourseAssignment
from apps.companies.models import Company, Department, Employee
from apps.courses.models import Course
from apps.reports.data import (
    company_summary,
    completion_by_department,
    employee_ranking,
    overdue_assignments,
)
from apps.reports.exporters import export_csv, export_excel
from apps.reports.models import ReportExportJob
from apps.reports.tasks import generate_report_export
from apps.users.models import CustomUser, Roles


def make_user(email, role=Roles.STUDENT):
    with patch("apps.notifications.tasks.send_welcome_email.delay"):
        return CustomUser.objects.create_user(
            email=email,
            full_name=email.split("@")[0],
            password="pass12345!",
            role=role,
        )


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def make_company(ruc="20999999999"):
    return Company.objects.create(name="Report Co", ruc=ruc)


def make_course(slug="report-course"):
    instructor = make_user(f"instructor-{slug}@t.com", Roles.INSTRUCTOR)
    return Course.objects.create(
        title="Report Course",
        slug=slug,
        instructor=instructor,
        is_published=True,
    )


def make_employee(company, department=None, suffix="1", is_hr_manager=False):
    role = Roles.HR_MANAGER if is_hr_manager else Roles.STUDENT
    return Employee.objects.create(
        user=make_user(f"employee-{suffix}@t.com", role),
        company=company,
        department=department,
        is_hr_manager=is_hr_manager,
    )


def make_record(company, employee, course, completed=False, due_date=None, score=None):
    assignment = CourseAssignment.objects.create(
        course=course,
        company=company,
        assigned_by=make_user(f"assigner-{employee.pk}@t.com", Roles.HR_MANAGER),
        due_date=due_date,
    )
    target = AssignmentTarget.objects.create(assignment=assignment, employee=employee)
    with patch("apps.notifications.tasks.send_assignment_notification.delay"):
        return CompletionRecord.objects.create(
            target=target,
            employee=employee,
            assignment=assignment,
            company_id=company.pk,
            completed=completed,
            completed_at=timezone.now() if completed else None,
            score=score,
        )


@pytest.fixture
def report_data(db):
    company = make_company()
    department = Department.objects.create(company=company, name="Engineering")
    hr = make_employee(company, suffix="hr", is_hr_manager=True).user
    employee_1 = make_employee(company, department, "1")
    employee_2 = make_employee(company, department, "2")
    course = make_course()
    make_record(company, employee_1, course, completed=True, score=95)
    make_record(
        company,
        employee_2,
        course,
        completed=False,
        due_date=timezone.now().date() - timedelta(days=2),
    )
    return {
        "company": company,
        "department": department,
        "hr": hr,
        "course": course,
    }


@pytest.mark.django_db
def test_report_data_builders(report_data):
    company = report_data["company"]

    assert company_summary(company)[0]["completion_rate"] == 50
    assert completion_by_department(company)[0]["completed_records"] == 1
    assert employee_ranking(company)[0]["completed_count"] == 1
    assert overdue_assignments(company)[0]["days_overdue"] == 2


@pytest.mark.django_db
def test_exporters_generate_csv_and_excel(report_data):
    company = report_data["company"]

    csv_content = export_csv("employee-ranking", company)
    xlsx_content = export_excel("company-summary", company)

    assert b"employee,email,department" in csv_content
    assert xlsx_content.startswith(b"PK")


@pytest.mark.django_db
def test_create_export_job_queues_task(report_data):
    company = report_data["company"]
    hr = report_data["hr"]

    with patch("apps.reports.tasks.generate_report_export.delay") as delay:
        response = auth_client(hr).post(
            "/api/v1/reports/exports/",
            {
                "company": company.pk,
                "report_type": "company-summary",
                "file_format": "csv",
            },
        )

    assert response.status_code == 201
    assert response.data["status"] == ReportExportJob.Status.PENDING
    delay.assert_called_once_with(response.data["id"])


@pytest.mark.django_db
def test_hr_cannot_export_other_company(report_data):
    other = make_company("20888888888")
    hr = report_data["hr"]

    response = auth_client(hr).post(
        "/api/v1/reports/exports/",
        {
            "company": other.pk,
            "report_type": "company-summary",
            "file_format": "csv",
        },
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_sync_report_endpoint(report_data):
    company = report_data["company"]
    hr = report_data["hr"]

    response = auth_client(hr).get(
        f"/api/v1/reports/completion-by-department/?company={company.pk}"
    )

    assert response.status_code == 200
    assert response.data[0]["department"] == "Engineering"


@pytest.mark.django_db
def test_generate_report_export_marks_ready(report_data):
    company = report_data["company"]
    hr = report_data["hr"]
    job = ReportExportJob.objects.create(
        requested_by=hr,
        company=company,
        report_type="employee-ranking",
        file_format="csv",
    )

    with patch("apps.reports.storage.save_report_export") as save:
        expires_at = timezone.now() + timedelta(minutes=30)
        save.return_value = {
            "object_path": "reports/test.csv",
            "signed_url": "/media/reports/test.csv",
            "expires_at": expires_at,
        }
        result = generate_report_export(job.pk)

    job.refresh_from_db()
    assert result["status"] == "ready"
    assert job.status == ReportExportJob.Status.READY
    assert job.gcs_object_path == "reports/test.csv"
