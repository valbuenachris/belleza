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
from ..utils.http_headers import sanitize_request

logger = logging.getLogger(__name__)

# ============================================================
# Rutas públicas que no requieren autenticación
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


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware que verifica la autenticación JWT en requests.

    Este middleware es el ÚNICO que decodifica el token JWT y valida
    que sea un access token válido. Los datos extraídos (user_id, email,
    rol, tenant_id) se inyectan en request.state para que el
    TenantMiddleware y las dependencias los usen sin re-decodificar.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Procesa cada request HTTP verificando autenticación.
        """
        path = request.url.path
        method = request.method

        # ----------------------------------------------------------
        # Permitir OPTIONS (CORS preflight) sin autenticación.
        # Se responde 200 de inmediato para que el CORSMiddleware
        # (más externo) añada las cabeceras y el preflight nunca
        # llegue a la validación de token.
        # ----------------------------------------------------------
        if method == "OPTIONS":
            return Response(status_code=200)

        # ----------------------------------------------------------
        # Normalizar Content-Type antes de procesar el request.
        # Descarta charset/parámetros malformados (ej: '; charset=',
        # '"utf-8', '[a-z') que provocan re.error tipo
        # "unterminated character set at position 0" en parsers de
        # charset. Esto asegura que los bodies JSON se parseen como JSON.
        # ----------------------------------------------------------
        request = sanitize_request(request)

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
        # Decodificar y validar el token (única decodificación por request)
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

            # Solo los access tokens autorizan rutas autenticadas
            if payload.get("type") != "access":
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Tipo de token inválido. Se requiere un access token.",
                        "code": "INVALID_TOKEN_TYPE",
                    },
                )

            # Almacenar datos del usuario en request.state
            # (TenantMiddleware y dependencias los usarán después)
            request.state.user_id = payload.get("sub")
            request.state.user_email = payload.get("email")
            request.state.user_rol = payload.get("rol")
            request.state.tenant_id = payload.get("tenant_id")

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

        # Apple Wallet Web Service: Apple autentica con la cabecera
        # 'Authorization: ApplePass <token>' (nunca con el JWT del SPA),
        # así que estas rutas se resuelven por su propio mecanismo.
        if path == "/v1/log" or path.startswith("/v1/devices/") or path.startswith("/v1/passes/"):
            return True

        # Tarjeta pública de fidelidad: el cliente entra SIN JWT; el token
        # de capacidad de la URL es la única credencial.
        if path.startswith("/api/v1/public/wallet/"):
            return True

        # Webhooks de WhatsApp/Evolution: Evolution autentica con su propio
        # token (?token=), nunca con el JWT del SPA; se valida en el router.
        if path.startswith("/webhooks/"):
            return True

        return False
