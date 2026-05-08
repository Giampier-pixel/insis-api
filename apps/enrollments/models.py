from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import SoftDeleteModel, TimestampedModel


class Enrollment(TimestampedModel, SoftDeleteModel):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Enrollment"
        verbose_name_plural = "Enrollments"
        unique_together = [("student", "course")]
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.student.email} → {self.course.title}"

    def check_and_complete(self):
        """Mark enrollment as completed when all active quizzes are passed."""
        if self.completed:
            return False

        from apps.quizzes.models import Attempt, Quiz

        quizzes = Quiz.objects.filter(course=self.course, is_active=True)
        total = quizzes.count()
        if total == 0:
            return False

        passed_quiz_ids = (
            Attempt.objects.filter(
                quiz__in=quizzes,
                student=self.student,
                passed=True,
                finished_at__isnull=False,
            )
            .values_list("quiz_id", flat=True)
            .distinct()
        )

        if set(passed_quiz_ids) >= set(quizzes.values_list("id", flat=True)):
            self.completed = True
            self.completed_at = timezone.now()
            self.save(update_fields=["completed", "completed_at"])

            from apps.notifications.tasks import generate_certificate, send_completion_email

            generate_certificate.delay(self.pk)
            send_completion_email.delay(self.pk)
            return True

        return False


class Certificate(TimestampedModel):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="certificates",
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.PROTECT,
        related_name="certificates",
    )
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="certificate",
    )
    pdf_file = models.FileField(upload_to="certificates/", null=True, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    is_ready = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Certificate"
        verbose_name_plural = "Certificates"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.student.email} — {self.course.title}"
