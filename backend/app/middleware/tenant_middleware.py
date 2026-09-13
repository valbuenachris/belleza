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
from jose import JWTError

from ..config import settings
from ..utils.security import decode_token
from ..database import SessionLocal
from ..models.tenant import Tenant

logger = logging.getLogger(__name__)

# ============================================================
# Rutas públicas que no requieren validación de tenant
# ============================================================
PUBLIC_PATHS: List[str] = [
    "/api/v1/auth/login",
    "/api/v1/auth/register",
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
    
    Flujo:
    1. Si la ruta es pública, pasar sin validación
    2. Extraer el token JWT del header Authorization
    3. Decodificar el token y obtener el tenant_id
    4. Validar que el tenant exista y esté activo
    5. Validar que el tenant no haya expirado
    6. Inyectar el tenant_id en request.state
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Procesa cada request HTTP.
        """
        path = request.url.path
        
        # ----------------------------------------------------------
        # Paso 1: Permitir rutas públicas sin validación
        # ----------------------------------------------------------
        if self._is_public_path(path):
            return await call_next(request)
        
        # ----------------------------------------------------------
        # Paso 2: Extraer el token del header Authorization
        # ----------------------------------------------------------
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token de autenticación no proporcionado"},
            )
        
        # Formato: "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                status_code=401,
                content={"detail": "Formato de token inválido. Use: Bearer <token>"},
            )
        
        token = parts[1]
        
        # ----------------------------------------------------------
        # Paso 3: Decodificar el token
        # ----------------------------------------------------------
        try:
            payload = decode_token(token)
        except JWTError as e:
            logger.warning(f"Token inválido: {e}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Token inválido o expirado"},
            )
        
        # Verificar que sea un access token
        if payload.get("type") != "access":
            return JSONResponse(
                status_code=401,
                content={"detail": "Tipo de token inválido"},
            )
        
        tenant_id = payload.get("tenant_id")
        
        # ----------------------------------------------------------
        # Paso 4: Superadmin no requiere tenant
        # ----------------------------------------------------------
        rol = payload.get("rol")
        if rol == "superadmin":
            request.state.tenant_id = None
            request.state.user_id = payload.get("sub")
            request.state.user_rol = rol
            return await call_next(request)
        
        # ----------------------------------------------------------
        # Paso 5: Validar que exista tenant_id en el token
        # ----------------------------------------------------------
        if not tenant_id:
            return JSONResponse(
                status_code=403,
                content={"detail": "No se encontró tenant asociado al usuario"},
            )
        
        # ----------------------------------------------------------
        # Paso 6: Validar el tenant en la base de datos
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
            # Paso 7: Validar que el tenant no haya expirado
            # ----------------------------------------------------------
            if tenant.fecha_expiracion and datetime.utcnow() > tenant.fecha_expiracion:
                logger.warning(f"Tenant expirado: {tenant_id}")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "La suscripción del tenant ha expirado"},
                )
            
            # ----------------------------------------------------------
            # Paso 8: Inyectar datos en request.state
            # ----------------------------------------------------------
            request.state.tenant_id = tenant_id
            request.state.tenant = tenant
            request.state.user_id = payload.get("sub")
            request.state.user_rol = rol
            
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
