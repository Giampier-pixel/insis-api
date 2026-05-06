from unittest.mock import MagicMock, patch

import pytest

from apps.assignments.models import AssignmentTarget, CompletionRecord, CourseAssignment
from apps.companies.models import Company, Employee
from apps.courses.models import Course
from apps.notifications.models import EmailNotification
from apps.notifications.tasks import (
    send_assignment_notification,
    send_bulk_assignment_emails,
    send_welcome_email,
)
from apps.users.models import CustomUser, Roles


def make_user(email, role=Roles.STUDENT):
    with patch("apps.notifications.tasks.send_welcome_email.delay"):
        return CustomUser.objects.create_user(
            email=email,
            full_name="Test User",
            password="pass12345!",
            role=role,
        )


def make_course(slug="notifications-course"):
    instructor = make_user(f"instructor-{slug}@t.com", role=Roles.INSTRUCTOR)
    return Course.objects.create(
        title="Notifications Course",
        slug=slug,
        instructor=instructor,
        is_published=True,
    )


def make_completion_record():
    company = Company.objects.create(name="Notify Co", ruc="10999999999")
    employee = Employee.objects.create(
        user=make_user("employee-notify@t.com"),
        company=company,
    )
    assignment = CourseAssignment.objects.create(
        course=make_course(),
        company=company,
        assigned_by=make_user("hr-notify@t.com", role=Roles.HR_MANAGER),
        scope=CourseAssignment.Scope.INDIVIDUAL,
    )
    target = AssignmentTarget.objects.create(assignment=assignment, employee=employee)
    with patch("apps.notifications.tasks.send_assignment_notification.delay"):
        return CompletionRecord.objects.create(
            target=target,
            employee=employee,
            assignment=assignment,
            company_id=company.pk,
        )


@pytest.mark.django_db
def test_send_welcome_email_creates_sent_notification():
    user = make_user("welcome-notification@t.com")

    with patch("apps.notifications.tasks.send_mail") as send_mail:
        send_welcome_email(user.id)

    notification = EmailNotification.objects.get(
        user=user,
        notification_type="welcome",
    )
    assert notification.status == EmailNotification.Status.SENT
    assert notification.sent_at is not None
    assert notification.body_template == "welcome"
    send_mail.assert_called_once()


@pytest.mark.django_db
def test_send_assignment_notification_is_idempotent():
    record = make_completion_record()

    with patch("apps.notifications.tasks.send_mail"):
        result = send_assignment_notification(record.id)
        skipped = send_assignment_notification(record.id)

    assert result["status"] == "sent"
    assert skipped["status"] == "skipped"
    assert (
        EmailNotification.objects.filter(
            user=record.employee.user,
            notification_type="assignment_notification",
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_send_bulk_assignment_emails_fans_out_with_group():
    record = make_completion_record()
    async_result = MagicMock()
    celery_group = MagicMock(return_value=async_result)

    with patch("apps.notifications.tasks.group", celery_group):
        result = send_bulk_assignment_emails(record.assignment_id)

    assert result == {"status": "ok", "queued": 1}
    celery_group.assert_called_once()
    async_result.apply_async.assert_called_once()


@pytest.mark.django_db
def test_completion_record_creation_queues_assignment_notification():
    company = Company.objects.create(name="Signal Co", ruc="10888888888")
    employee = Employee.objects.create(
        user=make_user("employee-signal@t.com"),
        company=company,
    )
    assignment = CourseAssignment.objects.create(
        course=make_course("signal-course"),
        company=company,
        assigned_by=make_user("hr-signal@t.com", role=Roles.HR_MANAGER),
        scope=CourseAssignment.Scope.INDIVIDUAL,
    )
    target = AssignmentTarget.objects.create(assignment=assignment, employee=employee)

    with patch("apps.notifications.tasks.send_assignment_notification.delay") as delay:
        record = CompletionRecord.objects.create(
            target=target,
            employee=employee,
            assignment=assignment,
            company_id=company.pk,
        )

    delay.assert_called_once_with(record.id)
