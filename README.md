# SPA Management System

## Descripción General

Sistema de gestión integral para SPAs (centros de estética y relajación) con arquitectura **multitenant SaaS**: múltiples spas comparten la misma infraestructura con datos completamente aislados por `tenant_id`.

---

## Stack de Arquitectura

- **Backend:** Python 3.11 + FastAPI 0.109 + SQLAlchemy 2.0 + Alembic 1.13
- **Frontend:** React 18 + TypeScript + Vite 6 + Tailwind CSS 4 (SPA en `src/`)
- **Base de datos:** MySQL 8 externa (configurada por `.env`)
- **Caché / Rate limiting:** Redis 7 (almacenamiento compartido de slowapi)
- **Proxy y estáticos:** Nginx 1.25 (sirve el build de React y hace reverse proxy de `/api/` y `/v1/`)
- **IA:** FreeLLMAPI — proxy self-hosted OpenAI-compatible (red Docker `freellmapi_default`)
- **Autenticación:** JWT (python-jose) + bcrypt
- **Contenedores:** Docker + Docker Compose

---

## Características Principales

- **Multitenancy real:** aislamiento por `tenant_id` en modelos, routers y middleware, con validación defensiva del tenant.
- **Autenticación y roles:** access/refresh tokens JWT y roles `superadmin`, `admin`, `manager`, `receptionist`, `therapist`.
- **Operación del SPA:** pacientes, servicios, citas (con validación anti-doble-reserva), historial clínico y reportes.
- **Programa de fidelidad:** estrellas por cita completada, sesiones gratis, canje y escáner QR.
- **Apple Wallet:** generación de `.pkpass`, firma PKCS#7 opcional, web service `/v1` y push APNs (requiere credenciales para producción).
- **Google Wallet:** LoyaltyClass/LoyaltyObject, enlace "Añadir a Wallet" y sincronización de puntos (deshabilitado por defecto).
- **Asistente IA:** integración con FreeLLMAPI con **historial de conversación** (array de mensajes estilo OpenAI) y contexto de negocio dinámico (RAG: servicios top, clientes inactivos, citas recientes).
- **Notificaciones internas:** campana en el Dashboard con polling cada 45 s, estado de lectura por usuario y generación por eventos (nueva cita, recompensa de fidelidad, recordatorios).
- **Rate limiting:** 5 req/min en `login`/`register` y 20 req/min por usuario en el asistente, **compartido entre workers** vía Redis.
- **Arranque seguro:** validación estricta de configuración y migraciones Alembic aplicadas automáticamente con `upgrade head` (nunca `stamp head`).

---

## Variables de Entorno

> ⚠️ **WARNING: Use ONLY the root `.env` file. Do not create or mount `backend/.env`.**
> `docker-compose.yml` inyecta el `.env` raíz vía `env_file`; el antiguo `backend/.env` está deprecado y **no** se monta. Crear o montar otro `.env` provoca drift de configuración (p. ej. errores 401 del asistente).

Variables esenciales (ver `.env.example` para la lista completa; `.env` está en `.gitignore`):

```bash
# --- Base de datos (MySQL externa) ---
DB_HOST=tu-host-mysql
DB_PORT=3306
DB_USER=spa_user
DB_PASSWORD=tu_password_seguro
DB_NAME=spa_management

# --- Seguridad / JWT ---
SECRET_KEY=genera_una_clave_de_al_menos_32_caracteres
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# --- Aplicación ---
APP_NAME=SPA Management System
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=production
API_PREFIX=/api/v1
CORS_ORIGINS=https://tu-dominio.com,https://www.tu-dominio.com
DOCKER_ENV=true
ENABLE_DOCS=false

# --- Redis (rate limiting compartido entre workers de Gunicorn) ---
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=tu_password_redis

# --- Asistente IA (FreeLLMAPI - proxy OpenAI-compatible) ---
FREELLMAPI_ENABLED=true
FREELLMAPI_API_KEY=tu_api_key
FREELLMAPI_BASE_URL=http://freellmapi-freellmapi-1:3001/v1
FREELLMAPI_MODEL=auto
FREELLMAPI_TIMEOUT=30

# --- Arranque seguro ---
# true (default): el contenedor ABORTA si hay configuración inválida
# (FreeLLMAPI/Google Wallet habilitados sin credenciales) o drift de esquema.
STARTUP_VALIDATION_STRICT=true

# --- Wallets (opcionales; detalle completo en .env.example) ---
WALLET_WEB_SERVICE_BASE_URL=https://tu-dominio.com
GOOGLE_WALLET_ENABLED=false
GOOGLE_WALLET_ISSUER_ID=
GOOGLE_WALLET_CLASS_ID=
GOOGLE_APPLICATION_CREDENTIALS=/app/google-credentials/service-account.json
APNS_ENABLED=false
APNS_KEY_ID=
APNS_TEAM_ID=
APNS_P8_PATH=
APNS_TOPIC=pass.com.tuuspa.fidelidad
```

**Notas:**

- `STARTUP_VALIDATION_STRICT=true` aborta el arranque si `FREELLMAPI_ENABLED=true` sin API key, `GOOGLE_WALLET_ENABLED=true` sin credenciales, o si el esquema no tiene historial de Alembic / presenta drift. Usa `false` **solo** para reparaciones puntuales.
- Si Redis no está disponible al arrancar, el backend avisa por log y degrada el rate limiting a memoria por worker (los límites dejan de compartirse).
- Las credenciales de wallet (`./google-credentials/`) nunca deben subirse al repositorio.

---

## Puesta en Marcha / Deployment

**Requisitos previos:**

- Docker 20.10+
- Docker Compose v2
- 2 GB de RAM mínimo recomendado
- Una base de datos MySQL 8 accesible (externa)

**Puesta en marcha en 3 pasos:**

```bash
# 1) Configuración: usa el .env raíz como única fuente de verdad
cp .env.example .env
#    Edita .env con tus valores reales (DB_*, SECRET_KEY, REDIS_PASSWORD,
#    FREELLMAPI_* y credenciales de wallet si aplica).

# 2) Construir las imágenes
docker compose build

# 3) Levantar el stack
docker compose up -d
```

**Qué ocurre en el primer arranque:**

- `backend/entrypoint.sh` espera a que MySQL esté disponible, valida la configuración y aplica **automáticamente** las migraciones con `alembic upgrade head` (crea o actualiza el esquema; es idempotente y nunca ejecuta `stamp head`).
- Si la validación estricta detecta un problema, el contenedor se detiene con un mensaje claro en los logs (`docker compose logs -f backend`).

**Accesos por defecto (compose base):**

- Frontend: `http://localhost:8088`
- API / health: `http://localhost:8000/health`
- Documentación interactiva: solo si `ENABLE_DOCS=true` (deshabilitada en producción).

**Producción (recomendado):**

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

El override de producción elimina los puertos publicados, aplica límites de recursos, rotación de logs y `restart: always`.

**Datos semilla (solo en bases de datos nuevas inicializadas con `database/seed.sql`):** se crea el superadmin `superadmin@spa.com` con la contraseña placeholder `CHANGE_ME_ON_FIRST_LOGIN_!23`. **Cámbiala inmediatamente** en producción.

---

## Estructura del Proyecto

```text
spa-management-system/
├── backend/
│   ├── Dockerfile                  # Imagen Python multi-stage (usuario no-root)
│   ├── entrypoint.sh               # Espera DB + validación estricta + alembic upgrade head
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/versions/           # Migraciones 0001..0011
│   └── app/
│       ├── main.py                 # FastAPI + middleware + rate limiting
│       ├── config.py               # pydantic-settings (config efectiva)
│       ├── database.py
│       ├── dependencies.py
│       ├── middleware/             # Auth JWT + validación de tenant
│       ├── models/                 # SQLAlchemy (notifications, assistant, wallet…)
│       ├── schemas/                # Pydantic
│       ├── routers/                # auth, tenants, patients, appointments, services,
│       │                           # users, clinical_records, loyalty, assistant, notifications
│       ├── services/               # Lógica de negocio (loyalty, assistant, notifications…)
│       └── utils/                  # security, validators, rate_limit
├── src/                            # Frontend React 18 + TypeScript + Vite (única UI)
│   ├── components/                 # Layout, NotificationBell…
│   ├── context/                    # AuthContext
│   ├── pages/                      # Dashboard, Citas, Pacientes, Asistente IA, Reportes…
│   ├── services/                   # Cliente API
│   └── types/
├── frontend/
│   ├── Dockerfile                  # Build de React + Nginx
│   └── nginx.conf                  # SPA + proxy /api/ y /v1/ + headers de seguridad
├── database/
│   ├── init.sql
│   ├── schema.sql                  # Paridad con las migraciones de Alembic
│   └── seed.sql                    # Datos semilla (contraseña placeholder)
├── scripts/
│   └── wallet_e2e_diagnostic.sh    # Diagnóstico E2E del web service de Apple Wallet
├── docker-compose.yml              # Stack base
├── docker-compose.prod.yml         # Override de producción
├── docker-compose.dev.yml          # Override de desarrollo (hot-reload backend)
├── index.html                      # Entry point de Vite
├── package.json
├── tsconfig.json
├── vite.config.js
├── .env                            # SINGLE SOURCE OF TRUTH (no versionado)
└── .env.example                    # Plantilla de variables de entorno
```
