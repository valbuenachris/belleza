# ============================================================
# backend/app/main.py - Punto de entrada de la aplicación FastAPI
# Sistema de Gestión Integral para SPAs - Arquitectura Multitenant
# ============================================================

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .database import init_db, check_connection, get_connection_info
from .middleware.tenant_middleware import TenantMiddleware
from .middleware.auth_middleware import AuthMiddleware
from .routers import auth, tenants, patients, appointments, services, users, clinical_records, loyalty, assistant, notifications, public_wallet, whatsapp, whatsapp_webhook
from .utils.rate_limit import limiter

# ============================================================
# Configuración de logging
# ============================================================

# Formato de logs apropiado para Docker
if settings.is_production:
    # En producción: formato JSON para facilitar parsing
    logging.basicConfig(
        level=logging.INFO,
        format='{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
        stream=sys.stdout,
    )
else:
    # En desarrollo: formato legible
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

logger = logging.getLogger(__name__)


# ============================================================
# Lifespan - Eventos de startup y shutdown
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Maneja los eventos de inicio y cierre de la aplicación.
    
    Startup:
    - Inicializa la base de datos (con reintentos para Docker)
    - Verifica conexión a servicios
    
    Shutdown:
    - Limpieza de recursos
    """
    # ----------------------------------------------------------
    # STARTUP
    # ----------------------------------------------------------
    logger.info(f"🚀 Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📡 Entorno: {settings.ENVIRONMENT}")
    logger.info(f"🐳 Docker: {settings.is_docker}")
    logger.info(f"🗄️ Base de datos: {get_connection_info()}")
    
# Inicializar base de datos con reintentos
    # (importante en Docker donde MySQL puede tardar en estar listo)
    try:
        init_db(max_retries=30, retry_delay=2)
        logger.info("✅ Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"❌ Error al inicializar base de datos: {e}")
        # No fallar completamente - el healthcheck detectará el problema
        logger.warning("La aplicación continuará iniciando, pero la DB no está disponible")

    # Registrar webhooks de WhatsApp en Evolution para instancias abiertas
    try:
        await _register_whatsapp_webhooks()
    except Exception as e:
        logger.warning(f"No se pudieron registrar webhooks de WhatsApp en startup: {e}")

    # Loop de recordatorios de citas por WhatsApp (24h antes)
    reminder_task = None
    try:
        from .services.whatsapp_reminder_service import reminder_loop

        reminder_task = asyncio.create_task(reminder_loop())
        logger.info("Loop de recordatorios de citas por WhatsApp iniciado")
    except Exception as e:
        logger.warning(f"No se pudo iniciar el loop de recordatorios: {e}")

    logger.info("✅ Aplicación lista para recibir requests")
    
    yield
    
    # ----------------------------------------------------------
    # SHUTDOWN
    # ----------------------------------------------------------
    if reminder_task:
        reminder_task.cancel()
    logger.info("🛑 Cerrando aplicación...")
    logger.info("✅ Aplicación cerrada correctamente")


# ============================================================
# Instancia principal de FastAPI
# ============================================================

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "API REST para el Sistema de Gestión Integral de SPAs.\n\n"
        "## Características\n\n"
        "- **Multitenant**: Cada SPA tiene datos completamente aislados\n"
        "- **Autenticación JWT**: Tokens seguros con refresh tokens\n"
        "- **Roles**: superadmin, admin, manager, receptionist, therapist\n"
        "- **Dockerizado**: Listo para desplegar con docker-compose\n\n"
        "## Autenticación\n\n"
        "Usa el endpoint `/api/v1/auth/login` para obtener tokens JWT.\n"
        "Incluye el token en el header: `Authorization: Bearer <token>`"
    ),
    version=settings.APP_VERSION,
    # La documentación interactiva se deshabilita en producción
    # (ver settings.ENABLE_DOCS / settings.docs_available)
    docs_url="/docs" if settings.docs_available else None,
    redoc_url="/redoc" if settings.docs_available else None,
    openapi_url="/openapi.json" if settings.docs_available else None,
    lifespan=lifespan,
)

# ============================================================
# Rate limiting (slowapi)
# Límites por endpoint definidos con @limiter.limit(...) en los
# routers. El handler devuelve 429 + cabeceras X-RateLimit-* y
# Retry-After cuando se excede el límite.
# ============================================================

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ============================================================
# Middleware - En orden de ejecución (LIFO de Starlette)
# ============================================================
#
# Cada add_middleware() envuelve la aplicación previa, así que el
# ÚLTIMO middleware agregado se ejecuta PRIMERO (el más externo).
#
# Orden deseado de ejecución:
#   1. CORSMiddleware        -> maneja preflight OPTIONS primero
#   2. AuthMiddleware        -> decodifica y valida el JWT (una sola vez)
#   3. TenantMiddleware      -> valida el tenant usando request.state
#
# Para lograrlo se registran en orden inverso: Tenant, Auth, CORS.

app.add_middleware(TenantMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    # Orígenes explícitos y configurables (nunca "*" con credentials)
    allow_origins=settings.cors_origins_list,
    # Permite localhost/127.0.0.1 en cualquier puerto (dev / acceso local)
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# ============================================================
# Incluir routers
# ============================================================

app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(tenants.router, prefix=settings.API_PREFIX)
app.include_router(patients.router, prefix=settings.API_PREFIX)
app.include_router(appointments.router, prefix=settings.API_PREFIX)
app.include_router(services.router, prefix=settings.API_PREFIX)
app.include_router(users.router, prefix=settings.API_PREFIX)
app.include_router(clinical_records.router, prefix=settings.API_PREFIX)
app.include_router(clinical_records.record_router, prefix=settings.API_PREFIX)
app.include_router(loyalty.router, prefix=settings.API_PREFIX)
app.include_router(loyalty.scan_router, prefix=settings.API_PREFIX)
app.include_router(assistant.router, prefix=settings.API_PREFIX)
app.include_router(notifications.router, prefix=settings.API_PREFIX)
# Tarjeta pública de fidelidad: enlace de capacidad compartido con el
# cliente (sin JWT). El token es la única clave; rate-limited por IP.
app.include_router(public_wallet.router, prefix=settings.API_PREFIX)
# WhatsApp / Evolution API: endpoints de administración protegidos.
app.include_router(whatsapp.router, prefix=settings.API_PREFIX)
# WhatsApp webhook público (sin JWT, validado por token).
app.include_router(whatsapp_webhook.router)
# Apple Wallet Web Service: se monta en /v1 (raíz, SIN /api/v1) porque
# Apple llama a /v1/devices/... /v1/passes/... y /v1/log directamente.
app.include_router(loyalty.wallet_router)
# WhatsApp webhook público (sin JWT, validado por token).
# No tiene prefix /api/v1 porque Evolution llama directo a /webhooks/evolution/...


# ============================================================
# Manejo global de excepciones
# ============================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Maneja excepciones HTTP de forma consistente."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Maneja errores de validación de Pydantic."""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Error de validación en los datos enviados",
            "errors": errors,
        },
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request: Request, exc: ValidationError):
    """Maneja errores de validación de Pydantic fuera de FastAPI."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Error de validación",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Maneja excepciones no capturadas."""
    logger.error(f"Error no capturado: {exc}", exc_info=True)
    
    # En producción no exponer detalles del error
    if settings.is_production:
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor"},
        )
    
    return JSONResponse(
        status_code=500,
        content={"detail": f"Error interno: {str(exc)}"},
    )


# ============================================================
# Endpoints raíz
# ============================================================

@app.get(
    "/",
    tags=["Root"],
    summary="Información de la API",
)
async def root():
    """
    Endpoint raíz con información general de la API.
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs" if settings.docs_available else None,
        "api_prefix": settings.API_PREFIX,
        "status": "running",
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
)
async def health_check():
    """
    Verifica el estado de salud de la aplicación.
    Usado por Docker para healthchecks.
    """
    db_healthy = check_connection()
    
    status_code = 200 if db_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "version": settings.APP_VERSION,
        },
    )


async def _register_whatsapp_webhooks():
    """Registra los webhooks de WhatsApp en Evolution para instancias abiertas."""
    try:
        from .database import SessionLocal
        from .models.whatsapp import WhatsAppSettings
        from .services.whatsapp_service import evolution_client

        public_url = settings.PUBLIC_API_URL.strip().rstrip("/") if settings.PUBLIC_API_URL else ""
        webhook_token = settings.EVOLUTION_WEBHOOK_TOKEN.strip() if settings.EVOLUTION_WEBHOOK_TOKEN else ""
        if not public_url or not webhook_token:
            logger.warning("PUBLIC_API_URL o EVOLUTION_WEBHOOK_TOKEN no configurados; webhooks no registrados.")
            return

        db = SessionLocal()
        try:
            instances = db.query(WhatsAppSettings).filter(
                WhatsAppSettings.status == "open",
                WhatsAppSettings.deleted_at == None,
                WhatsAppSettings.instance_name != None,
            ).all()

            for inst in instances:
                webhook_url = f"{public_url}/webhooks/evolution/{inst.instance_name}?token={webhook_token}"
                try:
                    await evolution_client.set_webhook(inst.instance_name, webhook_url)
                    inst.webhook_registered = True
                    logger.info(f"Webhook registrado al iniciar para {inst.instance_name}")
                except ValueError as e:
                    logger.warning(f"No se pudo registrar webhook para {inst.instance_name}: {e}")
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Error registrando webhooks WhatsApp al iniciar: {e}")


# ============================================================
# Punto de entrada para desarrollo
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
