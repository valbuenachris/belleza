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


def _token_suffix(token: str, n: int = 6) -> str:
    """Últimos n caracteres del push token (seguro para logs)."""
    return f"...{token[-n:]}" if token else ""


def _apns_enabled() -> bool:
    """
    APNs habilitado si:
      - APNS_ENABLED=true (explícito), o
      - APNS_ENABLED=false pero se configuraron las credenciales .p8
        (auto-detección: no queremos push silenciosamente desactivados
        cuando el operador ya dejó las llaves en el entorno).
    """
    if settings.APNS_ENABLED:
        return True
    return bool(settings.APNS_KEY_ID and settings.APNS_TEAM_ID and settings.APNS_P8_PATH)


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

    Cabeceras según la especificación de APNs para Wallet:
      - payload: cuerpo VACÍO '{}' (solo indica que hay un pase nuevo);
      - apns-topic: passTypeIdentifier del pase (NO el bundle del app);
      - apns-push-type: 'background' (silencioso); 'passkit-update' y
        'pass.kit-update' NO son tipos válidos y son rechazados (400);
      - apns-priority: 5 (obligatorio para push-type=background; 10
        es rechazado por APNs);
      - apns-expiration: TTL para que el push alcance a dispositivos
        offline (de lo contrario APNs lo descarta al instante).

    Returns:
        True si APNs aceptó la notificación (HTTP 200); False en cualquier
        otro caso (fallo de red, configuración incompleta, etc.).
    """
    if not push_token:
        return False

    if not _apns_enabled():
        logger.warning(
            "[WALLET][APNS] Push omitido: APNs no habilitado. Configura "
            "APNS_ENABLED=true (o APNS_KEY_ID + APNS_TEAM_ID + APNS_P8_PATH "
            "para activarlo automáticamente) y monta la clave .p8 en el "
            "contenedor del backend."
        )
        return False
    if not _http2_available():
        logger.warning("[WALLET][APNS] paquete 'h2' no instalado; push omitido (agrega h2==4.1.0 a requirements)")
        return False

    host = APNS_HOSTS["sandbox"] if settings.APNS_SANDBOX else APNS_HOSTS["production"]
    env = "sandbox" if settings.APNS_SANDBOX else "production"
    topic = topic or settings.APNS_TOPIC

    try:
        provider_token = _build_provider_token()
    except Exception as e:
        logger.warning(f"[WALLET][APNS] No se pudo firmar el token de APNs: {e}")
        return False

    headers = {
        "authorization": f"bearer {provider_token}",
        "apns-topic": topic,
        "apns-push-type": settings.APNS_PUSH_TYPE or "background",
        "apns-priority": str(settings.APNS_PRIORITY),
        "apns-expiration": str(settings.APNS_EXPIRATION),
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
            logger.info(
                f"[WALLET][APNS] Push enviado OK (env={env}, topic={topic}, "
                f"push={_token_suffix(push_token)})"
            )
            return True
        reason = "unknown"
        try:
            reason = response.json().get("reason", "unknown")
        except Exception:
            reason = response.text[:300]
        logger.warning(
            f"[WALLET][APNS] Rechazado {response.status_code} (reason={reason}) "
            f"env={env}, topic={topic}, push={_token_suffix(push_token)}"
        )
        return False
    except Exception as e:
        logger.warning(
            f"[WALLET][APNS] No se pudo enviar el push (env={env}, "
            f"push={_token_suffix(push_token)}): {e}"
        )
        return False