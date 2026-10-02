# ============================================================
# backend/app/routers/public_wallet.py - Tarjeta pública de fidelidad
# Enlace de capacidad (/tarjeta/{token}) que el personal comparte con
# el cliente para que instale su tarjeta en Apple/Google Wallet sin
# login. Seguridad: el token es la ÚNICA clave; solo se exponen datos
# de marca y progreso (nunca identidad ni tokens internos del pase).
# Rate-limited por IP con slowapi.
# ============================================================

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.patient import Patient
from ..models.tenant import Tenant
from ..schemas.wallet_share import (
    PublicGoogleWalletResponse,
    PublicWalletInfoResponse,
)
from ..services import google_wallet_service, loyalty_service
from ..utils.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/public/wallet", tags=["Tarjeta Pública (Wallet)"])

# Límite por IP para los endpoints públicos (anti-abuso).
PUBLIC_RATE_LIMIT = "10/minute"


def _get_patient_or_404(db: Session, token: str) -> Patient:
    """
    Resuelve el paciente por token. Respuesta 404 genérica para no
    revelar si el token existe, expiró o el paciente fue eliminado.
    """
    patient = loyalty_service.get_patient_by_share_token(db, token)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enlace inválido o expirado",
        )
    return patient


# ============================================================
# GET /api/v1/public/wallet/{token}
# Información pública de la tarjeta (marca + progreso).
# ============================================================

@router.get(
    "/{token}",
    response_model=PublicWalletInfoResponse,
    summary="Información pública de la tarjeta de fidelidad",
    description=(
        "Devuelve SOLO datos de marca y progreso (nombre del SPA, logo, "
        "color, estrellas y premio). No expone identidad ni tokens del pase."
    ),
)
@limiter.limit(PUBLIC_RATE_LIMIT)
def get_public_wallet_info(
    token: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    patient = _get_patient_or_404(db, token)
    tenant = db.query(Tenant).filter(Tenant.id == patient.tenant_id).first()
    config = loyalty_service.get_loyalty_config(tenant)
    return PublicWalletInfoResponse(
        tenant_name=(tenant.nombre if tenant else "SPA"),
        tenant_logo_url=(tenant.logo_url if tenant else None),
        tarjeta_color_hex=config["tarjeta_color_hex"],
        puntos_actuales=patient.puntos or 0,
        puntos_meta=config["puntos_meta"],
        premio_fidelidad=config["premio_fidelidad"],
    )


# ============================================================
# GET /api/v1/public/wallet/{token}/pkpass
# Descarga del pase de Apple Wallet del paciente tokenizado.
# ============================================================

@router.get(
    "/{token}/pkpass",
    summary="Descargar el .pkpass de Apple Wallet (enlace público)",
    description=(
        "Genera (si hace falta) y devuelve el archivo .pkpass del paciente "
        "asociado al token, para que el cliente lo añada a su Apple Wallet."
    ),
)
@limiter.limit(PUBLIC_RATE_LIMIT)
def get_public_pkpass(
    token: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    patient = _get_patient_or_404(db, token)
    # Idempotente: genera wallet_pass_id / wallet_auth_token si faltan.
    loyalty_service.ensure_wallet_pass(db, patient)
    tenant = db.query(Tenant).filter(Tenant.id == patient.tenant_id).first()
    pkpass_bytes = loyalty_service.build_pkpass_zip(patient, tenant)
    filename = f"fidelidad-{str(patient.id)[:8]}.pkpass"

    return Response(
        content=pkpass_bytes,
        media_type="application/vnd.apple.pkpass",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============================================================
# GET /api/v1/public/wallet/{token}/google
# Enlace "Añadir a Google Wallet" del paciente tokenizado.
# ============================================================

@router.get(
    "/{token}/google",
    response_model=PublicGoogleWalletResponse,
    summary="Enlace 'Añadir a Google Wallet' (enlace público)",
    description=(
        "Devuelve el enlace oficial de guardado en Google Wallet, o "
        "enabled=false si la integración no está disponible."
    ),
)
@limiter.limit(PUBLIC_RATE_LIMIT)
def get_public_google_link(
    token: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    patient = _get_patient_or_404(db, token)

    if not (settings.GOOGLE_WALLET_ENABLED and google_wallet_service.is_configured()):
        return PublicGoogleWalletResponse(
            enabled=False,
            save_url=None,
            message="Google Wallet no está disponible en este sistema.",
        )

    try:
        result = google_wallet_service.generate_save_url(db, patient, tenant=None)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[Wallet público] No se pudo generar el enlace de Google: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo generar el enlace de Google Wallet.",
        )

    return PublicGoogleWalletResponse(enabled=True, save_url=result["save_url"])
