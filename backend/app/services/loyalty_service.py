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
import zipfile
from typing import Optional

from sqlalchemy.orm import Session

from ..models.patient import Patient
from ..models.tenant import Tenant

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
# Otorgamiento de puntos
# ============================================================

def award_loyalty_points(db: Session, patient: Patient, tenant=None) -> dict:
    """
    Otorga PUNTOS_POR_CITA al paciente tras una cita completada.

    Regla de umbral: si los puntos alcanzan el puntos_meta del tenant
    (por defecto 10), se liquidan en su totalidad: puntos vuelve a 0
    (o al residuo si se superó el umbral) y sesiones_gratis se
    incrementa en el número de umbrales alcanzados.

    Args:
        tenant: opcional. Si no se pasa, se busca por patient.tenant_id
            (para mantener compatibilidad con los llamadores actuales).

    Returns:
        dict con puntos, sesiones_gratis y si se otorgó sesión gratis.
    """
    config = get_loyalty_config(tenant)
    if tenant is None:
        tenant = db.query(Tenant).filter(Tenant.id == patient.tenant_id).first()
        config = get_loyalty_config(tenant)
    puntos_meta = config["puntos_meta"]

    patient.puntos = (patient.puntos or 0) + PUNTOS_POR_CITA

    umbrales = patient.puntos // puntos_meta
    sesion_otorgada = umbrales > 0
    if umbrales > 0:
        patient.sesiones_gratis = (patient.sesiones_gratis or 0) + umbrales
        patient.puntos = patient.puntos % puntos_meta

    db.commit()
    db.refresh(patient)

    logger.info(
        f"[Fidelidad] Paciente {patient.id}: +{PUNTOS_POR_CITA} estrella(s), "
        f"puntos={patient.puntos}, meta={puntos_meta}, "
        f"sesiones_gratis={patient.sesiones_gratis}"
    )

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
    if (patient.sesiones_gratis or 0) <= 0:
        raise ValueError("El paciente no tiene sesiones gratuitas disponibles")

    patient.sesiones_gratis -= 1
    db.commit()
    db.refresh(patient)

    logger.info(f"[Fidelidad] Paciente {patient.id}: canjeó una sesión gratis "
                f"(restantes={patient.sesiones_gratis})")

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


def ensure_wallet_pass(db: Session, patient: Patient) -> str:
    """
    Devuelve el wallet_pass_id del paciente, generándolo y persistiéndolo
    si aún no existe. Es el identificador estable de su pase en las wallets.
    """
    if patient.wallet_pass_id:
        return patient.wallet_pass_id

    patient.wallet_pass_id = generate_wallet_pass_token(db)
    db.commit()
    db.refresh(patient)

    logger.info(f"[Fidelidad] Paciente {patient.id}: pase generado (wallet_pass_id={patient.wallet_pass_id})")
    return patient.wallet_pass_id


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
    return {
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


def build_pkpass_zip(patient: Patient, tenant=None, tenant_name: Optional[str] = None) -> bytes:
    """
    Construye el archivo .pkpass (zip) de Apple Wallet en memoria.

    Contiene pass.json (datos del pase) y manifest.json (hashes SHA1 de
    cada archivo). La firma (signature) con los certificados de Apple se
    agregará en una fase posterior una vez registrados los IDs oficiales.

    Returns:
        bytes del archivo .pkpass
    """
    pass_json = _pkpass_fields(patient, tenant, tenant_name)
    pass_bytes = json.dumps(pass_json, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    manifest = {
        "pass.json": hashlib.sha1(pass_bytes).hexdigest(),
    }
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("pass.json", pass_bytes)
        zf.writestr("manifest.json", manifest_bytes)

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