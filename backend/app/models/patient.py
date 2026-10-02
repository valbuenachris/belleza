# ============================================================
# backend/app/models/patient.py - Modelo de Paciente
# Representa un paciente/cliente que recibe servicios en el SPA
# ============================================================

from datetime import date, datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, Date, DateTime, Text, Integer, Index
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import TenantBaseModel

if TYPE_CHECKING:
    from .appointment import Appointment


class Patient(Base, TenantBaseModel):
    """
    Modelo que representa un paciente del SPA.
    Los datos son 100% aislados por tenant.
    """

    __tablename__ = "patients"
    __table_args__ = (
        # Índice compuesto para optimizar queries por tenant (paridad con
        # la migración 0002 y con database/schema.sql)
        Index("idx_tenant_active", "tenant_id", "is_active"),
    )

    # ----------------------------------------------------------
    # Información personal
    # ----------------------------------------------------------
    nombre: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Nombre del paciente",
    )
    apellido: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Apellido del paciente",
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Correo electrónico del paciente",
    )
    telefono: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Teléfono de contacto",
    )
    fecha_nacimiento: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Fecha de nacimiento",
    )
    genero: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="Género: female, male, other",
    )
    direccion: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Dirección del paciente",
    )
    notas_medicas: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notas/alergias relevantes del paciente",
    )

    # ----------------------------------------------------------
    # Programa de fidelidad (Loyalty Rewards)
    # ----------------------------------------------------------
    puntos: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Estrellas/puntos de fidelidad acumulados (10 = 1 sesión gratis)",
    )
    sesiones_gratis: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Sesiones gratuitas disponibles",
    )
    wallet_pass_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        unique=True,
        comment="Identificador único del pase digital (Apple Wallet / Google Wallet)",
    )

    # ----------------------------------------------------------
    # Apple Wallet Web Service (actualización dinámica del pase)
    # ----------------------------------------------------------
    wallet_auth_token: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        unique=True,
        comment="authenticationToken del pase (cabecera ApplePass del web service)",
    )
    wallet_updated_at: Mapped[Optional[datetime]] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=True,
        comment="Última actualización de puntos/sesiones (Last-Modified / If-Modified-Since)",
    )

    # ----------------------------------------------------------
    # Enlace público de la tarjeta (compartir con el cliente)
    # ----------------------------------------------------------
    wallet_share_token: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        comment="Token de capacidad del enlace público /tarjeta/{token} (CSPRNG)",
    )
    wallet_share_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Expiración del enlace público de la tarjeta (NULL = sin enlace activo)",
    )

    # ----------------------------------------------------------
    # Google Wallet (LoyaltyClass / LoyaltyObject integration)
    # ----------------------------------------------------------
    google_wallet_object_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        comment=(
            "Id del LoyaltyObject en Google Wallet "
            "(formato {issuer_id}.{patient_id}). Se crea al sincronizar."
        ),
    )
    google_wallet_class_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment=(
            "Id del LoyaltyClass usado para este objeto "
            "(per-tenant: {issuer_id}.loyalty-class-{tenant_id})."
        ),
    )
    google_wallet_updated_at: Mapped[Optional[datetime]] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=True,
        comment="Última sincronización exitosa con Google Wallet (para diagnóstico)",
    )

    # ----------------------------------------------------------
    # Relaciones
    # ----------------------------------------------------------
    citas: Mapped[List["Appointment"]] = relationship(
        "Appointment",
        back_populates="patient_rel",
        passive_deletes=True,
    )

    # ----------------------------------------------------------
    # Alias de conveniencia (compatibilidad con la UI)
    # ----------------------------------------------------------
    @property
    def activo(self) -> bool:
        """Alias para is_active."""
        return self.is_active

    @property
    def nombre_completo(self) -> str:
        """Nombre completo del paciente."""
        return f"{self.nombre} {self.apellido}".strip()

    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, nombre={self.nombre} {self.apellido})>"