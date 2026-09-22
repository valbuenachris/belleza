# ============================================================
# backend/app/schemas/patient.py - Schemas Pydantic para Patient
# Validación de datos de entrada/salida de pacientes
# ============================================================

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..utils.validators import validate_email, validate_phone


# ============================================================
# Schema base con campos comunes
# ============================================================

class PatientBase(BaseModel):
    """Campos comunes para todos los schemas de Patient."""
    nombre: str = Field(..., min_length=1, max_length=100, description="Nombre del paciente")
    apellido: str = Field(..., min_length=1, max_length=100, description="Apellido del paciente")
    email: Optional[str] = Field(None, max_length=255, description="Email de contacto")
    telefono: Optional[str] = Field(None, max_length=50, description="Teléfono")
    fecha_nacimiento: Optional[date] = Field(None, description="Fecha de nacimiento")
    genero: Optional[str] = Field(None, max_length=30, description="Género: female, male, other")
    direccion: Optional[str] = Field(None, max_length=500, description="Dirección")
    notas_medicas: Optional[str] = Field(None, description="Notas médicas / alergias")

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: Optional[str]) -> Optional[str]:
        if v and not validate_email(v):
            raise ValueError("Formato de email inválido")
        return v

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: Optional[str]) -> Optional[str]:
        if v and not validate_phone(v):
            raise ValueError("Formato de teléfono inválido")
        return v

    @field_validator("fecha_nacimiento")
    @classmethod
    def validar_fecha(cls, v: Optional[date]) -> Optional[date]:
        if v and v > datetime.utcnow().date():
            raise ValueError("La fecha de nacimiento no puede ser futura")
        return v


# ============================================================
# Schema para crear un nuevo paciente
# ============================================================

class PatientCreate(PatientBase):
    """Datos necesarios para crear un paciente."""


# ============================================================
# Schema para actualizar un paciente
# ============================================================

class PatientUpdate(BaseModel):
    """Datos opcionales para actualizar un paciente."""
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    apellido: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    telefono: Optional[str] = Field(None, max_length=50)
    fecha_nacimiento: Optional[date] = None
    genero: Optional[str] = Field(None, max_length=30)
    direccion: Optional[str] = Field(None, max_length=500)
    notas_medicas: Optional[str] = None
    activo: Optional[bool] = None


# ============================================================
# Schema de respuesta
# ============================================================

class PatientResponse(PatientBase):
    """Respuesta de paciente con campos calculados."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    activo: bool
    ultima_cita: Optional[str] = None
    total_citas: int = 0
    puntos: int = 0
    sesiones_gratis: int = 0
    wallet_pass_id: Optional[str] = None
    created_at: datetime