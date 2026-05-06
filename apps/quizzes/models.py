from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimestampedModel


class Quiz(TimestampedModel):
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.PROTECT,
        related_name="quizzes",
    )
    lesson = models.ForeignKey(
        "courses.Lesson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quizzes",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    max_attempts = models.PositiveIntegerField(null=True, blank=True)
    passing_score = models.DecimalField(max_digits=5, decimal_places=2, default=60.00)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Quiz"
        verbose_name_plural = "Quizzes"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(passing_score__gte=0)
                & models.Q(passing_score__lte=100),
                name="quiz_passing_score_0_to_100",
            )
        ]

    def __str__(self):
        return self.title

    def clean(self):
        if self.lesson_id and self.course_id:
            if self.lesson.course_id != self.course_id:
                raise ValidationError(
                    {"lesson": "Lesson does not belong to the selected course."}
                )


class Question(TimestampedModel):
    class Type(models.TextChoices):
        SINGLE = "SINGLE", "Single choice"
        MULTIPLE = "MULTIPLE", "Multiple choice"
        TRUE_FALSE = "TRUE_FALSE", "True / False"

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.SINGLE)
    order = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Question"
        verbose_name_plural = "Questions"
        ordering = ["order"]

    def __str__(self):
        return f"{self.quiz.title} — Q{self.order}"


class Option(TimestampedModel):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="options"
    )
    text = models.CharField(max_length=512)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Option"
        verbose_name_plural = "Options"
        ordering = ["order"]

    def __str__(self):
        return f"{self.question} — {self.text[:40]}"


class Attempt(TimestampedModel):
    quiz = models.ForeignKey(Quiz, on_delete=models.PROTECT, related_name="attempts")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="quiz_attempts",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    attempt_number = models.PositiveIntegerField()
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Attempt"
        verbose_name_plural = "Attempts"
        ordering = ["-started_at"]
        unique_together = [("quiz", "student", "attempt_number")]
        indexes = [
            models.Index(fields=["quiz", "student"], name="quizzes_att_quiz_stu_idx"),
        ]

    def __str__(self):
        return f"{self.student.email} — {self.quiz.title} #{self.attempt_number}"


class AttemptAnswer(TimestampedModel):
    attempt = models.ForeignKey(
        Attempt, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(
        Question, on_delete=models.PROTECT, related_name="attempt_answers"
    )
    selected_options = models.ManyToManyField(
        Option, blank=True, related_name="attempt_answers"
    )
    is_correct = models.BooleanField(default=False)
    points_earned = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Attempt Answer"
        verbose_name_plural = "Attempt Answers"
        unique_together = [("attempt", "question")]

    def __str__(self):
        return f"{self.attempt} — {self.question}"
