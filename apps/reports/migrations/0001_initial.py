import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("companies", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportExportJob",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "report_type",
                    models.CharField(
                        choices=[
                            ("company-summary", "Company summary"),
                            (
                                "completion-by-department",
                                "Completion by department",
                            ),
                            ("employee-ranking", "Employee ranking"),
                            ("overdue-assignments", "Overdue assignments"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "file_format",
                    models.CharField(
                        choices=[("csv", "CSV"), ("xlsx", "Excel")],
                        default="csv",
                        max_length=10,
                    ),
                ),
                ("parameters", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("RUNNING", "Running"),
                            ("READY", "Ready"),
                            ("FAILED", "Failed"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("gcs_object_path", models.CharField(blank=True, max_length=500)),
                ("signed_url", models.URLField(blank=True, max_length=1000)),
                ("signed_url_expires_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="report_export_jobs",
                        to="companies.company",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="report_export_jobs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Report Export Job",
                "verbose_name_plural": "Report Export Jobs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="reportexportjob",
            index=models.Index(
                fields=["requested_by", "status"], name="report_user_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="reportexportjob",
            index=models.Index(
                fields=["company", "report_type"], name="report_company_type_idx"
            ),
        ),
    ]
