"""
Management command to seed demo data and fix user roles in production.
Run: python manage.py seed_demo
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Seed demo data: fix roles, categories, courses, lessons, quizzes"

    @transaction.atomic
    def handle(self, *args, **options):
        from django.utils.text import slugify
        from apps.users.models import CustomUser, Roles
        from apps.courses.models import Category, Course, Lesson

        self.stdout.write("=== INSIS Demo Seed ===")

        # ── 1. Fix user roles ─────────────────────────────────────────────
        role_map = {
            "admin@insis.com":      Roles.ADMIN,
            "instructor@insis.com": Roles.INSTRUCTOR,
            "hr@insis.com":         Roles.HR_MANAGER,
            "student@insis.com":    Roles.STUDENT,
        }
        for email, role in role_map.items():
            try:
                u = CustomUser.objects.get(email=email)
                u.role = role
                u.save(update_fields=["role"])
                self.stdout.write(f"  ✓ {email} → {role}")
            except CustomUser.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  ! {email} not found, skipping"))

        instructor = CustomUser.objects.filter(email="instructor@insis.com").first()
        if not instructor:
            self.stdout.write(self.style.ERROR("Instructor not found, aborting course seed"))
            return

        # ── 2. Categories ─────────────────────────────────────────────────
        cats = {}
        for name, desc in [
            ("Liderazgo",   "Habilidades directivas y gestión de equipos"),
            ("Tecnología",  "Herramientas digitales y TI"),
            ("Compliance",  "Normativa, seguridad y ética empresarial"),
            ("Habilidades", "Comunicación, negociación y trabajo en equipo"),
        ]:
            cat, created = Category.objects.get_or_create(name=name, defaults={"description": desc})
            cats[name] = cat
            self.stdout.write(f"  {'✓ created' if created else '· exists'} category: {name}")

        # ── 3. Courses ────────────────────────────────────────────────────
        courses_data = [
            {
                "title": "Liderazgo de Equipos de Alto Rendimiento",
                "category": "Liderazgo",
                "level": "ADVANCED",
                "description": "Aprende a construir y gestionar equipos de alto rendimiento usando metodologías modernas.",
                "is_published": True,
                "lessons": [
                    ("Introducción al liderazgo situacional", "VIDEO", "18 min"),
                    ("La Pirámide de Lencioni",               "VIDEO", "22 min"),
                    ("Formación de equipos: modelo Tuckman",  "VIDEO", "25 min"),
                    ("Delegación efectiva",                   "TEXT",  "15 min"),
                ],
                "quiz": {
                    "title": "Quiz Final — Liderazgo",
                    "passing_score": 70,
                    "time_limit": 15,
                    "questions": [
                        ("¿Cuál es el principal objetivo de un equipo de alto rendimiento?",
                         ["Maximizar ganancias", "Alcanzar metas superando expectativas", "Reducir costos", "Cumplir horarios"], 1),
                        ("¿Qué define a un líder situacional?",
                         ["Mantiene siempre el mismo estilo", "Adapta su estilo según el colaborador", "Delega todas las decisiones", "Decide unilateralmente"], 1),
                        ("En la Pirámide de Lencioni, ¿cuál es la disfunción base?",
                         ["Falta de resultados", "Ausencia de confianza", "Miedo al conflicto", "Falta de compromiso"], 1),
                        ("¿Qué modelo describe Forming, Storming, Norming, Performing?",
                         ["Pirámide de Maslow", "Modelo Tuckman", "Ciclo PDCA", "Matriz BCG"], 1),
                    ],
                },
            },
            {
                "title": "Excel Avanzado para Análisis de Negocios",
                "category": "Tecnología",
                "level": "INTERMEDIATE",
                "description": "Domina tablas dinámicas, Power Query y macros para análisis empresarial.",
                "is_published": True,
                "lessons": [
                    ("Tablas dinámicas desde cero",   "VIDEO", "30 min"),
                    ("Power Query: transformar datos", "VIDEO", "25 min"),
                    ("Macros y automatización básica", "VIDEO", "20 min"),
                    ("Dashboard ejecutivo en Excel",   "VIDEO", "35 min"),
                ],
                "quiz": {
                    "title": "Quiz — Excel Avanzado",
                    "passing_score": 60,
                    "time_limit": 10,
                    "questions": [
                        ("¿Qué función agrupa y resume datos en Excel?",
                         ["BUSCARV", "Tabla dinámica", "CONCATENAR", "SI.ERROR"], 1),
                        ("¿Power Query sirve para…?",
                         ["Crear gráficos", "Transformar y limpiar datos", "Enviar emails", "Formatear celdas"], 1),
                        ("¿Qué tecla abre el editor de macros VBA?",
                         ["F1", "F5", "Alt+F11", "Ctrl+M"], 2),
                    ],
                },
            },
            {
                "title": "Seguridad Industrial y Prevención de Riesgos",
                "category": "Compliance",
                "level": "INTERMEDIATE",
                "description": "Normativa de seguridad laboral, identificación de riesgos y protocolos de emergencia.",
                "is_published": True,
                "lessons": [
                    ("Marco legal de seguridad laboral", "TEXT",  "20 min"),
                    ("Identificación y evaluación de riesgos", "VIDEO", "28 min"),
                    ("Equipos de protección personal",   "VIDEO", "15 min"),
                    ("Planes de emergencia y evacuación","VIDEO", "22 min"),
                ],
                "quiz": {
                    "title": "Quiz — Seguridad Industrial",
                    "passing_score": 80,
                    "time_limit": 12,
                    "questions": [
                        ("¿Qué significa EPP?",
                         ["Equipo de Primera Planta", "Equipo de Protección Personal", "Evaluación de Procesos Productivos", "Estándar de Prevención de Peligros"], 1),
                        ("La matriz IPER se usa para…",
                         ["Gestión de inventario", "Identificación y evaluación de riesgos", "Control de calidad", "Gestión de proyectos"], 1),
                    ],
                },
            },
        ]

        for cd in courses_data:
            course, created = Course.objects.get_or_create(
                slug=slugify(cd["title"])[:255],
                defaults={
                    "title":        cd["title"],
                    "instructor":   instructor,
                    "category":     cats[cd["category"]],
                    "level":        cd["level"],
                    "description":  cd["description"],
                    "is_published": cd["is_published"],
                }
            )
            self.stdout.write(f"  {'✓ created' if created else '· exists'} course: {cd['title']}")

            # Lessons
            for i, (ltitle, ltype, ldur) in enumerate(cd["lessons"], 1):
                dur_min = int(ldur.split()[0]) if ldur else 0
                Lesson.objects.get_or_create(
                    course=course, order=i,
                    defaults={
                        "title": ltitle,
                        "duration_minutes": dur_min,
                        "is_published": True,
                    }
                )

            # Quiz
            from apps.quizzes.models import Quiz, Question, Option
            qd = cd["quiz"]
            quiz, qcreated = Quiz.objects.get_or_create(
                course=course, title=qd["title"],
                defaults={
                    "passing_score":      qd["passing_score"],
                    "time_limit_minutes": qd["time_limit"],
                }
            )
            if qcreated:
                for order, (qt, opts, correct_idx) in enumerate(qd["questions"], 1):
                    q = Question.objects.create(quiz=quiz, text=qt, points=1, order=order)
                    for j, otext in enumerate(opts):
                        Option.objects.create(question=q, text=otext, is_correct=(j == correct_idx), order=j)

        self.stdout.write(self.style.SUCCESS("\n✅ Seed completo"))
