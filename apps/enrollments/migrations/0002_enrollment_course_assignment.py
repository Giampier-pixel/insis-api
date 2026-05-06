import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("enrollments", "0001_initial"),
        ("assignments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="enrollment",
            name="course_assignment",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="enrollments",
                to="assignments.courseassignment",
            ),
        ),
    ]
