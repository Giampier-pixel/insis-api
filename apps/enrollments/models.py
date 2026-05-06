from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import SoftDeleteModel, TimestampedModel


class Enrollment(TimestampedModel, SoftDeleteModel):
    class Source(models.TextChoices):
        DIRECT = "DIRECT", "Direct"
        B2B_ASSIGNMENT = "B2B_ASSIGNMENT", "B2B Assignment"

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
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.DIRECT
    )
    course_assignment = models.ForeignKey(
        "assignments.CourseAssignment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrollments",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    notified_completion_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Enrollment"
        verbose_name_plural = "Enrollments"
        unique_together = [("student", "course")]
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.student.email} → {self.course.title}"

    def mark_completed(self):
        if not self.completed:
            self.completed = True
            self.completed_at = timezone.now()
            self.save(update_fields=["completed", "completed_at"])


class LessonProgress(TimestampedModel):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="lesson_progresses",
    )
    lesson = models.ForeignKey(
        "courses.Lesson",
        on_delete=models.CASCADE,
        related_name="progresses",
    )
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Lesson Progress"
        verbose_name_plural = "Lesson Progresses"
        unique_together = [("enrollment", "lesson")]

    def __str__(self):
        return f"{self.enrollment} — {self.lesson.title}"
