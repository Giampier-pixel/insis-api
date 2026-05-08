"""
fresh_start — Drops all application tables then runs migrate.
Use only for a clean deployment from scratch.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection


APP_TABLES = [
    # Quizzes (FK deps first)
    "quizzes_attemptanswer_selected_options",
    "quizzes_attemptanswer",
    "quizzes_attempt",
    "quizzes_option",
    "quizzes_question",
    "quizzes_quiz",
    # Enrollments
    "enrollments_certificate",
    "enrollments_enrollment",
    "enrollments_lessonprogress",
    # Courses
    "courses_course_tags",
    "courses_coursereview",
    "courses_lesson",
    "courses_course",
    "courses_category",
    "courses_tag",
    # Notifications
    "notifications_emailnotification",
    # Companies / Assignments / Reports (legacy — may not exist)
    "assignments_completionrecord",
    "assignments_assignmenttarget",
    "assignments_courseassignment",
    "companies_employee",
    "companies_department",
    "companies_company",
    "reports_reportexportjob",
    # Users (last — other tables may FK into it)
    "users_userprofile",
    "users_customuser",
    # JWT token blacklist
    "token_blacklist_outstandingtoken",
    "token_blacklist_blacklistedtoken",
    # Django migrations table — reset so migrate runs fresh
    "django_migrations",
]


class Command(BaseCommand):
    help = "Drop all application tables and run migrate from scratch."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Starting fresh_start — dropping application tables…"))

        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            for table in APP_TABLES:
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS `{table}`;")
                    self.stdout.write(f"  ✓ Dropped {table}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"  ⚠ Could not drop {table}: {e}"))
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        self.stdout.write(self.style.SUCCESS("Tables dropped. Running migrate…"))
        call_command("migrate", verbosity=1)
        self.stdout.write(self.style.SUCCESS("✅ fresh_start complete."))
