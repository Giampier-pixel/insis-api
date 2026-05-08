"""
fresh_start — Drops ALL tables in the database then runs migrate from scratch.
Use only for a full clean deployment.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection


class Command(BaseCommand):
    help = "Drop ALL tables in the database and run migrate from scratch."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Starting fresh_start — dropping ALL tables…"))

        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

            # Get all tables in the current database
            cursor.execute("SHOW TABLES;")
            tables = [row[0] for row in cursor.fetchall()]

            if not tables:
                self.stdout.write("  No tables found — database is already empty.")
            else:
                for table in tables:
                    cursor.execute(f"DROP TABLE IF EXISTS `{table}`;")
                    self.stdout.write(f"  ✓ Dropped `{table}`")

            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        self.stdout.write(self.style.SUCCESS(f"Dropped {len(tables)} tables. Running migrate…"))
        call_command("migrate", verbosity=1)
        self.stdout.write(self.style.SUCCESS("✅ fresh_start complete — database is clean and migrated."))
