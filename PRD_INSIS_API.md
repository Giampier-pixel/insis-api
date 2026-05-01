# 🏆 PRD — INSIS API
### Plataforma EdTech Completa

---

| Campo                   | Detalle                                                                                 |
| ----------------------- | --------------------------------------------------------------------------------------- |
| **Proyecto**            | INSIS API                                                                               |
| **Versión**             | 1.0                                                                                     |
| **Tipo**                | Backend REST API — Plataforma EdTech Completa                                           |
| **Stack principal**     | Python 3.13 · Django 5.2 LTS · DRF 3.16 · MySQL 8.4 LTS · Celery 5.6 · Redis 8 · Docker |
| **Despliegue objetivo** | Google Cloud Run + Cloud SQL (MySQL)          
| **Repositorio**         | https://github.com/Giampier-pixel/insis-api.git                                         |

---

## 1. Visión General del Proyecto

INSIS API es un backend RESTful que replica el **núcleo completo de una plataforma EdTech, integrando en un solo sistema los dos grandes módulos que componen el negocio: la plataforma de aprendizaje para estudiantes individuales y el módulo corporativo B2B para empresas. Cubre el ciclo de vida completo: desde el registro de un usuario hasta la generación de reportes empresariales, pasando por cursos, lecciones, quizzes, inscripciones, progreso y notificaciones asíncronas.

Posee una arquitectura limpia con apps Django bien separadas, código limpio respetando PEP8, tests con cobertura real y despliegue preparado para Google Cloud Run.

---

## 2. Stack Tecnológico

| Tecnología | Versión | Rol |
|---|---|---|
| Python | 3.13 | Lenguaje principal |
| Django | 5.2 LTS | Framework web |
| Django REST Framework | 3.16 | Construcción de la API REST |
| MySQL | 8.4 LTS | Base de datos principal |
| Celery | 5.6 | Cola de tareas asíncronas |
| Redis | 8 | Broker de Celery + caché |
| Docker | latest | Contenedores |
| Gunicorn | 23.0 | Servidor WSGI para producción |


### 2.2 Librerías y Dependencias Completas

| Librería                        | Versión    | Propósito                                |
| ------------------------------- | ---------- | ---------------------------------------- |
| `Django`                        | `~=5.2.0`  | Framework web (LTS hasta abril 2028)     |
| `djangorestframework`           | `==3.16.*` | Core de la API REST                      |
| `djangorestframework-simplejwt` | `==5.5.*`  | Autenticación JWT con blacklist          |
| `drf-spectacular`               | `==0.29.*` | Documentación Swagger/OpenAPI automática |
| `celery[redis]`                 | `==5.6.*`  | Cola de tareas asíncronas                |
| `django-celery-beat`            | `==2.9.*`  | Scheduler para tareas periódicas         |
| `mysqlclient`                   | `==2.2.*`  | Conector MySQL para Django               |
| `python-decouple`               | `>=3.8`    | Manejo de variables de entorno           |
| `django-filter`                 | `==25.*`   | Filtros avanzados en listados            |
| `openpyxl`                      | `>=3.1.5`  | Exportación de reportes a Excel          |
| `pytest-django`                 | `>=4.9`    | Testing con pytest                       |
| `pytest-mock`                   | `>=3.14`   | Mocking de Celery tasks y emails         |
| `factory-boy`                   | `>=3.3`    | Generación de datos de prueba            |
| `coverage`                      | `>=7.6`    | Reporte de cobertura de tests            |
| `flake8`                        | `>=7.1`    | Linter PEP8                              |
| `black`                         | `>=25.0`   | Formateador de código                    |
| `gunicorn`                      | `==23.0.*` | Servidor WSGI para Cloud Run             |


---

## 3. Arquitectura y Estructura del Proyecto


```
insis-api/
├── apps/
│   │
│   ├── users/                  # Autenticación, perfiles, roles
│   │   ├── models.py           # CustomUser con roles
│   │   ├── serializers.py      # Register, Login, Profile serializers
│   │   ├── views.py            # Auth ViewSets
│   │   ├── permissions.py      # IsInstructor, IsAdmin, IsStudent
│   │   ├── signals.py          # post_save → send_welcome_email
│   │   ├── urls.py
│   │   └── tests/
│   │       ├── test_models.py
│   │       └── test_views.py
│   │
│   ├── courses/                # Catálogo de cursos y lecciones
│   │   ├── models.py           # Course, Lesson, Category, Tag
│   │   ├── serializers.py
│   │   ├── views.py            # CourseViewSet, LessonViewSet
│   │   ├── filters.py          # CourseFilter con django-filter
│   │   ├── urls.py
│   │   └── tests/
│   │       ├── test_models.py
│   │       └── test_views.py
│   │
│   ├── enrollments/            # Inscripciones y seguimiento de progreso
│   │   ├── models.py           # Enrollment, LessonProgress
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── signals.py          # post_save → confirmación + check completación
│   │   ├── urls.py
│   │   └── tests/
│   │       ├── test_models.py
│   │       └── test_views.py
│   │
│   ├── quizzes/                # Motor de evaluaciones
│   │   ├── models.py           # Quiz, Question, Option, Attempt, Score
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── graders.py          # Lógica de corrección automática
│   │   ├── signals.py          # post_save en Attempt → notificación resultado
│   │   ├── urls.py
│   │   └── tests/
│   │       ├── test_graders.py
│   │       └── test_views.py
│   │
│   ├── companies/              # Módulo B2B — empresas y empleados
│   │   ├── models.py           # Company, Department, Employee
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests/
│   │       └── test_views.py
│   │
│   ├── assignments/            # Asignación corporativa de cursos
│   │   ├── models.py           # CourseAssignment, CompletionRecord
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── signals.py
│   │   ├── urls.py
│   │   └── tests/
│   │       └── test_views.py
│   │
│   ├── reports/                # Reportes y exportaciones
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── exporters.py        # CSV streaming + Excel multi-hoja
│   │   ├── urls.py
│   │   └── tests/
│   │       └── test_reports.py
│   │
│   └── notifications/          # Celery tasks centralizadas
│       ├── tasks.py            # Todas las tasks de email
│       ├── models.py           # EmailNotification (log de envíos)
│       └── tests/
│           └── test_tasks.py
│
├── config/
│   ├── settings/
│   │   ├── base.py             # Configuración base compartida
│   │   ├── local.py            # Desarrollo local (DEBUG=True)
│   │   └── production.py      # Google Cloud Run (DEBUG=False)
│   ├── urls.py                 # URL root con versionado /api/v1/
│   └── celery.py               # Configuración de Celery + Beat
│
├── tests/
│   └── factories.py            # Todas las factories centralizadas
│
├── Dockerfile                  # Puerto 8080 para Cloud Run
├── docker-compose.yml          # 6 servicios: web, db, redis, worker, beat, flower
├── cloudbuild.yaml             # Pipeline deploy a Cloud Run
├── .dockerignore
├── entrypoint.sh               # Migrate + collectstatic + gunicorn
├── requirements.txt
├── requirements-dev.txt        # pytest, factory-boy, coverage, flake8, black
├── .env.example
├── setup.cfg                   # Configuración de pytest y flake8
└── README.md
```

### 3.2 Separación de Settings

```python
# config/settings/base.py — config compartida
INSTALLED_APPS = [
    ...
    'apps.users',
    'apps.courses',
    'apps.enrollments',
    'apps.quizzes',
    'apps.companies',
    'apps.assignments',
    'apps.reports',
    'apps.notifications',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'django_filters',
    'django_celery_beat',
]

# config/settings/local.py — solo desarrollo
from .base import *
DEBUG = True
DATABASES = { ... }  # MySQL local via docker-compose

# config/settings/production.py — Cloud Run
from .base import *
DEBUG = False
ALLOWED_HOSTS = ['*']  # restringir al dominio de Cloud Run
DATABASES = { ... }    # Cloud SQL via env vars
```

---

## 4. Modelos de Datos

### 4.1 Módulo de Usuarios

| Modelo              | Campos Principales                                                                                                          |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `User` (CustomUser) | `id`, `email` (unique), `full_name`, `role` (STUDENT/INSTRUCTOR/ADMIN/EMPLOYEE), `avatar`, `bio`, `is_active`, `created_at` |
| `UserProfile`       | `user` (OneToOne), `phone`, `country`, `linkedin_url`, `notification_preferences` (JSON)                                    |

### 4.2 Módulo de Cursos

| Modelo | Campos Principales |
|---|---|
| `Category` | `id`, `name`, `slug`, `icon`, `description`, `is_active` |
| `Tag` | `id`, `name`, `slug` |
| `Course` | `id`, `title`, `slug`, `description`, `instructor` (FK→User), `category` (FK), `tags` (M2M), `thumbnail`, `price`, `level` (BEGINNER/INTERMEDIATE/ADVANCED), `language`, `is_published`, `created_at`, `updated_at` |
| `Lesson` | `id`, `course` (FK→Course), `title`, `content`, `video_url`, `order`, `duration_minutes`, `is_free`, `is_published` |
| `CourseReview` | `id`, `course` (FK), `student` (FK→User), `rating` (1-5), `comment`, `created_at` |

### 4.3 Módulo de Inscripciones

| Modelo | Campos Principales |
|---|---|
| `Enrollment` | `id`, `student` (FK→User), `course` (FK→Course), `enrolled_at`, `is_active`, `completed`, `completed_at` |
| `LessonProgress` | `id`, `enrollment` (FK), `lesson` (FK→Lesson), `completed`, `completed_at`, `time_spent_seconds` |

### 4.4 Módulo de Quizzes

| Modelo | Campos Principales |
|---|---|
| `Quiz` | `id`, `lesson` (FK→Lesson, null), `course` (FK→Course), `title`, `description`, `time_limit_minutes`, `max_attempts`, `passing_score` (decimal), `is_active` |
| `Question` | `id`, `quiz` (FK→Quiz), `text`, `type` (SINGLE/MULTIPLE/TRUE_FALSE), `order`, `points` |
| `Option` | `id`, `question` (FK→Question), `text`, `is_correct`, `order` |
| `Attempt` | `id`, `quiz` (FK→Quiz), `student` (FK→User), `started_at`, `finished_at`, `score` (decimal), `passed`, `attempt_number` |
| `AttemptAnswer` | `id`, `attempt` (FK→Attempt), `question` (FK→Question), `selected_options` (M2M→Option), `is_correct` |

### 4.5 Módulo Corporativo B2B

| Modelo | Campos Principales |
|---|---|
| `Company` | `id`, `name`, `ruc`, `industry`, `country`, `plan` (BASIC/PRO/ENTERPRISE), `is_active`, `created_at` |
| `Department` | `id`, `company` (FK→Company), `name`, `description` |
| `Employee` | `id`, `user` (OneToOne→User), `company` (FK→Company), `department` (FK→Department, null), `job_title`, `hire_date`, `is_active` |
| `CourseAssignment` | `id`, `course` (FK→Course), `company` (FK→Company), `assigned_by` (FK→User), `due_date`, `is_mandatory` |
| `CompletionRecord` | `id`, `employee` (FK→Employee), `assignment` (FK→CourseAssignment), `completed`, `completed_at`, `score` |

### 4.6 Módulo de Notificaciones

| Modelo | Campos Principales |
|---|---|
| `EmailNotification` | `id`, `user` (FK→User), `subject`, `body`, `sent`, `sent_at`, `task_id`, `notification_type` |

### 4.7 Índices SQL Definidos en `Meta`

| Modelo | Índice | Justificación |
|---|---|---|
| `Enrollment` | UNIQUE `(student, course)` | Previene inscripciones duplicadas |
| `LessonProgress` | UNIQUE `(enrollment, lesson)` | Un registro por lección por inscripción |
| `Attempt` | Compuesto `(quiz, student)` | Historial de intentos rápido |
| `CompletionRecord` | UNIQUE `(employee, assignment)` | Un registro por empleado por asignación |
| `Course` | Compuesto `(instructor, is_published)` | Filtros de instructor eficientes |
| `Lesson` | Compuesto `(course, order)` | Ordenamiento de lecciones |
| `Employee` | Compuesto `(company, department, is_active)` | Filtros de organigrama |

---

## 5. Endpoints de la API

### 5.1 Autenticación — `/api/v1/auth/`

| Método + Ruta | Descripción | Auth |
|---|---|---|
| `POST /auth/register/` | Registro con validación de email único | No |
| `POST /auth/login/` | Login — retorna `access` + `refresh` tokens | No |
| `POST /auth/token/refresh/` | Renovar access token | No |
| `POST /auth/logout/` | Blacklist del refresh token | Sí |
| `GET /auth/me/` | Perfil del usuario autenticado | Sí |
| `PATCH /auth/me/` | Actualizar perfil e imagen | Sí |
| `POST /auth/change-password/` | Cambiar contraseña con validación actual | Sí |

### 5.2 Cursos — `/api/v1/courses/`

| Método + Ruta | Descripción | Permisos |
|---|---|---|
| `GET /courses/` | Listar cursos publicados con filtros y búsqueda | Público |
| `POST /courses/` | Crear curso | Instructor / Admin |
| `GET /courses/{slug}/` | Detalle con lecciones, reviews y stats | Público |
| `PATCH /courses/{slug}/` | Editar curso | Dueño / Admin |
| `DELETE /courses/{slug}/` | Eliminar curso | Admin |
| `GET /courses/{slug}/lessons/` | Lecciones del curso | Autenticado |
| `POST /courses/{slug}/lessons/` | Agregar lección | Instructor dueño |
| `PATCH /courses/{slug}/lessons/{id}/` | Editar lección | Instructor dueño |
| `POST /courses/{slug}/reviews/` | Dejar reseña (solo estudiantes inscritos) | Student inscrito |
| `GET /courses/{slug}/reviews/` | Listar reseñas del curso | Público |
| `GET /courses/{slug}/quizzes/` | Quizzes asociados al curso | Inscrito |

### 5.3 Inscripciones y Progreso — `/api/v1/enrollments/`

| Método + Ruta | Descripción | Permisos |
|---|---|---|
| `POST /enrollments/` | Inscribirse a un curso | Student |
| `GET /enrollments/` | Mis inscripciones con % de progreso | Autenticado |
| `GET /enrollments/{id}/` | Detalle con progreso por lección | Dueño |
| `POST /enrollments/{id}/complete-lesson/` | Marcar lección completada | Dueño |
| `GET /enrollments/{id}/progress/` | Progreso: completadas / total, % , tiempo total | Dueño |
| `DELETE /enrollments/{id}/` | Cancelar inscripción | Dueño |
| `GET /enrollments/my-certificates/` | Cursos completados al 100% (certificados) | Autenticado |

### 5.4 Quizzes — `/api/v1/quizzes/`

| Método + Ruta | Descripción | Permisos |
|---|---|---|
| `GET /quizzes/{id}/` | Detalle del quiz con preguntas y opciones | Inscrito al curso |
| `POST /quizzes/{id}/start/` | Iniciar intento — crea `Attempt` | Inscrito |
| `POST /quizzes/{id}/submit/` | Enviar respuestas — corrige y calcula score | Inscrito |
| `GET /quizzes/{id}/attempts/` | Historial de mis intentos en este quiz | Inscrito |
| `GET /quizzes/{id}/results/{attempt_id}/` | Resultado detallado: pregunta por pregunta | Dueño del intento |
| `GET /quizzes/{id}/stats/` | Stats del quiz: promedio, tasa aprobación | Instructor / Admin |
| `POST /quizzes/` | Crear quiz para un curso | Instructor dueño |

### 5.5 Módulo Corporativo — `/api/v1/companies/`

| Método + Ruta | Descripción | Permisos |
|---|---|---|
| `GET /companies/` | Listar empresas | Admin plataforma |
| `POST /companies/` | Crear empresa | Admin |
| `GET /companies/{id}/` | Detalle + stats de empleados | Admin / HR Manager |
| `GET /companies/{id}/departments/` | Departamentos | HR Manager |
| `POST /companies/{id}/departments/` | Crear departamento | HR Manager |
| `GET /companies/{id}/stats/` | Resumen: empleados, % progreso, asignaciones activas | HR Manager |

### 5.6 Empleados — `/api/v1/employees/`

| Método + Ruta | Descripción | Permisos |
|---|---|---|
| `GET /employees/` | Listar empleados de mi empresa | HR Manager |
| `POST /employees/` | Crear empleado | HR Manager |
| `POST /employees/bulk-import/` | Importar empleados desde CSV | HR Manager |
| `GET /employees/{id}/` | Perfil + cursos asignados + progreso | HR / Admin |
| `PATCH /employees/{id}/` | Actualizar empleado | HR Manager |

### 5.7 Asignaciones — `/api/v1/assignments/`

| Método + Ruta | Descripción | Permisos |
|---|---|---|
| `POST /assignments/` | Asignar curso a empresa con fecha límite | HR Manager |
| `POST /assignments/{id}/assign-department/` | Asignar a departamento completo | HR Manager |
| `GET /assignments/` | Asignaciones activas con % global completado | HR Manager |
| `DELETE /assignments/{id}/` | Cancelar asignación | HR Manager |

### 5.8 Reportes — `/api/v1/reports/`

| Método + Ruta | Descripción |
|---|---|
| `GET /reports/company-summary/` | Resumen ejecutivo de la empresa |
| `GET /reports/completion-by-department/` | Completación agrupada por departamento |
| `GET /reports/employee-ranking/` | Ranking de empleados más activos |
| `GET /reports/overdue-assignments/` | Empleados con cursos vencidos |
| `GET /reports/export-csv/` | Exportar reporte completo a CSV |
| `GET /reports/export-excel/` | Exportar a Excel multi-hoja |

---

## 6. Motor de Quizzes — Lógica de Negocio

### 6.1 Flujo Completo de un Intento

```
Estudiante                API                    Base de Datos
──────────                ───                    ─────────────
GET /quizzes/{id}/   →   Valida inscripción   →  Retorna Quiz + Questions + Options
                          Oculta is_correct

POST /quizzes/{id}/start/ →  Crea Attempt       →  Attempt(started_at=now, attempt_number=N)
                              Verifica max_attempts
                              Verifica time_limit

POST /quizzes/{id}/submit/ →  graders.py         →  AttemptAnswer por cada pregunta
                               Calcula score          Attempt(score=X, passed=bool, finished_at)
                               Dispara signal         Signal → task notificación resultado
```

### 6.2 Lógica de Corrección en `graders.py`

```python
# apps/quizzes/graders.py

def grade_attempt(attempt, submitted_answers):
    """
    submitted_answers: [
        {"question_id": 1, "selected_option_ids": [3]},
        {"question_id": 2, "selected_option_ids": [5, 7]},
    ]
    """
    total_points = 0
    earned_points = 0
    attempt_answers = []

    for answer in submitted_answers:
        question = Question.objects.prefetch_related("options").get(
            id=answer["question_id"], quiz=attempt.quiz
        )
        correct_ids = set(
            question.options.filter(is_correct=True).values_list("id", flat=True)
        )
        selected_ids = set(answer["selected_option_ids"])
        is_correct = correct_ids == selected_ids

        total_points += question.points
        if is_correct:
            earned_points += question.points

        attempt_answers.append(AttemptAnswer(
            attempt=attempt,
            question=question,
            is_correct=is_correct,
        ))

    # Bulk insert de respuestas
    AttemptAnswer.objects.bulk_create(attempt_answers)
    attempt_answers_m2m = zip(attempt_answers, submitted_answers)
    for aa, ans in attempt_answers_m2m:
        aa.selected_options.set(ans["selected_option_ids"])

    # Calcular score final
    score = (earned_points / total_points * 100) if total_points > 0 else 0
    attempt.score = round(score, 2)
    attempt.passed = score >= attempt.quiz.passing_score
    attempt.finished_at = timezone.now()
    attempt.save()

    return attempt
```

---

## 7. Tareas Asíncronas con Celery

### 7.1 Tasks Completas

| Task | Descripción | Disparador |
|---|---|---|
| `send_welcome_email` | Bienvenida al registrarse | Signal `post_save` User (created) |
| `send_enrollment_confirmation` | Confirmación de inscripción | Signal `post_save` Enrollment (created) |
| `send_lesson_completed_email` | Notificación al completar lección | Signal `post_save` LessonProgress |
| `send_course_completion` | Felicitación al completar 100% del curso | Lógica en endpoint `complete-lesson` |
| `send_quiz_result` | Resultado del intento del quiz con score y feedback | Signal `post_save` Attempt (finished) |
| `send_assignment_notification` | Notifica al empleado cuando le asignan un curso | Signal `post_save` CompletionRecord |
| `send_bulk_assignment_emails` | Emails masivos con `group()` para asignación por dpto | Endpoint `assign-department` |
| `send_due_date_reminder` | Recordatorio 3 días antes de vencimiento de asignación | Beat: diario 9:00am |
| `send_inactivity_reminder` | Recordatorio si el estudiante no avanza en 3 días | Beat: diario 9:00am |
| `send_weekly_progress_report` | Resumen semanal a todos los estudiantes activos | Beat: lunes 8:00am |
| `generate_monthly_company_report` | Reporte mensual a HR Admins de cada empresa | Beat: día 1 de cada mes |

### 7.2 Configuración de Beat

```python
# config/celery.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'inactivity-reminder': {
        'task': 'apps.notifications.tasks.send_inactivity_reminder',
        'schedule': crontab(hour=9, minute=0),
    },
    'due-date-reminder': {
        'task': 'apps.notifications.tasks.send_due_date_reminder',
        'schedule': crontab(hour=9, minute=30),
    },
    'weekly-progress-report': {
        'task': 'apps.notifications.tasks.send_weekly_progress_report',
        'schedule': crontab(day_of_week=1, hour=8, minute=0),
    },
    'monthly-company-report': {
        'task': 'apps.notifications.tasks.generate_monthly_company_report',
        'schedule': crontab(day_of_month=1, hour=7, minute=0),
    },
}
```

### 7.3 Signals Centralizados

```python
# apps/enrollments/signals.py
@receiver(post_save, sender=Enrollment)
def on_enrollment_created(sender, instance, created, **kwargs):
    if created:
        send_enrollment_confirmation.delay(instance.id)

@receiver(post_save, sender=LessonProgress)
def on_lesson_completed(sender, instance, created, **kwargs):
    if created and instance.completed:
        check_and_notify_course_completion.delay(instance.enrollment.id)

# apps/quizzes/signals.py
@receiver(post_save, sender=Attempt)
def on_attempt_finished(sender, instance, **kwargs):
    if instance.finished_at and not instance._already_notified:
        send_quiz_result.delay(instance.id)

# apps/users/signals.py
@receiver(post_save, sender=User)
def on_user_created(sender, instance, created, **kwargs):
    if created:
        send_welcome_email.delay(instance.id)
```

---

## 8. ORM Django Avanzado — Ejemplos Clave

### 8.1 Dashboard del Estudiante — Cursos con Progreso

```python
# apps/enrollments/views.py
Enrollment.objects.filter(
    student=request.user,
    is_active=True
).select_related(
    "course__category",
    "course__instructor"
).prefetch_related(
    "lesson_progress",
    "course__lessons"
).annotate(
    completed_lessons=Count(
        "lesson_progress",
        filter=Q(lesson_progress__completed=True)
    ),
    total_lessons=Count("course__lessons", distinct=True),
    progress_pct=ExpressionWrapper(
        Count("lesson_progress", filter=Q(lesson_progress__completed=True))
        * 100.0
        / Count("course__lessons", distinct=True),
        output_field=FloatField()
    )
).order_by("-enrolled_at")
```

### 8.2 Catálogo de Cursos con Stats Agregadas

```python
# apps/courses/views.py
Course.objects.filter(
    is_published=True
).select_related(
    "instructor", "category"
).prefetch_related(
    "tags"
).annotate(
    enrolled_count=Count("enrollments", distinct=True),
    avg_rating=Avg("reviews__rating"),
    review_count=Count("reviews", distinct=True),
    lesson_count=Count("lessons", distinct=True),
    completion_rate=Avg(
        Case(
            When(
                enrollments__lesson_progress__completed=True,
                then=Value(1)
            ),
            default=Value(0),
            output_field=FloatField()
        )
    )
).order_by("-enrolled_count")
```

### 8.3 Stats de Quiz para Instructores

```python
# apps/quizzes/views.py
Attempt.objects.filter(
    quiz=quiz,
    finished_at__isnull=False
).aggregate(
    total_attempts=Count("id"),
    unique_students=Count("student", distinct=True),
    avg_score=Avg("score"),
    pass_rate=Avg(
        Case(
            When(passed=True, then=Value(1)),
            default=Value(0),
            output_field=FloatField()
        )
    ) * 100,
    highest_score=Max("score"),
    lowest_score=Min("score"),
)
```

### 8.4 Pregunta Más Fallada del Quiz

```python
# apps/quizzes/views.py
Question.objects.filter(quiz=quiz).annotate(
    total_answers=Count("attemptanswer"),
    wrong_answers=Count(
        "attemptanswer",
        filter=Q(attemptanswer__is_correct=False)
    ),
    error_rate=ExpressionWrapper(
        Count("attemptanswer", filter=Q(attemptanswer__is_correct=False))
        * 100.0
        / Count("attemptanswer"),
        output_field=FloatField()
    )
).order_by("-error_rate")
```

---

## 9. Docker y Despliegue

### 9.1 Servicios en `docker-compose.yml`

| Servicio | Imagen | Puerto | Descripción |
|---|---|---|---|
| `web` | `python:3.13-slim` | `8080` | Django + Gunicorn |
| `db` | `mysql:8.4` | `3306` | Base de datos MySQL LTS |
| `redis` | `redis:8-alpine` | `6379` | Broker Celery + caché |
| `celery_worker` | (mismo que web) | — | Worker `concurrency=4` |
| `celery_beat` | (mismo que web) | — | Scheduler periódico |
| `flower` | `mher/flower` | `5555` | Dashboard Celery (solo dev) |

### 9.2 `Dockerfile`

```dockerfile
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev gcc pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

### 9.3 `entrypoint.sh`

```bash
#!/bin/bash
set -e
echo "Running migrations..."
python manage.py migrate --noinput
echo "Collecting static files..."
python manage.py collectstatic --noinput
echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8080 \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
```

### 9.4 `cloudbuild.yaml`

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/insis', '.']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/insis']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'run'
      - 'deploy'
      - 'insis'
      - '--image=gcr.io/$PROJECT_ID/insis'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--memory=512Mi'
      - '--set-env-vars=DJANGO_SETTINGS_MODULE=config.settings.production'
```

### 9.5 `.env.example`

```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings.local
ALLOWED_HOSTS=localhost,127.0.0.1

# MySQL
DB_HOST=db
DB_NAME=insis_db
DB_USER=insis_user
DB_PASSWORD=your-db-password
DB_PORT=3306

# Celery / Redis
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=INSIS <noreply@insis.com>

# Cloud Storage (solo producción)
GCS_BUCKET_NAME=insis-reports
```

---

## 10. Plan de Tests

### 10.1 Cobertura por App

| App | Tests a Implementar |
|---|---|
| `users` | Registro email duplicado, login exitoso/fallido, refresh, perfil, cambio contraseña |
| `courses` | CRUD con permisos por rol, filtros por categoría, detalle con annotate |
| `enrollments` | Inscripción exitosa, duplicada (400), marcar lección, cálculo de progreso % |
| `quizzes` | Iniciar intento, límite de intentos, corrección automática, score correcto, pregunta M2M |
| `companies` | CRUD empresa, permisos HR Manager vs Admin, stats con annotate |
| `assignments` | Asignación individual, masiva por dpto, cancelar con notificación |
| `reports` | Completación por dpto con datos conocidos, ranking, vencidos, CSV headers |
| `notifications tasks` | `send_welcome_email` crea `EmailNotification`, mock de SMTP |
| `signals` | `post_save` Enrollment dispara task (mock), signal User crea email |
| `permissions` | Instructor no edita curso ajeno, Employee solo ve sus asignaciones |

### 10.2 Factories Centralizadas

```python
# tests/factories.py
import factory
from apps.users.models import User
from apps.courses.models import Course, Lesson, Category
from apps.enrollments.models import Enrollment
from apps.quizzes.models import Quiz, Question, Option, Attempt

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    email = factory.Sequence(lambda n: f"user{n}@test.com")
    full_name = factory.Faker("name")
    role = "STUDENT"

class InstructorFactory(UserFactory):
    role = "INSTRUCTOR"

class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
    name = factory.Faker("word")
    slug = factory.LazyAttribute(lambda o: o.name.lower())

class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course
    title = factory.Faker("sentence", nb_words=4)
    slug = factory.Sequence(lambda n: f"course-{n}")
    instructor = factory.SubFactory(InstructorFactory)
    category = factory.SubFactory(CategoryFactory)
    is_published = True

class QuizFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Quiz
    course = factory.SubFactory(CourseFactory)
    title = factory.Faker("sentence", nb_words=3)
    passing_score = 60.0
    max_attempts = 3
```

### 10.3 Ejemplo de Test del Motor de Quizzes

```python
# apps/quizzes/tests/test_graders.py
import pytest
from tests.factories import UserFactory, QuizFactory, QuestionFactory, OptionFactory

@pytest.mark.django_db
class TestQuizGrader:

    def test_all_correct_answers_gives_100_score(self):
        student = UserFactory()
        quiz = QuizFactory(passing_score=60.0)
        question = QuestionFactory(quiz=quiz, points=10, type="SINGLE")
        correct_option = OptionFactory(question=question, is_correct=True)
        wrong_option = OptionFactory(question=question, is_correct=False)

        attempt = Attempt.objects.create(
            quiz=quiz, student=student, attempt_number=1
        )
        result = grade_attempt(attempt, [
            {"question_id": question.id, "selected_option_ids": [correct_option.id]}
        ])

        assert result.score == 100.0
        assert result.passed is True

    def test_all_wrong_answers_gives_0_score(self):
        student = UserFactory()
        quiz = QuizFactory(passing_score=60.0)
        question = QuestionFactory(quiz=quiz, points=10, type="SINGLE")
        correct_option = OptionFactory(question=question, is_correct=True)
        wrong_option = OptionFactory(question=question, is_correct=False)

        attempt = Attempt.objects.create(
            quiz=quiz, student=student, attempt_number=1
        )
        result = grade_attempt(attempt, [
            {"question_id": question.id, "selected_option_ids": [wrong_option.id]}
        ])

        assert result.score == 0.0
        assert result.passed is False
```

---

## 11. Código Limpio y PEP8

### 11.1 Convenciones Aplicadas

| Convención | Herramienta | Config |
|---|---|---|
| PEP8 | `flake8` | `setup.cfg` con `max-line-length = 88` |
| Formateo automático | `black` | `line-length = 88` |
| Imports ordenados | `isort` | Compatible con black |
| Docstrings en ViewSets | Manual | Aparecen en Swagger automáticamente |

### 11.2 `setup.cfg`

```ini
[flake8]
max-line-length = 88
exclude = migrations, __pycache__, .git, venv
extend-ignore = E203, W503

[tool:pytest]
DJANGO_SETTINGS_MODULE = config.settings.local
python_files = tests.py test_*.py *_tests.py
addopts = --reuse-db -v

[coverage:run]
source = apps
omit = */migrations/*, */tests/*, */factories.py
```

---

## 13. Comandos Rápidos

```bash
# Setup inicial
git clone https://github.com/[usuario]/insis-api
cd insis-api
cp .env.example .env

# Levantar todos los servicios
docker-compose up --build

# Acceder al contenedor web
docker-compose exec web bash

# Correr tests con cobertura
docker-compose exec web pytest --cov=apps --cov-report=term-missing

# Ver reporte de cobertura en HTML
docker-compose exec web pytest --cov=apps --cov-report=html
# Abrir htmlcov/index.html en el navegador

# Lint y formato
docker-compose exec web flake8 apps/
docker-compose exec web black apps/

# Documentación Swagger
http://localhost:8080/api/schema/swagger-ui/

# Dashboard de Celery (Flower)
http://localhost:5555

# Shell de Django
docker-compose exec web python manage.py shell_plus
```


---


