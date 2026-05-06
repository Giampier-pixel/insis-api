from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.assignments.models import CompletionRecord
from apps.companies.models import Department, Employee


def company_summary(company):
    records = CompletionRecord.objects.filter(company_id=company.pk)
    total_records = records.count()
    completed_records = records.filter(completed=True).count()
    overdue_records = records.filter(
        completed=False,
        assignment__is_active=True,
        assignment__due_date__lt=timezone.now().date(),
    ).count()
    completion_rate = (
        round(completed_records / total_records * 100, 1) if total_records else 0
    )

    return [
        {
            "company": company.name,
            "total_employees": company.employees.count(),
            "total_departments": company.departments.count(),
            "active_assignments": company.course_assignments.filter(
                is_active=True
            ).count(),
            "total_assignment_records": total_records,
            "completed_assignment_records": completed_records,
            "overdue_assignment_records": overdue_records,
            "completion_rate": completion_rate,
        }
    ]


def completion_by_department(company):
    rows = []
    departments = Department.objects.filter(company=company).annotate(
        employee_count=Count("employees", distinct=True),
        total_records=Count("employees__completion_records", distinct=True),
        completed_records=Count(
            "employees__completion_records",
            filter=Q(employees__completion_records__completed=True),
            distinct=True,
        ),
    )

    for department in departments:
        total = department.total_records
        completed = department.completed_records
        rows.append(
            {
                "department": department.name,
                "employee_count": department.employee_count,
                "total_records": total,
                "completed_records": completed,
                "completion_rate": round(completed / total * 100, 1) if total else 0,
            }
        )

    no_department_records = CompletionRecord.objects.filter(
        company_id=company.pk,
        employee__department__isnull=True,
    )
    if no_department_records.exists():
        total = no_department_records.count()
        completed = no_department_records.filter(completed=True).count()
        rows.append(
            {
                "department": "Sin departamento",
                "employee_count": Employee.objects.filter(
                    company=company, department__isnull=True
                ).count(),
                "total_records": total,
                "completed_records": completed,
                "completion_rate": round(completed / total * 100, 1) if total else 0,
            }
        )

    return rows


def employee_ranking(company):
    employees = (
        Employee.objects.filter(company=company)
        .select_related("user", "department")
        .annotate(
            assigned_count=Count("completion_records", distinct=True),
            completed_count=Count(
                "completion_records",
                filter=Q(completion_records__completed=True),
                distinct=True,
            ),
            average_score=Avg("completion_records__score"),
        )
        .order_by("-completed_count", "-average_score", "user__full_name")
    )

    rows = []
    for employee in employees:
        assigned = employee.assigned_count
        completed = employee.completed_count
        rows.append(
            {
                "employee": employee.user.full_name,
                "email": employee.user.email,
                "department": employee.department.name if employee.department else "",
                "assigned_count": assigned,
                "completed_count": completed,
                "completion_rate": (
                    round(completed / assigned * 100, 1) if assigned else 0
                ),
                "average_score": (
                    round(float(employee.average_score), 2)
                    if employee.average_score is not None
                    else None
                ),
            }
        )
    return rows


def overdue_assignments(company):
    records = (
        CompletionRecord.objects.filter(
            company_id=company.pk,
            completed=False,
            assignment__is_active=True,
            assignment__due_date__lt=timezone.now().date(),
        )
        .select_related(
            "employee__user",
            "employee__department",
            "assignment__course",
        )
        .order_by("assignment__due_date", "employee__user__full_name")
    )

    return [
        {
            "employee": record.employee.user.full_name,
            "email": record.employee.user.email,
            "department": (
                record.employee.department.name if record.employee.department else ""
            ),
            "course": record.assignment.course.title,
            "due_date": (
                record.assignment.due_date.isoformat()
                if record.assignment.due_date
                else ""
            ),
            "days_overdue": (timezone.now().date() - record.assignment.due_date).days,
        }
        for record in records
    ]


REPORT_BUILDERS = {
    "company-summary": company_summary,
    "completion-by-department": completion_by_department,
    "employee-ranking": employee_ranking,
    "overdue-assignments": overdue_assignments,
}


REPORT_TITLES = {
    "company-summary": "Company Summary",
    "completion-by-department": "Completion by Department",
    "employee-ranking": "Employee Ranking",
    "overdue-assignments": "Overdue Assignments",
}


def build_report(report_type, company):
    return REPORT_BUILDERS[report_type](company)


def build_all_reports(company):
    return {
        report_type: builder(company)
        for report_type, builder in REPORT_BUILDERS.items()
    }
