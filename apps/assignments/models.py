from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class CourseAssignment(TimestampedModel):
    class Scope(models.TextChoices):
        COMPANY = "COMPANY", "Company"
        DEPARTMENT = "DEPARTMENT", "Department"
        INDIVIDUAL = "INDIVIDUAL", "Individual"

    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.PROTECT,
        related_name="course_assignments",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        related_name="course_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_assignments",
    )
    scope = models.CharField(
        max_length=20, choices=Scope.choices, default=Scope.COMPANY
    )
    due_date = models.DateField(null=True, blank=True)
    is_mandatory = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Course Assignment"
        verbose_name_plural = "Course Assignments"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(scope__in=["COMPANY", "DEPARTMENT", "INDIVIDUAL"]),
                name="valid_assignment_scope",
            )
        ]

    def __str__(self):
        return f"{self.company.name} — {self.course.title} ({self.scope})"


class AssignmentTarget(TimestampedModel):
    assignment = models.ForeignKey(
        CourseAssignment, on_delete=models.CASCADE, related_name="targets"
    )
    employee = models.ForeignKey(
        "companies.Employee",
        on_delete=models.PROTECT,
        related_name="assignment_targets",
    )

    class Meta:
        verbose_name = "Assignment Target"
        verbose_name_plural = "Assignment Targets"
        unique_together = [("assignment", "employee")]

    def __str__(self):
        return f"{self.assignment} → {self.employee}"


class CompletionRecord(TimestampedModel):
    target = models.OneToOneField(
        AssignmentTarget, on_delete=models.CASCADE, related_name="completion_record"
    )
    employee = models.ForeignKey(
        "companies.Employee",
        on_delete=models.PROTECT,
        related_name="completion_records",
    )
    assignment = models.ForeignKey(
        CourseAssignment, on_delete=models.PROTECT, related_name="completion_records"
    )
    # Denormalized company_id for efficient reporting queries
    company_id = models.BigIntegerField(db_index=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = "Completion Record"
        verbose_name_plural = "Completion Records"
        unique_together = [("employee", "assignment")]

    def __str__(self):
        status = "✓" if self.completed else "✗"
        return f"{self.employee} — {self.assignment.course.title} {status}"
