# ============================================================
# backend/app/schemas/tenant.py - Schemas Pydantic para Tenant
# Validación de datos de entrada/salida para la API
# ============================================================

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..utils.validators import validate_subdomain, validate_email


# ============================================================
# Schema base con campos comunes
# ============================================================

class TenantBase(BaseModel):
    """Campos comunes para todos los schemas de Tenant."""
    nombre: str = Field(..., min_length=2, max_length=255, description="Nombre del SPA")
    subdominio: str = Field(..., min_length=3, max_length=100, description="Subdominio único")
    email: Optional[str] = Field(None, max_length=255, description="Email de contacto")
    telefono: Optional[str] = Field(None, max_length=50, description="Teléfono de contacto")
    direccion: Optional[str] = Field(None, max_length=500, description="Dirección física")
    timezone: str = Field("America/Bogota", max_length=50, description="Zona horaria")
    moneda: str = Field("USD", max_length=3, description="Moneda (ISO 4217)")
    
    @field_validator("subdominio")
    @classmethod
    def validar_subdominio(cls, v: str) -> str:
        if not validate_subdomain(v):
            raise ValueError(
                "El subdominio solo puede contener minúsculas, números y guiones. "
                "Mínimo 3 caracteres."
            )
        return v.lower()
    
    @field_validator("email")
    @classmethod
    def validar_email(cls, v: Optional[str]) -> Optional[str]:
        if v and not validate_email(v):
            raise ValueError("Formato de email inválido")
        return v


# ============================================================
# Schema para crear un nuevo Tenant
# ============================================================

class TenantCreate(TenantBase):
    """Datos necesarios para crear un nuevo tenant."""
    plan: str = Field("basic", description="Plan: basic, professional, enterprise")
    limite_usuarios: int = Field(10, ge=1, le=1000, description="Límite de usuarios")
    limite_pacientes: int = Field(1000, ge=1, le=100000, description="Límite de pacientes")
    
    @field_validator("plan")
    @classmethod
    def validar_plan(cls, v: str) -> str:
        planes_validos = ["basic", "professional", "enterprise"]
        if v.lower() not in planes_validos:
            raise ValueError(f"Plan inválido. Opciones: {', '.join(planes_validos)}")
        return v.lower()


# ============================================================
# Schema para actualizar un Tenant
# ============================================================

class TenantUpdate(BaseModel):
    """Datos opcionales para actualizar un tenant. Todos los campos son opcionales."""
    nombre: Optional[str] = Field(None, min_length=2, max_length=255)
    plan: Optional[str] = None
    activo: Optional[bool] = None
    fecha_expiracion: Optional[datetime] = None
    configuracion: Optional[Dict[str, Any]] = None
    limite_usuarios: Optional[int] = Field(None, ge=1, le=1000)
    limite_pacientes: Optional[int] = Field(None, ge=1, le=100000)
    logo_url: Optional[str] = Field(None, max_length=500)
    direccion: Optional[str] = Field(None, max_length=500)
    telefono: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    timezone: Optional[str] = Field(None, max_length=50)
    moneda: Optional[str] = Field(None, max_length=3)


# ============================================================
# Schema de respuesta completa
# ============================================================

class TenantResponse(TenantBase):
    """Respuesta completa con todos los campos del tenant."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    plan: str
    activo: bool
    fecha_creacion: datetime
    fecha_expiracion: Optional[datetime] = None
    configuracion: Optional[Dict[str, Any]] = None
    limite_usuarios: int
    limite_pacientes: int
    logo_url: Optional[str] = None


# ============================================================
# Schema para listados (campos reducidos)
# ============================================================

class TenantListResponse(BaseModel):
    """Respuesta reducida para listados de tenants."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    nombre: str
    subdominio: str
    plan: str
    activo: bool
    fecha_creacion: datetime
    email: Optional[str] = None
    telefono: Optional[str] = None


# ============================================================
# Schema para configuración del tenant
# ============================================================

class TenantConfig(BaseModel):
    """Configuración específica del tenant."""
    horario_apertura: str = "08:00"
    horario_cierre: str = "20:00"
    dias_operacion: List[int] = Field(default=[1, 2, 3, 4, 5, 6])
    duracion_cita_default: int = Field(60, ge=15, le=240)
    recordatorio_citas: bool = True
    confirmacion_citas: bool = True
