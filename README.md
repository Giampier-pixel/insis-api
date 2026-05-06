# INSIS API

Backend REST para plataforma EdTech B2B/B2C. Django 5.2 + DRF + MySQL + Celery, desplegado en Google Cloud Run.

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Framework | Django 5.2 + Django REST Framework 3.16 |
| Base de datos | MySQL 8 (local Docker / Cloud SQL en prod) |
| Auth | JWT via `djangorestframework-simplejwt` |
| Cola de tareas | Celery 5.6 + Redis |
| Documentación | drf-spectacular (OpenAPI 3) |
| Deploy | Google Cloud Run + Artifact Registry |
| Archivos | Google Cloud Storage |

---

## Setup local

```bash
# 1. Clonar e instalar dependencias
git clone <repo>
cd insis-api
cp .env.example .env          # Editar con tus valores locales

# 2. Levantar todos los servicios (web, db, redis, celery, flower)
docker-compose up --build

# 3. En otra terminal: aplicar migraciones
docker-compose exec web python manage.py migrate

# 4. Crear superusuario
docker-compose exec web python manage.py createsuperuser
```

Servicios disponibles:
- API: http://localhost:8081
- Swagger UI: http://localhost:8081/api/schema/swagger-ui/
- Admin: http://localhost:8081/admin/
- Flower (Celery): http://localhost:5556

---

## Comandos de desarrollo

```bash
# Tests
pytest
pytest apps/users/
pytest -k test_login
coverage run -m pytest && coverage report

# Lint y formato
flake8 apps/
black apps/
isort apps/

# Migraciones
docker-compose exec web python manage.py makemigrations <app>
docker-compose exec web python manage.py migrate
```

---

## Deploy en Google Cloud Run

### Variables de entorno requeridas

| Variable | Descripción |
|----------|-------------|
| `GCLOUD` | `/home/giampier/google/google-cloud-sdk/bin/gcloud` |
| `PROJECT_ID` | `inisis-api` |
| `REGION` | `us-central1` |
| `ACCOUNT` | `alejandroesquivelpaucar@gmail.com` |
| `IMAGE` | `us-central1-docker.pkg.dev/inisis-api/insis-repo/insis-api:latest` |

Puedes exportarlas al inicio de cada sesión:

```bash
export GCLOUD=/home/giampier/google/google-cloud-sdk/bin/gcloud
export PROJECT_ID=inisis-api
export REGION=us-central1
export ACCOUNT=alejandroesquivelpaucar@gmail.com
export IMAGE=us-central1-docker.pkg.dev/inisis-api/insis-repo/insis-api:latest
```

---

### Redeploy completo (cuando hay cambios en el código)

```bash
# 1. Autenticarse (solo si es una sesión nueva)
$GCLOUD auth login --account=$ACCOUNT
$GCLOUD config set project $PROJECT_ID

# 2. Configurar Docker para Artifact Registry (solo primera vez por máquina)
$GCLOUD auth configure-docker us-central1-docker.pkg.dev --account=$ACCOUNT

# 3. Build de la imagen
docker build -t $IMAGE .

# 4. Push a Artifact Registry
docker push $IMAGE

# 5. Ejecutar migraciones (si hubo cambios en modelos)
$GCLOUD run jobs update migrate-job \
  --image=$IMAGE \
  --region=$REGION \
  --account=$ACCOUNT \
  --project=$PROJECT_ID

$GCLOUD run jobs execute migrate-job \
  --region=$REGION \
  --wait \
  --account=$ACCOUNT \
  --project=$PROJECT_ID

# 6. Deploy a Cloud Run
$GCLOUD run deploy insis-api \
  --image=$IMAGE \
  --region=$REGION \
  --account=$ACCOUNT \
  --project=$PROJECT_ID
```

---

### Solo redeploy sin migraciones (cambios de código sin modelos)

```bash
docker build -t $IMAGE . && \
docker push $IMAGE && \
$GCLOUD run deploy insis-api \
  --image=$IMAGE \
  --region=$REGION \
  --account=$ACCOUNT \
  --project=$PROJECT_ID
```

---

### Ver logs en tiempo real

```bash
$GCLOUD logging tail \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="insis-api"' \
  --account=$ACCOUNT \
  --project=$PROJECT_ID
```

---

### Gestión de secrets

```bash
# Ver secrets existentes
$GCLOUD secrets list --project=$PROJECT_ID --account=$ACCOUNT

# Actualizar un secret (ej: nueva SECRET_KEY)
echo -n "nuevo-valor" | $GCLOUD secrets versions add SECRET_KEY \
  --data-file=- --project=$PROJECT_ID --account=$ACCOUNT

# Ver versión activa de un secret
$GCLOUD secrets versions access latest --secret=SECRET_KEY \
  --project=$PROJECT_ID --account=$ACCOUNT
```

---

### Gestión de Cloud SQL

```bash
# Ver estado de la instancia
$GCLOUD sql instances describe insis-db \
  --project=$PROJECT_ID --account=$ACCOUNT

# Conectarse a la DB (requiere Cloud SQL Auth Proxy o IP autorizada)
$GCLOUD sql connect insis-db --user=insisuser \
  --project=$PROJECT_ID --account=$ACCOUNT
```

---

### Monitorear el servicio

```bash
# URL del servicio
$GCLOUD run services describe insis-api \
  --region=$REGION --format='value(status.url)' \
  --project=$PROJECT_ID --account=$ACCOUNT

# Ver revisiones desplegadas
$GCLOUD run revisions list --service=insis-api \
  --region=$REGION \
  --project=$PROJECT_ID --account=$ACCOUNT

# Escalar a 0 instancias (para no gastar créditos)
$GCLOUD run services update insis-api \
  --min-instances=0 \
  --region=$REGION \
  --project=$PROJECT_ID --account=$ACCOUNT
```

---

### CI/CD automático con Cloud Build (opcional)

Para activar deploy automático en cada `git push` a `main`:

```bash
# Habilitar Cloud Build API (ya habilitada)
# Conectar el repositorio GitHub desde la consola:
# https://console.cloud.google.com/cloud-build/triggers?project=inisis-api
# Crear trigger: Branch = main, Config = cloudbuild.yaml
```

El archivo `cloudbuild.yaml` en la raíz del proyecto ya tiene los steps configurados:
`build → push → migrate → deploy`

---

## Infraestructura GCP

| Recurso | Nombre | Región |
|---------|--------|--------|
| Cloud Run | `insis-api` | `us-central1` |
| Cloud SQL MySQL 8 | `insis-db` | `us-central1` |
| Artifact Registry | `insis-repo` | `us-central1` |
| GCS Bucket | `insis-reports` | `us-central1` |
| Proyecto | `inisis-api` | — |

**URL de producción:** `https://insis-api-569731688530.us-central1.run.app`

**Swagger UI:** `https://insis-api-569731688530.us-central1.run.app/api/schema/swagger-ui/`

---

## Estructura del proyecto

```
insis-api/
├── apps/
│   ├── core/          # Mixins base: TimestampedModel, SoftDeleteModel
│   ├── users/         # Auth JWT, roles, perfiles
│   ├── companies/     # Empresas, departamentos, empleados (B2B)
│   ├── courses/       # Cursos, lecciones, categorías, reviews
│   ├── enrollments/   # Inscripciones, progreso, certificados
│   ├── quizzes/       # Evaluaciones, intentos, calificaciones
│   ├── assignments/   # Asignaciones B2B por empresa/departamento
│   ├── reports/       # Exportaciones asíncronas a GCS
│   └── notifications/ # Tasks Celery para emails
├── config/
│   ├── settings/
│   │   ├── base.py       # Configuración compartida
│   │   ├── local.py      # Desarrollo local (Docker)
│   │   └── production.py # Cloud Run + Cloud SQL + GCS
│   ├── celery.py
│   └── urls.py
├── tests/
│   ├── conftest.py
│   └── factories.py
├── cloudbuild.yaml    # CI/CD pipeline
├── Dockerfile         # Multi-stage build
├── docker-compose.yml # Entorno local completo
└── requirements.txt
```

---

## Links

- PRD completo: `PRD_INSIS_API.md`
- Roadmap de seguridad: `Security_future.md`
- Tareas pendientes: `TODO.md`
