# ============================================================
# backend/app/services/loyalty_service.py - Programa de Fidelidad
# Puntos (estrellas) por cita completada, sesiones gratis y
# generación de pases digitales (Apple Wallet .pkpass / Google
# Wallet JSON) integrados con pacientes.
# ============================================================

import hashlib
import io
import json
import logging
import secrets
import threading
import zipfile
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from ..config import settings
from ..models.patient import Patient
from ..models.tenant import Tenant
from . import notification_service
from .pass_signer import (
    is_signing_configured,
    sign_manifest,
    warn_if_unconfigured,
)

logger = logging.getLogger(__name__)

# ============================================================
# Constantes del programa (valores por defecto, personalizables
# por tenant vía puntos_meta / premio_fidelidad / tarjeta_color_hex)
# ============================================================

PUNTOS_POR_CITA = 1

DEFAULT_PUNTOS_META = 10
DEFAULT_PREMIO_FIDELIDAD = "Sesión de Spa gratis"
DEFAULT_TARJETA_COLOR_HEX = "#0D9488"

DEFAULT_LOYALTY_CONFIG = {
    "puntos_meta": DEFAULT_PUNTOS_META,
    "premio_fidelidad": DEFAULT_PREMIO_FIDELIDAD,
    "tarjeta_color_hex": DEFAULT_TARJETA_COLOR_HEX,
}

# Placeholders: se reemplazarán con los identificadores emitidos por
# Apple (Certificates, Identifiers & Profiles) al registrarse oficialmente.
PASS_TYPE_IDENTIFIER = "pass.com.tuuspa.fidelidad"
TEAM_IDENTIFIER = "XXXXXXXXXX"

# ============================================================
# Actualización dinámica del pase (Apple Wallet Web Service)
# ============================================================

def _wallet_service_url() -> str:
    """URL base pública del web service de Apple (sin barra final)."""
    return (settings.WALLET_WEB_SERVICE_BASE_URL or "").rstrip("/")


def mark_pass_changed(db: Session, patient: Patient) -> None:
    """
    Marca el pase como actualizado. Se llama junto con cada cambio de
    puntos/sesiones (SOBRE la transacción en curso) para alimentar la
    cabecera Last-Modified y la comparación If-Modified-Since.
    """
    patient.wallet_updated_at = datetime.utcnow()


def _push_pass_update(tokens: List[str]) -> None:
    """
    Hilo worker (fire-and-forget): envía el push APNs a cada dispositivo
    registrado. No toca sesiones de BD ni bloquea la respuesta HTTP.
    Registra el resultado por dispositivo (solo el sufijo del token).
    """
    from .apns_push import send_pass_update_push

    ok = 0
    for token in tokens:
        suffix = f"...{token[-6:]}" if token else ""
        try:
            if send_pass_update_push(token):
                ok += 1
            else:
                logger.warning(f"[Fidelidad][APNS] Push rechazado u omitido (push={suffix})")
        except Exception as e:
            logger.warning(f"[Fidelidad][APNS] Push fallido (push={suffix}): {e}")
    logger.info(f"[Fidelidad][APNS] Push terminado: {ok}/{len(tokens)} notificaciones enviadas")


def maybe_sync_google_wallet(patient_id) -> None:
    """
    Dispara la sincronización asíncrona del paciente con Google Wallet
    tras un cambio de puntos/sesiones (fire-and-forget).

    Es best-effort y totalmente aislado de la transacción de BD: usa su
    propia sesión (SessionLocal) en un hilo daemon, nunca lanza
    excepciones y NO afecta si la integración está deshabilitada (en ese
    caso no hace absolutamente nada).
    """
    try:
        from .google_wallet_service import maybe_sync_patient_async

        maybe_sync_patient_async(patient_id)
    except Exception as e:
        logger.warning(f"[Fidelidad][GWallet] No se pudo sincronizar: {e}")


def notify_pass_update(db: Session, patient: Patient) -> int:
    """
    Notifica a los dispositivos con el pase registrado que hubo cambios,
    para que consulten /v1/passes/... y lo actualicen (push APNs).

    Es best-effort y asíncrono (thread daemon): nunca bloquea la
    respuesta y nunca lanza excepciones. El pase siempre se actualiza
    de todos modos en la siguiente consulta del web service.

    Returns:
        Número de push tokens recolectados (0 si no hay dispositivos).
    """
    tokens: List[str] = []
    registrations = []
    try:
        from ..models.pass_registration import PassRegistration

        query = db.query(PassRegistration).filter(
            PassRegistration.patient_id == str(patient.id),
            PassRegistration.deleted_at == None,
        )
        if patient.wallet_pass_id:
            query = query.filter(PassRegistration.serial_number == patient.wallet_pass_id)
        registrations = query.all()
        tokens = [reg.push_token for reg in registrations if reg.push_token]
    except Exception as e:
        logger.warning(f"[Fidelidad] No se pudo recolectar dispositivos registrados: {e}")
        return 0

    if not registrations:
        logger.warning(
            "[WALLET][PUSH] Sin dispositivos registrados para el pase "
            f"serial={patient.wallet_pass_id}. El dispositivo NO re-registró "
            "o el pase instalado aún no declara webServiceURL/authenticationToken."
        )
    elif not tokens:
        logger.warning(
            f"[WALLET][PUSH] {len(registrations)} dispositivo(s) registrado(s) "
            "pero sin push token APNs; no se puede notificar."
        )
    else:
        threading.Thread(target=_push_pass_update, args=(tokens,), daemon=True).start()
        logger.info(
            f"[WALLET][PUSH] Pase de {patient.id} (serial={patient.wallet_pass_id}): "
            f"push programado para {len(tokens)} dispositivo(s) registrado(s)"
        )
    return len(tokens)


def get_loyalty_config(tenant=None) -> dict:
    """
    Devuelve la configuración de fidelidad del tenant con valores por
    defecto. Acepta None para tolerar tenants creados antes de que
    existieran estos campos.
    """
    if tenant is None:
        return dict(DEFAULT_LOYALTY_CONFIG)
    return {
        "puntos_meta": getattr(tenant, "puntos_meta", None) or DEFAULT_PUNTOS_META,
        "premio_fidelidad": getattr(tenant, "premio_fidelidad", None) or DEFAULT_PREMIO_FIDELIDAD,
        "tarjeta_color_hex": getattr(tenant, "tarjeta_color_hex", None) or DEFAULT_TARJETA_COLOR_HEX,
    }


def _hex_to_rgb(hex_color: str) -> str:
    """
    Convierte un color hex (#RRGGBB) al formato rgb(r, g, b) que espera
    Apple Wallet en el pass.json. Devuelve el valor por defecto si el
    formato no es válido.
    """
    color = (hex_color or "").strip().lstrip("#")
    if len(color) != 6:
        return _hex_to_rgb(DEFAULT_TARJETA_COLOR_HEX)
    try:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    except ValueError:
        return _hex_to_rgb(DEFAULT_TARJETA_COLOR_HEX)
    return f"rgb({r}, {g}, {b})"


# ============================================================
# Bloqueo de fila del paciente (anti race conditions)
# ============================================================

def _lock_patient(db: Session, patient: Patient) -> Patient:
    """
    Relee y bloquea la fila del paciente con SELECT ... FOR UPDATE para
    que la secuencia leer-modificar-escribir de `puntos` y
    `sesiones_gratis` sea atómica entre peticiones concurrentes.

    - `with_for_update()` evita lost updates y doble-spend (dos escaneos
      o dos canjes simultáneos del mismo paciente).
    - `populate_existing()` fuerza a refrescar los atributos ya cargados
      en la identidad de la sesión (si no, se devolverían valores viejos).

    Raises:
        ValueError: Si el paciente no existe (o fue eliminado).
    """
    locked = (
        db.query(Patient)
        .filter(
            Patient.id == str(patient.id),
            Patient.deleted_at == None,  # noqa: E711
        )
        .with_for_update()
        .populate_existing()
        .first()
    )
    if locked is None:
        raise ValueError("Paciente no encontrado")
    return locked


# ============================================================
# Otorgamiento de puntos
# ============================================================

def award_loyalty_points(
    db: Session, patient: Patient, tenant=None, sync_google_wallet: bool = True
) -> dict:
    """
    Otorga PUNTOS_POR_CITA al paciente tras una cita completada.

    Regla de umbral: si los puntos alcanzan el puntos_meta del tenant
    (por defecto 10), se liquidan en su totalidad: puntos vuelve a 0
    (o al residuo si se superó el umbral) y sesiones_gratis se
    incrementa en el número de umbrales alcanzados.

    Args:
        tenant: opcional. Si no se pasa, se busca por patient.tenant_id
            (para mantener compatibilidad con los llamadores actuales).
        sync_google_wallet: si True (default), dispara la sincronización
            asíncrona del LoyaltyObject con Google Wallet (best-effort).
            El endpoint de scan pasa False porque realiza su propio PATCH
            síncrono justo después de este commit (evita dobles PATCH).

    Returns:
        dict con puntos, sesiones_gratis y si se otorgó sesión gratis.
    """
    config = get_loyalty_config(tenant)
    if tenant is None:
        tenant = db.query(Tenant).filter(Tenant.id == patient.tenant_id).first()
        config = get_loyalty_config(tenant)
    puntos_meta = config["puntos_meta"]

    # Bloquea la fila del paciente (SELECT ... FOR UPDATE) antes de
    # modificar el saldo: serializa awards concurrentes.
    patient = _lock_patient(db, patient)

    patient.puntos = (patient.puntos or 0) + PUNTOS_POR_CITA

    umbrales = patient.puntos // puntos_meta
    sesion_otorgada = umbrales > 0
    if umbrales > 0:
        patient.sesiones_gratis = (patient.sesiones_gratis or 0) + umbrales
        patient.puntos = patient.puntos % puntos_meta

    # El pase cambió: marca para Last-Modified / If-Modified-Since.
    mark_pass_changed(db, patient)
    db.commit()
    db.refresh(patient)

    logger.info(
        f"[Fidelidad] Paciente {patient.id}: +{PUNTOS_POR_CITA} estrella(s), "
        f"puntos={patient.puntos}, meta={puntos_meta}, "
        f"sesiones_gratis={patient.sesiones_gratis}"
    )

    # Notifica a los dispositivos registrados (push APNs, best-effort).
    notify_pass_update(db, patient)

    # Notificación interna al staff cuando se otorga una recompensa.
    if sesion_otorgada:
        notification_service.notify_loyalty_reward(
            db, patient, config["premio_fidelidad"], umbrales
        )

    if sync_google_wallet:
        # Sincroniza la tarjeta en Google Wallet (async, best-effort, nunca
        # lanza y no hace nada si la integración está deshabilitada). Así,
        # una estrella otorgada desde la completación de una cita también
        # actualiza la tarjeta del paciente automáticamente.
        maybe_sync_google_wallet(patient.id)

    return {
        "puntos": patient.puntos,
        "sesiones_gratis": patient.sesiones_gratis,
        "puntos_otorgados": PUNTOS_POR_CITA,
        "puntos_meta": puntos_meta,
        "estrellas": f"{patient.puntos} / {puntos_meta} Estrellas",
        "premio": config["premio_fidelidad"],
        "sesion_gratis_otorgada": sesion_otorgada,
    }


# ============================================================
# Canje de una sesión gratuita
# ============================================================

def redeem_free_session(db: Session, patient: Patient) -> dict:
    """
    Decrementa sesiones_gratis en 1 cuando el paciente usa una sesión gratis.

    Raises:
        ValueError: Si el paciente no tiene sesiones gratuitas disponibles
    """
    # Bloquea la fila del paciente: el chequeo + decremento deben ser
    # atómicos para que dos canjes concurrentes no consuman la misma sesión.
    patient = _lock_patient(db, patient)

    if (patient.sesiones_gratis or 0) <= 0:
        db.rollback()  # libera el lock antes de devolver el error
        raise ValueError("El paciente no tiene sesiones gratuitas disponibles")

    patient.sesiones_gratis -= 1
    # El pase cambió: marca para Last-Modified / If-Modified-Since.
    mark_pass_changed(db, patient)
    db.commit()
    db.refresh(patient)

    logger.info(f"[Fidelidad] Paciente {patient.id}: canjeó una sesión gratis "
                f"(restantes={patient.sesiones_gratis})")

    # Notifica a los dispositivos registrados (push APNs, best-effort).
    notify_pass_update(db, patient)

    # Sincroniza con Google Wallet (async, best-effort, nunca bloquea).
    maybe_sync_google_wallet(patient.id)

    return {
        "message": "Sesión gratuita canjeada exitosamente",
        "puntos": patient.puntos or 0,
        "sesiones_gratis": patient.sesiones_gratis,
    }


# ============================================================
# Token de pase digital (cryptográfico y único)
# ============================================================

def generate_wallet_pass_token(db: Session, length: int = 64) -> str:
    """
    Genera un token cryptográficamente seguro y único para el pase digital.

    Usa secrets.token_urlsafe (48 bytes -> 64 caracteres url-safe).
    Garantiza unicidad consultando la columna wallet_pass_id de patients.
    """
    while True:
        token = secrets.token_urlsafe(48)[:length]
        exists = db.query(Patient.id).filter(Patient.wallet_pass_id == token).first()
        if not exists:
            return token


def generate_wallet_auth_token(db: Session, length: int = 64) -> str:
    """
    Genera el authenticationToken del pase para el Apple Wallet Web
    Service (cabecera 'Authorization: ApplePass <token>').

    Se genera de forma INDEPENDIENTE del wallet_pass_id (nunca derivado
    de él) y es único consultando la columna wallet_auth_token.
    """
    while True:
        token = secrets.token_urlsafe(48)[:length]
        exists = db.query(Patient.id).filter(Patient.wallet_auth_token == token).first()
        if not exists:
            return token


def ensure_wallet_pass(db: Session, patient: Patient) -> str:
    """
    Devuelve el wallet_pass_id del paciente, generándolo y persistiéndolo
    si aún no existe. Es el identificador estable de su pase en las wallets.

    También asegura el wallet_auth_token (web service de Apple): así los
    pacientes anteriores a la migración 0007 quedan habilitados para
    actualizaciones dinámicas en su próxima descarga del pase.
    """
    changed = False
    if not patient.wallet_pass_id:
        patient.wallet_pass_id = generate_wallet_pass_token(db)
        changed = True
    if not patient.wallet_auth_token:
        patient.wallet_auth_token = generate_wallet_auth_token(db)
        changed = True

    if changed:
        db.commit()
        db.refresh(patient)
        logger.info(
            f"[Fidelidad] Paciente {patient.id}: pase generado "
            f"(wallet_pass_id={patient.wallet_pass_id})"
        )
    return patient.wallet_pass_id


# ============================================================
# Enlace público de la tarjeta (compartir con el cliente)
# ============================================================

# TTL del enlace público de la tarjeta. El personal puede regenerarlo
# simplemente volviendo a pulsar "Compartir Tarjeta".
WALLET_SHARE_TTL_DAYS = 7


def generate_wallet_share_token(db: Session, length: int = 64) -> str:
    """
    Genera un token de capacidad CSPRNG y único para el enlace público
    de la tarjeta (/tarjeta/{token}). Se guarda en wallet_share_token.
    """
    while True:
        token = secrets.token_urlsafe(48)[:length]
        exists = db.query(Patient.id).filter(Patient.wallet_share_token == token).first()
        if not exists:
            return token


def ensure_wallet_share_token(
    db: Session, patient: Patient, ttl_days: int = WALLET_SHARE_TTL_DAYS
) -> str:
    """
    Devuelve el token del enlace público del paciente, generándolo (o
    renovándolo si expiró) si hace falta. Cada generación establece una
    nueva expiración de `ttl_days` días.
    """
    now = datetime.utcnow()
    if (
        not patient.wallet_share_token
        or patient.wallet_share_expires_at is None
        or patient.wallet_share_expires_at <= now
    ):
        patient.wallet_share_token = generate_wallet_share_token(db)
        patient.wallet_share_expires_at = now + timedelta(days=ttl_days)
        db.commit()
        db.refresh(patient)
        logger.info(
            f"[Fidelidad] Paciente {patient.id}: enlace público generado "
            f"(expira {patient.wallet_share_expires_at} UTC)"
        )
    return patient.wallet_share_token


def get_patient_by_share_token(db: Session, token: str) -> Optional[Patient]:
    """
    Resuelve el paciente a partir del token del enlace público.
    Devuelve None si el token es vacío, no existe, expiró, fue eliminado
    o el paciente está inactivo (nunca revela cuál de los casos es).
    """
    norm = (token or "").strip()
    if not norm:
        return None
    now = datetime.utcnow()
    return db.query(Patient).filter(
        Patient.wallet_share_token == norm,
        Patient.wallet_share_expires_at != None,  # noqa: E711
        Patient.wallet_share_expires_at > now,
        Patient.deleted_at == None,  # noqa: E711
        Patient.is_active == True,  # noqa: E712
    ).first()


# ============================================================
# Datos estructurados de fidelidad y pase
# ============================================================

def build_loyalty_summary(patient: Patient, config: Optional[dict] = None) -> dict:
    """Resumen del estado de fidelidad del paciente (para UI y pases)."""
    config = config or dict(DEFAULT_LOYALTY_CONFIG)
    puntos_meta = config["puntos_meta"]
    premio = config["premio_fidelidad"]

    puntos = patient.puntos or 0
    sesiones = patient.sesiones_gratis or 0
    tiene_sesion_gratis = sesiones > 0

    return {
        "puntos": puntos,
        "sesiones_gratis": sesiones,
        "puntos_meta": puntos_meta,
        "premio": premio,
        "progreso": min(puntos, puntos_meta) * 100 // puntos_meta,
        "estrellas": f"{puntos} / {puntos_meta} Estrellas",
        "tiene_sesion_gratis": tiene_sesion_gratis,
        "mensaje": "¡Sesión Gratis Disponible!" if tiene_sesion_gratis
        else f"{puntos} / {puntos_meta} Estrellas",
    }


def build_pass_data(patient: Patient, tenant=None, tenant_name: Optional[str] = None) -> dict:
    """
    Estructura JSON del pase digital (fallback Google Wallet / metadata).

    Contiene los datos del pase tipo tarjeta (storeCard) que usan tanto
    el JSON de Google Wallet como la generación del .pkpass de Apple.
    """
    summary = build_loyalty_summary(patient, get_loyalty_config(tenant))
    name = tenant_name or (tenant.nombre if tenant else "SPA")
    return {
        "wallet_pass_id": patient.wallet_pass_id,
        "puntos": summary["puntos"],
        "sesiones_gratis": summary["sesiones_gratis"],
        "estrellas": summary["estrellas"],
        "progreso": summary["progreso"],
        "premio": summary["premio"],
        "tiene_sesion_gratis": summary["tiene_sesion_gratis"],
        "pase": {
            "tipo": "storeCard",
            "formato": "pkpass",
            "organization_name": name,
            "serial_number": patient.wallet_pass_id,
            "pass_type_identifier": PASS_TYPE_IDENTIFIER,
            "team_identifier": TEAM_IDENTIFIER,
        },
    }


# ============================================================
# Generación del archivo Apple Wallet (.pkpass)
# ============================================================

def _pkpass_fields(patient: Patient, tenant=None, tenant_name: Optional[str] = None) -> dict:
    """Campos del pase para la tarjeta de fidelidad (Apple Wallet)."""
    config = get_loyalty_config(tenant)
    summary = build_loyalty_summary(patient, config)
    name = tenant_name or (tenant.nombre if tenant else "SPA")
    estado = summary["mensaje"]
    backgroundColor = _hex_to_rgb(config["tarjeta_color_hex"])
    pass_fields = {
        "formatVersion": 1,
        "passTypeIdentifier": PASS_TYPE_IDENTIFIER,
        "serialNumber": patient.wallet_pass_id,
        "teamIdentifier": TEAM_IDENTIFIER,
        "organizationName": name,
        "description": summary["premio"],
        "logoText": name,
        "foregroundColor": "rgb(255, 255, 255)",
        "backgroundColor": backgroundColor,
        "labelColor": "rgb(255, 255, 255)",
        "storeCard": {
            "headerFields": [
                {
                    "key": "sesion_gratis",
                    "label": "Sesión Gratis",
                    "value": summary["sesiones_gratis"],
                    "textAlignment": "PKTextAlignmentRight",
                }
            ],
            "primaryFields": [
                {
                    "key": "estrellas",
                    "label": "Fidelidad",
                    "value": estado,
                }
            ],
            "secondaryFields": [
                {
                    "key": "puntos",
                    "label": "Estrellas",
                    "value": summary["puntos"],
                    "textAlignment": "PKTextAlignmentCenter",
                },
                {
                    "key": "progreso",
                    "label": f"de {summary['puntos_meta']}",
                    "value": summary["puntos"],
                    "textAlignment": "PKTextAlignmentCenter",
                },
            ],
            "backFields": [
                {
                    "key": "paciente",
                    "label": "Paciente",
                    "value": f"{patient.nombre} {patient.apellido}".strip(),
                },
                {
                    "key": "premio",
                    "label": "Premio",
                    "value": summary["premio"],
                },
                {
                    "key": "pass_id",
                    "label": "ID del Pase",
                    "value": patient.wallet_pass_id,
                },
            ],
        },
        "barcodes": [
            {
                "format": "PKBarcodeFormatQR",
                "message": f"{PASS_TYPE_IDENTIFIER}/{patient.wallet_pass_id}",
                "messageEncoding": "iso-8859-1",
            }
        ],
    }

    # Apple Wallet Web Service: solo se declara webServiceURL si existe el
    # authenticationToken Y una URL base pública configurada (son
    # inseparables en pass.json). Ambos permiten que el dispositivo se
    # registre y reciba pases actualizados.
    if patient.wallet_auth_token and _wallet_service_url():
        pass_fields["webServiceURL"] = _wallet_service_url()
        pass_fields["authenticationToken"] = patient.wallet_auth_token

    return pass_fields


def build_pkpass_zip(patient: Patient, tenant=None, tenant_name: Optional[str] = None) -> bytes:
    """
    Construye el archivo .pkpass (zip) de Apple Wallet en memoria.

    Contiene pass.json (datos del pase), manifest.json (hashes SHA1 de
    cada archivo) y, si hay certificados configurados para firmar, la
    firma PKCS#7/CMS (signature) de manifest.json. Sin credenciales el
    pase se genera sin firma (warning en logs) para mantener el flujo
    de prueba actual hasta que se emitan los certificados oficiales.

    Returns:
        bytes del archivo .pkpass
    """
    pass_json = _pkpass_fields(patient, tenant, tenant_name)
    pass_bytes = json.dumps(pass_json, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    manifest = {
        "pass.json": hashlib.sha1(pass_bytes).hexdigest(),
    }
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    signature_bytes = None
    if is_signing_configured():
        signature_bytes = sign_manifest(manifest_bytes)
        if signature_bytes is None:
            logger.warning("[WALLET][PKPASS] No se pudo firmar el pase; se entrega sin firma")
    else:
        warn_if_unconfigured()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("pass.json", pass_bytes)
        zf.writestr("manifest.json", manifest_bytes)
        if signature_bytes:
            zf.writestr("signature", signature_bytes)

    return buffer.getvalue()


# ============================================================
# Buscar paciente por pase (escáner de tarjetas de fidelidad)
# ============================================================

def get_patient_by_wallet_pass(db: Session, tenant_id: str, wallet_pass_id: str):
    """
    Busca un paciente dentro del tenant por su wallet_pass_id (el
    identificador del pase que el escáner lee del QR de la tarjeta).
    """
    norm_id = (wallet_pass_id or "").strip()
    if not norm_id:
        return None
    return db.query(Patient).filter(
        Patient.tenant_id == tenant_id,
        Patient.wallet_pass_id == norm_id,
        Patient.deleted_at == None,
    ).first()