#!/bin/bash
# ============================================================
# INSIS API — Entrypoint
# ============================================================
# NO ejecuta migrate aquí (eso se hace explícitamente o en CI/CD).
# Espera a que DB y Redis estén listos, luego ejecuta el CMD.
# ============================================================

set -e

echo "============================================"
echo "  INSIS API — Starting..."
echo "============================================"

# --- Wait for database ---
echo "Waiting for database..."
python << 'EOF'
import time
import sys
import MySQLdb
from decouple import config

host = config("DB_HOST", default="db")
port = int(config("DB_PORT", default="3306"))
user = config("DB_USER", default="insis_user")
password = config("DB_PASSWORD", default="insis_dev_password")
db_name = config("DB_NAME", default="insis_db")

max_retries = 30
retry = 0
while retry < max_retries:
    try:
        # Unix socket path (Cloud Run / Cloud SQL) vs TCP host (Docker local)
        if host.startswith("/"):
            conn = MySQLdb.connect(
                unix_socket=host, user=user, passwd=password, db=db_name
            )
        else:
            conn = MySQLdb.connect(
                host=host, port=port, user=user, passwd=password, db=db_name
            )
        conn.close()
        print(f"✅ Database is ready! (attempt {retry + 1})")
        sys.exit(0)
    except Exception as e:
        retry += 1
        if retry >= max_retries:
            print(f"❌ Database not available after {max_retries} attempts: {e}")
            sys.exit(1)
        print(f"⏳ Database not ready (attempt {retry}/{max_retries}), retrying in 2s...")
        time.sleep(2)
EOF

# --- Wait for Redis (optional: skip if no broker URL configured) ---
echo "Waiting for Redis..."
python << 'EOF'
import time
import sys
import os

try:
    import redis
    from decouple import config

    broker_url = config("CELERY_BROKER_URL", default="")
    if not broker_url:
        print("⚠️  CELERY_BROKER_URL not set, skipping Redis check")
        sys.exit(0)

    r = redis.from_url(broker_url)

    max_retries = 15
    retry = 0
    while retry < max_retries:
        try:
            r.ping()
            print(f"✅ Redis is ready! (attempt {retry + 1})")
            sys.exit(0)
        except Exception as e:
            retry += 1
            if retry >= max_retries:
                print(f"⚠️  Redis not available, continuing anyway: {e}")
                sys.exit(0)
            print(f"⏳ Redis not ready (attempt {retry}/{max_retries}), retrying in 1s...")
            time.sleep(1)
except ImportError:
    print("⚠️  redis-py not installed, skipping Redis check")
EOF

echo "============================================"
echo "  Executing: $@"
echo "============================================"

# Execute whatever command was passed (CMD from Dockerfile or docker-compose)
exec "$@"
