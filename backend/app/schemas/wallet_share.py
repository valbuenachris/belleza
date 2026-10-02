# ============================================================
# backend/app/schemas/wallet_share.py - Esquemas del enlace público
# de la tarjeta de fidelidad (/tarjeta/{token}).
#
# IMPORTANTE: estos esquemas exponen SOLO datos de marca y progreso.
# Nunca incluyen identidad del paciente ni tokens internos del pase.
# ============================================================

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PublicWalletInfoResponse(BaseModel):
    """Datos públicos de la tarjeta (sin información personal del paciente)."""
    tenant_name: str = Field(..., description="Nombre del SPA")
    tenant_logo_url: Optional[str] = Field(None, description="URL del logo del SPA (opcional)")
    tarjeta_color_hex: str = Field(..., description="Color de la tarjeta (#RRGGBB)")
    puntos_actuales: int = Field(..., ge=0, description="Estrellas actuales")
    puntos_meta: int = Field(..., ge=1, description="Estrellas necesarias para el premio")
    premio_fidelidad: str = Field(..., description="Premio al alcanzar la meta")


class PublicGoogleWalletResponse(BaseModel):
    """Enlace 'Añadir a Google Wallet' o su indisponibilidad."""
    enabled: bool
    save_url: Optional[str] = None
    message: Optional[str] = None


class WalletShareLinkResponse(BaseModel):
    """Enlace público generado por el personal para compartir con el cliente."""
    url: str
    token: str
    expires_at: Optional[datetime] = None
