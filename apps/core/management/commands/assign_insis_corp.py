"""
Management command to create INSIS Corp and assign all users without a company.
Run: python manage.py assign_insis_corp
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Create INSIS Corp and assign all users without a company to it"

    @transaction.atomic
    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model

        from apps.companies.models import Company, Employee
        from apps.users.models import Roles

        User = get_user_model()

        self.stdout.write("=== Assign INSIS Corp ===")

        company, created = Company.objects.get_or_create(
            name="INSIS Corp",
            defaults={"ruc": "20000000001", "industry": "Educación"},
        )
        action = "created" if created else "already exists"
        self.stdout.write(f"  INSIS Corp {action} (id={company.pk})")

        users = User.objects.all()
        assigned = 0
        skipped = 0

        for user in users:
            already = Employee.objects.filter(user=user, company=company).exists()
            if already:
                skipped += 1
                continue

            is_hr = user.role == Roles.HR_MANAGER
            Employee.objects.create(
                user=user,
                company=company,
                is_hr_manager=is_hr,
            )
            assigned += 1
            self.stdout.write(f"  + {user.email} ({user.role}) → INSIS Corp")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Done — {assigned} assigned, {skipped} already had INSIS Corp"
            )
        )
