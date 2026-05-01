# ============================================================
# INSIS API — Dockerfile
# ============================================================
# Multi-stage build: instala deps → copia código → entrypoint
# Usuario no-root para seguridad en producción
# ============================================================

FROM python:3.13-slim AS base

# Evitar prompts y buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# --- Dependencias del sistema para mysqlclient ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    gcc \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# --- Instalar dependencias Python ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copiar código ---
COPY . .

# --- Collectstatic en build-time ---
RUN SECRET_KEY=build-placeholder \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    DB_NAME=x DB_USER=x DB_PASSWORD=x DB_HOST=x \
    ALLOWED_HOSTS=* \
    python manage.py collectstatic --noinput 2>/dev/null || true

# --- Copiar y preparar entrypoint ---
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# --- Crear usuario no-root ---
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]

# CMD por defecto: Gunicorn (docker-compose puede sobreescribir esto)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
