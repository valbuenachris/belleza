# ============================================================
# backend/app/main.py - Punto de entrada de la aplicación FastAPI
# Sistema de Gestión Integral para SPAs - Arquitectura Multitenant
# ============================================================

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from .config import settings
from .database import init_db, check_connection
from .middleware.tenant_middleware import TenantMiddleware
from .middleware.auth_middleware import AuthMiddleware
from .routers import auth, tenants

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
    
    # Inicializar base de datos con reintentos
    # (importante en Docker donde MySQL puede tardar en estar listo)
    try:
        init_db(max_retries=30, retry_delay=2)
        logger.info("✅ Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"❌ Error al inicializar base de datos: {e}")
        # No fallar completamente - el healthcheck detectará el problema
        logger.warning("La aplicación continuará iniciando, pero la DB no está disponible")
    
    logger.info("✅ Aplicación lista para recibir requests")
    
    yield
    
    # ----------------------------------------------------------
    # SHUTDOWN
    # ----------------------------------------------------------
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
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ============================================================
# Middleware - CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# ============================================================
# Middleware - Autenticación y Tenant (en orden de ejecución)
# ============================================================

# Primero Auth (verifica token), luego Tenant (verifica tenant_id)
app.add_middleware(AuthMiddleware)
app.add_middleware(TenantMiddleware)


# ============================================================
# Incluir routers
# ============================================================

app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(tenants.router, prefix=settings.API_PREFIX)


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
        "docs_url": "/docs",
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
