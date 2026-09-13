# ============================================================
# backend/app/middleware/auth_middleware.py
# Middleware que verifica la autenticación JWT en requests
# ============================================================

import logging
from typing import List

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import JWTError

from ..utils.security import decode_token

logger = logging.getLogger(__name__)

# ============================================================
# Rutas públicas que no requieren autenticación
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
    "/api/v1/tenants/check-subdomain",  # Público para registro
]


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware que verifica la presencia y validez del token JWT.
    
    Este middleware se ejecuta ANTES del TenantMiddleware.
    Solo verifica que el token exista y sea válido.
    La validación del tenant se hace en TenantMiddleware.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Procesa cada request HTTP verificando autenticación.
        """
        path = request.url.path
        method = request.method
        
        # ----------------------------------------------------------
        # Permitir OPTIONS (CORS preflight) sin autenticación
        # ----------------------------------------------------------
        if method == "OPTIONS":
            return await call_next(request)
        
        # ----------------------------------------------------------
        # Permitir rutas públicas sin autenticación
        # ----------------------------------------------------------
        if self._is_public_path(path):
            return await call_next(request)
        
        # ----------------------------------------------------------
        # Verificar presencia del token
        # ----------------------------------------------------------
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "No se proporcionó token de autenticación",
                    "code": "MISSING_TOKEN",
                },
            )
        
        # ----------------------------------------------------------
        # Validar formato del header
        # ----------------------------------------------------------
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Formato de autenticación inválido. Use: Bearer <token>",
                    "code": "INVALID_FORMAT",
                },
            )
        
        token = parts[1]
        
        # ----------------------------------------------------------
        # Decodificar y validar el token
        # ----------------------------------------------------------
        try:
            payload = decode_token(token)
            
            # Verificar que tenga los campos mínimos
            if not payload.get("sub"):
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Token inválido: falta identificador de usuario",
                        "code": "INVALID_TOKEN",
                    },
                )
            
            # Almacenar datos del usuario en request.state
            # (TenantMiddleware los usará después)
            request.state.user_id = payload.get("sub")
            request.state.user_email = payload.get("email")
            request.state.user_rol = payload.get("rol")
            
            return await call_next(request)
        
        except JWTError as e:
            error_msg = str(e)
            if "expired" in error_msg.lower():
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "El token ha expirado. Inicia sesión nuevamente.",
                        "code": "TOKEN_EXPIRED",
                    },
                )
            else:
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Token de autenticación inválido",
                        "code": "INVALID_TOKEN",
                    },
                )
        
        except Exception as e:
            logger.error(f"Error inesperado en AuthMiddleware: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Error interno del servidor",
                    "code": "INTERNAL_ERROR",
                },
            )
    
    def _is_public_path(self, path: str) -> bool:
        """Verifica si la ruta es pública."""
        for public_path in PUBLIC_PATHS:
            if path == public_path:
                return True
        
        # Permitir documentación de la API
        if path.startswith("/docs") or path.startswith("/redoc"):
            return True
        
        return False
