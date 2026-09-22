# ============================================================
# backend/app/utils/http_headers.py
# Sanitización de cabeceras HTTP de entrada
#
# SOLO usa operaciones de string seguras (split/strip), sin regex.
# Evita a propósito `re` porque ciertos valores de Content-Type
# (corchetes sin balancear, comillas sin cerrar, etc.) rompían
# parsers con "re.error: unterminated character set at position 0".
#
# Regla general: de todo Content-Type solo se conserva el media type
# anterior al ';' (spam: 'application/json'). Todo lo demás
# (charset, boundary, params malformados) se descarta.
# ============================================================

from typing import Optional

from starlette.requests import Request

_DEFAULT_CONTENT_TYPE = "application/json"


def sanitize_content_type(raw: Optional[str]) -> str:
    """
    Normaliza un header Content-Type a un valor robusto.

    - None / vacío -> 'application/json'
    - Solo conserva la parte antes del primer ';' (media type).
    - Quita espacios y comillas sobrantes del media type.
    - Si el media type queda vacío o no tiene 'type/subtype' -> 'application/json'.

    Contra ningún valor puede lanzar excepción: usa solo split/strip/lower.
    """
    if raw is None:
        return _DEFAULT_CONTENT_TYPE

    if not isinstance(raw, str):
        raw = str(raw)

    value = raw.strip()
    if not value:
        return _DEFAULT_CONTENT_TYPE

    # Ignoar todo lo posterior a ';' (charset, boundary, params rotos)
    media = value.split(";", 1)[0]
    media = media.strip().strip('"').strip().lower()

    if not media or "/" not in media:
        return _DEFAULT_CONTENT_TYPE

    return media


def sanitize_request(request: Request) -> Request:
    """
    Normaliza el header Content-Type del scope del request (in-place).

    - No consume el body ni interfiere con el canal 'receive'.
    - Idempotente: aplicarlo varias veces es seguro.
    - Starlette lee las cabeceras de forma perezosa desde el scope, así
      que downstream (AuthMiddleware, TenantMiddleware, routers) ve el
      valor limpio.
    """
    original_headers = request.scope.get("headers") or []

    # Identificar el content-type actual (claves del scope siempre en bytes)
    current_content_type = None
    for key, value in original_headers:
        if _header_key(key) == b"content-type":
            current_content_type = value.decode("latin-1", errors="replace")
            break

    clean = sanitize_content_type(current_content_type)

    new_headers = [
        (key, value)
        for key, value in original_headers
        if _header_key(key) != b"content-type"
    ]
    new_headers.append((b"content-type", clean.encode("latin-1", errors="replace")))

    request.scope["headers"] = new_headers
    return request


def _header_key(key) -> bytes:
    """Devuelve la clave de cabecera normalizada a bytes en minúsculas."""
    if isinstance(key, bytes):
        return key.lower()
    return key.lower().encode("ascii", errors="ignore")