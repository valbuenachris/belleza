# ============================================================
# backend/app/routers/loyalty.py - Endpoints del Programa de Fidelidad
# Pase digital (Apple Wallet .pkpass / Google Wallet JSON) y canje
# de sesiones gratuitas, aislado por tenant.
# ============================================================

import logging
from datetime import datetime, timezone
from email.utils import formatdate, parsedate_to_datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, get_current_tenant_id, require_role
from ..models.pass_registration import PassRegistration
from ..models.patient import Patient
from ..models.tenant import Tenant
from ..models.user import User
from ..config import settings
from ..schemas.wallet_share import WalletShareLinkResponse
from ..services import loyalty_service
from ..services import google_wallet_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/patients", tags=["Programa de Fidelidad"])
scan_router = APIRouter(prefix="/loyalty", tags=["Escáner de Fidelidad"])
# Apple Wallet Web Service: Apple llama DIRECTAMENTE a estos endpoints con
# la cabecera 'Authorization: ApplePass <authenticationToken>' (NUNCA con
# el JWT de usuarios del SPA). Se montan en /v1 (sin el prefijo /api/v1)
# y se declaran como rutas públicas en los middlewares.
wallet_router = APIRouter(prefix="/v1", tags=["Apple Wallet Web Service"])


# ============================================================
# Helpers: búsqueda de pacientes por tenant / por pase
# ============================================================

def _get_patient_or_404(db: Session, tenant_id: str, patient_id: str) -> Patient:
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.tenant_id == tenant_id,
        Patient.deleted_at == None,
    ).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado",
        )
    return patient


def _normalize_wallet_pass_id(raw: str) -> str:
    """
    Normaliza el valor escaneado del QR. Si el lector devuelve el mensaje
    completo ("pass_type_identifier/token") se conserva solo el token.
    """
    value = (raw or "").strip()
    if "/" in value:
        value = value.rsplit("/", 1)[-1]
    return value


def _get_patient_by_pass_or_404(
    db: Session, tenant_id: str, wallet_pass_id: str
) -> Patient:
    patient = loyalty_service.get_patient_by_wallet_pass(
        db, tenant_id, _normalize_wallet_pass_id(wallet_pass_id)
    )
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarjeta de fidelidad no encontrada. Verifica el código escaneado.",
        )
    return patient


# ============================================================
# GET /api/v1/patients/{id}/wallet-pass
# Genera (si falta) el pase digital del paciente.
#   formato=pkpass -> archivo .pkpass descargable (Apple Wallet)
#   formato=json   -> JSON estructurado (fallback Google Wallet)
# ============================================================

@router.get(
    "/{patient_id}/wallet-pass",
    summary="Obtener pase digital (Apple Wallet .pkpass / Google Wallet JSON)",
    description=(
        "Genera y devuelve el pase de fidelidad del paciente. Por defecto "
        "descarga el archivo .pkpass de Apple Wallet; con ?formato=json "
        "devuelve la representación estructurada (fallback Google Wallet)."
    ),
)
def get_wallet_pass(
    patient_id: str,
    formato: str = Query(
        "pkpass",
        pattern="^(pkpass|json)$",
        description="Formato del pase: 'pkpass' (Apple Wallet) o 'json' (Google Wallet)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    patient = _get_patient_or_404(db, tenant_id, patient_id)

    wallet_pass_id = loyalty_service.ensure_wallet_pass(db, patient)

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    if formato == "json":
        data = loyalty_service.build_pass_data(patient, tenant)
        return {
            "message": "Pase digital generado exitosamente",
            "patient_id": str(patient.id),
            **data,
        }

    # Apple Wallet: archivo .pkpass (zip con pass.json + manifest.json
    # + firma). Se incluye Last-Modified para que el dispositivo arranque
    # con el mismo tag que usará después en If-Modified-Since.
    pkpass_bytes = loyalty_service.build_pkpass_zip(patient, tenant)
    filename = f"fidelidad-{str(patient.id)[:8]}.pkpass"

    last_modified_dt = (
        patient.wallet_updated_at or patient.updated_at or patient.created_at
    )
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if last_modified_dt is not None:
        headers["Last-Modified"] = _http_date(last_modified_dt)

    return Response(
        content=pkpass_bytes,
        media_type="application/vnd.apple.pkpass",
        headers=headers,
    )


# ============================================================
# GET /api/v1/patients/{id}/google-wallet
# Enlace oficial "Añadir a Google Wallet" para el paciente.
# El JWT savetowallet se firma localmente (offline, sin llamar a la
# API de Google). Si la integración no está habilitada, devuelve
# enabled=false para que la UI lo comunique sin romper el flujo.
# ============================================================

@router.get(
    "/{patient_id}/google-wallet",
    summary="Obtener enlace 'Añadir a Google Wallet' del paciente",
    description=(
        "Genera el enlace oficial https://pay.google.com/gp/v/save/{jwt} "
        "con la tarjeta de fidelidad del paciente (LoyaltyClass/LoyaltyObject "
        "dentro del JWT firmado con la cuenta de servicio). Devuelve "
        "enabled=false si Google Wallet no está configurado en el sistema."
    ),
)
def get_google_wallet_save_link(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    patient = _get_patient_or_404(db, tenant_id, patient_id)

    if not (settings.GOOGLE_WALLET_ENABLED and google_wallet_service.is_configured()):
        return {
            "enabled": False,
            "patient_id": str(patient.id),
            "message": (
                "Google Wallet no está habilitado en este sistema. "
                "Configúralo en el backend (GOOGLE_WALLET_ENABLED y credenciales)."
            ),
        }

    try:
        result = google_wallet_service.generate_save_url(db, patient, tenant=None)
    except Exception as e:
        logger.error(f"[GWallet] No se pudo generar el enlace de guardado: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo generar el enlace de Google Wallet. Revisa la configuración.",
        )

    # Asegura (asíncrono, best-effort) que clase y objeto existan en Google
    # para que los próximos PATCH de balance lleguen sin crear el objeto.
    google_wallet_service.maybe_sync_patient_async(patient.id)

    return {
        "enabled": True,
        "patient_id": str(patient.id),
        "save_url": result["save_url"],
        "object_id": result["object_id"],
        "class_id": result["class_id"],
        "wallet_pass_id": result["wallet_pass_id"],
        "message": "Enlace generado. Ábrelo en un dispositivo con Google Wallet.",
    }


# ============================================================
# POST /api/v1/patients/{id}/wallet-share-link
# Genera (o renueva) el enlace público para que el CLIENTE instale su
# tarjeta en su propio teléfono (/tarjeta/{token}).
# ============================================================

@router.post(
    "/{patient_id}/wallet-share-link",
    response_model=WalletShareLinkResponse,
    summary="Generar enlace público para compartir la tarjeta",
    description=(
        "Genera (o renueva si expiró) un token de capacidad del paciente y "
        "devuelve la URL pública que el personal puede compartir con el "
        "cliente por WhatsApp/SMS/email para añadir la tarjeta a su Wallet."
    ),
)
def create_wallet_share_link(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    patient = _get_patient_or_404(db, tenant_id, patient_id)
    token = loyalty_service.ensure_wallet_share_token(db, patient)
    base = (settings.WALLET_WEB_SERVICE_BASE_URL or "").strip().rstrip("/")
    return WalletShareLinkResponse(
        url=f"{base}/tarjeta/{token}",
        token=token,
        expires_at=patient.wallet_share_expires_at,
    )


# ============================================================
# POST /api/v1/patients/{id}/redeem-session
# Canjea una sesión gratuita (decrementa sesiones_gratis).
# ============================================================

@router.post(
    "/{patient_id}/redeem-session",
    summary="Canjear una sesión gratuita",
    description="Decrementa en 1 las sesiones gratuitas del paciente al usarse una.",
)
def redeem_session(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(["admin", "manager", "receptionist"])
    ),
    tenant_id: str = Depends(get_current_tenant_id),
):
    patient = _get_patient_or_404(db, tenant_id, patient_id)

    try:
        result = loyalty_service.redeem_free_session(db, patient)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {
        "message": result["message"],
        "patient_id": str(patient.id),
        "wallet_pass_id": patient.wallet_pass_id,
        "puntos": result["puntos"],
        "sesiones_gratis": result["sesiones_gratis"],
    }


# ============================================================
# POST /api/v1/loyalty/scan/{wallet_pass_id}/add-point
# Escáner de tarjetas de fidelidad: registra 1 estrella al paciente
# cuyo pase digital fue escaneado (QR de la tarjeta).
# Roles permitidos: admin, manager, receptionist.
# ============================================================

@scan_router.post(
    "/scan/{wallet_pass_id}/add-point",
    summary="Registrar estrella escaneando el pase de fidelidad",
    description=(
        "El personal (admin, manager, receptionist) escanea el QR de la "
        "tarjeta de fidelidad del paciente y se le otorga 1 estrella. "
        "Si alcanza la meta del tenant, se libera una sesión gratuita."
    ),
)
def scan_add_point(
    wallet_pass_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "receptionist"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    patient = _get_patient_by_pass_or_404(db, tenant_id, wallet_pass_id)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    # sync_google_wallet=False: este endpoint realiza su PROPIO PATCH
    # síncrono a Google Wallet justo debajo (update_loyalty_object), así
    # que award_loyalty_points no debe disparar otro más (evita dobles
    # actualizaciones y mantiene la respuesta cero-extra del escáner).
    result = loyalty_service.award_loyalty_points(
        db, patient, tenant, sync_google_wallet=False
    )

    # Sincroniza el LoyaltyObject con Google Wallet (solo si está habilitado).
    # Fail-safe: nunca lanza ni afecta a la respuesta del endpoint. La
    # actualización de la BD ya está commiteada en award_loyalty_points.
    if settings.GOOGLE_WALLET_ENABLED:
        google_wallet_service.update_loyalty_object(
            str(patient.id), patient.puntos or 0, patient.sesiones_gratis or 0
        )

    mensaje = "Estrella registrada correctamente."
    if result["sesion_gratis_otorgada"]:
        mensaje = f"¡Meta alcanzada! Se otorgó: {result['premio']}."

    return {
        "message": mensaje,
        "patient_id": str(patient.id),
        "patient_nombre": f"{patient.nombre} {patient.apellido}".strip(),
        "wallet_pass_id": patient.wallet_pass_id,
        **result,
    }


# ============================================================
# POST /api/v1/loyalty/scan/{wallet_pass_id}/redeem
# Escáner de tarjetas de fidelidad: canjea una sesión gratuita
# del paciente cuyo pase digital fue escaneado.
# ============================================================

@scan_router.post(
    "/scan/{wallet_pass_id}/redeem",
    summary="Canjear sesión gratuita escaneando el pase de fidelidad",
    description="Decrementa en 1 las sesiones gratuitas del paciente al usarse una.",
)
def scan_redeem(
    wallet_pass_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "receptionist"])),
    tenant_id: str = Depends(get_current_tenant_id),
):
    patient = _get_patient_by_pass_or_404(db, tenant_id, wallet_pass_id)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    try:
        result = loyalty_service.redeem_free_session(db, patient)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    config = loyalty_service.get_loyalty_config(tenant)

    return {
        "message": result["message"],
        "patient_id": str(patient.id),
        "patient_nombre": f"{patient.nombre} {patient.apellido}".strip(),
        "wallet_pass_id": patient.wallet_pass_id,
        "puntos": result["puntos"],
        "puntos_meta": config["puntos_meta"],
        "premio": config["premio_fidelidad"],
        "sesiones_gratis": result["sesiones_gratis"],
    }


# ============================================================
# GET /api/v1/loyalty/google-wallet/status
# Diagnóstico de la integración con Google Wallet (sin secretos).
# Indica si está habilitada, si las credenciales están completas y
# qué parámetros faltan, para poder debuggear sin exponer claves.
# ============================================================

@scan_router.get(
    "/google-wallet/status",
    summary="Estado de la integración con Google Wallet",
    description=(
        "Devuelve si Google Wallet está habilitado y bien configurado, "
        "junto con los campos que faltan (sin exponer secretos)."
    ),
)
def google_wallet_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    enabled = settings.GOOGLE_WALLET_ENABLED
    configured = google_wallet_service.is_configured()
    missing = [] if configured else google_wallet_service.missing_config_fields()

    return {
        "enabled": enabled,
        "configured": configured,
        "origin": google_wallet_service.origin(),
        "issuer_id": settings.GOOGLE_WALLET_ISSUER_ID or None,
        "service_account_email": google_wallet_service.service_account_email(),
        "class_id_override": settings.GOOGLE_WALLET_CLASS_ID or None,
        "class_id_mode": (
            "manual" if settings.GOOGLE_WALLET_CLASS_ID else "auto-per-tenant"
        ),
        "api_base": settings.GOOGLE_WALLET_API_BASE,
        "scope": settings.GOOGLE_WALLET_SCOPE,
        "active": enabled and configured,
        "missing": missing,
    }


# ============================================================
# Apple Wallet Web Service (Apple Wallet → nuestro backend)
# ============================================================
#
# Especificación oficial de Apple (esquema /v1):
#   POST   /v1/devices/{deviceLibraryIdentifier}/registrations/{passTypeIdentifier}/{serialNumber}
#   DELETE /v1/devices/{deviceLibraryIdentifier}/registrations/{passTypeIdentifier}/{serialNumber}
#   GET    /v1/devices/{deviceLibraryIdentifier}/registrations/{passTypeIdentifier}   (serialNumbers)
#   GET    /v1/passes/{passTypeIdentifier}/{serialNumber}                             (última versión)
#   POST   /v1/log
#
# Autenticación: cabecera 'Authorization: ApplePass <authenticationToken>'.
# El authenticationToken es el patient.wallet_auth_token (independiente
# del wallet_pass_id). El tenant se resuelve desde el paciente, por lo
# que estas rutas son públicas para los middlewares JWT/tenant.

def _authenticate_wallet_request(
    db: Session,
    request: Request,
    pass_type_identifier: str,
    serial_number: Optional[str],
) -> Patient:
    """
    Valida la cabecera 'Authorization: ApplePass <token>' contra el
    wallet_auth_token del paciente y comprueba el tipo de pase y el
    serial number de la URL. Devuelve el paciente (y su tenant vía
    patient.tenant_id).
    """
    auth_header = request.headers.get("Authorization", "") or ""
    parts = auth_header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "applepass":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autorización de Apple Wallet inválida (ApplePass <token>)",
        )
    token = parts[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de pase inválido",
        )

    patient = db.query(Patient).filter(
        Patient.wallet_auth_token == token,
        Patient.deleted_at == None,
    ).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de pase inválido",
        )

    if pass_type_identifier != loyalty_service.PASS_TYPE_IDENTIFIER:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de pase no soportado",
        )
    if serial_number is not None and patient.wallet_pass_id != serial_number:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pase no encontrado",
        )
    return patient


def _find_registration(
    db: Session,
    device_library_identifier: str,
    pass_type_identifier: str,
    serial_number: str,
    patient_id: Optional[str] = None,
):
    query = db.query(PassRegistration).filter(
        PassRegistration.device_library_identifier == device_library_identifier,
        PassRegistration.pass_type_identifier == pass_type_identifier,
        PassRegistration.serial_number == serial_number,
        PassRegistration.deleted_at == None,
    )
    if patient_id is not None:
        query = query.filter(PassRegistration.patient_id == patient_id)
    return query.first()


def _last_modified_dt(
    patient: Patient,
    registrations: Optional[List[PassRegistration]] = None,
) -> datetime:
    """Momento de la última actualización del pase (UTC)."""
    candidates = [patient.wallet_updated_at, patient.updated_at]
    if registrations:
        for registration in registrations:
            if registration.updated_at:
                candidates.append(registration.updated_at)
    valid = [dt for dt in candidates if dt is not None]
    return max(valid) if valid else datetime.utcnow()


def _http_date(dt: datetime) -> str:
    """Fecha HTTP (RFC 7231) para la cabecera Last-Modified."""
    return formatdate(dt.replace(tzinfo=timezone.utc).timestamp(), usegmt=True)


def _parse_wallet_timestamp(value: Optional[str]) -> Optional[datetime]:
    """
    Parsea el tag 'passesUpdatedSince' / 'lastUpdated' que envía Apple
    (RFC 3339). Tolera fecha-hora con/sin offset y fecha sola.
    Devuelve un datetime naïve en UTC para comparar con los valores
    naïve (UTC) que almacena el backend (MySQL DATETIME).
    """
    if not value:
        return None
    value = (value or "").strip()
    if not value:
        return None

    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    logger.debug(f"[Wallet] passesUpdatedSince no parseable: {value!r}")
    return None


# ------------------------------------------------------------
# POST /v1/devices/{deviceLibraryIdentifier}/registrations/{passTypeIdentifier}/{serialNumber}
# Registra el dispositivo para recibir actualizaciones del pase.
#   201 si es un registro nuevo, 200 si ya estaba registrado.
# ------------------------------------------------------------

@wallet_router.post(
    "/devices/{device_library_identifier}/registrations/{pass_type_identifier}/{serial_number}",
    summary="Registrar un dispositivo para recibir actualizaciones del pase",
)
def register_wallet_device(
    device_library_identifier: str,
    pass_type_identifier: str,
    serial_number: str,
    request: Request,
    payload: Optional[dict] = Body(default=None),
    db: Session = Depends(get_db),
):
    patient = _authenticate_wallet_request(db, request, pass_type_identifier, serial_number)
    push_token = (payload or {}).get("pushToken")

    registration = _find_registration(
        db, device_library_identifier, pass_type_identifier, serial_number
    )
    if registration:
        if push_token is not None and registration.push_token != push_token:
            registration.push_token = push_token
            registration.patient_id = str(patient.id)
            registration.tenant_id = str(patient.tenant_id)
            db.commit()
        return Response(status_code=status.HTTP_200_OK)

    db.add(
        PassRegistration(
            tenant_id=str(patient.tenant_id),
            patient_id=str(patient.id),
            pass_type_identifier=pass_type_identifier,
            serial_number=serial_number,
            device_library_identifier=device_library_identifier,
            push_token=push_token,
        )
    )
    db.commit()
    logger.info(
        f"[Wallet] Registro: device={device_library_identifier} -> "
        f"pase={serial_number} (paciente {patient.id})"
    )
    return Response(status_code=status.HTTP_201_CREATED)


# ------------------------------------------------------------
# DELETE /v1/devices/.../registrations/{passTypeIdentifier}/{serialNumber}
# Da de baja el dispositivo (deja de recibir actualizaciones).
# ------------------------------------------------------------

@wallet_router.delete(
    "/devices/{device_library_identifier}/registrations/{pass_type_identifier}/{serial_number}",
    summary="Dar de baja el dispositivo para un pase",
)
def unregister_wallet_device(
    device_library_identifier: str,
    pass_type_identifier: str,
    serial_number: str,
    request: Request,
    db: Session = Depends(get_db),
):
    patient = _authenticate_wallet_request(db, request, pass_type_identifier, serial_number)
    registration = _find_registration(
        db,
        device_library_identifier,
        pass_type_identifier,
        serial_number,
        patient_id=str(patient.id),
    )
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro de pase no encontrado",
        )
    db.delete(registration)
    db.commit()
    logger.info(f"[Wallet] Baja: device={device_library_identifier} -> pase={serial_number}")
    return Response(status_code=status.HTTP_200_OK)


# ------------------------------------------------------------
# GET /v1/devices/{deviceLibraryIdentifier}/registrations/{passTypeIdentifier}
# Lista los serialNumbers del pase registrados en el dispositivo.
#   200 con {serialNumbers, lastUpdated} | 204 si no hay registros
#   (o si ninguna actualización supera el tag passesUpdatedSince).
# ------------------------------------------------------------

@wallet_router.get(
    "/devices/{device_library_identifier}/registrations/{pass_type_identifier}",
    summary="Obtener serial numbers de pases registrados para el dispositivo",
)
def get_wallet_device_serials(
    device_library_identifier: str,
    pass_type_identifier: str,
    request: Request,
    passesUpdatedSince: Optional[str] = Query(
        default=None,
        alias="passesUpdatedSince",
        description="Tag (RFC 3339) de la última actualización vista por el dispositivo",
    ),
    db: Session = Depends(get_db),
):
    patient = _authenticate_wallet_request(db, request, pass_type_identifier, None)

    registrations = db.query(PassRegistration).filter(
        PassRegistration.device_library_identifier == device_library_identifier,
        PassRegistration.pass_type_identifier == pass_type_identifier,
        PassRegistration.patient_id == str(patient.id),
        PassRegistration.deleted_at == None,
    ).all()

    if not registrations:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # Filtrar por el tag de actualización (passesUpdatedSince): solo se
    # devuelven los serialNumbers con cambios posteriores al tag.
    since = _parse_wallet_timestamp(passesUpdatedSince)
    serial_numbers = []
    for registration in registrations:
        if since is not None:
            modified = (
                registration.updated_at
                or patient.wallet_updated_at
                or patient.updated_at
                or patient.created_at
            )
            if modified is not None and modified <= since:
                continue
        serial_numbers.append(registration.serial_number)

    if not serial_numbers:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    last_updated = _last_modified_dt(patient, registrations)
    return JSONResponse(content={
        "serialNumbers": serial_numbers,
        # Formato ISO 8601 esperado por Apple (p.ej. 2011-06-25T07:47:32+0000)
        "lastUpdated": last_updated.strftime("%Y-%m-%dT%H:%M:%S+0000"),
    })


# ------------------------------------------------------------
# GET /v1/passes/{passTypeIdentifier}/{serialNumber}
# Entrega la última versión del .pkpass.
#   304 si no cambió desde If-Modified-Since | 200 con el pase.
# ------------------------------------------------------------

@wallet_router.get(
    "/passes/{pass_type_identifier}/{serial_number}",
    summary="Obtener la última versión del pase",
)
def get_latest_wallet_pass(
    pass_type_identifier: str,
    serial_number: str,
    request: Request,
    db: Session = Depends(get_db),
):
    patient = _authenticate_wallet_request(db, request, pass_type_identifier, serial_number)

    last_modified_dt = patient.wallet_updated_at or patient.updated_at or patient.created_at
    if last_modified_dt is not None:
        if_modified_since = request.headers.get("If-Modified-Since")
        if if_modified_since:
            try:
                since = parsedate_to_datetime(if_modified_since)
                if since is not None and since.tzinfo is not None:
                    since = since.replace(tzinfo=None)
                if last_modified_dt <= since:
                    return Response(status_code=status.HTTP_304_NOT_MODIFIED)
            except (TypeError, ValueError):
                logger.debug("[Wallet] If-Modified-Since inválido; se devuelve el pase completo")

    tenant = db.query(Tenant).filter(Tenant.id == patient.tenant_id).first()
    pkpass_bytes = loyalty_service.build_pkpass_zip(patient, tenant)
    filename = f"fidelidad-{serial_number[:16]}.pkpass"

    headers = {}
    if last_modified_dt is not None:
        headers["Last-Modified"] = _http_date(last_modified_dt)
    headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    return Response(
        content=pkpass_bytes,
        media_type="application/vnd.apple.pkpass",
        headers=headers,
    )


# ------------------------------------------------------------
# POST /v1/log
# Apple reporta logs del web service. Los registramos y respondemos 200.
# ------------------------------------------------------------

@wallet_router.post("/log", summary="Registrar logs del web service de Apple Wallet")
def receive_wallet_logs(
    payload: Any = Body(default=None),
):
    messages: List[str] = []
    if isinstance(payload, list):
        messages = [str(message) for message in payload]
    elif isinstance(payload, dict):
        logs = payload.get("logs", payload.get("messages", []))
        if isinstance(logs, list):
            messages = [str(message) for message in logs]

    for message in messages:
        logger.info(f"[Apple Wallet log] {message}")

    return {"success": True}