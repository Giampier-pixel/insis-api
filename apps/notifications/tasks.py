from celery import group, shared_task

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.notifications.models import EmailNotification

# ──────────────────────────────────────────────────────────────
# Internal helper
# ──────────────────────────────────────────────────────────────


def _deliver(notification, body):
    """Send one email and update the notification status in-place."""
    try:
        send_mail(
            subject=notification.subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.user.email],
            fail_silently=False,
        )
        notification.status = EmailNotification.Status.SENT
        notification.sent_at = timezone.now()
        notification.save(update_fields=["status", "sent_at"])
    except Exception as exc:
        notification.status = EmailNotification.Status.FAILED
        notification.error_message = str(exc)[:500]
        notification.save(update_fields=["status", "error_message"])


def _already_notified(user, notification_type, **context_filters):
    qs = EmailNotification.objects.filter(
        user=user,
        notification_type=notification_type,
    )
    for key, value in context_filters.items():
        qs = qs.filter(**{f"context__{key}": value})
    return qs.exists()


# ──────────────────────────────────────────────────────────────
# Transactional tasks  (triggered by signals / endpoints)
# ──────────────────────────────────────────────────────────────


@shared_task
def send_welcome_email(user_id):
    from django.contrib.auth import get_user_model

    User = get_user_model()

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    notif = EmailNotification.objects.create(
        user=user,
        subject="¡Bienvenido/a a INSIS!",
        body_template="welcome",
        context={"full_name": user.full_name, "email": user.email},
        notification_type="welcome",
    )
    body = (
        f"Hola {user.full_name},\n\n"
        f"Tu cuenta en INSIS ha sido creada exitosamente.\n"
        f"Email: {user.email}\n\n"
        f"¡Empieza a aprender hoy!"
    )
    _deliver(notif, body)


@shared_task
def send_enrollment_confirmation(enrollment_id):
    from apps.enrollments.models import Enrollment

    try:
        enrollment = Enrollment.objects.select_related("student", "course").get(
            pk=enrollment_id
        )
    except Enrollment.DoesNotExist:
        return

    user = enrollment.student
    notif = EmailNotification.objects.create(
        user=user,
        subject=f"Inscripción confirmada: {enrollment.course.title}",
        body_template="enrollment_confirmation",
        context={"course_title": enrollment.course.title, "full_name": user.full_name},
        notification_type="enrollment_confirmation",
    )
    body = (
        f"Hola {user.full_name},\n\n"
        f"Te has inscrito exitosamente en '{enrollment.course.title}'.\n"
        f"¡Buena suerte!"
    )
    _deliver(notif, body)


@shared_task
def send_lesson_completed_email(lesson_progress_id):
    from apps.enrollments.models import LessonProgress

    try:
        lp = LessonProgress.objects.select_related("enrollment__student", "lesson").get(
            pk=lesson_progress_id
        )
    except LessonProgress.DoesNotExist:
        return

    user = lp.enrollment.student
    notif = EmailNotification.objects.create(
        user=user,
        subject=f"Lección completada: {lp.lesson.title}",
        body_template="lesson_completed",
        context={
            "lesson_title": lp.lesson.title,
            "full_name": user.full_name,
            "course_title": lp.enrollment.course.title,
        },
        notification_type="lesson_completed",
    )
    body = (
        f"Hola {user.full_name},\n\n"
        f"Has completado la lección '{lp.lesson.title}' "
        f"del curso '{lp.enrollment.course.title}'.\n\n"
        f"¡Sigue adelante!"
    )
    _deliver(notif, body)


@shared_task
def send_course_completion(enrollment_id):
    from apps.enrollments.models import Enrollment

    try:
        enrollment = Enrollment.objects.select_related("student", "course").get(
            pk=enrollment_id
        )
    except Enrollment.DoesNotExist:
        return

    user = enrollment.student
    notif = EmailNotification.objects.create(
        user=user,
        subject=f"¡Felicitaciones! Completaste '{enrollment.course.title}'",
        body_template="course_completion",
        context={"course_title": enrollment.course.title, "full_name": user.full_name},
        notification_type="course_completion",
    )
    body = (
        f"Hola {user.full_name},\n\n"
        f"¡Felicitaciones! Has completado el curso "
        f"'{enrollment.course.title}' al 100%.\n\n"
        f"Tu certificado ya está disponible en la plataforma."
    )
    _deliver(notif, body)


@shared_task
def send_quiz_result(attempt_id):
    from apps.quizzes.models import Attempt

    try:
        attempt = Attempt.objects.select_related("student", "quiz__course").get(
            pk=attempt_id
        )
    except Attempt.DoesNotExist:
        return

    user = attempt.student
    score = float(attempt.score) if attempt.score is not None else 0
    result_text = "APROBADO ✓" if attempt.passed else "No aprobado ✗"
    notif = EmailNotification.objects.create(
        user=user,
        subject=f"Resultado del quiz: {attempt.quiz.title}",
        body_template="quiz_result",
        context={
            "quiz_title": attempt.quiz.title,
            "score": score,
            "passed": attempt.passed,
            "attempt_number": attempt.attempt_number,
            "full_name": user.full_name,
        },
        notification_type="quiz_result",
    )
    body = (
        f"Hola {user.full_name},\n\n"
        f"Resultado del quiz '{attempt.quiz.title}' - "
        f"Intento #{attempt.attempt_number}:\n"
        f"Score: {score:.1f}% — {result_text}\n"
        f"Nota mínima: {float(attempt.quiz.passing_score):.1f}%"
    )
    _deliver(notif, body)


@shared_task
def send_assignment_notification(completion_record_id):
    from apps.assignments.models import CompletionRecord

    try:
        record = CompletionRecord.objects.select_related(
            "employee__user", "assignment__course"
        ).get(pk=completion_record_id)
    except CompletionRecord.DoesNotExist:
        return

    user = record.employee.user
    if _already_notified(
        user,
        "assignment_notification",
        completion_record_id=record.pk,
    ):
        return {"status": "skipped", "reason": "already_notified"}

    notif = EmailNotification.objects.create(
        user=user,
        subject=f"Nuevo curso asignado: {record.assignment.course.title}",
        body_template="assignment_notification",
        context={
            "completion_record_id": record.pk,
            "assignment_id": record.assignment_id,
            "course_title": record.assignment.course.title,
            "full_name": user.full_name,
            "due_date": (
                str(record.assignment.due_date) if record.assignment.due_date else None
            ),
            "is_mandatory": record.assignment.is_mandatory,
        },
        notification_type="assignment_notification",
    )
    mandatory_text = "obligatorio" if record.assignment.is_mandatory else "opcional"
    due_text = (
        f"\nFecha límite: {record.assignment.due_date}"
        if record.assignment.due_date
        else ""
    )
    body = (
        f"Hola {user.full_name},\n\n"
        f"Se te ha asignado el curso "
        f"'{record.assignment.course.title}' ({mandatory_text}).{due_text}\n\n"
        f"Accede a la plataforma para comenzar."
    )
    _deliver(notif, body)
    return {"status": "sent", "notification_id": notif.pk}


@shared_task
def send_bulk_assignment_emails(assignment_id, department_id=None):
    """Fan out one notification task per assignment completion record."""
    from apps.assignments.models import CompletionRecord

    qs = CompletionRecord.objects.filter(assignment_id=assignment_id)
    if department_id:
        qs = qs.filter(employee__department_id=department_id)

    record_ids = list(qs.values_list("id", flat=True))
    if not record_ids:
        return {"status": "ok", "queued": 0}

    group(
        send_assignment_notification.s(record_id) for record_id in record_ids
    ).apply_async()
    return {"status": "ok", "queued": len(record_ids)}


# ──────────────────────────────────────────────────────────────
# Beat periodic tasks
# ──────────────────────────────────────────────────────────────


@shared_task
def send_due_date_reminder():
    """Runs daily at 09:30 — finds assignments due within 3 days."""
    from datetime import timedelta

    from apps.assignments.models import CompletionRecord

    today = timezone.now().date()
    cutoff = today + timedelta(days=3)

    records = CompletionRecord.objects.filter(
        completed=False,
        assignment__is_active=True,
        assignment__due_date__range=(today, cutoff),
    ).select_related("employee__user", "assignment__course")

    for record in records:
        user = record.employee.user
        notif = EmailNotification.objects.create(
            user=user,
            subject=f"Recordatorio: '{record.assignment.course.title}' vence pronto",
            body_template="due_date_reminder",
            context={
                "full_name": user.full_name,
                "course_title": record.assignment.course.title,
                "due_date": str(record.assignment.due_date),
            },
            notification_type="due_date_reminder",
        )
        body = (
            f"Hola {user.full_name},\n\n"
            f"El curso '{record.assignment.course.title}' vence el "
            f"{record.assignment.due_date}.\n"
            f"¡Complétalo a tiempo!"
        )
        _deliver(notif, body)


@shared_task
def send_inactivity_reminder():
    """Runs daily at 09:00 — reminds students inactive for 3+ days."""
    from datetime import timedelta

    from django.db.models import Max, Q

    from apps.enrollments.models import Enrollment

    cutoff = timezone.now() - timedelta(days=3)

    inactive = (
        Enrollment.objects.filter(is_active=True, completed=False)
        .annotate(last_activity=Max("lesson_progresses__updated_at"))
        .filter(
            Q(last_activity__lt=cutoff)
            | Q(last_activity__isnull=True, enrolled_at__lt=cutoff)
        )
        .select_related("student", "course")
        .distinct()
    )

    for enrollment in inactive:
        user = enrollment.student
        notif = EmailNotification.objects.create(
            user=user,
            subject=f"Continúa tu aprendizaje: {enrollment.course.title}",
            body_template="inactivity_reminder",
            context={
                "full_name": user.full_name,
                "course_title": enrollment.course.title,
            },
            notification_type="inactivity_reminder",
        )
        body = (
            f"Hola {user.full_name},\n\n"
            f"Llevamos 3 días sin verte en '{enrollment.course.title}'.\n"
            f"¡Vuelve y continúa desde donde lo dejaste!"
        )
        _deliver(notif, body)


@shared_task
def send_weekly_progress_report():
    """Runs every Monday at 08:00 — sends a progress summary to active students."""
    from django.contrib.auth import get_user_model

    from apps.enrollments.models import Enrollment

    User = get_user_model()
    students = User.objects.filter(
        enrollments__is_active=True,
        enrollments__completed=False,
    ).distinct()

    for student in students:
        active = Enrollment.objects.filter(
            student=student, is_active=True, completed=False
        ).count()
        completed = Enrollment.objects.filter(student=student, completed=True).count()

        notif = EmailNotification.objects.create(
            user=student,
            subject="Tu resumen semanal — INSIS",
            body_template="weekly_progress_report",
            context={
                "full_name": student.full_name,
                "active_courses": active,
                "completed_courses": completed,
            },
            notification_type="weekly_progress_report",
        )
        body = (
            f"Hola {student.full_name},\n\n"
            f"Resumen semanal de tu progreso:\n"
            f"  • Cursos en progreso: {active}\n"
            f"  • Cursos completados: {completed}\n\n"
            f"¡Sigue aprendiendo!"
        )
        _deliver(notif, body)


@shared_task
def generate_monthly_company_report():
    """Runs on day 1 of each month at 07:00 — sends company stats to HR Managers."""
    from apps.assignments.models import CompletionRecord
    from apps.companies.models import Employee

    hr_managers = (
        Employee.objects.filter(is_hr_manager=True)
        .select_related("user", "company")
        .distinct()
    )

    for hr_emp in hr_managers:
        company = hr_emp.company
        total_emps = company.employees.count()
        active_assignments = company.course_assignments.filter(is_active=True).count()
        total_records = CompletionRecord.objects.filter(company_id=company.pk).count()
        completed = CompletionRecord.objects.filter(
            company_id=company.pk, completed=True
        ).count()
        rate = round(completed / total_records * 100, 1) if total_records else 0

        notif = EmailNotification.objects.create(
            user=hr_emp.user,
            subject=f"Reporte mensual — {company.name}",
            body_template="monthly_company_report",
            context={
                "company_name": company.name,
                "total_employees": total_emps,
                "active_assignments": active_assignments,
                "completion_rate": rate,
            },
            notification_type="monthly_company_report",
        )
        body = (
            f"Estimado/a {hr_emp.user.full_name},\n\n"
            f"Reporte mensual de {company.name}:\n"
            f"  • Empleados: {total_emps}\n"
            f"  • Asignaciones activas: {active_assignments}\n"
            f"  • Tasa de completación: {rate}%\n\n"
            f"Ingresa a la plataforma para ver el detalle completo."
        )
        _deliver(notif, body)
