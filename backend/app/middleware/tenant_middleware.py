# ============================================================
# backend/app/middleware/tenant_middleware.py
# Middleware que valida el tenant en cada request autenticado
# ============================================================

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import Request, Response
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..database import SessionLocal
from ..models.tenant import Tenant
from ..utils.http_headers import sanitize_request

logger = logging.getLogger(__name__)

# ============================================================
# Defaults del programa de fidelidad
# Se aplican si la base de datos registra NULL/vacío/formatos
# inválidos (tenants creados antes de la migración 0006 o con
# migraciones de fidelidad pendientes de aplicar en el servidor).
# ============================================================
DEFAULT_PUNTOS_META = 10
DEFAULT_PREMIO_FIDELIDAD = "Sesión de Spa gratis"
DEFAULT_TARJETA_COLOR_HEX = "#0D9488"


def _valid_color_hex(value) -> bool:
    """True si el valor es un hex de color válido (#RRGGBB)."""
    if not isinstance(value, str):
        return False
    value = value.strip()
    return (
        len(value) == 7
        and value.startswith("#")
        and all(c in "0123456789abcdefABCDEF" for c in value[1:])
    )


def _apply_loyalty_defaults(tenant) -> None:
    """
    Normaliza en memoria la configuración de fidelidad del tenant.
    Si la BD entrega NULL/vacío/inválido, aplica el valor por defecto
    para que ningún endpoint ruta-consume valores rotos. Nunca rompe
    el middleware (defensa ante datos heredados).
    """
    try:
        puntos = getattr(tenant, "puntos_meta", None)
        if puntos is None or not isinstance(puntos, int) or puntos < 1:
            tenant.puntos_meta = DEFAULT_PUNTOS_META

        premio = getattr(tenant, "premio_fidelidad", None)
        if premio is None or not isinstance(premio, str) or not premio.strip():
            tenant.premio_fidelidad = DEFAULT_PREMIO_FIDELIDAD

        color = getattr(tenant, "tarjeta_color_hex", None)
        if not _valid_color_hex(color):
            tenant.tarjeta_color_hex = DEFAULT_TARJETA_COLOR_HEX
    except Exception:  # pragma: no cover - defensa extrema
        pass


def _load_tenant_fallback(db, tenant_id: str) -> Optional[Tenant]:
    """
    Carga el tenant cuando la query normal falla porque la tabla
    `tenants` NO tiene alguna columna que el modelo espera (migraciones
    de fidelidad p.ej. 0006+ pendientes). Selecciona solo las columnas
    existentes y construye el Tenant con los defaults de fidelidad,
    manteniendo operativo el sistema hasta que el operador ejecute
    `alembic upgrade head`.

    Si el error no era por columnas faltantes, reintenta la query normal
    (la excepción pudo ser transitoria, p.ej. timeout de conexión).
    """
    try:
        db.rollback()
    except Exception:
        pass

    try:
        rows = db.execute(text("SHOW COLUMNS FROM tenants")).mappings().all()
    except Exception:
        return None

    present = {row["Field"] for row in rows}
    all_cols = set(Tenant.__table__.columns.keys())

    if all_cols.issubset(present):
        try:
            return db.query(Tenant).filter(
                Tenant.id == tenant_id,
                Tenant.deleted_at == None,
            ).first()
        except Exception:
            return None

    missing = sorted(all_cols - present)
    logger.error(
        "[TenantMiddleware] La tabla `tenants` no tiene las columnas %s. "
        "Ejecuta en el servidor: docker compose exec backend alembic upgrade head. "
        "Mientras tanto se usa un fallback con los valores por defecto.",
        missing,
    )

    existing = sorted(all_cols & present)
    try:
        stmt = select(*[getattr(Tenant, name) for name in existing]).where(
            Tenant.id == tenant_id,
            Tenant.deleted_at == None,
        )
        row = db.execute(stmt).mappings().first()
    except Exception:
        return None
    if row is None:
        return None

    tenant = Tenant(**{key: value for key, value in row.items()})
    _apply_loyalty_defaults(tenant)
    return tenant

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
            # ----------------------------------------------------------
            # Paso 5: Validar el tenant en la base de datos
            # ----------------------------------------------------------
            try:
                tenant = db.query(Tenant).filter(
                    Tenant.id == tenant_id,
                    Tenant.deleted_at == None,
                ).first()
            except OperationalError:
                # La query falló (p.ej. columna esperada por el modelo que aún
                # no existe en la BD: migraciones de fidelidad sin aplicar).
                # Se carga el tenant con las columnas disponibles y defaults.
                tenant = _load_tenant_fallback(db, tenant_id)

            if not tenant:
                logger.warning(f"Tenant no encontrado: {tenant_id}")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "El tenant no existe o ha sido eliminado"},
                )

            # Configuración de fidelidad defensiva: si la BD registra NULL,
            # vacío o formatos inválidos, aplicar defaults (no excepciones).
            _apply_loyalty_defaults(tenant)

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

            # ----------------------------------------------------------
            # Ejecutar el request (solo si la validación del tenant fue exitosa)
            # ----------------------------------------------------------
            return await call_next(request)

        except Exception as e:
            # SOLO errors que ocurrieron DURANTE la validación del tenant
            # (no errors lanzados por el route handler via call_next).
            # Si el route lanza HTTPException, este handler no debería
            # atraparlo porque Starlette's ExceptionMiddleware lo captura primero.
            # Pero por seguridad, logueamos y devolvemos 500 genérico.
            logger.error(
                f"Error en TenantMiddleware al validar el tenant {tenant_id}: {e}",
                exc_info=True,
            )
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
        # Apple Wallet Web Service: el tenant se resuelve desde el pase/paciente,
        # no desde el JWT, así que estas rutas no requieren tenant en sesión.
        if path == "/v1/log" or path.startswith("/v1/devices/") or path.startswith("/v1/passes/"):
            return True
        # Tarjeta pública de fidelidad: sin JWT ni tenant en sesión; el
        # tenant se resuelve desde el token de capacidad.
        if path.startswith("/api/v1/public/wallet/"):
            return True
        return False