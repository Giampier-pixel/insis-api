# ============================================================
# INSIS API — Dockerfile (multi-stage)
# Stage 1 (builder): instala dependencias Python
# Stage 2 (runtime): imagen mínima, usuario no-root
# ============================================================

# --- Stage 1: builder ---
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    gcc \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- Stage 2: runtime ---
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias de sistema en tiempo de ejecución (solo libmysqlclient)
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar paquetes instalados desde el builder
COPY --from=builder /install /usr/local

# Copiar código
COPY . .

# Collectstatic en build-time (whitenoise requiere el paso en producción)
RUN SECRET_KEY=build-placeholder \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    DB_NAME=x DB_USER=x DB_PASSWORD=x DB_HOST=x \
    ALLOWED_HOSTS=* \
    python manage.py collectstatic --noinput 2>/dev/null || true

# Entrypoints
COPY entrypoint.sh /entrypoint.sh
COPY worker-start.sh /worker-start.sh
RUN chmod +x /entrypoint.sh /worker-start.sh

# Usuario no-root
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
