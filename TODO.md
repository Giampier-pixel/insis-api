# INSIS API — To-Do List

> Camino crítico: #9 → #10 → #11 → #12 → #14 → #15 → #16 → #17 → #19 → #20 → #22 → #23 → #24 → #26 → #27 → #30

---

## F1 — Fundación

- [x] **#9 · Setup inicial del proyecto**
  - `django-admin startproject config`, split settings (`base` / `local` / `production`)
  - `requirements.txt` + `requirements-dev.txt` con todas las libs del PRD
  - `setup.cfg` (flake8 / pytest / coverage), `.gitignore`, `manage.py` funcionando

- [x] **#10 · Docker y orquestación local** *(depende de #9)*
  - `docker-compose.yml` con 6 servicios: `web`, `db` (MySQL 8.4), `redis` (8), `celery_worker`, `celery_beat`, `flower`
  - `Dockerfile` multi-stage, usuario no-root, `collectstatic` en build-time
  - `entrypoint.sh` **sin** `migrate`, healthchecks de db y redis
  - Verificar `docker-compose up --build` levanta todo limpio

---

## F2 — Apps Django

- [ ] **#11 · App `core` — mixins base** *(depende de #10)*
  - `TimestampedModel`, `SoftDeleteModel` + `SoftDeleteManager` + `SoftDeleteQuerySet`, `TenantScopedModel`
  - Modelos abstract (sin migraciones propias), tests unitarios de los managers

- [ ] **#12 · App `users` — auth JWT** *(depende de #11)*
  - `CustomUser` con email único normalizado a lower, roles `STUDENT / INSTRUCTOR / ADMIN / HR_MANAGER / SUPPORT`
  - `UserProfile` OneToOne
  - Endpoints: `register`, `login`, `refresh`, `logout` (blacklist), `me` (GET/PATCH), `change-password`
  - Permission classes: `IsInstructor`, `IsAdmin`, `IsStudent`, `IsHRManager`
  - Signal `post_save` → `send_welcome_email`

- [ ] **#13 · App `companies` — B2B base** *(depende de #12)*
  - Modelos: `Company` (`ruc` unique), `Department`, `Employee` con `is_hr_manager` + FK `PROTECT` a `User`
  - Permission `IsHRManagerOfCompany` con validación de tenancy
  - Endpoints CRUD scoped por empresa

- [ ] **#14 · App `courses`** *(depende de #12)*
  - Modelos: `Category`, `Tag`, `Course` (`price` Decimal, `slug` unique global, `instructor` PROTECT), `Lesson`, `CourseReview` (FK obligatoria a `Enrollment` + UNIQUE `(course, student)`)
  - Filters con `django-filter`
  - Endpoints CRUD con permisos por rol
  - Anotaciones: `enrolled_count`, `avg_rating`, `lesson_count`

- [ ] **#15 · App `enrollments`** *(depende de #14)*
  - `Enrollment` con `source` DIRECT/B2B_ASSIGNMENT, FK opcional a `CourseAssignment`, `notified_completion_at`
  - `LessonProgress` con UNIQUE `(enrollment, lesson)`
  - Endpoints: inscribir, listar, `complete-lesson` (update atómico de `notified_completion_at`), `progress`, `my-certificates`
  - Signals: `post_save` Enrollment → confirmación; `post_save` LessonProgress → check completación

- [ ] **#16 · App `quizzes` — motor de evaluaciones** *(depende de #15)*
  - Modelos: `Quiz` (`clean()` valida `lesson.course == quiz.course`), `Question`, `Option`, `Attempt` (`notified_at` persistido + UNIQUE `(quiz, student, attempt_number)`), `AttemptAnswer` con `points_earned`
  - `graders.py` con `grade_attempt()`
  - Endpoints: `detail` (oculta `is_correct` para students), `start` (`transaction.atomic` + `select_for_update`), `submit` (valida `time_limit`), `attempts`, `results`, `stats`
  - Signal `Attempt` finished con update atómico de `notified_at`

- [ ] **#17 · App `assignments` — asignaciones B2B** *(depende de #13 y #15)*
  - Modelos: `CourseAssignment` con `scope` COMPANY/DEPARTMENT/INDIVIDUAL + CHECK constraint, `AssignmentTarget` (intermedia), `CompletionRecord` OneToOne a target con `company_id` denormalizado
  - Task Celery `materialize_assignment_targets`: crea targets + Enrollments con `source=B2B_ASSIGNMENT`
  - Signal: cuando `Enrollment.completed=True` → actualizar `CompletionRecord`
  - Endpoints: crear, asignar a departamento, listar con % global, cancelar

- [ ] **#18 · App `notifications` — Celery tasks** *(depende de #12)*
  - Modelo `EmailNotification` con `body_template` + `context` JSON, `status` PENDING/SENT/FAILED
  - 11 tasks: `welcome`, `enrollment_confirmation`, `lesson_completed`, `course_completion`, `quiz_result`, `assignment_notification`, `bulk_assignment`, `due_date_reminder`, `inactivity_reminder`, `weekly_progress_report`, `generate_monthly_company_report`
  - Celery Beat con crontab (diario 9:00, lunes 8:00, día 1 7:00)

- [ ] **#19 · App `reports` — asíncronos** *(depende de #17 y #18)*
  - Modelo `ReportExportJob` (PENDING/RUNNING/READY/FAILED, `gcs_object_path`)
  - Endpoints: `POST /reports/exports/` crea job + dispara Celery; `GET /reports/exports/{id}/` retorna status + signed URL si READY
  - `exporters.py`: CSV streaming + Excel multi-hoja con openpyxl
  - Reportes: `company-summary`, `completion-by-department`, `employee-ranking`, `overdue-assignments`
  - Subida a GCS con TTL 30 min en signed URL

---

## F3 — Integridad y Documentación

- [ ] **#20 · Migraciones consolidadas y verificadas** *(depende de #19)*
  - `makemigrations` en orden: `core → users → companies → courses → enrollments → quizzes → assignments → reports → notifications`
  - Verificar CHECK constraints (`Quiz.passing_score`, `CourseAssignment.scope`, `CourseReview.rating`)
  - Verificar UNIQUE parciales con `Q(deleted_at__isnull=True)`
  - Probar `migrate` y rollback en MySQL local

- [ ] **#21 · Documentación OpenAPI con drf-spectacular** *(depende de #20)*
  - Config en settings, `/api/schema/`, `/api/schema/swagger-ui/`, `/api/schema/redoc/`
  - Docstrings en cada ViewSet, schemas explícitos para endpoints custom (`start`, `submit`, `complete-lesson`)
  - Tags por módulo, verificar que Swagger renderiza correctamente

---

## F4 — Calidad

- [ ] **#22 · Factories centralizadas** *(depende de #20)*
  - `tests/factories.py` con factory-boy: `UserFactory`, `InstructorFactory`, `HRManagerFactory`, `CategoryFactory`, `CourseFactory`, `LessonFactory`, `EnrollmentFactory`, `QuizFactory`, `QuestionFactory`, `OptionFactory`, `AttemptFactory`, `CompanyFactory`, `EmployeeFactory`, `CourseAssignmentFactory`, `AssignmentTargetFactory`

- [ ] **#23 · Tests por app — target ≥ 80% coverage** *(depende de #22)*
  - Por app: `test_models` (constraints, soft-delete, métodos), `test_views` (endpoints + permisos por rol), `test_signals` (mock Celery)
  - Casos específicos: graders (100%, 0%, parcial, multiple choice), `max_attempts` en concurrencia, `time_limit` excedido, `materialize_assignment_targets` crea N enrollments, `CompletionRecord` se actualiza al completar, multi-tenancy (HR de empresa A no ve empresa B)

- [ ] **#24 · Lint y formato CI-ready** *(depende de #23)*
  - `flake8 apps/` sin errores, `black apps/` aplicado, `isort` compatible
  - `coverage report --fail-under=80`

---

## F5 — Deploy Cloud Run

- [ ] **#25 · Provisionar GCP**
  - Cloud SQL MySQL 8.4 (private IP), Memorystore Redis 8, bucket GCS `insis-reports` con lifecycle 30 días
  - Service Account con permisos mínimos (`cloudsql.client`, `secretmanager.secretAccessor`, `storage.objectAdmin`)
  - Secret Manager: `django-secret`, `db-password`, `smtp-password`
  - VPC Connector para acceso privado a Cloud SQL y Memorystore

- [ ] **#26 · cloudbuild.yaml + deploy a Cloud Run** *(depende de #24 y #25)*
  - Steps: `build → push → migrate (Cloud Run Job) → deploy`
  - Cloud Run con 1Gi memoria, Cloud SQL Auth Proxy via socket Unix, secrets de Secret Manager
  - Trigger en push a `main`

- [ ] **#27 · Smoke tests post-deploy** *(depende de #26)*
  - Curl contra dominio Cloud Run: `/health/`, `/api/schema/`, `register`, `courses`
  - Verificar estáticos (Django Admin con CSS via WhiteNoise)
  - Verificar Celery worker conecta a Memorystore
  - Generación de reporte completo end-to-end

---

## F6 — Documentación y Demo

- [ ] **#28 · README del repositorio** *(depende de #20)*
  - Descripción, stack, requisitos, setup local (`clone → cp .env.example → docker-compose up`), comandos rápidos, estructura del proyecto, links a PRD y Security_future.md

- [ ] **#29 · Seed de datos demo** *(depende de #20, opcional)*
  - Management command `seed_demo`: 1 admin, 2 instructores, 1 empresa con 3 departamentos, 10 empleados (1 HR Manager), 5 categorías, 8 cursos publicados (5 lecciones c/u), 2 quizzes con preguntas, 1 asignación corporativa activa

---

## F7 — Seguridad pre-prod

- [ ] **#30 · Aplicar fase pre-prod de Security_future.md** *(depende de #27)*
  - Aplicar los 7 items 🔴 bloqueantes antes de exponer la API a usuarios reales:
    `ALLOWED_HOSTS` real, HTTPS hardening, throttling auth, mass assignment fix, ocultar `is_correct`, password validators, JWT hardening, todo en Secret Manager
  - Ver roadmap completo en `Security_future.md`
