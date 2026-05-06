# F3 - Integridad y Documentacion

## Migraciones

Las migraciones de F3 cubren todos los apps activos:

- `core`: modelos abstractos, sin migraciones propias.
- `users`: `CustomUser` y `UserProfile`.
- `companies`: `Company`, `Department`, `Employee`.
- `courses`: cursos, lecciones, reviews y migracion de nombres de indices.
- `enrollments`: inscripciones, progreso y enlace B2B a assignments.
- `quizzes`: quizzes, preguntas, opciones, intentos y respuestas.
- `assignments`: asignaciones B2B y registros de completacion.
- `reports`: `ReportExportJob`.
- `notifications`: `EmailNotification`.

Comandos de verificacion local:

```bash
DB_HOST=127.0.0.1 DB_PORT=3308 .venv/bin/python manage.py makemigrations --check --dry-run
DB_HOST=127.0.0.1 DB_PORT=3308 .venv/bin/python manage.py migrate
```

## Constraints

Constraints activos:

- `Quiz.passing_score`: CHECK `0 <= passing_score <= 100`.
- `CourseAssignment.scope`: CHECK para `COMPANY`, `DEPARTMENT`, `INDIVIDUAL`.
- `CourseReview.rating`: CHECK `1 <= rating <= 5`.
- Unicos relacionales: `Enrollment(student, course)`, `Attempt(quiz, student, attempt_number)`, `AttemptAnswer(attempt, question)`, `AssignmentTarget(assignment, employee)`, `CompletionRecord(employee, assignment)`, `Employee(user, company)`, `Department(company, name)`.

Nota de motor: el proyecto usa MySQL 8.4. MySQL no soporta indices unicos parciales con `Q(deleted_at__isnull=True)` como PostgreSQL. Por eso los campos unicos actuales son globales y los modelos con soft-delete evitan reutilizar la misma clave natural tras borrar logicamente un registro. Si se requiere reutilizacion de claves en registros soft-deleted, la alternativa en MySQL es un indice compuesto con una columna generada o una regla de aplicacion transaccional.

## OpenAPI

Rutas:

- `/api/schema/`
- `/api/schema/swagger-ui/`
- `/api/schema/redoc/`

La documentacion se genera con `drf-spectacular`. Los custom actions criticos tienen schemas explicitos:

- `POST /api/v1/quizzes/{id}/start/`
- `POST /api/v1/quizzes/{id}/submit/`
- `POST /api/v1/enrollments/{id}/complete-lesson/`

Comando de verificacion:

```bash
DB_HOST=127.0.0.1 DB_PORT=3308 .venv/bin/python manage.py spectacular --file /tmp/insis-schema.yml --validate
```
