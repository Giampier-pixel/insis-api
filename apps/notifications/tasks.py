import os

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.notifications.email_client import send_email
from apps.notifications.models import EmailNotification

ADMIN_FROM_EMAIL = "INSIS <noreply@sysifdev.com>"


def _record(user, subject, notification_type, context):
    return EmailNotification.objects.create(
        user=user,
        subject=subject,
        body_template=notification_type,
        context=context,
        notification_type=notification_type,
    )


def _mark_sent(notif):
    notif.status = EmailNotification.Status.SENT
    notif.sent_at = timezone.now()
    notif.save(update_fields=["status", "sent_at"])


def _mark_failed(notif, error):
    notif.status = EmailNotification.Status.FAILED
    notif.error_message = str(error)[:500]
    notif.save(update_fields=["status", "error_message"])


# ──────────────────────────────────────────────────────────────
# Bienvenida al registrarse
# ──────────────────────────────────────────────────────────────


@shared_task
def send_welcome_email(user_id):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    notif = _record(
        user,
        "¡Bienvenido/a a INSIS!",
        "welcome",
        {"full_name": user.full_name, "email": user.email},
    )
    html = f"""
    <h2>¡Hola, {user.full_name}!</h2>
    <p>Tu cuenta en <strong>INSIS</strong> ha sido creada exitosamente.</p>
    <p>Ya puedes explorar el catálogo de cursos e inscribirte en los que más te interesen.</p>
    <p>¡Bienvenido/a a tu nueva experiencia de aprendizaje!</p>
    """
    ok = send_email(to=user.email, subject=notif.subject, html=html)
    if ok:
        _mark_sent(notif)
    else:
        _mark_failed(notif, "Resend delivery failed")


# ──────────────────────────────────────────────────────────────
# Confirmación de inscripción
# ──────────────────────────────────────────────────────────────


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
    course_title = enrollment.course.title
    notif = _record(
        user,
        f"Inscripción confirmada: {course_title}",
        "enrollment_confirmation",
        {"full_name": user.full_name, "course_title": course_title},
    )
    html = f"""
    <h2>¡Hola, {user.full_name}!</h2>
    <p>Te has inscrito exitosamente en <strong>"{course_title}"</strong>.</p>
    <p>Ya puedes acceder al curso y comenzar los quizzes desde tu portal.</p>
    <p>¡Buena suerte!</p>
    """
    ok = send_email(to=user.email, subject=notif.subject, html=html)
    if ok:
        _mark_sent(notif)
    else:
        _mark_failed(notif, "Resend delivery failed")


# ──────────────────────────────────────────────────────────────
# Email de felicitación al completar un curso
# ──────────────────────────────────────────────────────────────


@shared_task
def send_completion_email(enrollment_id):
    from apps.enrollments.models import Enrollment

    try:
        enrollment = Enrollment.objects.select_related("student", "course").get(
            pk=enrollment_id
        )
    except Enrollment.DoesNotExist:
        return

    user = enrollment.student
    course_title = enrollment.course.title

    notif = _record(
        user,
        f"¡Felicitaciones! Completaste '{course_title}'",
        "course_completion",
        {"full_name": user.full_name, "course_title": course_title},
    )
    html = f"""
    <h2>¡Felicitaciones, {user.full_name}!</h2>
    <p>Has completado exitosamente el curso <strong>"{course_title}"</strong>.</p>
    <p>Tu certificado ya está siendo generado. Podrás descargarlo desde el
       <strong>módulo de Certificados</strong> en tu portal de estudiante.</p>
    <p>¡Sigue aprendiendo!</p>
    <br>
    <p>— Equipo INSIS</p>
    """
    ok = send_email(
        to=user.email,
        subject=notif.subject,
        html=html,
        from_email=ADMIN_FROM_EMAIL,
    )
    if ok:
        _mark_sent(notif)
    else:
        _mark_failed(notif, "Resend delivery failed")


# ──────────────────────────────────────────────────────────────
# Generación de certificado PDF
# ──────────────────────────────────────────────────────────────


@shared_task
def generate_certificate(enrollment_id):
    from io import BytesIO

    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    from django.core.files.base import ContentFile

    from apps.enrollments.models import Certificate, Enrollment

    try:
        enrollment = Enrollment.objects.select_related("student", "course").get(
            pk=enrollment_id
        )
    except Enrollment.DoesNotExist:
        return

    cert, _ = Certificate.objects.get_or_create(
        enrollment=enrollment,
        defaults={
            "student": enrollment.student,
            "course": enrollment.course,
        },
    )

    if cert.is_ready:
        return

    # Generar PDF horizontal con el nombre del curso centrado en negrita
    buffer = BytesIO()
    page_size = landscape(A4)
    width, height = page_size

    c = canvas.Canvas(buffer, pagesize=page_size)
    c.setFont("Helvetica-Bold", 36)

    course_title = enrollment.course.title
    text_width = c.stringWidth(course_title, "Helvetica-Bold", 36)
    x = (width - text_width) / 2
    y = height / 2

    c.drawString(x, y, course_title)
    c.save()

    pdf_content = buffer.getvalue()
    filename = f"certificates/certificado_{enrollment_id}.pdf"
    cert.pdf_file.save(filename, ContentFile(pdf_content), save=False)
    cert.generated_at = timezone.now()
    cert.is_ready = True
    cert.save(update_fields=["pdf_file", "generated_at", "is_ready"])
