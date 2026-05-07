"""
Management command to fix empty full_name for existing users.
Applies known demo names first, then falls back to email username.
Run: python manage.py fix_user_names
"""
from django.core.management.base import BaseCommand
from django.db import transaction


KNOWN_NAMES = {
    "admin@insis.com": "Administrador INSIS",
    "instructor@insis.com": "Instructor Demo",
    "hr@insis.com": "HR Manager Demo",
    "student@insis.com": "Estudiante Demo",
    "alan@insis.com": "Alan Demo",
}


class Command(BaseCommand):
    help = "Fill empty full_name fields using known demo names or email username"

    @transaction.atomic
    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        self.stdout.write("=== Fix User Names ===")
        updated = 0

        for user in User.objects.all():
            name = KNOWN_NAMES.get(user.email)
            if not name and not user.full_name.strip():
                name = user.email.split("@")[0].replace(".", " ").title()

            if name and user.full_name != name:
                old = repr(user.full_name)
                user.full_name = name
                user.save(update_fields=["full_name"])
                self.stdout.write(f"  {user.email}: {old} → {repr(name)}")
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"\n✅ {updated} user(s) updated"))
