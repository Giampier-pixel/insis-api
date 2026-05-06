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
            name="Quiz",
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
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "time_limit_minutes",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                ("max_attempts", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "passing_score",
                    models.DecimalField(decimal_places=2, default=60.0, max_digits=5),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="quizzes",
                        to="courses.course",
                    ),
                ),
                (
                    "lesson",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="quizzes",
                        to="courses.lesson",
                    ),
                ),
            ],
            options={
                "verbose_name": "Quiz",
                "verbose_name_plural": "Quizzes",
                "ordering": ["id"],
            },
        ),
        migrations.AddConstraint(
            model_name="quiz",
            constraint=models.CheckConstraint(
                condition=models.Q(("passing_score__gte", 0))
                & models.Q(("passing_score__lte", 100)),
                name="quiz_passing_score_0_to_100",
            ),
        ),
        migrations.CreateModel(
            name="Question",
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
                ("text", models.TextField()),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("SINGLE", "Single choice"),
                            ("MULTIPLE", "Multiple choice"),
                            ("TRUE_FALSE", "True / False"),
                        ],
                        default="SINGLE",
                        max_length=20,
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0)),
                ("points", models.PositiveIntegerField(default=1)),
                (
                    "quiz",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questions",
                        to="quizzes.quiz",
                    ),
                ),
            ],
            options={
                "verbose_name": "Question",
                "verbose_name_plural": "Questions",
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="Option",
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
                ("text", models.CharField(max_length=512)),
                ("is_correct", models.BooleanField(default=False)),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="options",
                        to="quizzes.question",
                    ),
                ),
            ],
            options={
                "verbose_name": "Option",
                "verbose_name_plural": "Options",
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="Attempt",
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
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "score",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                ("passed", models.BooleanField(blank=True, null=True)),
                ("attempt_number", models.PositiveIntegerField()),
                ("notified_at", models.DateTimeField(blank=True, null=True)),
                (
                    "quiz",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="attempts",
                        to="quizzes.quiz",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="quiz_attempts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Attempt",
                "verbose_name_plural": "Attempts",
                "ordering": ["-started_at"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="attempt",
            unique_together={("quiz", "student", "attempt_number")},
        ),
        migrations.AddIndex(
            model_name="attempt",
            index=models.Index(
                fields=["quiz", "student"], name="quizzes_att_quiz_stu_idx"
            ),
        ),
        migrations.CreateModel(
            name="AttemptAnswer",
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
                ("is_correct", models.BooleanField(default=False)),
                ("points_earned", models.PositiveIntegerField(default=0)),
                (
                    "attempt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="answers",
                        to="quizzes.attempt",
                    ),
                ),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="attempt_answers",
                        to="quizzes.question",
                    ),
                ),
                (
                    "selected_options",
                    models.ManyToManyField(
                        blank=True,
                        related_name="attempt_answers",
                        to="quizzes.option",
                    ),
                ),
            ],
            options={
                "verbose_name": "Attempt Answer",
                "verbose_name_plural": "Attempt Answers",
            },
        ),
        migrations.AlterUniqueTogether(
            name="attemptanswer",
            unique_together={("attempt", "question")},
        ),
    ]
