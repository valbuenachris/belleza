# ============================================================
# backend/app/schemas/appointment.py - Schemas Pydantic para Appointment
# Validación de datos de entrada/salida de citas
# ============================================================

from datetime import datetime
from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..models.appointment import ESTADOS_CITA


# ============================================================
# Schema base con campos comunes
# ============================================================

class AppointmentBase(BaseModel):
    """Campos comunes para todos los schemas de Appointment."""
    patient_id: str = Field(..., description="ID del paciente")
    therapist_id: Optional[str] = Field(None, description="ID del terapeuta (usuario)")
    service_id: Optional[str] = Field(None, description="ID del servicio")
    date_time: Optional[datetime] = Field(None, description="Fecha y hora de inicio de la cita")
    duracion: Optional[int] = Field(None, ge=5, le=1440, description="Duración en minutos (default: la del servicio)")
    estado: Optional[str] = Field(None, description="Estado inicial de la cita")
    precio: Optional[Decimal] = Field(None, ge=0, description="Precio (default: el del servicio)")
    notas: Optional[str] = Field(None, description="Notas adicionales")
    # Campos legacy (compatibilidad con la UI actual)
    therapist: Optional[str] = Field(None, description="Nombre del terapeuta (alternativa a therapist_id)")
    service: Optional[str] = Field(None, description="Nombre del servicio (alternativa a service_id)")
    fecha: Optional[str] = Field(None, description="Fecha 'YYYY-MM-DD' (alternativa a date_time)")
    time: Optional[str] = Field(None, description="Hora 'HH:MM' (alternativa a date_time)")


# ============================================================
# Schema para crear una nueva cita
# ============================================================

class AppointmentCreate(AppointmentBase):
    """Datos necesarios para crear una cita."""

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: Optional[str]) -> Optional[str]:
        if v and v.lower() not in ESTADOS_CITA:
            raise ValueError(f"Estado inválido. Opciones: {', '.join(ESTADOS_CITA)}")
        return v.lower() if v else v


# ============================================================
# Schema para actualizar una cita
# ============================================================

class AppointmentUpdate(BaseModel):
    """Datos opcionales para actualizar una cita."""
    patient_id: Optional[str] = None
    therapist_id: Optional[str] = None
    service_id: Optional[str] = None
    date_time: Optional[datetime] = None
    duracion: Optional[int] = Field(None, ge=5, le=1440)
    estado: Optional[str] = None
    precio: Optional[Decimal] = Field(None, ge=0)
    notas: Optional[str] = None
    # Campos legacy (compatibilidad con la UI actual)
    therapist: Optional[str] = None
    service: Optional[str] = None
    fecha: Optional[str] = None
    time: Optional[str] = None

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: Optional[str]) -> Optional[str]:
        if v and v.lower() not in ESTADOS_CITA:
            raise ValueError(f"Estado inválido. Opciones: {', '.join(ESTADOS_CITA)}")
        return v.lower() if v else v


# ============================================================
# Schema de respuesta (con campos calculados para la UI)
# ============================================================

class AppointmentResponse(BaseModel):
    """Respuesta de cita con campos calculados (nombres, hora, etc.)."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    patient_id: str
    therapist_id: str
    service_id: str
    date_time: datetime
    duracion: int
    estado: str
    precio: Optional[Decimal] = None
    notas: Optional[str] = None
    # Campos calculados (compatibilidad con la UI)
    patient: str
    service: str
    therapist: str
    fecha: Optional[str] = None
    hora_inicio: Optional[str] = None
    time: Optional[str] = None
    total_precio: Optional[Decimal] = None
    created_at: datetime