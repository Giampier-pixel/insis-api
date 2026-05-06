import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
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
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                (
                    "icon",
                    models.ImageField(
                        blank=True, null=True, upload_to="categories/icons/"
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Category",
                "verbose_name_plural": "Categories",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Tag",
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
                ("name", models.CharField(max_length=50, unique=True)),
                ("slug", models.SlugField(max_length=50, unique=True)),
            ],
            options={
                "verbose_name": "Tag",
                "verbose_name_plural": "Tags",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Course",
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
                ("title", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=255, unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "thumbnail",
                    models.ImageField(
                        blank=True, null=True, upload_to="courses/thumbnails/"
                    ),
                ),
                (
                    "price",
                    models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
                ),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("BEGINNER", "Beginner"),
                            ("INTERMEDIATE", "Intermediate"),
                            ("ADVANCED", "Advanced"),
                        ],
                        default="BEGINNER",
                        max_length=20,
                    ),
                ),
                ("language", models.CharField(default="Spanish", max_length=50)),
                ("is_published", models.BooleanField(default=False)),
                (
                    "category",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="courses",
                        to="courses.category",
                    ),
                ),
                (
                    "instructor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="courses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tags",
                    models.ManyToManyField(
                        blank=True, related_name="courses", to="courses.tag"
                    ),
                ),
            ],
            options={
                "verbose_name": "Course",
                "verbose_name_plural": "Courses",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="course",
            index=models.Index(
                fields=["instructor", "is_published"], name="courses_cou_instruc_idx"
            ),
        ),
        migrations.CreateModel(
            name="Lesson",
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
                ("title", models.CharField(max_length=255)),
                ("content", models.TextField(blank=True)),
                ("video_url", models.URLField(blank=True)),
                ("order", models.PositiveIntegerField(default=0)),
                ("duration_minutes", models.PositiveIntegerField(default=0)),
                ("is_free", models.BooleanField(default=False)),
                ("is_published", models.BooleanField(default=False)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lessons",
                        to="courses.course",
                    ),
                ),
            ],
            options={
                "verbose_name": "Lesson",
                "verbose_name_plural": "Lessons",
                "ordering": ["order"],
            },
        ),
        migrations.AddIndex(
            model_name="lesson",
            index=models.Index(
                fields=["course", "order"], name="courses_les_course_idx"
            ),
        ),
        migrations.CreateModel(
            name="CourseReview",
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
                    "rating",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ]
                    ),
                ),
                ("comment", models.TextField(blank=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reviews",
                        to="courses.course",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="course_reviews",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Course Review",
                "verbose_name_plural": "Course Reviews",
            },
        ),
        migrations.AlterUniqueTogether(
            name="coursereview",
            unique_together={("course", "student")},
        ),
        migrations.AddConstraint(
            model_name="coursereview",
            constraint=models.CheckConstraint(
                condition=models.Q(("rating__gte", 1)) & models.Q(("rating__lte", 5)),
                name="review_rating_1_to_5",
            ),
        ),
    ]
