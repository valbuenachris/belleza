# ============================================================
# backend/app/routers/loyalty.py - Endpoints del Programa de Fidelidad
# Pase digital (Apple Wallet .pkpass / Google Wallet JSON) y canje
# de sesiones gratuitas, aislado por tenant.
# ============================================================

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, get_current_tenant_id, require_role
from ..models.patient import Patient
from ..models.tenant import Tenant
from ..models.user import User
from ..services import loyalty_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/patients", tags=["Programa de Fidelidad"])
scan_router = APIRouter(prefix="/loyalty", tags=["Escáner de Fidelidad"])


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

    # Apple Wallet: archivo .pkpass (zip con pass.json + manifest.json)
    pkpass_bytes = loyalty_service.build_pkpass_zip(patient, tenant)
    filename = f"fidelidad-{str(patient.id)[:8]}.pkpass"

    return Response(
        content=pkpass_bytes,
        media_type="application/vnd.apple.pkpass",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
    current_user: User = Depends(get_current_user),
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

    result = loyalty_service.award_loyalty_points(db, patient, tenant)

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