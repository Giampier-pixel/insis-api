import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseAssignment",
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
                    "scope",
                    models.CharField(
                        choices=[
                            ("COMPANY", "Company"),
                            ("DEPARTMENT", "Department"),
                            ("INDIVIDUAL", "Individual"),
                        ],
                        default="COMPANY",
                        max_length=20,
                    ),
                ),
                ("due_date", models.DateField(blank=True, null=True)),
                ("is_mandatory", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "assigned_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="course_assignments",
                        to="companies.company",
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="course_assignments",
                        to="courses.course",
                    ),
                ),
            ],
            options={
                "verbose_name": "Course Assignment",
                "verbose_name_plural": "Course Assignments",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="courseassignment",
            constraint=models.CheckConstraint(
                condition=models.Q(scope__in=["COMPANY", "DEPARTMENT", "INDIVIDUAL"]),
                name="valid_assignment_scope",
            ),
        ),
        migrations.CreateModel(
            name="AssignmentTarget",
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
                    "assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="targets",
                        to="assignments.courseassignment",
                    ),
                ),
                (
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assignment_targets",
                        to="companies.employee",
                    ),
                ),
            ],
            options={
                "verbose_name": "Assignment Target",
                "verbose_name_plural": "Assignment Targets",
            },
        ),
        migrations.AlterUniqueTogether(
            name="assignmenttarget",
            unique_together={("assignment", "employee")},
        ),
        migrations.CreateModel(
            name="CompletionRecord",
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
                ("company_id", models.BigIntegerField(db_index=True)),
                ("completed", models.BooleanField(default=False)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "score",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                (
                    "assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="completion_records",
                        to="assignments.courseassignment",
                    ),
                ),
                (
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="completion_records",
                        to="companies.employee",
                    ),
                ),
                (
                    "target",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="completion_record",
                        to="assignments.assignmenttarget",
                    ),
                ),
            ],
            options={
                "verbose_name": "Completion Record",
                "verbose_name_plural": "Completion Records",
            },
        ),
        migrations.AlterUniqueTogether(
            name="completionrecord",
            unique_together={("employee", "assignment")},
        ),
    ]
