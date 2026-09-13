# ============================================================
# backend/app/schemas/user.py - Schemas Pydantic para User
# Validación de datos de entrada/salida para usuarios
# ============================================================

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..utils.validators import validate_email, validate_password_strength
from .tenant import TenantResponse


# ============================================================
# Schema base con campos comunes
# ============================================================

class UserBase(BaseModel):
    """Campos comunes para todos los schemas de User."""
    username: str = Field(..., min_length=3, max_length=100, description="Nombre de usuario")
    email: str = Field(..., max_length=255, description="Correo electrónico")
    nombre: str = Field(..., min_length=1, max_length=100, description="Nombre")
    apellido: str = Field(..., min_length=1, max_length=100, description="Apellido")
    telefono: Optional[str] = Field(None, max_length=50, description="Teléfono")
    
    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        if not validate_email(v):
            raise ValueError("Formato de email inválido")
        return v.lower()
    
    @field_validator("username")
    @classmethod
    def validar_username(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("El username solo puede contener letras y números")
        return v.lower()


# ============================================================
# Schema para crear un nuevo usuario
# ============================================================

class UserCreate(UserBase):
    """Datos necesarios para crear un nuevo usuario."""
    password: str = Field(..., min_length=8, max_length=128, description="Contraseña")
    rol: str = Field(..., description="Rol: admin, manager, receptionist, therapist")
    tenant_id: Optional[str] = Field(None, description="ID del tenant")
    
    @field_validator("password")
    @classmethod
    def validar_password(cls, v: str) -> str:
        es_valida, mensaje = validate_password_strength(v)
        if not es_valida:
            raise ValueError(mensaje)
        return v
    
    @field_validator("rol")
    @classmethod
    def validar_rol(cls, v: str) -> str:
        roles_validos = ["admin", "manager", "receptionist", "therapist"]
        if v.lower() not in roles_validos:
            raise ValueError(f"Rol inválido. Opciones: {', '.join(roles_validos)}")
        return v.lower()


# ============================================================
# Schema para actualizar un usuario
# ============================================================

class UserUpdate(BaseModel):
    """Datos opcionales para actualizar un usuario."""
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    apellido: Optional[str] = Field(None, min_length=1, max_length=100)
    telefono: Optional[str] = Field(None, max_length=50)
    rol: Optional[str] = None
    activo: Optional[bool] = None
    avatar_url: Optional[str] = Field(None, max_length=500)


# ============================================================
# Schema de respuesta (sin password_hash)
# ============================================================

class UserResponse(UserBase):
    """Respuesta de usuario (excluye password_hash por seguridad)."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    tenant_id: Optional[str] = None
    rol: str
    activo: bool
    ultimo_acceso: Optional[datetime] = None
    avatar_url: Optional[str] = None
    email_verificado: bool = False
    created_at: datetime


# ============================================================
# Schema para login
# ============================================================

class UserLogin(BaseModel):
    """Credenciales para iniciar sesión."""
    email: str = Field(..., description="Correo electrónico")
    password: str = Field(..., description="Contraseña")
    
    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        return v.lower().strip()


# ============================================================
# Schema de respuesta de tokens
# ============================================================

class TokenResponse(BaseModel):
    """Respuesta exitosa de autenticación con tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
    tenant: Optional[TenantResponse] = None


# ============================================================
# Schema para datos decodificados del token
# ============================================================

class TokenData(BaseModel):
    """Datos extraídos del payload del token JWT."""
    sub: Optional[str] = None  # user_id o email
    tenant_id: Optional[str] = None
    rol: Optional[str] = None
    type: Optional[str] = None  # "access" o "refresh"
    exp: Optional[int] = None


# ============================================================
# Schema para cambio de contraseña
# ============================================================

class ChangePassword(BaseModel):
    """Datos para cambiar la contraseña."""
    current_password: str = Field(..., description="Contraseña actual")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña")
    
    @field_validator("new_password")
    @classmethod
    def validar_nueva_password(cls, v: str) -> str:
        es_valida, mensaje = validate_password_strength(v)
        if not es_valida:
            raise ValueError(mensaje)
        return v


# ============================================================
# Schema para recuperación de contraseña
# ============================================================

class ForgotPassword(BaseModel):
    """Datos para solicitar recuperación de contraseña."""
    email: str = Field(..., description="Correo electrónico asociado a la cuenta")


class ResetPassword(BaseModel):
    """Datos para restablecer la contraseña con token."""
    token: str = Field(..., description="Token de recuperación")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña")
