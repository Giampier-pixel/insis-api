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
            if user.full_name.strip():
                # Only apply KNOWN_NAMES overrides for demo accounts; never
                # overwrite a non-empty name that isn't in the known list.
                known = KNOWN_NAMES.get(user.email)
                if known and user.full_name != known:
                    old = repr(user.full_name)
                    user.full_name = known
                    user.save(update_fields=["full_name"])
                    self.stdout.write(f"  {user.email}: {old} → {repr(known)}")
                    updated += 1
                continue

            # Name is empty — derive from known list or email username
            name = KNOWN_NAMES.get(user.email) or (
                user.email.split("@")[0].replace(".", " ").title()
            )
            old = repr(user.full_name)
            user.full_name = name
            user.save(update_fields=["full_name"])
            self.stdout.write(f"  {user.email}: {old} → {repr(name)}")
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"\n✅ {updated} user(s) updated"))
