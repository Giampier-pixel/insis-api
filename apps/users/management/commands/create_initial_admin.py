from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

ADMIN_EMAIL = "giampieraliagaesquivel@gmail.com"
ADMIN_NAME = "Administrador INSIS"
DEFAULT_PASSWORD = "Insis2024!"


class Command(BaseCommand):
    help = "Crea el usuario administrador inicial si no existe."

    def add_arguments(self, parser):
        parser.add_argument("--email", default=ADMIN_EMAIL)
        parser.add_argument("--name", default=ADMIN_NAME)
        parser.add_argument("--password", default=DEFAULT_PASSWORD)

    def handle(self, *args, **options):
        email = options["email"]
        name = options["name"]
        password = options["password"]

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f"Admin '{email}' ya existe. Sin cambios."))
            return

        User.objects.create_superuser(
            email=email,
            full_name=name,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f"Admin creado: {email} / {password}"))
