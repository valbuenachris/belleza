#!/bin/sh
# ============================================================
# backend/entrypoint.sh - Punto de entrada del contenedor backend
#
# SECUENCIA DE ARRANQUE SEGURA
# ------------------------------------------------------------
#   1. Valida la configuración de integraciones opcionales y ABORTA
#      si están habilitadas pero mal configuradas (fail-fast).
#   2. Espera a que MySQL esté disponible (con reintentos).
#   3. Preflight de Alembic: detecta esquemas con tablas pero sin
#      historial de revisiones (estado ambiguo) y explica cómo
#      repararlo sin sellar a ciegas.
#   4. Ejecuta SIEMPRE `alembic upgrade head` (idempotente).
#   5. Postflight: verifica que el esquema real contiene los objetos
#      de las migraciones recientes; aborta ante drift silencioso.
#   6. Lanza el servicio (gunicorn/uvicorn).
#
# IMPORTANTE
# ------------------------------------------------------------
#   - Este entrypoint NUNCA ejecuta `alembic stamp head`.
#     Sellar sin aplicar migraciones provoca drift de esquema y
#     errores 500 silenciosos en runtime.
#   - Si una BD heredada ya tiene tablas sin historial de Alembic,
#     el paso 3 indica cómo sellar MANUALMENTE y verificado.
#   - Variable de escape SOLO para reparaciones puntuales:
#       STARTUP_VALIDATION_STRICT=false
#     degrada los abortes de validación a advertencias. No usar
#     como norma: permite arrancar con un esquema/config roto.
# ============================================================

set -eu

cd /app

log() {
    printf '%s\n' "[entrypoint] $*"
}

# ------------------------------------------------------------
# 1. Validación fail-fast de integraciones opcionales
# ------------------------------------------------------------
log "Validando configuración de integraciones..."

python - <<'PY'
import json
import os
import sys

from app.config import settings

BOLD = "\033[1m"
RED = "\033[1;31m"
YELLOW = "\033[1;33m"
RESET = "\033[0m"

strict = os.getenv("STARTUP_VALIDATION_STRICT", "true").strip().lower() not in (
    "0", "false", "no", "off",
)

problems = []

# FreeLLMAPI: si el asistente está habilitado, la API key es obligatoria.
if settings.FREELLMAPI_ENABLED and not (settings.FREELLMAPI_API_KEY or "").strip():
    problems.append(
        "FREELLMAPI_ENABLED=true pero FREELLMAPI_API_KEY está vacía. "
        "Define la API key o pon FREELLMAPI_ENABLED=false."
    )

# Google Wallet: si está habilitada, las credenciales deben ser utilizables
# (issuer id + clave privada inline o un .json existente y parseable).
if settings.GOOGLE_WALLET_ENABLED:
    gw_problems = []

    if not (settings.GOOGLE_WALLET_ISSUER_ID or "").strip():
        gw_problems.append("falta GOOGLE_WALLET_ISSUER_ID")

    inline_key = (settings.GOOGLE_WALLET_PRIVATE_KEY or "").strip()
    creds_path = (
        (settings.GOOGLE_APPLICATION_CREDENTIALS or "").strip()
        or (settings.GOOGLE_WALLET_SERVICE_ACCOUNT_FILE or "").strip()
    )

    if not inline_key:
        if not creds_path:
            gw_problems.append(
                "falta GOOGLE_APPLICATION_CREDENTIALS "
                "(o GOOGLE_WALLET_SERVICE_ACCOUNT_FILE / GOOGLE_WALLET_PRIVATE_KEY)"
            )
        elif not os.path.exists(creds_path):
            gw_problems.append(f"no existe el archivo de credenciales: {creds_path}")
        else:
            try:
                with open(creds_path, "r", encoding="utf-8") as fh:
                    blob = json.load(fh)
                if not (blob.get("private_key") or "").strip():
                    gw_problems.append(
                        f"{creds_path} no contiene 'private_key' "
                        "(¿archivo vacío o corrupto?)"
                    )
            except Exception as exc:  # noqa: BLE001
                gw_problems.append(f"no se pudo leer/parsear {creds_path}: {exc}")

    if gw_problems:
        problems.append(
            "GOOGLE_WALLET_ENABLED=true pero la integración no está configurada: "
            + "; ".join(gw_problems)
            + ". Configura las credenciales o pon GOOGLE_WALLET_ENABLED=false."
        )

if problems:
    print("")
    print(f"{RED}{'=' * 72}{RESET}")
    print(f"{RED}[entrypoint] ALERTA DE CONFIGURACIÓN DE INTEGRACIONES{RESET}")
    print(f"{RED}{'=' * 72}{RESET}")
    for problem in problems:
        print(f"{BOLD}  - {problem}{RESET}")
    if strict:
        print("")
        print(f"{RED}[entrypoint] ARRANQUE ABORTADO (STARTUP_VALIDATION_STRICT=true).{RESET}")
        print("[entrypoint] Corrige el .env y reinicia el contenedor.")
        print("[entrypoint] Escape temporal: STARTUP_VALIDATION_STRICT=false")
        sys.exit(1)
    print("")
    print(f"{YELLOW}[entrypoint] STARTUP_VALIDATION_STRICT=false: se continúa el{RESET}")
    print(f"{YELLOW}[entrypoint] arranque; la app puede fallar en runtime.{RESET}")
else:
    print("[entrypoint] Configuración de integraciones OK.")
PY

# ------------------------------------------------------------
# 2. Espera a que MySQL esté disponible
# ------------------------------------------------------------
log "Esperando a que MySQL esté disponible..."

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

# ------------------------------------------------------------
# 3. Preflight de Alembic: estado ambiguo sin historial de revisiones
# ------------------------------------------------------------
log "Comprobando el historial de migraciones de Alembic..."

python - <<'PY'
import os
import sys

from sqlalchemy import create_engine, inspect, text
from app.config import settings

BOLD = "\033[1m"
RED = "\033[1;31m"
YELLOW = "\033[1;33m"
RESET = "\033[0m"

strict = os.getenv("STARTUP_VALIDATION_STRICT", "true").strip().lower() not in (
    "0", "false", "no", "off",
)

engine = create_engine(settings.DATABASE_URL)
inspector = inspect(engine)

has_schema = inspector.has_table("tenants")
has_version_table = inspector.has_table("alembic_version")

if not has_schema:
    print("[entrypoint] Base de datos sin esquema: Alembic lo creará desde cero.")
    sys.exit(0)

current_rev = None
if has_version_table:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        current_rev = row[0] if row else None

if current_rev:
    print(f"[entrypoint] Revisión Alembic registrada: {current_rev}")
    sys.exit(0)

# Estado ambiguo: hay tablas pero no hay revisión registrada.
print("")
print(f"{RED}{'=' * 72}{RESET}")
print(f"{RED}[entrypoint] ARRANQUE ABORTADO: esquema sin historial de Alembic{RESET}")
print(f"{RED}{'=' * 72}{RESET}")
lines = [
    "La base de datos ya tiene tablas pero no hay una revisión registrada",
    "en `alembic_version`.",
    "",
    "Ejecutar `alembic upgrade head` fallaría con 'table already exists'.",
    "Sellar automáticamente (`alembic stamp head`) está PROHIBIDO aquí:",
    "ocultaría migraciones pendientes y causaría drift silencioso (500s).",
    "",
    "Reparación manual (verifica antes la paridad del esquema):",
    "  docker compose run --rm --entrypoint alembic backend current",
    "  docker compose run --rm --entrypoint alembic backend heads",
    "  docker compose run --rm --entrypoint alembic backend stamp <revision_verificada>",
    "",
    "Después reinicia el backend: `alembic upgrade head` aplicará lo pendiente.",
]
for line in lines:
    print(f"{BOLD}{line}{RESET}" if line else "")
print("")
if strict:
    sys.exit(1)
print(f"{YELLOW}[entrypoint] STARTUP_VALIDATION_STRICT=false: se continúa.{RESET}")
PY

# ------------------------------------------------------------
# 4. Migraciones idempotentes (nunca stamp)
# ------------------------------------------------------------
log "Aplicando migraciones: alembic upgrade head"
if ! alembic upgrade head; then
    printf '\n'
    printf '%s\n' "\033[1;31m====================================================\033[0m"
    printf '%s\n' "\033[1;31m[entrypoint] FALLÓ 'alembic upgrade head'\033[0m"
    printf '%s\n' "\033[1;31mRevisa el error anterior. NO ejecutes 'alembic stamp'\033[0m"
    printf '%s\n' "\033[1;31ma ciegas: primero verifica qué migraciones SÍ se aplicaron.\033[0m"
    printf '%s\n' "\033[1;31m====================================================\033[0m"
    exit 1
fi
log "Migraciones al día."

# ------------------------------------------------------------
# 5. Postflight: verificación anti-drift del esquema esperado
# ------------------------------------------------------------
log "Verificando el esquema resultante..."

python - <<'PY'
import os
import sys

from sqlalchemy import create_engine, inspect
from app.config import settings

BOLD = "\033[1m"
RED = "\033[1;31m"
YELLOW = "\033[1;33m"
RESET = "\033[0m"

strict = os.getenv("STARTUP_VALIDATION_STRICT", "true").strip().lower() not in (
    "0", "false", "no", "off",
)

# Objetos que DEBEN existir tras `alembic upgrade head` (migraciones 0001-0010).
# Alarma anti-drift: si la BD se selló con stamp sin aplicar migraciones,
# faltarán columnas/tablas y el arranque fallará de forma visible.
REQUIRED_TABLES = [
    "tenants", "users", "patients", "services", "appointments",
    "clinical_records", "pass_registrations", "assistant_queries",
    "notifications",
]
REQUIRED_COLUMNS = {
    "tenants": ["puntos_meta", "premio_fidelidad", "tarjeta_color_hex"],
    "patients": [
        "puntos", "sesiones_gratis", "wallet_pass_id", "wallet_auth_token",
        "wallet_updated_at", "google_wallet_object_id", "google_wallet_class_id",
        "google_wallet_updated_at", "wallet_share_token", "wallet_share_expires_at",
    ],
    "appointments": ["loyalty_awarded"],
}

engine = create_engine(settings.DATABASE_URL)
inspector = inspect(engine)

missing = []
for table in REQUIRED_TABLES:
    if not inspector.has_table(table):
        missing.append(f"tabla `{table}`")

for table, columns in REQUIRED_COLUMNS.items():
    if not inspector.has_table(table):
        continue
    existing = {col["name"] for col in inspector.get_columns(table)}
    for column in columns:
        if column not in existing:
            missing.append(f"columna `{table}.{column}`")

if not missing:
    print("[entrypoint] Esquema verificado: todos los objetos esperados existen.")
    sys.exit(0)

print("")
print(f"{RED}{'=' * 72}{RESET}")
print(f"{RED}[entrypoint] ALERTA: DRIFT DE ESQUEMA DETECTADO{RESET}")
print(f"{RED}{'=' * 72}{RESET}")
print(f"{BOLD}La revisión de Alembic está al día, pero faltan objetos:{RESET}")
for item in missing:
    print(f"{BOLD}  - {item}{RESET}")
print("")
lines = [
    "Esto indica que la BD se selló con `alembic stamp` sin ejecutar las",
    "migraciones (drift silencioso que causa errores 500).",
    "",
    "Reparación manual:",
    "  1) Identifica la última revisión cuyos cambios SÍ están aplicados",
    "     (p. ej. 0004 si el esquema es anterior a fidelidad).",
    "  2) Sella esa revisión manualmente:",
    "       docker compose run --rm --entrypoint alembic backend stamp <revision>",
    "  3) Reinicia el backend: `alembic upgrade head` aplicará lo pendiente.",
]
for line in lines:
    print(f"{BOLD}{line}{RESET}" if line else "")
print("")
if strict:
    sys.exit(1)
print(f"{YELLOW}[entrypoint] STARTUP_VALIDATION_STRICT=false: se continúa con drift.{RESET}")
PY

# ------------------------------------------------------------
# 6. Servicio
# ------------------------------------------------------------
log "Iniciando servicio: $*"
exec "$@"
