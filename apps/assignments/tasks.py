from celery import shared_task


def _create_targets_for_employees(assignment, employees):
    """
    Creates AssignmentTarget + Enrollment + CompletionRecord for each employee.
    Idempotent: uses get_or_create throughout.
    Returns the count of newly created targets.
    """
    from django.db import IntegrityError

    from apps.assignments.models import AssignmentTarget, CompletionRecord
    from apps.enrollments.models import Enrollment

    created = 0
    for employee in employees:
        target, target_new = AssignmentTarget.objects.get_or_create(
            assignment=assignment,
            employee=employee,
        )
        if not target_new:
            continue

        # Enrollment may already exist (direct enrollment) — that is fine
        try:
            Enrollment.objects.get_or_create(
                student=employee.user,
                course=assignment.course,
                defaults={
                    "source": Enrollment.Source.B2B_ASSIGNMENT,
                    "course_assignment": assignment,
                },
            )
        except IntegrityError:
            # Soft-deleted enrollment occupies the unique slot; leave it
            pass

        CompletionRecord.objects.get_or_create(
            target=target,
            defaults={
                "employee": employee,
                "assignment": assignment,
                "company_id": employee.company_id,
            },
        )
        created += 1

    return created


@shared_task
def materialize_assignment_targets(assignment_id, department_id=None, employee_id=None):
    """
    Materializes AssignmentTarget rows (plus Enrollment + CompletionRecord) for a
    CourseAssignment.  Extra params narrow the scope for DEPARTMENT / INDIVIDUAL calls.
    """
    from apps.assignments.models import CourseAssignment
    from apps.companies.models import Employee

    try:
        assignment = CourseAssignment.objects.select_related("course", "company").get(
            pk=assignment_id, is_active=True
        )
    except CourseAssignment.DoesNotExist:
        return {"status": "not_found"}

    if department_id:
        employees = Employee.objects.filter(
            department_id=department_id, company=assignment.company
        )
    elif employee_id:
        employees = Employee.objects.filter(pk=employee_id, company=assignment.company)
    elif assignment.scope == CourseAssignment.Scope.COMPANY:
        employees = Employee.objects.filter(company=assignment.company)
    else:
        return {"status": "no_target"}

    count = _create_targets_for_employees(assignment, employees)
    return {"status": "ok", "created": count}
