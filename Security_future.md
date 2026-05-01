# 🛡️ Security_future — INSIS API

> **Estado:** pendiente / fase posterior
> **Alcance:** todo lo relacionado a seguridad (hardening, autenticación avanzada, compliance, observabilidad de seguridad) que se difiere para iteraciones posteriores al MVP.
> **Decisión:** el equipo prioriza correctness de modelos y operativa Cloud Run para empezar a codear. La seguridad se aborda como un track paralelo posterior, **antes de exponer la API a clientes reales**.

---

## 1. Vulnerabilidades Críticas (deben resolverse antes de producción real)

### 1.1 `ALLOWED_HOSTS = ['*']` en producción
**Riesgo:** Host header injection, password reset poisoning, cache poisoning.
**Mitigación:**
```python
# config/settings/production.py
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())
# Ej.: ALLOWED_HOSTS=insis-api-xxxxx-uc.a.run.app,api.insis.com
```
Establecer la variable como secret en Cloud Run, **nunca** dejar `*`.

### 1.2 Falta de hardening HTTPS / cookies
Agregar a `production.py`:
```python
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # Cloud Run termina TLS upstream
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
```

### 1.3 Sin throttling / rate limiting
Cualquiera puede martillar `/auth/login/` y `/auth/register/` indefinidamente.
**Mitigación:** DRF throttling por endpoint sensible:
```python
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "1000/hour",
        "login": "5/min",
        "register": "3/hour",
        "password_reset": "3/hour",
    },
}
```
Aplicar `throttle_classes` específicos en views de auth.

### 1.4 Mass assignment en `RegisterSerializer`
Riesgo: usuario se auto-asigna `role=ADMIN` durante registro.
**Mitigación:**
```python
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "password", "full_name"]  # role NUNCA acá
        extra_kwargs = {"password": {"write_only": True}}
```
Lista blanca explícita; el rol se asigna server-side con valor fijo `STUDENT`.

### 1.5 Quiz: fuga de `is_correct` en respuestas de la API
Riesgo: estudiante hace `GET /quizzes/{id}/` y recibe `Option.is_correct=true/false` → ve respuestas correctas antes de responder.
**Mitigación:**
```python
class OptionStudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["id", "text", "order"]  # SIN is_correct

class OptionInstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["id", "text", "is_correct", "order"]
```
Switch por rol en el view; tests que verifiquen explícitamente que el campo no aparece en respuestas a estudiantes.

### 1.6 Política de contraseñas
Activar en `base.py`:
```python
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
```

### 1.7 JWT: configuración endurecida
```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
}
```
Logout siempre debe blacklistear el refresh token (ya planeado en endpoint).

---

## 2. Vulnerabilidades Medias

### 2.1 Validación de uploads (`avatar`, `thumbnail`)
- Validar `Content-Type` y extensión.
- Limitar tamaño (`FILE_UPLOAD_MAX_MEMORY_SIZE`, `DATA_UPLOAD_MAX_MEMORY_SIZE`).
- Re-encodear imágenes con Pillow para sanitizar metadata y prevenir polyglots.
- Servir desde GCS con `Content-Disposition: attachment` para evitar render inline de SVG malicioso.
- Considerar escaneo de malware (Cloud Storage + Cloud Functions con ClamAV) si se permite cualquier archivo.

### 2.2 Bulk import CSV (`/employees/bulk-import/`)
- Limitar tamaño del archivo (ej. 5 MB / 10k filas).
- Validar headers contra whitelist.
- Sanitizar campos para prevenir **CSV injection** al re-exportar (prefijo `'` en valores que empiecen con `=`, `+`, `-`, `@`).
- Procesar en Celery, no sincrónicamente.

### 2.3 CORS
Sin config explícita Django no responde CORS. Frontend SPA fallará.
```python
# requirements: django-cors-headers
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", cast=Csv())
CORS_ALLOW_CREDENTIALS = True
```
Whitelist explícito por entorno. **Nunca** `CORS_ALLOW_ALL_ORIGINS=True` en prod.

### 2.4 Email injection
`EmailNotification.body_template + context` debe rendear con `select_template` y escape automático. Evitar concatenación de strings con input de usuario en headers.

### 2.5 Falta de auditoría
B2B exige trazabilidad de cambios sensibles (cambios de plan, asignaciones, cambios de rol HR).
- Usar `django-simple-history` en modelos críticos: `Company`, `Employee`, `CourseAssignment`, `User` (cambios de role).
- Log estructurado con `request_id`, `user_id`, `tenant_id` en todas las acciones de write.

### 2.6 Sin 2FA
Para cuentas con `role=ADMIN` o `Employee.is_hr_manager=True` debería ser obligatorio.
**Stack sugerido:** `django-otp` + `django-two-factor-auth` o TOTP custom con Authenticator apps.

---

## 3. Compliance & Privacidad

### 3.1 GDPR / LOPD
- Endpoint para que un usuario solicite exportación de sus datos (right to access).
- Endpoint para borrado de cuenta (right to erasure) → soft-delete + anonimización (no borrado real por requisitos académicos del módulo B2B).
- Política de retención: `ReportExportJob` con TTL 30 días, attempts y enrollments según política del cliente B2B.
- Aviso de procesamiento de datos en registro.

### 3.2 PII en logs y emails
- Nunca loggear `password`, `refresh_token`, `access_token`.
- `EmailNotification` guarda template + context (no body renderizado), evita PII en texto plano persistido (ya aplicado en sección 4.6 del PRD).
- Sanitizar excepciones antes de enviarlas a Sentry.

### 3.3 Encriptación at-rest
- Cloud SQL: usar Customer-Managed Encryption Keys (CMEK) si el cliente lo exige.
- GCS: misma recomendación para reportes exportados.
- Considerar campos cifrados a nivel ORM para datos sensibles del empleado (`hire_date`, `job_title`) si aplica.

---

## 4. Hardening de Infraestructura

### 4.1 Cloud Run
- Cambiar `--allow-unauthenticated` a IAM-restricted donde sea posible. Para endpoints públicos, exponer detrás de Cloud Armor (WAF + rate limiting + bot management).
- VPC Connector para tráfico privado a Cloud SQL (en lugar de Auth Proxy directo si se requiere mayor aislamiento).
- Service Account dedicado con permisos mínimos (solo `cloudsql.client`, `secretmanager.secretAccessor`, `storage.objectAdmin` sobre el bucket de reportes).
- Habilitar **Binary Authorization** para que solo se desplieguen imágenes firmadas.

### 4.2 Cloud SQL
- Backups automáticos diarios + Point-in-Time Recovery 7 días.
- Instancia en red privada (private IP).
- Usuario de aplicación distinto al `root`, con permisos solo sobre la BD `insis_db`.
- Rotación automática de password vía Secret Manager + Cloud Function.

### 4.3 Secret Manager
Todos los secretos (`SECRET_KEY`, `DB_PASSWORD`, `EMAIL_HOST_PASSWORD`, futuros `STRIPE_KEY`) deben vivir en Secret Manager y montarse vía `--set-secrets`. Nunca en `--set-env-vars` en texto plano.

### 4.4 Imagen Docker
- Usuario no-root (`USER app`) — ya aplicado en sección 9.2 del PRD.
- Imagen base `python:3.13-slim` reescaneada periódicamente (Trivy / Grype).
- `pip install` con hash pinning (`pip-tools` o `pip-compile --generate-hashes`) para evitar dependency confusion.
- Build reproducible con `SOURCE_DATE_EPOCH`.

---

## 5. Observabilidad de Seguridad

### 5.1 Logging estructurado
- JSON logs con `python-json-logger`.
- Campos obligatorios: `timestamp`, `level`, `request_id`, `user_id`, `tenant_id`, `path`, `method`, `status`, `latency_ms`.
- Eventos de seguridad explícitos: `auth.login.success`, `auth.login.failure`, `auth.password.change`, `permission.denied`, `assignment.created`, `role.changed`.

### 5.2 Métricas y alertas
- Cloud Monitoring: alertas en spikes de 401/403 (ataque de fuerza bruta).
- Alerta en exceso de `auth.login.failure` por IP en ventana de 5 minutos.
- Alerta en errores 5xx > 1% sostenido.

### 5.3 Detección de anomalías
- Tracking de "device fingerprint" en login (User-Agent + IP geo) para alertar al usuario sobre login desde nuevo dispositivo/país.
- Detección de exfiltración: descarga masiva de empleados o reportes desde una cuenta fuera de patrón normal.

---

## 6. Pentesting y Code Review

Antes de exponer la API a clientes reales:
1. **Pentesting externo** sobre staging que replique production al 100%.
2. **Code review de seguridad** enfocado en:
   - Permission classes y multi-tenancy (verificar que ningún queryset retorne datos de otro tenant).
   - Serializers: verificar campos `read_only` y `write_only` en cada uno.
   - Signals: verificar que no haya leak de información en post_save.
3. **Static analysis:** `bandit`, `semgrep` con ruleset Django.
4. **Dependency audit:** `pip-audit`, `safety check` en CI.
5. **Threat modeling** del módulo B2B con foco en:
   - Privilege escalation: ¿puede un Employee convertirse en HR Manager solo?
   - Tenant escape: ¿algún endpoint retorna IDs de otra empresa?
   - IDOR (Insecure Direct Object Reference) en endpoints `/{id}/` — verificar permission por objeto, no solo por rol.

---

## 7. Roadmap Sugerido (post-MVP)

| Fase | Item | Prioridad |
|---|---|---|
| **Pre-prod** | 1.1 ALLOWED_HOSTS | 🔴 bloqueante |
| **Pre-prod** | 1.2 HTTPS hardening | 🔴 bloqueante |
| **Pre-prod** | 1.3 Throttling auth | 🔴 bloqueante |
| **Pre-prod** | 1.4 Mass assignment fix | 🔴 bloqueante |
| **Pre-prod** | 1.5 Ocultar `is_correct` | 🔴 bloqueante |
| **Pre-prod** | 1.6 Password validators | 🔴 bloqueante |
| **Pre-prod** | 1.7 JWT hardening | 🔴 bloqueante |
| **Pre-prod** | Secret Manager para todo | 🔴 bloqueante |
| **Post-MVP v1** | 2.1 Validación de uploads | 🟡 alta |
| **Post-MVP v1** | 2.2 Bulk import seguro | 🟡 alta |
| **Post-MVP v1** | 2.3 CORS configurado | 🟡 alta |
| **Post-MVP v1** | 2.5 Auditoría con simple-history | 🟡 alta |
| **Post-MVP v2** | 2.6 2FA para Admin/HR | 🟢 media |
| **Post-MVP v2** | 3.1 GDPR endpoints | 🟢 media |
| **Post-MVP v2** | 4.1 Cloud Armor + IAM | 🟢 media |
| **Post-MVP v2** | 5.1-5.3 Observabilidad | 🟢 media |
| **Antes de cliente real** | 6. Pentesting externo | 🔴 bloqueante |
