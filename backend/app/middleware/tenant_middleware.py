# ============================================================
# backend/app/middleware/tenant_middleware.py
# Middleware que valida el tenant en cada request autenticado
# ============================================================

import logging
from typing import List
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..database import SessionLocal
from ..models.tenant import Tenant
from ..utils.http_headers import sanitize_request

logger = logging.getLogger(__name__)

# ============================================================
# Rutas públicas que no requieren validación de tenant
# ============================================================
PUBLIC_PATHS: List[str] = [
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/",
]


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware que valida el tenant en cada request autenticado.

    NOTA: El token JWT ya fue decodificado por el AuthMiddleware
    (que es más externo y se ejecuta primero). Este middleware usa
    request.state provisto por AuthMiddleware y NO vuelve a decodificar
    el token. Solo abre una sesión de BD cuando se necesita validar
    un tenant no-superadmin.

    IMPORTANTE: el tenant NO se resuelve desde el subdominio de la URL.
    El sistema usa login universal por email desde la root URL: el tenant
    se determina a partir del claim 'tenant_id' del JWT del usuario. Por
    eso este middleware solo valida el tenant indicado en el token.

    Flujo:
    1. Rutas públicas y OPTIONS pasan sin validación
    2. Superadmin no requiere tenant
    3. Validar el tenant en la base de datos (activo y no expirado)
    4. Inyectar el tenant en request.state
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Procesa cada request HTTP.
        """
        path = request.url.path
        method = request.method

        # ----------------------------------------------------------
        # Permitir OPTIONS (CORS preflight) sin validación de tenant.
        # Se responde 200 de inmediato para saltar toda validación.
        # ----------------------------------------------------------
        if method == "OPTIONS":
            return Response(status_code=200)

        # ----------------------------------------------------------
        # Red de seguridad: normalizar Content-Type (idempotente).
        # AuthMiddleware ya lo hace al ser más externo; aquí se aplica
        # por si un proxy/ruta saltó esa capa. Protege el pipeline de
        # "unterminated character set at position 0" (charsets rotos).
        # ----------------------------------------------------------
        request = sanitize_request(request)

        # ----------------------------------------------------------
        # Paso 1: Permitir rutas públicas sin validación
        # (login/registro/refresh son globales por email, sin tenant)
        # ----------------------------------------------------------
        if self._is_public_path(path):
            return await call_next(request)

        # ----------------------------------------------------------
        # Paso 2: Usar el estado autenticado provisto por AuthMiddleware
        # ----------------------------------------------------------
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token de autenticación no proporcionado"},
            )

        tenant_id = getattr(request.state, "tenant_id", None)
        rol = getattr(request.state, "user_rol", None)

        # ----------------------------------------------------------
        # Paso 3: Superadmin no requiere tenant
        # ----------------------------------------------------------
        if rol == "superadmin":
            request.state.tenant_id = None
            request.state.tenant = None
            return await call_next(request)

        # ----------------------------------------------------------
        # Paso 4: Validar que exista tenant_id en el token
        # ----------------------------------------------------------
        if not tenant_id:
            return JSONResponse(
                status_code=403,
                content={"detail": "No se encontró tenant asociado al usuario"},
            )

        # ----------------------------------------------------------
        # Paso 5: Validar el tenant en la base de datos
        # ----------------------------------------------------------
        db = SessionLocal()
        try:
            tenant = db.query(Tenant).filter(
                Tenant.id == tenant_id,
                Tenant.deleted_at == None,
            ).first()

            if not tenant:
                logger.warning(f"Tenant no encontrado: {tenant_id}")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "El tenant no existe o ha sido eliminado"},
                )

            if not tenant.is_active:
                logger.warning(f"Intento de acceso a tenant inactivo: {tenant_id}")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "El tenant está desactivado. Contacta al administrador."},
                )

            # ----------------------------------------------------------
            # Paso 6: Validar que el tenant no haya expirado
            # ----------------------------------------------------------
            if tenant.fecha_expiracion and datetime.utcnow() > tenant.fecha_expiracion:
                logger.warning(f"Tenant expirado: {tenant_id}")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "La suscripción del tenant ha expirado"},
                )

            # ----------------------------------------------------------
            # Paso 7: Inyectar datos en request.state
            # ----------------------------------------------------------
            request.state.tenant_id = tenant.id
            request.state.tenant = tenant

            return await call_next(request)

        except Exception as e:
            logger.error(f"Error en TenantMiddleware: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Error interno al validar el tenant"},
            )
        finally:
            db.close()

    def _is_public_path(self, path: str) -> bool:
        """Verifica si la ruta es pública (no requiere validación de tenant)."""
        for public_path in PUBLIC_PATHS:
            if path == public_path or path.startswith("/docs") or path.startswith("/redoc"):
                return True
        return False