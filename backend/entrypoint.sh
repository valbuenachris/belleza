#!/bin/sh
# ============================================================
# backend/entrypoint.sh - Punto de entrada del contenedor backend
#
# 1. Espera a que MySQL esté disponible (con reintentos)
# 2. Ejecuta migraciones de Alembic:
#    - Esquema vacío     -> alembic upgrade head (crea tablas)
#    - Esquema existente -> alembic stamp head (registra la versión,
#      por ejemplo cuando database/schema.sql + seed.sql ya fueron
#      aplicados por docker-entrypoint-initdb.d)
# 3. Ejecuta el comando del servicio (CMD), p.ej. gunicorn/uvicorn
# ============================================================

set -e

echo "[entrypoint] Esperando a que MySQL esté disponible..."

python - <<'PY'
import sys
import time

from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.DATABASE_URL)
max_retries = 60  # ~120s a 2s por intento
for attempt in range(1, max_retries + 1):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[entrypoint] MySQL disponible.")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"[entrypoint] Intento {attempt}/{max_retries} - DB no disponible: {exc}")
        time.sleep(2)

print("[entrypoint] No se pudo conectar a MySQL a tiempo.")
sys.exit(1)
PY

TABLE_EXISTS=$(python - <<'PY'
from sqlalchemy import create_engine, inspect
from app.config import settings

engine = create_engine(settings.DATABASE_URL)
insp = inspect(engine)
print("1" if insp.has_table("tenants") else "0")
PY
)

cd /app

if [ "$TABLE_EXISTS" = "1" ]; then
    echo "[entrypoint] Esquema existente detectado. Sellando versión con Alembic..."
    alembic stamp head
else
    echo "[entrypoint] Esquema vacío. Aplicando migraciones con Alembic..."
    alembic upgrade head
fi

echo "[entrypoint] Iniciando servicio: $*"
exec "$@"