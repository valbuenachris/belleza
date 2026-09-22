# ============================================================
# backend/app/services/apns_push.py - Push APNs para Apple Wallet
# Notifica a los dispositivos registrados que su pase cambió
# (estrellas/sesiones), para que consulten /v1/passes/... y lo
# actualicen. Es estrictamente best-effort: nunca propaga
# excepciones al llamador (si APNs no está configurado o falla,
# el pase sigue actualizándose al momento de consultarse).
# ============================================================

import logging
import os
import time
from typing import Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

APNS_HOSTS = {
    "production": "api.push.apple.com",
    "sandbox": "api.sandbox.push.apple.com",
}

# Cache del JWT de proveedor (Apple recomienda reutilizar el token
# firmado hasta 60 minutos; aquí se regenera cada 55 minutos).
_PROVIDER_TOKEN_CACHE = {"token": None, "issued_at": 0}


def _http2_available() -> bool:
    """APNs solo habla HTTP/2; httpx lo usa solo si 'h2' está instalado."""
    try:
        import h2  # noqa: F401
        return True
    except ImportError:
        return False


def _build_provider_token() -> str:
    """
    JWT de proveedor (ES256) para APNs. Requiere la clave .p8 descargada
    desde Certificates, Identifiers & Profiles (APNs Keys) y los settings
    APNS_KEY_ID / APNS_TEAM_ID / APNS_P8_PATH.
    """
    now = int(time.time())
    if _PROVIDER_TOKEN_CACHE["token"] and now - _PROVIDER_TOKEN_CACHE["issued_at"] < 55 * 60:
        return _PROVIDER_TOKEN_CACHE["token"]

    if not settings.APNS_P8_PATH or not os.path.isfile(settings.APNS_P8_PATH):
        raise RuntimeError("APNS_P8_PATH no apunta a una clave .p8 válida")

    with open(settings.APNS_P8_PATH, "r", encoding="utf-8") as fh:
        private_key = fh.read()

    from jose import jwt as jose_jwt

    try:
        token = jose_jwt.encode(
            {"iss": settings.APNS_TEAM_ID, "iat": now},
            private_key,
            algorithm="ES256",
            headers={"kid": settings.APNS_KEY_ID},
        )
    except Exception:
        raise RuntimeError("No se pudo firmar el token APNs con la clave .p8")

    _PROVIDER_TOKEN_CACHE["token"] = token
    _PROVIDER_TOKEN_CACHE["issued_at"] = now
    return token


def send_pass_update_push(push_token: str, topic: Optional[str] = None) -> bool:
    """
    Envía un push APNs silencioso para que el dispositivo descargue la
    última versión del pase.

    Returns:
        True si APNs aceptó la notificación (HTTP 200); False en cualquier
        otro caso (fallo de red, configuración incompleta, etc.).
    """
    if not settings.APNS_ENABLED:
        logger.debug("[Wallet] APNS_ENABLED=false; push de pase omitido")
        return False
    if not push_token:
        return False
    if not _http2_available():
        logger.warning("[Wallet] paquete 'h2' no instalado; push APNs omitido (agrega h2==4.1.0 a requirements)")
        return False

    host = APNS_HOSTS["sandbox"] if settings.APNS_SANDBOX else APNS_HOSTS["production"]
    topic = topic or settings.APNS_TOPIC

    try:
        provider_token = _build_provider_token()
    except Exception as e:
        logger.warning(f"[Wallet] No se pudo firmar el token de APNs: {e}")
        return False

    headers = {
        "authorization": f"bearer {provider_token}",
        "apns-topic": topic,
        "apns-push-type": "passkit-update",
        "apns-priority": "10",
        "content-type": "application/json",
    }

    try:
        with httpx.Client(http2=True, timeout=10.0) as client:
            response = client.post(
                f"https://{host}/3/device/{push_token}",
                headers=headers,
                content=b"{}",
            )
        if response.status_code == 200:
            logger.info(f"[Wallet] Push de actualización de pase enviado (topic={topic})")
            return True
        logger.warning(
            f"[Wallet] APNs respondió {response.status_code}: {response.text[:300]}"
        )
        return False
    except Exception as e:
        logger.warning(f"[Wallet] No se pudo enviar el push APNs: {e}")
        return False