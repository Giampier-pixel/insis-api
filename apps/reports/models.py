from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class ReportExportJob(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        READY = "READY", "Ready"
        FAILED = "FAILED", "Failed"

    class ReportType(models.TextChoices):
        COMPANY_SUMMARY = "company-summary", "Company summary"
        COMPLETION_BY_DEPARTMENT = (
            "completion-by-department",
            "Completion by department",
        )
        EMPLOYEE_RANKING = "employee-ranking", "Employee ranking"
        OVERDUE_ASSIGNMENTS = "overdue-assignments", "Overdue assignments"

    class FileFormat(models.TextChoices):
        CSV = "csv", "CSV"
        XLSX = "xlsx", "Excel"

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="report_export_jobs",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        related_name="report_export_jobs",
    )
    report_type = models.CharField(max_length=50, choices=ReportType.choices)
    file_format = models.CharField(
        max_length=10, choices=FileFormat.choices, default=FileFormat.CSV
    )
    parameters = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    gcs_object_path = models.CharField(max_length=500, blank=True)
    signed_url = models.URLField(max_length=1000, blank=True)
    signed_url_expires_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Report Export Job"
        verbose_name_plural = "Report Export Jobs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["requested_by", "status"],
                name="report_user_status_idx",
            ),
            models.Index(
                fields=["company", "report_type"],
                name="report_company_type_idx",
            ),
        ]

    def __str__(self):
        return f"{self.report_type}.{self.file_format} [{self.status}]"
