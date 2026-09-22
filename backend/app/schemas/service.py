# ============================================================
# backend/app/schemas/service.py - Schemas Pydantic para Service
# Validación de datos de entrada/salida del catálogo de servicios
# ============================================================

from datetime import datetime
from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict


# ============================================================
# Schema base con campos comunes
# ============================================================

class ServiceBase(BaseModel):
    """Campos comunes para todos los schemas de Service."""
    nombre: str = Field(..., min_length=1, max_length=255, description="Nombre del servicio")
    descripcion: Optional[str] = Field(None, description="Descripción del servicio")
    precio: Decimal = Field(Decimal("0.00"), ge=0, description="Precio del servicio")
    duracion: int = Field(60, ge=5, le=1440, description="Duración en minutos")


# ============================================================
# Schema para crear un nuevo servicio
# ============================================================

class ServiceCreate(ServiceBase):
    """Datos necesarios para crear un servicio."""


# ============================================================
# Schema para actualizar un servicio
# ============================================================

class ServiceUpdate(BaseModel):
    """Datos opcionales para actualizar un servicio."""
    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    descripcion: Optional[str] = None
    precio: Optional[Decimal] = Field(None, ge=0)
    duracion: Optional[int] = Field(None, ge=5, le=1440)
    activo: Optional[bool] = None


# ============================================================
# Schema de respuesta
# ============================================================

class ServiceResponse(ServiceBase):
    """Respuesta completa de un servicio."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    activo: bool
    created_at: datetime