# ============================================================
# backend/app/utils/rate_limit.py - Rate limiting (slowapi)
# Instancia compartida del limitador de peticiones y funciones de
# clave (IP real / usuario autenticado) usadas por los routers.
#
# ALMACENAMIENTO (clave para que el límite funcione):
#   - El backend corre con `gunicorn -w 4` (varios procesos). El
#     almacenamiento en memoria es POR WORKER: 7 peticiones repartidas
#     entre 4 workers nunca alcanzan el límite de 5 y no hay 429.
#   - Por eso se usa Redis como almacenamiento COMPARTIDO entre todos
#     los workers, con detección al arranque y fallback a memoria si
#     Redis no responde (en ese caso avisa por log: los límites vuelven
#     a ser por worker).
#
# Notas:
#   - headers_enabled=True añade X-RateLimit-Limit/Remaining/Reset y
#     Retry-After. Requiere que el endpoint decorado declare un
#     parámetro `response: Response` (slowapi inyecta ahí las cabeceras).
#   - `_client_ip` prioriza X-Forwarded-For, que Nginx establece con la
#     IP real del cliente. El backend NO debe exponerse directamente.
# ============================================================

import logging
from typing import Optional

from fastapi import Request
from slowapi import Limiter

from ..config import settings

logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    """IP real del cliente (respeta X-Forwarded-For / X-Real-IP del proxy)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


def user_or_ip_key(request: Request) -> str:
    """Clave por usuario autenticado (request.state.user_id); si no, por IP."""
    user_id = getattr(request.state, "user_id", None)
    return f"user:{user_id}" if user_id else f"ip:{_client_ip(request)}"


def _redis_storage_uri() -> Optional[str]:
    """
    Devuelve la URI de Redis si responde al arranque; None para usar
    memoria local. Evita penalizar cada request si Redis no existe.
    """
    try:
        import redis  # redis-py (incluido en requirements.txt)

        client = redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        try:
            client.ping()
        finally:
            client.close()
        logger.info(
            "[rate-limit] Redis disponible en %s:%s -> límites COMPARTIDOS "
            "entre todos los workers.",
            settings.REDIS_HOST,
            settings.REDIS_PORT,
        )
        return settings.REDIS_URL
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[rate-limit] Redis no disponible (%s). Se usará almacenamiento EN "
            "MEMORIA POR WORKER: los límites NO se comparten entre los workers "
            "de gunicorn.",
            exc,
        )
        return None


_storage_uri = _redis_storage_uri()

# Limitador compartido de toda la aplicación.
limiter = Limiter(
    key_func=_client_ip,
    headers_enabled=True,
    # Redis compartido si está disponible; memoria local como fallback.
    storage_uri=_storage_uri or "memory://",
    # Timeouts cortos para que una caída de Redis no cuelgue los requests.
    storage_options={
        "socket_connect_timeout": 1,
        "socket_timeout": 1,
    },
    # Si Redis falla en runtime, limits degrada a un limitador en memoria
    # (aplica los mismos límites por endpoint) en vez de devolver 500.
    in_memory_fallback_enabled=True,
)
