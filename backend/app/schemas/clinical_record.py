# ============================================================
# backend/app/schemas/clinical_record.py - Schemas Pydantic para
# Registros clínicos (historia clínica / evoluciones)
# ============================================================

from datetime import datetime, date, time
from typing import Optional, Union

from pydantic import BaseModel, Field, ConfigDict, field_validator


def parse_fecha(value) -> Optional[datetime]:
    """
    Normaliza el campo `fecha` aceptando datetime, date o string.

    - datetime -> se pasa tal cual
    - date / "YYYY-MM-DD" -> se convierte a datetime a medianoche
      (datetime.combine(d, datetime.min.time()))
    - "YYYY-MM-DDTHH:MM:SS[.ffffff]" -> datetime ISO
    - None o "" -> hora actual UTC (se usa la del servidor)
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            try:
                return datetime.strptime(s, "%Y-%m-%d")
            except ValueError:
                raise ValueError(
                    "fecha debe ser un datetime válido, un date o 'YYYY-MM-DD'"
                )
    raise ValueError(
        "fecha debe ser un datetime válido, un date o 'YYYY-MM-DD'"
    )


# ============================================================
# Schema para crear un registro clínico
# ============================================================

class ClinicalRecordCreate(BaseModel):
    """Datos para registrar una nueva evolución/sesión clínica."""
    fecha: Union[datetime, date, str, None] = Field(
        None,
        description="Fecha y hora de la sesión. Acepta datetime, date o "
        "'YYYY-MM-DD'. Si se omite o está vacío, se usa la hora actual.",
    )

    @field_validator("fecha", mode="before")
    @classmethod
    def _normalize_fecha(cls, v):
        return parse_fecha(v) or datetime.utcnow()

    zona_tratada: Optional[str] = Field(
        None, max_length=255, description="Zona tratada (ej: Rostro, Espalda)"
    )
    tratamiento_servicio: Optional[str] = Field(
        None, max_length=255, description="Tratamiento o servicio realizado"
    )
    productos_parametros: Optional[str] = Field(
        None, description="Productos aplicados / parámetros (ej: Ácido hialurónico 2ml)"
    )
    observaciones: Optional[str] = Field(
        None, description="Observaciones y evolución del paciente"
    )
    diagnostico: Optional[str] = Field(
        None, description="Diagnóstico o valoración clínica"
    )
    therapist_id: Optional[str] = Field(
        None, description="FK al terapeuta (si se omite, se usa el usuario autenticado)"
    )
    appointment_id: Optional[str] = Field(
        None, description="FK a la cita/sesión asociada"
    )


# ============================================================
# Schema para actualizar un registro clínico
# ============================================================

class ClinicalRecordUpdate(BaseModel):
    """Datos opcionales para actualizar un registro clínico."""
    fecha: Union[datetime, date, str, None] = None
    zona_tratada: Optional[str] = Field(None, max_length=255)
    tratamiento_servicio: Optional[str] = Field(None, max_length=255)
    productos_parametros: Optional[str] = None
    observaciones: Optional[str] = None
    diagnostico: Optional[str] = None
    therapist_id: Optional[str] = None
    appointment_id: Optional[str] = None
    activo: Optional[bool] = None

    @field_validator("fecha", mode="before")
    @classmethod
    def _normalize_fecha(cls, v):
        return parse_fecha(v) or datetime.utcnow()


# ============================================================
# Schema de respuesta
# ============================================================

class ClinicalRecordResponse(BaseModel):
    """Respuesta de un registro clínico con campos calculados."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    patient_id: str
    therapist_id: Optional[str] = None
    appointment_id: Optional[str] = None
    fecha: datetime
    zona_tratada: Optional[str] = None
    tratamiento_servicio: Optional[str] = None
    productos_parametros: Optional[str] = None
    observaciones: Optional[str] = None
    diagnostico: Optional[str] = None
    therapist_name: str
    patient_name: str
    servicio: str
    activo: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None