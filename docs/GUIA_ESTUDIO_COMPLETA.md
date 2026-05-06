# Guía de Estudio Completa — INSIS API

> **Objetivo:** Entender profundamente cómo se usó Django, Django REST Framework, ORM avanzado, Signals, Docker, Celery, Cloud Run, PEP 8, tests y Postman — todo referenciado al código real de este proyecto.

---

## Índice

1. [Estructura general del proyecto](#1-estructura-general-del-proyecto)
2. [Django: cómo y dónde se usa](#2-django-cómo-y-dónde-se-usa)
3. [Django REST Framework (DRF)](#3-django-rest-framework-drf)
4. [Modelos y base de datos](#4-modelos-y-base-de-datos)
5. [Django ORM avanzado](#5-django-orm-avanzado)
6. [Django Signals](#6-django-signals)
7. [Docker: qué es y por qué lo usamos](#7-docker-qué-es-y-por-qué-lo-usamos)
8. [PEP 8 y documentación de código](#8-pep-8-y-documentación-de-código)
9. [Tests unitarios con pytest](#9-tests-unitarios-con-pytest)
10. [Celery y cola de tareas](#10-celery-y-cola-de-tareas)
11. [Despliegue en Cloud Run](#11-despliegue-en-cloud-run)
12. [Colecciones Postman: todas las rutas](#12-colecciones-postman-todas-las-rutas)

---

## 1. Estructura general del proyecto

```
insis-api/
├── apps/                        # Lógica de negocio (cada módulo = una app Django)
│   ├── core/                    # Modelos abstractos reutilizables
│   ├── users/                   # Autenticación y roles
│   ├── companies/               # Multi-tenancy B2B
│   ├── courses/                 # Contenido (cursos, lecciones)
│   ├── enrollments/             # Matrículas y progreso
│   ├── quizzes/                 # Evaluaciones
│   ├── assignments/             # Asignación corporativa de cursos
│   ├── reports/                 # Reportes y exportaciones
│   └── notifications/           # Emails async vía Celery
├── config/
│   ├── settings/
│   │   ├── base.py              # Settings compartidos (DRF, JWT, Celery)
│   │   ├── local.py             # Dev local (MySQL Docker, debug)
│   │   ├── production.py        # Cloud Run (Cloud SQL, SMTP, GCS)
│   │   └── test.py              # Tests (SQLite, tareas síncronas)
│   ├── urls.py                  # Router raíz
│   └── celery.py                # App Celery + schedule de tareas periódicas
├── tests/
│   ├── conftest.py              # Fixtures globales pytest
│   └── factories.py             # Factory Boy (datos de prueba)
├── Dockerfile                   # Imagen multi-stage Python 3.13
├── docker-compose.yml           # 6 servicios orquestados
├── requirements.txt             # Deps de producción
├── requirements-dev.txt         # Deps de desarrollo (pytest, black, etc.)
└── setup.cfg                    # Config de flake8, pytest, coverage, isort
```

### ¿Por qué este diseño?

Django fomenta la separación en **apps** (módulos independientes). Cada app tiene sus propios modelos, vistas, serializers, URLs y tests. Esto hace que el código sea:
- Testeable de forma aislada
- Extensible sin tocar otras partes
- Reutilizable entre proyectos

---

## 2. Django: cómo y dónde se usa

### 2.1 El entry point: `manage.py`

`manage.py` es el CLI de Django. Permite ejecutar comandos como `migrate`, `runserver`, `createsuperuser`. Internamente setea `DJANGO_SETTINGS_MODULE` (configurado a `config.settings.local` por defecto).

### 2.2 Settings divididos (base / local / production / test)

**Archivo:** `config/settings/base.py`

```python
# Línea 1-30: Imports y lectura del .env
from decouple import config, Csv

SECRET_KEY = config("SECRET_KEY")
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())
```

`python-decouple` lee variables de `.env` en local y de variables de entorno en producción. Así el mismo código funciona en ambos ambientes sin hardcodear secrets.

**`base.py` define:**
- `INSTALLED_APPS`: todas las apps Django + las nuestras (prefijadas `apps.`)
- `MIDDLEWARE`: seguridad, CORS, sesiones
- `REST_FRAMEWORK`: configuración global de DRF
- `SIMPLE_JWT`: duración de tokens, rotación, blacklist
- `CELERY_*`: broker Redis, serialización JSON
- `TIME_ZONE = "America/Lima"`

**`local.py`** hereda de base y agrega:
```python
from .base import *          # herencia de settings
DEBUG = True
DATABASES = {
    "default": {
        "HOST": "db",        # nombre del servicio Docker
        ...
    }
}
```

**`test.py`** usa SQLite (sin servidor) y tareas síncronas para tests rápidos:
```python
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3"}}
CELERY_TASK_ALWAYS_EAGER = True   # las tareas se ejecutan al instante, no en cola
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # más rápido en tests
```

### 2.3 URLs raíz

**Archivo:** `config/urls.py`

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.users.urls")),
    path("api/v1/", include("apps.companies.urls")),
    path("api/v1/", include("apps.courses.urls")),
    # ... resto de apps
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(), name="swagger-ui"),
]
```

Todas las APIs están bajo `/api/v1/`. El Swagger está en `/api/schema/swagger-ui/`.

### 2.4 Admin de Django

Django incluye un panel de administración automático en `/admin/`. Cada app registra sus modelos en `admin.py`. Esto permite gestionar datos sin escribir endpoints extra.

### 2.5 Migraciones

Las migraciones son archivos Python que describen cambios en la base de datos. Django los genera automáticamente desde los modelos:

```bash
# Generar migración después de cambiar un modelo
docker-compose exec web python manage.py makemigrations users

# Aplicar migraciones
docker-compose exec web python manage.py migrate
```

Las migraciones viven en `apps/<nombre>/migrations/`. Nunca edites el archivo de migración a mano; edita el modelo y regenera.

---

## 3. Django REST Framework (DRF)

DRF es la librería que convierte Django en una API REST. Sus componentes principales son:

### 3.1 ViewSets y Routers

Un **ViewSet** agrupa las vistas CRUD de un recurso. El **Router** genera las URLs automáticamente.

**Ejemplo — `apps/courses/urls.py`:**
```python
router = DefaultRouter()
router.register("categories", CategoryViewSet)
router.register("courses", CourseViewSet)
urlpatterns = router.urls
```

Esto genera automáticamente:
- `GET /categories/` → list
- `POST /categories/` → create
- `GET /categories/{id}/` → retrieve
- `PATCH /categories/{id}/` → partial_update
- `DELETE /categories/{id}/` → destroy

### 3.2 `@action` — endpoints personalizados

Cuando un recurso necesita una acción que no es CRUD estándar, se usa `@action`.

**Ejemplo — `apps/courses/views.py` (CourseViewSet):**
```python
@action(detail=True, methods=["get", "post"], url_path="lessons")
def lessons(self, request, slug=None):
    ...

@action(detail=True, methods=["post"], url_path="reviews")
def reviews(self, request, slug=None):
    ...
```

`detail=True` significa que la acción aplica a un objeto específico (`/courses/{slug}/lessons/`).
`detail=False` sería sobre la colección (`/courses/my-courses/`).

### 3.3 Serializers

Los serializers convierten objetos Python ↔ JSON. Son el "formulario" de la API.

**Ejemplo — `apps/users/serializers.py`:**
```python
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = ["email", "password", "full_name"]

    def create(self, validated_data):
        return CustomUser.objects.create_user(**validated_data)
```

`write_only=True` → el campo se recibe pero nunca se envía en la respuesta (passwords).
`read_only=True` → el campo se envía en la respuesta pero no se puede escribir.

**Serializers anidados (nested):**
```python
# apps/users/serializers.py — UserSerializer
class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()   # nested

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        # actualiza user
        UserProfile.objects.filter(user=instance).update(**profile_data)
        return instance
```

### 3.4 Permissions (permisos)

**Archivo:** `apps/users/permissions.py`

```python
class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == Roles.ADMIN

class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:   # GET, HEAD, OPTIONS
            return request.user.is_authenticated
        return request.user.role == Roles.ADMIN
```

Se aplican en los ViewSets:
```python
class CategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
```

O por acción:
```python
def get_permissions(self):
    if self.action in ["create", "partial_update"]:
        return [IsAdmin()]
    return [IsAuthenticated()]
```

### 3.5 Pagination

Configurada globalmente en `base.py`:
```python
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
```

Todas las listas devuelven:
```json
{
  "count": 100,
  "next": "http://...?page=2",
  "previous": null,
  "results": [...]
}
```

### 3.6 Throttling (limitación de velocidad)

```python
# base.py
"DEFAULT_THROTTLE_RATES": {
    "anon": "100/hour",
    "user": "1000/hour",
}
```

Previene abuso de la API (brute force, spam).

### 3.7 Filters

**Archivo:** `apps/courses/filters.py`

```python
class CourseFilter(FilterSet):
    min_price = NumberFilter(field_name="price", lookup_expr="gte")
    max_price = NumberFilter(field_name="price", lookup_expr="lte")
    is_free = BooleanFilter(method="filter_free")
    tag = CharFilter(field_name="tags__slug")

    class Meta:
        model = Course
        fields = ["category", "level", "language"]
```

Permite queries como: `GET /courses/?level=BEGINNER&min_price=0&tag=python`

### 3.8 drf-spectacular (documentación OpenAPI)

```python
# En cualquier ViewSet o View
@extend_schema(
    summary="Register a new user",
    request=RegisterSerializer,
    responses={201: UserSerializer},
)
```

Genera automáticamente el Swagger en `/api/schema/swagger-ui/`. **Siempre úsalo** en lugar de documentar en comentarios.

---

## 4. Modelos y base de datos

### 4.1 Modelos abstractos (apps/core/models.py)

Los modelos abstractos son clases base reutilizables que **no crean tablas propias**:

```python
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True   # ← clave: Django no crea tabla para esta clase
```

**Todos los modelos del proyecto heredan de `TimestampedModel`**, garantizando que siempre tenemos `created_at` y `updated_at`.

### 4.2 Soft Delete (borrado lógico)

En lugar de borrar registros de la BD, marcamos `deleted_at`:

```python
# apps/core/models.py
class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    objects = SoftDeleteManager()       # solo muestra registros vivos

    def delete(self, *args, **kwargs):
        self.deleted_at = timezone.now()   # borrado lógico
        self.save(update_fields=["deleted_at"])

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)    # borrado físico real

    class Meta:
        abstract = True
```

**¿Por qué?** Para preservar historial, auditoría y referencias (FKs no se rompen).

### 4.3 Manager personalizado

```python
class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()
```

**Regla del proyecto:** Siempre usar `objects.alive()` en filtros. El manager ya lo hace automáticamente, pero en queries avanzadas es explícito.

### 4.4 Tipos de relaciones

```python
# ForeignKey (muchos a uno) — una lección pertenece a un curso
class Lesson(TimestampedModel):
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,      # no permite borrar el curso si tiene lecciones
        related_name="lessons"         # course.lessons.all() desde el Course
    )

# ManyToMany — un curso tiene muchas tags, una tag tiene muchos cursos
class Course(TimestampedModel):
    tags = models.ManyToManyField(Tag, blank=True, related_name="courses")

# OneToOne — cada usuario tiene un perfil
class UserProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,      # si se borra el usuario, se borra el perfil
        related_name="profile"
    )
```

**on_delete options:**
- `CASCADE` → borra en cascada
- `PROTECT` → lanza error si hay FK referenciando
- `SET_NULL` → pone NULL (requiere `null=True`)
- `SET_DEFAULT` → pone el valor default

### 4.5 CustomUser: AbstractBaseUser

Para autenticación con email (en vez de username):

```python
# apps/users/models.py
class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    USERNAME_FIELD = "email"    # Django usa email para autenticar
    REQUIRED_FIELDS = ["full_name"]

    objects = CustomUserManager()
```

`AbstractBaseUser` da control total sobre el modelo de usuario.
`PermissionsMixin` agrega groups, permissions, is_superuser.

### 4.6 Índices de base de datos

```python
# apps/courses/models.py
class Course(TimestampedModel, SoftDeleteModel):
    class Meta:
        indexes = [
            models.Index(fields=["instructor", "is_published"]),
        ]
```

Los índices aceleran queries frecuentes. Se crean automáticamente en las migraciones.

### 4.7 Restricciones (constraints)

```python
# apps/quizzes/models.py
class Quiz(TimestampedModel):
    passing_score = models.DecimalField(...)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(passing_score__gte=0) & Q(passing_score__lte=100),
                name="quiz_passing_score_range"
            )
        ]
```

Las `CheckConstraint` se validan en la BD (no solo en Python), garantizando integridad de datos.

---

## 5. Django ORM avanzado

El ORM (Object-Relational Mapper) de Django convierte operaciones Python en SQL. Aprenderás las técnicas más avanzadas que usamos.

### 5.1 Annotations (anotaciones)

Agregan campos calculados a los QuerySets **en SQL** (una sola query, sin loops en Python):

```python
# apps/courses/views.py — CourseViewSet.get_queryset()
queryset = Course.objects.annotate(
    avg_rating=Avg("reviews__rating"),          # promedio de ratings
    review_count=Count("reviews", distinct=True),
    lesson_count=Count("lessons", distinct=True),
    enrolled_count=Count("enrollments", distinct=True),
)
```

Esto genera SQL como:
```sql
SELECT courses.*,
       AVG(reviews.rating) AS avg_rating,
       COUNT(DISTINCT reviews.id) AS review_count,
       ...
FROM courses
LEFT JOIN reviews ON reviews.course_id = courses.id
...
GROUP BY courses.id
```

Luego en el serializer:
```python
class CourseListSerializer(serializers.ModelSerializer):
    avg_rating = serializers.FloatField(read_only=True)   # viene de la annotation
    lesson_count = serializers.IntegerField(read_only=True)
```

### 5.2 select_related y prefetch_related

Evitan el problema N+1 (N queries extra por cada objeto):

```python
# select_related: JOIN para ForeignKey/OneToOne (una sola query)
Course.objects.select_related("instructor", "category")

# prefetch_related: query separada para ManyToMany o reverse FK
Course.objects.prefetch_related("tags", "lessons")

# Combinación típica:
Course.objects.select_related("instructor").prefetch_related("tags").annotate(...)
```

**¿Cuándo usar cuál?**
- `select_related` → relaciones FK/OneToOne (JOIN SQL)
- `prefetch_related` → ManyToMany o reverse FK (2 queries, luego Python junta)

### 5.3 select_for_update (bloqueo optimista)

Previene condiciones de carrera en operaciones críticas:

```python
# apps/quizzes/views.py — start action
with transaction.atomic():
    existing = Attempt.objects.select_for_update().filter(
        quiz=quiz, student=request.user, finished_at__isnull=True
    ).first()
```

`select_for_update()` agrega `FOR UPDATE` al SQL, bloqueando la fila hasta que termine la transacción. Impide que dos requests creen dos intentos simultáneos.

### 5.4 F() expressions

Referencian campos del modelo en expresiones SQL (sin cargar el objeto a Python):

```python
from django.db.models import F

# Incrementar contador atómicamente (no hay race condition)
Attempt.objects.filter(pk=attempt.pk).update(
    attempt_number=F("attempt_number") + 1
)

# Filtrar donde campo A > campo B
Enrollment.objects.filter(completed_at__gt=F("enrolled_at"))
```

### 5.5 Q() objects (queries complejas)

Permite OR, AND, NOT en filtros:

```python
from django.db.models import Q

# OR: cursos publicados O gratuitos
Course.objects.filter(Q(is_published=True) | Q(price=0))

# AND negado: NO borrados Y no expirados
Course.objects.filter(Q(deleted_at__isnull=True) & ~Q(is_published=False))
```

### 5.6 Subqueries y Exists

```python
from django.db.models import Exists, OuterRef, Subquery

# Cursos en los que el usuario está matriculado
enrolled_courses = Enrollment.objects.filter(
    student=request.user,
    course=OuterRef("pk")      # referencia al Course padre
)
Course.objects.annotate(is_enrolled=Exists(enrolled_courses))
```

### 5.7 Values y Values_list (queries optimizadas)

```python
# Solo traer IDs (más rápido que cargar objetos completos)
enrolled_course_ids = Enrollment.objects.filter(
    student=request.user
).values_list("course_id", flat=True)

# Diccionarios en vez de objetos
Course.objects.values("id", "title", "price")
```

### 5.8 aggregate vs annotate

```python
# aggregate: UN resultado para todo el QuerySet
Course.objects.aggregate(avg=Avg("price"), total=Count("id"))
# → {"avg": 49.99, "total": 127}

# annotate: UN resultado POR CADA objeto
Course.objects.annotate(lesson_count=Count("lessons"))
# → [<Course: ..., lesson_count=5>, <Course: ..., lesson_count=12>, ...]
```

### 5.9 get_or_create y update_or_create

Operaciones atómicas para evitar duplicados:

```python
# apps/assignments/tasks.py — materialize_assignment_targets
enrollment, created = Enrollment.objects.get_or_create(
    student=employee.user,
    course=assignment.course,
    defaults={
        "source": Enrollment.Source.B2B_ASSIGNMENT,
        "course_assignment": assignment,
    }
)
```

`get_or_create` intenta hacer GET; si no existe, hace CREATE. Es atómico y evita duplicados bajo concurrencia.

### 5.10 Consultas con fechas

```python
from django.utils import timezone
from datetime import timedelta

# Asignaciones que vencen en los próximos 3 días
due_soon = CourseAssignment.objects.filter(
    due_date__date__lte=timezone.now().date() + timedelta(days=3),
    due_date__date__gte=timezone.now().date(),
    is_active=True,
)

# Estudiantes inactivos (sin completar lección en 3 días)
cutoff = timezone.now() - timedelta(days=3)
inactive = LessonProgress.objects.filter(
    completed_at__lt=cutoff
)
```

---

## 6. Django Signals

Los signals son el mecanismo de **eventos** de Django: cuando algo ocurre en un modelo, se dispara automáticamente otra acción.

### 6.1 ¿Qué son?

Son el patrón Observer/Pub-Sub de Django. Un modelo "emite" una señal, y uno o varios "receptores" (receivers) la escuchan y reaccionan.

**Signals más comunes:**
- `pre_save` → antes de guardar
- `post_save` → después de guardar
- `pre_delete` → antes de borrar
- `post_delete` → después de borrar

### 6.2 Signal 1: Crear UserProfile automáticamente

**Archivo:** `apps/users/signals.py`

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:                             # solo cuando se CREA, no al actualizar
        UserProfile.objects.create(user=instance)
```

**Flujo:**
1. `CustomUser.objects.create_user(email=..., password=...)` se ejecuta
2. Django guarda el usuario en BD
3. Django dispara `post_save`
4. `create_user_profile` recibe la señal
5. Se crea el `UserProfile` automáticamente

**¿Por qué signals y no en el manager?** Los signals garantizan que siempre se crea el perfil, sin importar cómo se cree el usuario (admin, import, test, etc.).

### 6.3 Signal 2: Enviar email de bienvenida

```python
@receiver(post_save, sender=CustomUser)
def send_welcome_email_signal(sender, instance, created, **kwargs):
    if created:
        from apps.notifications.tasks import send_welcome_email
        send_welcome_email.delay(instance.pk)   # async, no bloquea la request
```

`delay()` encola la tarea en Celery; la request responde inmediatamente sin esperar el email.

### 6.4 Signal 3: Confirmar matrícula

**Archivo:** `apps/enrollments/signals.py`

```python
@receiver(post_save, sender=Enrollment)
def on_enrollment_created(sender, instance, created, **kwargs):
    if created:
        send_enrollment_confirmation.delay(instance.pk)
```

### 6.5 Signal 4: Detectar completación de curso

```python
@receiver(post_save, sender=LessonProgress)
def on_lesson_completed(sender, instance, **kwargs):
    if not instance.completed:
        return

    enrollment = instance.enrollment
    total = enrollment.course.lessons.filter(is_published=True).count()
    done = LessonProgress.objects.filter(
        enrollment=enrollment, completed=True
    ).count()

    if total > 0 and done >= total:
        enrollment.mark_completed()
        send_course_completion.delay(enrollment.pk)
```

**Flujo completo:**
1. Estudiante hace POST `/enrollments/{id}/complete-lesson/`
2. Se crea/actualiza `LessonProgress(completed=True)`
3. `post_save` dispara `on_lesson_completed`
4. Se cuenta si todas las lecciones están completas
5. Si sí → `enrollment.mark_completed()` + email async

### 6.6 Signal 5: Resultado de quiz

**Archivo:** `apps/quizzes/signals.py`

```python
@receiver(post_save, sender=Attempt)
def on_attempt_finished(sender, instance, **kwargs):
    if not instance.finished_at or instance.notified_at:
        return
    # Actualización atómica para evitar doble notificación
    updated = Attempt.objects.filter(
        pk=instance.pk, notified_at__isnull=True
    ).update(notified_at=timezone.now())
    if updated:
        send_quiz_result.delay(instance.pk)
```

El check `notified_at__isnull=True` en el `update()` es un **guard atómico**: si dos requests concurrentes terminan el quiz simultáneamente, solo una disparará el email.

### 6.7 ¿Dónde se registran los signals?

En el `AppConfig` de cada app:

```python
# apps/users/apps.py
class UsersConfig(AppConfig):
    name = "apps.users"

    def ready(self):
        import apps.users.signals   # registra los receivers al iniciar Django
```

---

## 7. Docker: qué es y por qué lo usamos

### 7.1 ¿Qué es Docker?

Docker empaqueta una aplicación con **todo lo que necesita** (Python, librerías, variables de configuración) en un "contenedor". El contenedor corre igual en cualquier máquina.

**Sin Docker:** "En mi máquina funciona" (diferentes versiones de Python, MySQL, Redis).
**Con Docker:** Todos los desarrolladores y el servidor de producción usan exactamente las mismas versiones.

### 7.2 Dockerfile: imagen multi-stage

**Archivo:** `Dockerfile`

```dockerfile
# STAGE 1: builder — instala dependencias y compila wheels
FROM python:3.13-slim AS builder
RUN apt-get install -y default-libmysqlclient-dev
COPY requirements.txt .
RUN pip wheel --no-deps -r requirements.txt -w /wheels

# STAGE 2: runtime — imagen final mínima (sin herramientas de build)
FROM python:3.13-slim
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/*

# Colectar archivos estáticos
RUN python manage.py collectstatic --noinput

# Usuario sin privilegios (seguridad)
RUN useradd -r appuser && chown -R appuser /app
USER appuser

# Servidor de producción
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8080", "--workers", "2"]
```

**¿Por qué multi-stage?**
- Stage 1 tiene compiladores (150MB+ de herramientas)
- Stage 2 solo tiene lo necesario para correr (~50MB menos)
- La imagen de producción es más pequeña y segura

### 7.3 docker-compose.yml: 6 servicios

**Archivo:** `docker-compose.yml`

```yaml
services:
  db:           # MySQL 8.4 — base de datos principal
  redis:        # Redis 8 — broker de Celery y cache
  web:          # Django + Gunicorn — la API REST
  celery_worker: # Procesa tareas async (emails, reportes)
  celery_beat:   # Dispara tareas periódicas (recordatorios)
  flower:        # UI web para monitorear Celery (dev only)
```

**Healthchecks y depends_on:**
```yaml
web:
  depends_on:
    db:
      condition: service_healthy   # espera hasta que MySQL esté listo
    redis:
      condition: service_healthy
```

Sin esto, Django intentaría conectarse a MySQL antes de que esté listo y fallaría.

### 7.4 Comandos Docker esenciales

```bash
# Iniciar todo
docker-compose up --build

# Iniciar en background
docker-compose up -d

# Ver logs de Django
docker-compose logs -f web

# Ejecutar comando dentro del contenedor
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser

# Abrir shell Python dentro del contenedor
docker-compose exec web python manage.py shell

# Parar todo
docker-compose down

# Parar y eliminar volúmenes (datos de BD)
docker-compose down -v
```

### 7.5 Volúmenes

```yaml
volumes:
  mysql_data:   # persiste datos de MySQL entre reinicios
  redis_data:   # persiste datos de Redis
  static_data:  # archivos estáticos (CSS, JS admin)
  media_data:   # uploads de usuarios (avatars, logos)
```

Sin volúmenes, los datos desaparecerían cada vez que se reinicia el contenedor.

---

## 8. PEP 8 y documentación de código

### 8.1 ¿Qué es PEP 8?

PEP 8 es la guía de estilo oficial de Python. Define:
- Indentación: 4 espacios (no tabs)
- Longitud máxima de línea: 88 caracteres (usamos black que lo impone)
- Nombres en snake_case para variables/funciones, PascalCase para clases
- Dos líneas en blanco entre clases, una línea entre métodos
- Imports ordenados: stdlib → third-party → local

### 8.2 Herramientas configuradas

**Archivo:** `setup.cfg`

```ini
[flake8]
max-line-length = 88      # compatible con black
exclude = migrations, venv
ignore = E203, W503       # conflictos con black

[isort]
profile = black           # compatibilidad con black
known_django = django
known_drf = rest_framework
sections = FUTURE, STDLIB, THIRDPARTY, DJANGO, DRF, FIRSTPARTY, LOCALFOLDER
```

**Workflow de calidad:**
```bash
isort apps/        # ordena imports
black apps/        # formatea código
flake8 apps/       # verifica estilo y errores
```

### 8.3 Código limpio PEP 8 vs código sucio

**Malo:**
```python
def getuser(id,type='admin',active=True):
    u=CustomUser.objects.filter(pk=id,role=type,is_active=active).first()
    if u==None:
        return None
    return u
```

**Bueno (PEP 8):**
```python
def get_user(user_id, role="admin", is_active=True):
    return CustomUser.objects.filter(
        pk=user_id,
        role=role,
        is_active=is_active,
    ).first()
```

### 8.4 Documentación de endpoints con drf-spectacular

En vez de comentarios en el código, usamos decoradores que generan Swagger:

```python
# apps/users/views.py
@extend_schema(
    summary="Register a new user",
    description="Creates a user account. Sends a welcome email async.",
    request=RegisterSerializer,
    responses={
        201: UserSerializer,
        400: OpenApiResponse(description="Validation errors"),
    },
    tags=["Authentication"],
)
class RegisterView(generics.CreateAPIView):
    ...
```

El Swagger en `/api/schema/swagger-ui/` muestra:
- Descripción de cada endpoint
- Request body con tipos y validaciones
- Response schemas
- Ejemplos

### 8.5 Comentarios: cuándo sí y cuándo no

**Regla del proyecto:** Comentar el PORQUÉ, no el QUÉ. Los nombres descriptivos hacen el QUÉ obvio.

```python
# MAL: el comentario no agrega información
# Get the course
course = Course.objects.get(slug=slug)

# BIEN: explica una decisión no obvia
# Use select_for_update to prevent double-attempt race condition
attempt = Attempt.objects.select_for_update().filter(...)

# BIEN: explica un workaround
# MD5 only for tests — real hashing is too slow for 500+ test cases
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
```

---

## 9. Tests unitarios con pytest

### 9.1 ¿Por qué tests?

Los tests verifican que el código funciona correctamente después de cada cambio. Sin tests, cada cambio puede romper algo sin que te enteres hasta producción.

**Nuestro objetivo:** 80% de cobertura de código (configurado en `setup.cfg`).

### 9.2 Configuración pytest

**Archivo:** `setup.cfg`

```ini
[tool:pytest]
DJANGO_SETTINGS_MODULE = config.settings.test   # usa SQLite, tareas síncronas
python_files = tests.py test_*.py *_tests.py
addopts = --reuse-db -v                         # reutiliza la BD entre runs (más rápido)
```

### 9.3 Fixtures: conftest.py

**Archivo:** `tests/conftest.py`

```python
@pytest.fixture(autouse=True)
def fast_isolated_tests(settings, mocker):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    mocker.patch("celery.app.task.Task.delay")  # no encola tareas reales en tests
```

`autouse=True` → aplica a TODOS los tests sin declararlos explícitamente.
`mocker.patch` → reemplaza `Task.delay` con un mock (fake), así los tests no intentan conectarse a Redis.

### 9.4 Factory Boy: datos de prueba

**Archivo:** `tests/factories.py`

Factory Boy genera objetos de prueba con datos realistas:

```python
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomUser

    email = factory.Sequence(lambda n: f"user{n}@example.com")  # email único
    full_name = factory.Faker("name")                           # nombre aleatorio
    role = Roles.STUDENT
    is_active = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "testpass123")
        self.save()
```

**Factories especializadas:**
```python
class InstructorFactory(UserFactory):
    role = Roles.INSTRUCTOR

class AdminFactory(UserFactory):
    role = Roles.ADMIN

class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course

    title = factory.Sequence(lambda n: f"Course {n}")
    instructor = factory.SubFactory(InstructorFactory)   # crea instructor automáticamente
    is_published = True
```

### 9.5 Estructura de un test

**Archivo:** `apps/core/tests/test_models.py`

```python
import pytest
from django.utils import timezone

@pytest.mark.django_db   # permite acceso a la BD en este test
class TestSoftDeleteModel:

    def test_soft_delete_sets_deleted_at(self, soft_delete_instance):
        """Soft delete should set deleted_at, not remove the row."""
        soft_delete_instance.delete()

        # El objeto sigue en BD
        assert ConcreteModel.all_objects.filter(pk=soft_delete_instance.pk).exists()
        # Pero objects.alive() no lo ve
        assert not ConcreteModel.objects.filter(pk=soft_delete_instance.pk).exists()
        # deleted_at fue seteado
        soft_delete_instance.refresh_from_db()
        assert soft_delete_instance.deleted_at is not None
```

**Patrón AAA (Arrange, Act, Assert):**
```python
def test_login_with_valid_credentials(self, client):
    # Arrange (preparar)
    user = UserFactory(email="test@example.com")
    user.set_password("secret123")
    user.save()

    # Act (ejecutar)
    response = client.post("/api/v1/auth/login/", {
        "email": "test@example.com",
        "password": "secret123",
    })

    # Assert (verificar)
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data
```

### 9.6 Ejecutar tests

```bash
# Todos los tests
pytest

# Tests de una app específica
pytest apps/users/

# Test específico por nombre
pytest -k test_soft_delete

# Con cobertura
coverage run -m pytest && coverage report

# Ver qué líneas no tienen cobertura
coverage html && open htmlcov/index.html

# Verbose con print output
pytest -v -s
```

### 9.7 Tipos de tests en el proyecto

| Tipo | Qué prueba | Ejemplo |
|------|-----------|---------|
| Unit test | Un modelo/función aislada | `test_soft_delete_sets_deleted_at` |
| API test | Un endpoint completo | `test_register_returns_201` |
| Integration test | Flujo completo | `test_enrollment_triggers_email` |

### 9.8 Fixtures de pytest

```python
@pytest.fixture
def admin_user():
    return AdminFactory()

@pytest.fixture
def auth_client(client, admin_user):
    client.force_login(admin_user)   # autenticar sin contraseña
    return client

# Uso en el test:
def test_admin_can_delete_course(auth_client, course):
    response = auth_client.delete(f"/api/v1/courses/{course.slug}/")
    assert response.status_code == 204
```

---

## 10. Celery y cola de tareas

### 10.1 ¿Qué es Celery y por qué lo usamos?

**Problema:** Enviar un email puede tardar 2-3 segundos. Si lo hacemos en la request, el usuario espera 3 segundos para registrarse.

**Solución:** Celery encola la tarea. La request responde inmediatamente (< 100ms), y Celery procesa el email en background.

**Arquitectura:**
```
Django API  →  Redis (broker)  →  Celery Worker  →  Email/Reporte
   (encola)      (cola)              (procesa)
```

### 10.2 Configuración

**Archivo:** `config/celery.py`

```python
app = Celery("insis")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()   # descubre tasks.py en todas las apps
```

**Archivo:** `config/settings/base.py`

```python
CELERY_BROKER_URL = config("REDIS_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://redis:6379/0")
CELERY_TASK_SERIALIZER = "json"
CELERY_TASK_TIME_LIMIT = 300        # 5 min hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 240   # 4 min soft limit (lanza SoftTimeLimitExceeded)
```

### 10.3 Definir una tarea

**Archivo:** `apps/notifications/tasks.py`

```python
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def send_welcome_email(self, user_id):
    try:
        user = CustomUser.objects.get(pk=user_id)
        # ... crear EmailNotification y enviar email
        _deliver(notification, body)
    except Exception as exc:
        # Reintento con backoff exponencial
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

`@shared_task` → la tarea no está atada a una app Celery específica (útil con multi-tenant).
`bind=True` → `self` es la instancia de la tarea (para acceder a `self.retry`).
`max_retries=3` → reintenta hasta 3 veces si falla.

### 10.4 Disparar una tarea

```python
# Async (encola en Redis, no bloquea)
send_welcome_email.delay(user.pk)

# Con countdown (encola para ejecutar en 60 segundos)
send_due_date_reminder.apply_async(countdown=60)

# Síncrono (solo en tests o debug)
send_welcome_email(user.pk)
```

### 10.5 Tareas periódicas (Celery Beat)

**Archivo:** `config/celery.py`

```python
app.conf.beat_schedule = {
    "inactivity-reminder": {
        "task": "apps.notifications.tasks.send_inactivity_reminder",
        "schedule": crontab(hour=9, minute=0),        # 09:00 todos los días
    },
    "weekly-progress-report": {
        "task": "apps.notifications.tasks.send_weekly_progress_report",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),  # Lunes 08:00
    },
    "monthly-company-report": {
        "task": "apps.notifications.tasks.generate_monthly_company_report",
        "schedule": crontab(hour=7, minute=0, day_of_month=1), # Día 1 del mes
    },
}
```

`celery_beat` (servicio Docker) ejecuta estas tareas según el schedule.

### 10.6 Fan-out: tareas en grupo

Para enviar emails a muchos usuarios a la vez:

```python
# apps/notifications/tasks.py — send_bulk_assignment_emails
@shared_task
def send_bulk_assignment_emails(assignment_id, department_id=None):
    records = CompletionRecord.objects.filter(
        assignment_id=assignment_id, ...
    )
    for record in records:
        send_assignment_notification.delay(record.pk)  # una tarea por empleado
```

Cada empleado recibe su email en paralelo, procesados por los workers disponibles.

### 10.7 Monitorear Celery

**Flower** (en Docker) → http://localhost:5556

Muestra:
- Tareas en cola, en proceso, completadas, fallidas
- Workers activos y su carga
- Historial de tareas con duración y resultado

### 10.8 Tareas en tests

En `config/settings/test.py`:
```python
CELERY_TASK_ALWAYS_EAGER = True  # ejecuta tareas síncronamente
```

Y en `conftest.py`:
```python
mocker.patch("celery.app.task.Task.delay")  # mock: no ejecuta nada
```

Usamos el mock para tests que no necesitan que la tarea se ejecute, y `ALWAYS_EAGER` para tests que sí necesitan verificar el resultado de la tarea.

---

## 11. Despliegue en Cloud Run

### 11.1 ¿Qué es Cloud Run?

Cloud Run es el servicio serverless de Google Cloud para contenedores. Características:
- Escala automáticamente (0 a N instancias según tráfico)
- Pagas solo cuando hay requests
- Cada deploy es el Dockerfile construido

### 11.2 Arquitectura de producción

```
Internet
    ↓
Cloud Load Balancer (HTTPS)
    ↓
Cloud Run (Django + Gunicorn, múltiples instancias)
    ├── Cloud SQL (MySQL 8.4, IP privada)
    ├── Memorystore Redis (broker Celery)
    ├── Cloud Storage (reportes, avatars)
    └── Secret Manager (variables sensibles)

Cloud Run Jobs (Celery Worker + Beat)
    → misma imagen Docker, diferente CMD
```

### 11.3 Settings de producción

**Archivo:** `config/settings/production.py`

```python
DEBUG = False

# Cloud SQL Auth Proxy (Unix socket — más rápido que TCP)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "HOST": f"/cloudsql/{config('CLOUD_SQL_CONNECTION_NAME')}",
        "NAME": config("DB_NAME"),
        ...
    }
}

# WhiteNoise: sirve archivos estáticos sin Nginx
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Seguridad HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# GCS para reportes
GCS_BUCKET_NAME = config("GCS_BUCKET_NAME", default="insis-reports")
```

### 11.4 Dockerfile para Cloud Run

Cloud Run requiere:
- Puerto 8080 (configurado en gunicorn)
- Usuario no-root (appuser)
- Variables de entorno vía Secret Manager

```dockerfile
# CMD en el Dockerfile
CMD ["gunicorn", "config.wsgi:application",
     "--bind", "0.0.0.0:8080",
     "--workers", "2",
     "--timeout", "120"]
```

Cloud Run inyecta `PORT=8080` y escala instancias automáticamente.

### 11.5 Variables de entorno en producción

Nunca hardcodeamos secrets. Cloud Run los inyecta desde Secret Manager:

```bash
# Crear secret en GCP
gcloud secrets create SECRET_KEY --data-file=-

# Montar en Cloud Run
gcloud run deploy insis-api \
  --set-secrets SECRET_KEY=SECRET_KEY:latest \
  --set-secrets DB_PASSWORD=DB_PASSWORD:latest
```

### 11.6 Gunicorn: servidor WSGI de producción

`runserver` de Django es para desarrollo. Gunicorn es el servidor de producción:
- **2 workers** (2 procesos paralelos)
- Maneja hasta N requests simultáneos por worker
- Timeout 120s para requests lentos (generación de reportes)

### 11.7 collectstatic

```bash
python manage.py collectstatic --noinput
```

Copia todos los archivos CSS/JS del admin a `STATIC_ROOT`. WhiteNoise los sirve directamente desde Gunicorn (sin Nginx).

### 11.8 Migraciones en producción

```bash
# Correr migraciones antes de cada deploy (en Cloud Build CI/CD)
gcloud run jobs execute migrate-job
```

El Dockerfile NO corre migraciones automáticamente (ver `entrypoint.sh`). Se corren explícitamente antes del deploy.

---

## 12. Colecciones Postman: todas las rutas

### 12.1 Configuración inicial en Postman

**Variables de entorno (crear un Environment "INSIS Local"):**

| Variable | Valor |
|----------|-------|
| `base_url` | `http://localhost:8081/api/v1` |
| `access_token` | *(se llena automáticamente)* |
| `refresh_token` | *(se llena automáticamente)* |

**Pre-request Script global (en la Collection):**
```javascript
// Agregar Authorization header automáticamente
if (pm.environment.get("access_token")) {
    pm.request.headers.add({
        key: "Authorization",
        value: "Bearer " + pm.environment.get("access_token")
    });
}
```

**Test script en Login (para guardar tokens automáticamente):**
```javascript
const json = pm.response.json();
pm.environment.set("access_token", json.access);
pm.environment.set("refresh_token", json.refresh);
```

---

### 12.2 Colección 1: Autenticación (`/api/v1/auth/`)

#### POST /auth/register/
```
URL: {{base_url}}/auth/register/
Method: POST
Body (JSON):
{
    "email": "estudiante@example.com",
    "password": "MiPassword123",
    "full_name": "Juan Pérez"
}
```
**Respuesta 201:**
```json
{
    "email": "estudiante@example.com",
    "full_name": "Juan Pérez"
}
```

#### POST /auth/login/
```
URL: {{base_url}}/auth/login/
Method: POST
Body (JSON):
{
    "email": "estudiante@example.com",
    "password": "MiPassword123"
}
```
**Respuesta 200:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```
> Pega el test script de la sección anterior aquí para guardar tokens.

#### POST /auth/token/refresh/
```
URL: {{base_url}}/auth/token/refresh/
Method: POST
Body (JSON):
{
    "refresh": "{{refresh_token}}"
}
```

#### GET /auth/me/
```
URL: {{base_url}}/auth/me/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```

#### PATCH /auth/me/
```
URL: {{base_url}}/auth/me/
Method: PATCH
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "full_name": "Juan Pérez Actualizado",
    "bio": "Desarrollador Python",
    "profile": {
        "phone": "+51999888777",
        "country": "PE"
    }
}
```

#### POST /auth/change-password/
```
URL: {{base_url}}/auth/change-password/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "current_password": "MiPassword123",
    "new_password": "NuevoPassword456"
}
```

#### POST /auth/logout/
```
URL: {{base_url}}/auth/logout/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "refresh": "{{refresh_token}}"
}
```

---

### 12.3 Colección 2: Empresas (`/api/v1/companies/`)

> Requiere rol ADMIN o HR_MANAGER.

#### POST /companies/ (crear empresa)
```
URL: {{base_url}}/companies/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "name": "Tech Corp S.A.C.",
    "ruc": "20123456789",
    "industry": "Tecnología",
    "website": "https://techcorp.pe"
}
```

#### GET /companies/ (listar empresas)
```
URL: {{base_url}}/companies/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```

#### GET /companies/{id}/ (detalle)
```
URL: {{base_url}}/companies/1/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```

#### GET /companies/{id}/stats/ (estadísticas)
```
URL: {{base_url}}/companies/1/stats/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```

#### POST /companies/{id}/departments/ (crear departamento)
```
URL: {{base_url}}/companies/1/departments/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "name": "Ingeniería de Software"
}
```

#### GET /companies/{id}/departments/ (listar departamentos)
```
URL: {{base_url}}/companies/1/departments/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```

---

### 12.4 Colección 3: Empleados (`/api/v1/employees/`)

#### POST /employees/ (crear empleado)
```
URL: {{base_url}}/employees/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "email": "empleado@techcorp.pe",
    "full_name": "Ana García",
    "company": 1,
    "department": 1,
    "is_hr_manager": false
}
```

#### GET /employees/ (listar empleados)
```
URL: {{base_url}}/employees/
Method: GET
Headers: Authorization: Bearer {{access_token}}
Query params: ?company=1
```

#### POST /employees/bulk-import/ (importación masiva CSV)
```
URL: {{base_url}}/employees/bulk-import/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (form-data):
  file: [archivo CSV con columnas: email, full_name, department, is_hr_manager]
  company: 1
```

---

### 12.5 Colección 4: Categorías y Tags

#### GET /categories/ (público, sin auth)
```
URL: {{base_url}}/categories/
Method: GET
```

#### POST /categories/ (solo ADMIN)
```
URL: {{base_url}}/categories/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "name": "Desarrollo Web",
    "description": "Cursos de frontend y backend",
    "is_active": true
}
```

#### GET /tags/
```
URL: {{base_url}}/tags/
Method: GET
```

#### POST /tags/
```
URL: {{base_url}}/tags/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "name": "Python"
}
```

---

### 12.6 Colección 5: Cursos (`/api/v1/courses/`)

#### GET /courses/ (listado público con filtros)
```
URL: {{base_url}}/courses/
Method: GET
Query params opcionales:
  ?level=BEGINNER
  ?category=1
  ?min_price=0&max_price=100
  ?tag=python
  ?is_free=true
  ?search=django
  ?language=es
```

#### POST /courses/ (crear curso — INSTRUCTOR/ADMIN)
```
URL: {{base_url}}/courses/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "title": "Django REST Framework desde cero",
    "description": "Aprende a construir APIs REST profesionales con Django",
    "category": 1,
    "tags": [1, 2],
    "price": "49.99",
    "level": "INTERMEDIATE",
    "language": "es",
    "is_published": false
}
```
**Nota:** el `slug` se genera automáticamente desde el título.

#### GET /courses/{slug}/ (detalle del curso)
```
URL: {{base_url}}/courses/django-rest-framework-desde-cero/
Method: GET
```

#### POST /courses/{slug}/lessons/ (agregar lección — dueño/ADMIN)
```
URL: {{base_url}}/courses/django-rest-framework-desde-cero/lessons/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "title": "Introducción a Django",
    "content": "En esta lección aprenderemos...",
    "video_url": "https://youtube.com/...",
    "order": 1,
    "duration_minutes": 25,
    "is_free": true,
    "is_published": true
}
```

#### GET /courses/{slug}/lessons/ (listar lecciones)
```
URL: {{base_url}}/courses/django-rest-framework-desde-cero/lessons/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```

#### POST /courses/{slug}/reviews/ (crear reseña — estudiante matriculado)
```
URL: {{base_url}}/courses/django-rest-framework-desde-cero/reviews/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "rating": 5,
    "comment": "Excelente curso, muy claro y práctico"
}
```

#### GET /courses/{slug}/quizzes/ (quizzes del curso)
```
URL: {{base_url}}/courses/django-rest-framework-desde-cero/quizzes/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```

---

### 12.7 Colección 6: Matrículas (`/api/v1/enrollments/`)

#### POST /enrollments/ (matricularse — STUDENT)
```
URL: {{base_url}}/enrollments/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "course": 1
}
```

#### GET /enrollments/ (mis matrículas)
```
URL: {{base_url}}/enrollments/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```

#### GET /enrollments/{id}/progress/ (progreso detallado)
```
URL: {{base_url}}/enrollments/1/progress/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```
**Respuesta:**
```json
{
    "total_lessons": 10,
    "completed_lessons": 3,
    "progress_pct": 30.0,
    "lessons": [
        {
            "lesson_id": 1,
            "title": "Introducción",
            "completed": true,
            "time_spent_seconds": 1500
        }
    ]
}
```

#### POST /enrollments/{id}/complete-lesson/ (marcar lección como completada)
```
URL: {{base_url}}/enrollments/1/complete-lesson/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "lesson_id": 1,
    "time_spent_seconds": 1500
}
```

#### GET /enrollments/my-certificates/ (certificados completados)
```
URL: {{base_url}}/enrollments/my-certificates/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```

---

### 12.8 Colección 7: Quizzes (`/api/v1/quizzes/`)

#### POST /quizzes/ (crear quiz — dueño del curso/ADMIN)
```
URL: {{base_url}}/quizzes/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "course": 1,
    "title": "Quiz: Fundamentos Django",
    "description": "Evalúa tus conocimientos básicos",
    "time_limit_minutes": 30,
    "max_attempts": 3,
    "passing_score": "70.00",
    "is_active": true
}
```

#### POST /quizzes/{id}/questions/ (agregar pregunta)
```
URL: {{base_url}}/quizzes/1/questions/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "text": "¿Qué es un ViewSet en DRF?",
    "type": "SINGLE",
    "order": 1,
    "points": 1,
    "options": [
        {"text": "Una clase que agrupa vistas CRUD", "is_correct": true, "order": 1},
        {"text": "Un tipo de modelo Django", "is_correct": false, "order": 2},
        {"text": "Una función decoradora", "is_correct": false, "order": 3}
    ]
}
```

#### POST /quizzes/{id}/start/ (iniciar intento)
```
URL: {{base_url}}/quizzes/1/start/
Method: POST
Headers: Authorization: Bearer {{access_token}}
```
**Respuesta:**
```json
{
    "attempt_id": 1,
    "attempt_number": 1,
    "started_at": "2026-05-04T10:00:00Z",
    "time_limit_minutes": 30
}
```

#### POST /quizzes/{id}/submit/ (enviar respuestas)
```
URL: {{base_url}}/quizzes/1/submit/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "attempt_id": 1,
    "answers": [
        {
            "question_id": 1,
            "selected_option_ids": [1]
        }
    ]
}
```
**Respuesta:**
```json
{
    "score": 85.5,
    "passed": true,
    "finished_at": "2026-05-04T10:15:00Z"
}
```

#### GET /quizzes/{id}/attempts/ (mis intentos)
```
URL: {{base_url}}/quizzes/1/attempts/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```

#### GET /quizzes/{id}/results/{attempt_id}/ (resultado detallado)
```
URL: {{base_url}}/quizzes/1/results/1/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```

#### GET /quizzes/{id}/stats/ (estadísticas del quiz — INSTRUCTOR/ADMIN)
```
URL: {{base_url}}/quizzes/1/stats/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```

---

### 12.9 Colección 8: Asignaciones B2B (`/api/v1/assignments/`)

#### POST /assignments/ (crear asignación — ADMIN/HR)
```
URL: {{base_url}}/assignments/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "course": 1,
    "company": 1,
    "scope": "COMPANY",
    "due_date": "2026-07-01T23:59:00Z",
    "is_mandatory": true
}
```

#### GET /assignments/ (listar asignaciones)
```
URL: {{base_url}}/assignments/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```

#### POST /assignments/{id}/assign-department/ (asignar a departamento)
```
URL: {{base_url}}/assignments/1/assign-department/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "department": 1
}
```

#### GET /assignments/{id}/targets/ (ver objetivos y completación)
```
URL: {{base_url}}/assignments/1/targets/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```

---

### 12.10 Colección 9: Reportes (`/api/v1/reports/`)

#### GET /reports/company-summary/ (resumen en tiempo real)
```
URL: {{base_url}}/reports/company-summary/
Method: GET
Headers: Authorization: Bearer {{access_token}}
Query params: ?company=1
```

#### GET /reports/completion-by-department/
```
URL: {{base_url}}/reports/completion-by-department/
Method: GET
Headers: Authorization: Bearer {{access_token}}
Query params: ?company=1
```

#### GET /reports/employee-ranking/
```
URL: {{base_url}}/reports/employee-ranking/
Method: GET
Headers: Authorization: Bearer {{access_token}}
Query params: ?company=1
```

#### GET /reports/overdue-assignments/
```
URL: {{base_url}}/reports/overdue-assignments/
Method: GET
Headers: Authorization: Bearer {{access_token}}
Query params: ?company=1
```

#### POST /reports/exports/ (generar reporte exportable)
```
URL: {{base_url}}/reports/exports/
Method: POST
Headers: Authorization: Bearer {{access_token}}
Body (JSON):
{
    "company": 1,
    "report_type": "company-summary",
    "file_format": "xlsx"
}
```
**Respuesta 202 (procesando):**
```json
{
    "id": 1,
    "status": "PENDING",
    "report_type": "company-summary",
    "file_format": "xlsx"
}
```

#### GET /reports/exports/{id}/ (verificar estado y obtener URL)
```
URL: {{base_url}}/reports/exports/1/
Method: GET
Headers: Authorization: Bearer {{access_token}}
```
**Respuesta cuando está listo:**
```json
{
    "id": 1,
    "status": "READY",
    "signed_url": "https://storage.googleapis.com/...",
    "signed_url_expires_at": "2026-05-04T11:00:00Z"
}
```

---

### 12.11 Flujo completo de prueba recomendado

Sigue este orden para probar el sistema completo:

```
1. Registro y login (guardar tokens)
   POST /auth/register/ → POST /auth/login/

2. Crear contenido (con cuenta de admin/instructor)
   POST /categories/ → POST /tags/ → POST /courses/ → POST /courses/{slug}/lessons/
   → POST /quizzes/ → POST /quizzes/{id}/questions/

3. Flujo de estudiante
   POST /enrollments/ → GET /enrollments/{id}/progress/
   → POST /enrollments/{id}/complete-lesson/ (repetir por cada lección)
   → GET /enrollments/my-certificates/ (verificar completación)

4. Flujo de quiz
   POST /quizzes/{id}/start/ → POST /quizzes/{id}/submit/
   → GET /quizzes/{id}/results/{attempt_id}/

5. Flujo corporativo B2B
   POST /companies/ → POST /companies/{id}/departments/
   → POST /employees/ → POST /assignments/ → POST /assignments/{id}/assign-department/
   → GET /assignments/{id}/targets/

6. Reportes
   GET /reports/company-summary/ → POST /reports/exports/
   → GET /reports/exports/{id}/ (polling hasta status=READY)
```

### 12.12 Swagger interactivo

Abre en tu navegador: **http://localhost:8081/api/schema/swagger-ui/**

El Swagger permite:
- Ver todos los endpoints documentados
- Probar directamente con "Try it out"
- Ver los schemas de request/response
- Autenticarte con JWT (botón "Authorize")

---

## Resumen de conceptos clave

| Concepto | Dónde verlo en el código |
|----------|--------------------------|
| Abstract models | `apps/core/models.py` |
| CustomUser + Manager | `apps/users/models.py` |
| ViewSet + Router | `apps/courses/urls.py`, `apps/courses/views.py` |
| @action personalizado | `apps/quizzes/views.py` (start, submit, results) |
| Serializer anidado | `apps/users/serializers.py` (UserSerializer + profile) |
| Permissions custom | `apps/users/permissions.py`, `apps/companies/permissions.py` |
| ORM Annotations | `apps/courses/views.py` (CourseViewSet.get_queryset) |
| select_for_update | `apps/quizzes/views.py` (start action) |
| get_or_create | `apps/assignments/tasks.py` |
| Signals | `apps/users/signals.py`, `apps/enrollments/signals.py` |
| Celery task | `apps/notifications/tasks.py` |
| Celery beat | `config/celery.py` |
| Factory Boy | `tests/factories.py` |
| pytest fixtures | `tests/conftest.py` |
| Settings split | `config/settings/{base,local,production,test}.py` |
| Docker multi-stage | `Dockerfile` |
| Cloud Run config | `config/settings/production.py` |
