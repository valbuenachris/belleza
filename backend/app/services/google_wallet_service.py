# ============================================================
# backend/app/services/google_wallet_service.py - Google Wallet API
# Integración REAL con Google Wallet (LoyaltyClass / LoyaltyObject)
#
# Autenticación:
#   - Application Default Credentials (google-auth): lee la variable
#     GOOGLE_APPLICATION_CREDENTIALS apuntando al .json de la cuenta de
#     servicio (montado en el contenedor). Fallback: la variable propia
#     GOOGLE_WALLET_SERVICE_ACCOUNT_FILE o GOOGLE_WALLET_PRIVATE_KEY.
#   - Scope: https://www.googleapis.com/auth/wallet_object.issuer
#
# Operaciones:
#   - update_loyalty_object(): PATCH del LoyaltyObject (balance de puntos
#     y sesiones gratis) tras guardar en BD. Es la integración principal
#     requerida en el endpoint de scan. Fail-safe: nunca lanza.
#   - ensure_loyalty_class() / get_or_create_object(): crean la clase y
#     el objeto si aún no existen (GET -> 404 -> INSERT).
#   - generate_save_url(): enlace oficial "Añadir a Google Wallet"
#     (https://pay.google.com/gp/v/save/{jwt}) firmado con la clave de
#     la cuenta de servicio (claims iss/aud="google"/typ="savetowallet").
#
# REGLAS DE SEGURIDAD:
#   - Nunca se registran claves privadas, JWT de guardado ni credenciales.
#   - Si GOOGLE_WALLET_ENABLED=false no se hace NINGUNA llamada a Google.
#   - La falla de Google JAMÁS interrumpe el flujo principal de la app:
#     toda operación devuelve bool y los errores se registran.
# ============================================================

import base64
import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse

from jose import jwt as jose_jwt
from sqlalchemy.orm import Session

from ..config import settings
from ..models.patient import Patient
from ..models.tenant import Tenant

logger = logging.getLogger(__name__)

# Cache de credenciales / cliente (hilo seguro).
_credentials = None
_client = None
_client_lock = threading.Lock()

# Id de la clase confirmado en memoria (evita re-GETs repetidos).
_class_cache: Dict[str, str] = {}


# ============================================================
# Estado de la integración
# ============================================================

def is_enabled() -> bool:
    """True si la integración está activa (env GOOGLE_WALLET_ENABLED)."""
    return bool(settings.GOOGLE_WALLET_ENABLED)


def _credentials_file() -> Optional[str]:
    """
    Ruta al .json de la cuenta de servicio. Prioridad:
    GOOGLE_APPLICATION_CREDENTIALS (ADC estándar) y después la variable
    propia GOOGLE_WALLET_SERVICE_ACCOUNT_FILE.
    """
    for var in ("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_WALLET_SERVICE_ACCOUNT_FILE"):
        path = (getattr(settings, var, "") or "").strip()
        if path:
            return path
    return None


def _load_private_key() -> Optional[str]:
    """
    Clave privada RSA de la cuenta de servicio (para el JWT de guardado).
    Se lee de: GOOGLE_WALLET_PRIVATE_KEY (PEM o base64) o del campo
    private_key del .json apuntado por GOOGLE_APPLICATION_CREDENTIALS /
    GOOGLE_WALLET_SERVICE_ACCOUNT_FILE.
    """
    raw = (settings.GOOGLE_WALLET_PRIVATE_KEY or "").strip()
    if raw:
        if raw.startswith("-----BEGIN"):
            return raw
        try:
            decoded = base64.b64decode(raw).decode("utf-8")
            if decoded.startswith("-----BEGIN"):
                return decoded
        except Exception:
            pass
        return raw  # mejor esfuerzo

    path = _credentials_file()
    if path:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            key = (data.get("private_key") or "").strip()
            if key:
                return key
        except Exception as exc:
            logger.warning(f"[GWallet] No se pudo leer {path}: {exc}")
    return None


def is_configured() -> bool:
    """
    True si hay credenciales suficientes (issuer id + clave privada o
    archivo de la cuenta de servicio existente). No valida contra Google
    (eso se detecta al primer request y se registra).
    """
    if not settings.GOOGLE_WALLET_ISSUER_ID:
        return False
    if _load_private_key():
        return True
    path = _credentials_file()
    return bool(path and os.path.exists(path))


def missing_config_fields() -> List[str]:
    """Campos requeridos sin valor (para el endpoint de diagnóstico)."""
    missing = []
    if not settings.GOOGLE_WALLET_ISSUER_ID:
        missing.append("GOOGLE_WALLET_ISSUER_ID")
    if not _load_private_key():
        path = _credentials_file()
        if not path:
            missing.append(
                "GOOGLE_APPLICATION_CREDENTIALS (o GOOGLE_WALLET_SERVICE_ACCOUNT_FILE "
                "o GOOGLE_WALLET_PRIVATE_KEY)"
            )
        elif not os.path.exists(path):
            missing.append(f"Archivo de credenciales no encontrado: {path}")
    return missing


def origin() -> str:
    """
    Claim 'origins' del JWT de guardado (dominios, sin esquema).
    Se deriva del host de WALLET_WEB_SERVICE_BASE_URL si no se configura
    GOOGLE_WALLET_ORIGIN explícitamente.
    """
    explicit = (settings.GOOGLE_WALLET_ORIGIN or "").strip()
    if explicit:
        return explicit.replace("https://", "").replace("http://", "").rstrip("/")
    base = (settings.WALLET_WEB_SERVICE_BASE_URL or "").strip()
    host = urlparse(base if "://" in base else f"https://{base}").netloc
    return host.split(":")[0] or ""


# ============================================================
# Credenciales ADC y cliente de la API de Google
# ============================================================

def _get_credentials():
    """
    Credenciales de la cuenta de servicio desde GOOGLE_APPLICATION_CREDENTIALS
    (o GOOGLE_WALLET_SERVICE_ACCOUNT_FILE) con el scope de wallet objects.
    Se refrescan de forma agresiva para fallar rápido con credenciales malas.
    """
    global _credentials

    if _credentials is not None:
        return _credentials

    path = _credentials_file()
    if not path:
        raise RuntimeError(
            "No se encontró el archivo de credenciales: "
            "GOOGLE_APPLICATION_CREDENTIALS (o GOOGLE_WALLET_SERVICE_ACCOUNT_FILE)"
        )
    if not os.path.exists(path):
        raise RuntimeError(f"Archivo de credenciales no encontrado en la ruta: {path}")

    from google.oauth2 import service_account
    from google.auth.transport.requests import Request

    _credentials = service_account.Credentials.from_service_account_file(
        path, scopes=[settings.GOOGLE_WALLET_SCOPE]
    )
    # Refresco inmediato: falla rápido si la cuenta no tiene permisos/scope.
    _credentials.refresh(Request())
    return _credentials


def _get_client():
    """
    Cliente de discovery para walletobjects v1 (google-api-python-client).
    Se cachea a nivel de proceso; se cache_discovery=False para no escribir
    ficheros en el contenedor (volumen de solo lectura).
    """
    global _client

    if _client is not None:
        return _client

    with _client_lock:
        if _client is None:
            from googleapiclient.discovery import build

            _client = build(
                "walletobjects",
                "v1",
                credentials=_get_credentials(),
                cache_discovery=False,
            )
        return _client


# ============================================================
# Ids (formato oficial: {issuer_id}.{suffix})
# ============================================================

def class_id(tenant: Tenant) -> str:
    """Id de la clase de fidelidad (override manual o per-tenant)."""
    override = (settings.GOOGLE_WALLET_CLASS_ID or "").strip()
    if override:
        return override
    return f"{settings.GOOGLE_WALLET_ISSUER_ID}.loyalty-class-{tenant.id}"


def object_id(patient: Patient) -> str:
    """Id del objeto de fidelidad (estable por paciente)."""
    return f"{settings.GOOGLE_WALLET_ISSUER_ID}.{patient.id}"


# ============================================================
# Construcción de payloads (LoyaltyClass / LoyaltyObject)
# ============================================================

def build_class(tenant: Tenant, config: dict, cls_id: str) -> dict:
    """JSON de la LoyaltyClass para insert/update."""
    name = tenant.nombre or "SPA"
    description = (
        f"Programa de fidelidad de {name}: gana {config['puntos_meta']} estrellas "
        f"y canjea {config['premio_fidelidad'].lower()}"
    )
    loyalty_class: dict = {
        "id": cls_id,
        "issuerName": name,
        "programName": name,
        "reviewStatus": "UNDER_REVIEW",
        "accountNameLabel": "Paciente",
        "accountIdLabel": "Nº de cliente",
        "programDescription": {
            "defaultValue": {"language": "es", "value": description}
        },
    }
    if tenant.logo_url:
        loyalty_class["programLogo"] = {
            "sourceUri": {"uri": tenant.logo_url},
            "contentDescription": {
                "defaultValue": {"language": "es", "value": f"Logo de {name}"}
            },
        }
    homepage = (settings.WALLET_WEB_SERVICE_BASE_URL or "").rstrip()
    if homepage:
        loyalty_class["homepageUri"] = {"uri": homepage}
    return loyalty_class


def build_object(patient: Patient, cls_id: str, obj_id: str, config: dict) -> dict:
    """JSON del LoyaltyObject (insert). Usa el MISMO QR que Apple Wallet
    para que el escáner de recepción siga funcionando con ambas tarjetas."""
    data = _summary_data(patient, config)
    return {
        "id": obj_id,
        "classId": cls_id,
        "state": "ACTIVE",
        "accountName": f"{patient.nombre} {patient.apellido}".strip()[:90],
        "accountId": str(patient.id)[:20],
        "barcode": {
            "type": "QR_CODE",
            "value": f"pass.com.tuuspa.fidelidad/{patient.wallet_pass_id}",
            "alternateText": f"{data['puntos']} {data['estrellas']}",
        },
        "loyaltyPoints": {
            "label": "Estrellas",
            "balance": {"string": str(data["puntos"])},
        },
        "textModulesData": [
            {"id": "progreso", "header": "Progreso", "body": data["estrellas"]},
            {"id": "premio", "header": "Premio", "body": data["premio"]},
            {"id": "sesiones", "header": "Sesiones gratis", "body": str(data["sesiones"])},
        ],
        "infoModuleData": {
            "showLastUpdateTime": True,
            "labelValueRows": [
                {"label": "Estrellas", "value": str(data["puntos"])},
                {"label": "Meta", "value": f"{data['meta']} estrellas"},
                {"label": "Sesiones gratis", "value": str(data["sesiones"])},
            ],
        },
        "messages": [],
    }


def _summary_data(patient: Patient, config: dict) -> dict:
    return _summary_from_values(
        patient.puntos or 0, patient.sesiones_gratis or 0, config
    )


def _summary_from_values(points: int, free_sessions: int, config: dict) -> dict:
    puntos = int(points or 0)
    sesiones = int(free_sessions or 0)
    meta = config["puntos_meta"]
    return {
        "puntos": puntos,
        "sesiones": sesiones,
        "meta": meta,
        "estrellas": f"{puntos} / {meta} Estrellas",
        "premio": config["premio_fidelidad"],
    }


def _patch_payload(points: int, free_sessions: int, config: dict) -> dict:
    """Cuerpo del PATCH (balance + textos), listo para añadir notifyPreference."""
    data = _summary_from_values(points, free_sessions, config)
    return {
        "loyaltyPoints": {
            "label": "Estrellas",
            "balance": {"string": str(data["puntos"])},
        },
        "textModulesData": [
            {"id": "progreso", "header": "Progreso", "body": data["estrellas"]},
            {"id": "premio", "header": "Premio", "body": data["premio"]},
            {"id": "sesiones", "header": "Sesiones gratis", "body": str(data["sesiones"])},
        ],
        "infoModuleData": {
            "showLastUpdateTime": True,
            "labelValueRows": [
                {"label": "Estrellas", "value": str(data["puntos"])},
                {"label": "Meta", "value": f"{data['meta']} estrellas"},
                {"label": "Sesiones gratis", "value": str(data["sesiones"])},
            ],
        },
    }


def _is_http_error(exc: Exception, status: Optional[int] = None) -> bool:
    """Detecta googleapiclient.errors.HttpError (y opcionalmente el status)."""
    try:
        from googleapiclient.errors import HttpError  # noqa: F401
    except ImportError:
        return False
    if isinstance(exc, HttpError):
        if status is None:
            return True
        return exc.resp.status == status
    return False


# ============================================================
# Operaciones sobre la REST API (google-api-python-client)
# ============================================================

def ensure_loyalty_class(tenant: Tenant, config: dict) -> str:
    """
    Asegura que la LoyaltyClass exista en Google (get; si 404, insert).
    Devuelve el class id. reviewStatus=UNDER_REVIEW es lo que documenta
    Google para contenido creado/actualizado programáticamente.
    """
    cls_id = class_id(tenant)
    if _class_cache.get(cls_id):
        return cls_id

    try:
        _get_client().loyaltyclass().get(resourceId=cls_id).execute()
        _class_cache[cls_id] = cls_id
        return cls_id
    except Exception as exc:
        if not _is_http_error(exc, 404):
            raise RuntimeError(
                f"Error consultando LoyaltyClass {cls_id}: {_exc_summary(exc)}"
            )

    try:
        _get_client().loyaltyclass().insert(
            body=build_class(tenant, config, cls_id)
        ).execute()
        _class_cache[cls_id] = cls_id
        logger.info(f"[GWallet] Clase de fidelidad creada: {cls_id}")
        return cls_id
    except Exception as exc:
        if _is_http_error(exc, 409):
            # Ya existía entre el GET y el INSERT (race): usar la existente.
            _class_cache[cls_id] = cls_id
            return cls_id
        raise RuntimeError(
            f"Error creando LoyaltyClass {cls_id}: {_exc_summary(exc)}"
        )


def get_or_create_object(patient: Patient, cls_id: str, config: dict) -> str:
    """
    Asegura que exista el LoyaltyObject del paciente (get; si 404, insert).
    Devuelve el object id.
    """
    obj_id = object_id(patient)

    try:
        _get_client().loyaltyobject().get(resourceId=obj_id).execute()
        logger.debug(f"[GWallet] Objeto {obj_id} ya existe")
        return obj_id
    except Exception as exc:
        if not _is_http_error(exc, 404):
            raise RuntimeError(
                f"Error consultando LoyaltyObject {obj_id}: {_exc_summary(exc)}"
            )

    try:
        _get_client().loyaltyobject().insert(
            body=build_object(patient, cls_id, obj_id, config)
        ).execute()
        logger.info(f"[GWallet] Objeto de fidelidad creado: {obj_id}")
        return obj_id
    except Exception as exc:
        if _is_http_error(exc, 409):
            return obj_id  # race: ya lo creó otro hilo
        raise RuntimeError(
            f"Error creando LoyaltyObject {obj_id}: {_exc_summary(exc)}"
        )


def _patch_object(obj_id: str, payload: dict) -> None:
    """
    PATCH del objeto. Con notifyPreference=NOTIFY (efímero, en CADA PATCH)
    Google empuja una notificación al dispositivo del usuario (balance es
    un campo permitido). Si Google rechaza el notify (cuota u otro), se
    reintenta SIN él para que el saldo quede en sincronía igualmente.
    """
    notify_payload = {**payload, "notifyPreference": "NOTIFY"}
    try:
        _get_client().loyaltyobject().patch(resourceId=obj_id, body=notify_payload).execute()
        return
    except Exception as exc:
        if _is_http_error(exc):  # resp.status en (400,403,...)
            logger.warning(
                f"[GWallet] PATCH de {obj_id} rechazado con notifyPreference; "
                f"reintento sin notificación: {_exc_summary(exc)}"
            )
        else:
            raise RuntimeError(
                f"Error actualizando LoyaltyObject {obj_id}: {_exc_summary(exc)}"
            )

    try:
        _get_client().loyaltyobject().patch(resourceId=obj_id, body=payload).execute()
    except Exception as exc:
        raise RuntimeError(
            f"Error actualizando LoyaltyObject {obj_id}: {_exc_summary(exc)}"
        )


# ============================================================
# API pública requerida: actualiza el LoyaltyObject del paciente
# ============================================================

def update_loyalty_object(patient_id: str, points: int, free_sessions: int) -> bool:
    """
    PATCH del LoyaltyObject del paciente en Google Wallet con el saldo de
    puntos y las sesiones gratis actuales. Se llama DESPUÉS de guardar en
    la base de datos (endpoint de scan).

    Fail-safe: NUNCA lanza al llamador. Devuelve True si se completó.
    Carga su propia sesión de BD (valores frescos post-commit) y registra:
    info en éxito, warning/error en fallo.

    Args:
        patient_id: UUID del paciente (columna patients.id).
        points: saldo de estrellas actual del paciente.
        free_sessions: sesiones gratuitas disponibles actuales.
    """
    if not (is_enabled() and is_configured()):
        logger.debug(
            "[GWallet] update_loyalty_object omitido (GOOGLE_WALLET_ENABLED=false "
            "o credenciales incompletas)"
        )
        return False

    from ..database import SessionLocal
    from .loyalty_service import ensure_wallet_pass, get_loyalty_config

    obj_id: Optional[str] = None
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(
            Patient.id == str(patient_id),
            Patient.deleted_at == None,  # noqa: E711
        ).first()
        if not patient:
            logger.warning(f"[GWallet] Paciente {patient_id} no encontrado para actualizar")
            return False

        tenant = db.query(Tenant).filter(Tenant.id == patient.tenant_id).first()
        config = get_loyalty_config(tenant)

        # Garantiza el wallet_pass_id (QR del pase) y el objeto en Google.
        ensure_wallet_pass(db, patient)
        cls_id = ensure_loyalty_class(tenant, config)
        obj_id = get_or_create_object(patient, cls_id, config)

        _patch_object(obj_id, _patch_payload(points, free_sessions, config))

        patient.google_wallet_class_id = cls_id
        patient.google_wallet_object_id = obj_id
        patient.google_wallet_updated_at = datetime.utcnow()
        db.commit()

        logger.info(
            f"[GWallet] LoyaltyObject {obj_id} actualizado: "
            f"puntos={points}, sesiones_gratis={free_sessions}"
        )
        return True
    except Exception as exc:
        logger.warning(
            f"[GWallet] No se pudo actualizar el LoyaltyObject del paciente "
            f"{patient_id}: {exc}"
        )
        return False
    finally:
        db.close()


# ============================================================
# Sincronización completa (worker del hilo asíncrono)
# ============================================================

def sync_patient(db: Session, patient: Patient, tenant: Optional[Tenant], config: Optional[dict] = None) -> bool:
    """
    Sincroniza el estado del paciente con Google Wallet (misma lógica que
    update_loyalty_object pero reutilizando un paciente ya cargado en una
    sesión). Se usa desde el hilo asíncrono para canjes y generación de
    enlaces.
    """
    from .loyalty_service import get_loyalty_config

    if not (is_enabled() and is_configured()):
        logger.debug("[GWallet] Sincronización omitida (no habilitado/configurado)")
        return False

    if tenant is None:
        tenant = db.query(Tenant).filter(Tenant.id == patient.tenant_id).first()
    config = config or get_loyalty_config(tenant)

    try:
        cls_id = ensure_loyalty_class(tenant, config)
        obj_id = get_or_create_object(patient, cls_id, config)
        _patch_object(obj_id, _patch_payload(patient.puntos or 0, patient.sesiones_gratis or 0, config))

        patient.google_wallet_class_id = cls_id
        patient.google_wallet_object_id = obj_id
        patient.google_wallet_updated_at = datetime.utcnow()
        db.commit()
        logger.info(
            f"[GWallet] Paciente {patient.id} sincronizado (object={obj_id}, "
            f"puntos={patient.puntos or 0})"
        )
        return True
    except Exception as exc:
        logger.warning(f"[GWallet] Sincronización fallida para paciente {patient.id}: {exc}")
        return False


def _sync_worker(patient_id: str) -> None:
    """Ejecuta sync_patient en su propia sesión de BD (hilo daemon)."""
    from ..database import SessionLocal

    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(
            Patient.id == patient_id,
            Patient.deleted_at == None,  # noqa: E711
        ).first()
        if not patient:
            logger.warning(f"[GWallet] Paciente {patient_id} no encontrado para sincronizar")
            return
        sync_patient(db, patient, tenant=None, config=None)
    except Exception as exc:
        logger.warning(f"[GWallet] Worker de sincronización falló: {exc}")
    finally:
        db.close()


def maybe_sync_patient_async(patient_id) -> None:
    """
    Dispara la sincronización asíncrona (fire-and-forget). Best-effort:
    nunca bloquea ni lanza. Solo actúa si la integración está
    habilitada y configurada.
    """
    if not (is_enabled() and is_configured()):
        return
    try:
        threading.Thread(target=_sync_worker, args=(str(patient_id),), daemon=True).start()
        logger.debug(f"[GWallet] Sincronización de {patient_id} programada")
    except Exception as exc:
        logger.warning(f"[GWallet] No se pudo programar sincronización: {exc}")


# ============================================================
# Enlace "Añadir a Google Wallet" (savetowallet JWT, offline)
# ============================================================

def generate_save_url(db: Session, patient: Patient, tenant: Optional[Tenant]) -> dict:
    """
    Genera el enlace oficial "Añadir a Google Wallet" (pay.google.com/
    gp/v/save/{jwt}), firmado con la clave de la cuenta de servicio.
    No requiere llamar a la API (el JWT crea clase+objeto al guardar).

    Devuelve {save_url, object_id, class_id}. Lanza RuntimeError si no
    está configurado o si falla el firmado.
    """
    from .loyalty_service import ensure_wallet_pass, get_loyalty_config

    if not (is_enabled() and is_configured()):
        raise RuntimeError("Google Wallet no está habilitado/configurado")

    wallet_pass_id = ensure_wallet_pass(db, patient)
    if tenant is None:
        tenant = db.query(Tenant).filter(Tenant.id == patient.tenant_id).first()
    config = get_loyalty_config(tenant)

    cls_id = class_id(tenant)
    obj_id = object_id(patient)

    key = _load_private_key()
    claims = {
        "iss": settings.GOOGLE_WALLET_SERVICE_ACCOUNT_EMAIL,
        "aud": "google",
        "typ": "savetowallet",
        "iat": int(time.time()),
        "origins": [origin()],
        "payload": {
            "loyaltyClasses": [build_class(tenant, config, cls_id)],
            "loyaltyObjects": [build_object(patient, cls_id, obj_id, config)],
        },
    }
    try:
        token = jose_jwt.encode(claims, key, algorithm="RS256")
    except Exception as exc:
        logger.error("[GWallet] No se pudo firmar el JWT de guardado")
        raise RuntimeError(f"No se pudo firmar el enlace de Google Wallet: {exc}")

    save_url = f"{settings.GOOGLE_WALLET_SAVE_BASE_URL}/{token}"

    # Persistir los ids que este objeto tendrá (diagnóstico).
    if (
        patient.google_wallet_class_id != cls_id
        or patient.google_wallet_object_id != obj_id
    ):
        patient.google_wallet_class_id = cls_id
        patient.google_wallet_object_id = obj_id
        db.commit()

    return {
        "save_url": save_url,
        "object_id": obj_id,
        "class_id": cls_id,
        "wallet_pass_id": wallet_pass_id,
    }


# ============================================================
# Utilidades
# ============================================================

def _exc_summary(exc: Exception) -> str:
    """Resumen seguro de una excepción de la API de Google (sin secretos)."""
    try:
        from googleapiclient.errors import HttpError

        if isinstance(exc, HttpError):
            status = exc.resp.status
            reason = ""
            try:
                body = json.loads(exc.content.decode("utf-8", "replace"))
                err = ((body or {}).get("error") or {}).get("message") or ""
                reason = f" - {err[:200]}"
            except Exception:
                pass
            return f"HTTP {status}{reason}"
    except Exception:
        pass
    return str(exc)[:300]