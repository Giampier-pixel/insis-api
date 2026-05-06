import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Enrollment",
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
                    "deleted_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("DIRECT", "Direct"),
                            ("B2B_ASSIGNMENT", "B2B Assignment"),
                        ],
                        default="DIRECT",
                        max_length=20,
                    ),
                ),
                ("enrolled_at", models.DateTimeField(auto_now_add=True)),
                ("is_active", models.BooleanField(default=True)),
                ("completed", models.BooleanField(default=False)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("notified_completion_at", models.DateTimeField(blank=True, null=True)),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="enrollments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="enrollments",
                        to="courses.course",
                    ),
                ),
            ],
            options={
                "verbose_name": "Enrollment",
                "verbose_name_plural": "Enrollments",
                "ordering": ["-enrolled_at"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="enrollment",
            unique_together={("student", "course")},
        ),
        migrations.CreateModel(
            name="LessonProgress",
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
                ("completed", models.BooleanField(default=False)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("time_spent_seconds", models.PositiveIntegerField(default=0)),
                (
                    "enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lesson_progresses",
                        to="enrollments.enrollment",
                    ),
                ),
                (
                    "lesson",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="progresses",
                        to="courses.lesson",
                    ),
                ),
            ],
            options={
                "verbose_name": "Lesson Progress",
                "verbose_name_plural": "Lesson Progresses",
            },
        ),
        migrations.AlterUniqueTogether(
            name="lessonprogress",
            unique_together={("enrollment", "lesson")},
        ),
    ]
