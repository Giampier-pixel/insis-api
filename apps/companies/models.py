from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel, TimestampedModel


class Company(TimestampedModel, SoftDeleteModel):
    name = models.CharField(max_length=255)
    ruc = models.CharField(max_length=11, unique=True)
    logo = models.ImageField(upload_to="companies/logos/", null=True, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.ruc})"


class Department(TimestampedModel, SoftDeleteModel):
    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, related_name="departments"
    )
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        ordering = ["name"]
        unique_together = [("company", "name")]

    def __str__(self):
        return f"{self.name} — {self.company.name}"


class Employee(TimestampedModel, SoftDeleteModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="employee_records",
    )
    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, related_name="employees"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    is_hr_manager = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Employee"
        verbose_name_plural = "Employees"
        unique_together = [("user", "company")]

    def __str__(self):
        return f"{self.user.email} @ {self.company.name}"
