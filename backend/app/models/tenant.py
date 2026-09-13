# ============================================================
# backend/app/models/tenant.py - Modelo de Tenant (SPA)
# Representa cada centro de estética registrado en el sistema
# ============================================================

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from ..database import Base
from .base import BaseMixin, generate_uuid

if TYPE_CHECKING:
    from .user import User


class Tenant(Base, BaseMixin):
    """
    Modelo que representa un SPA/centro de estética (tenant).
    Cada tenant tiene sus datos completamente aislados.
    """
    
    __tablename__ = "tenants"
    
    # ----------------------------------------------------------
    # Campos principales
    # ----------------------------------------------------------
    nombre: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nombre del SPA",
    )
    subdominio: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Subdominio único para el tenant (ej: 'demo' -> demo.spasystem.com)",
    )
    plan: Mapped[str] = mapped_column(
        String(50),
        default="basic",
        nullable=False,
        comment="Plan de suscripción: basic, professional, enterprise",
    )
    
    # ----------------------------------------------------------
    # Estado y fechas
    # ----------------------------------------------------------
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="Fecha de creación del tenant",
    )
    fecha_expiracion: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        comment="Fecha de expiración de la suscripción (null = sin expiración)",
    )
    
    # ----------------------------------------------------------
    # Configuración y límites
    # ----------------------------------------------------------
    configuracion: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="Configuración específica del tenant en formato JSON",
    )
    limite_usuarios: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
        comment="Número máximo de usuarios permitidos",
    )
    limite_pacientes: Mapped[int] = mapped_column(
        Integer,
        default=1000,
        nullable=False,
        comment="Número máximo de pacientes permitidos",
    )
    
    # ----------------------------------------------------------
    # Información de contacto
    # ----------------------------------------------------------
    logo_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL del logo del SPA",
    )
    direccion: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Dirección física del SPA",
    )
    telefono: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Teléfono de contacto",
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Email de contacto del SPA",
    )
    
    # ----------------------------------------------------------
    # Configuración regional
    # ----------------------------------------------------------
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="America/Bogota",
        nullable=False,
        comment="Zona horaria del tenant",
    )
    moneda: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
        comment="Moneda principal (ISO 4217)",
    )
    
    # ----------------------------------------------------------
    # Relaciones
    # ----------------------------------------------------------
    usuarios: Mapped[List["User"]] = relationship(
        "User",
        back_populates="tenant",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    
    # ----------------------------------------------------------
    # Métodos de negocio
    # ----------------------------------------------------------
    
    def is_valid(self) -> bool:
        """Verifica si el tenant es válido (activo y no expirado)."""
        return self.activo and not self.has_expired
    
    @property
    def activo(self) -> bool:
        """Alias para is_active."""
        return self.is_active
    
    @property
    def has_expired(self) -> bool:
        """Verifica si la suscripción ha expirado."""
        if self.fecha_expiracion is None:
            return False  # Sin expiración
        return datetime.utcnow() > self.fecha_expiracion
    
    def can_add_user(self, current_count: int) -> bool:
        """Verifica si se puede agregar otro usuario."""
        return current_count < self.limite_usuarios
    
    def can_add_patient(self, current_count: int) -> bool:
        """Verifica si se puede agregar otro paciente."""
        return current_count < self.limite_pacientes
    
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, nombre={self.nombre}, subdominio={self.subdominio})>"
