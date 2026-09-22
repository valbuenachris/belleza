# ============================================================
# backend/app/models/service.py - Modelo de Servicio
# Representa un servicio que el SPA ofrece (masajes, faciales, etc.)
# ============================================================

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, Text, Integer, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import TenantBaseModel

if TYPE_CHECKING:
    from .appointment import Appointment


class Service(Base, TenantBaseModel):
    """
    Modelo que representa un servicio ofrecido por el SPA.
    Cada tenant define su propio catálogo de servicios.
    """

    __tablename__ = "services"
    __table_args__ = (
        # Índice compuesto para optimizar queries por tenant (paridad con
        # la migración 0002 y con database/schema.sql)
        Index("idx_tenant_active", "tenant_id", "is_active"),
    )

    # ----------------------------------------------------------
    # Datos del servicio
    # ----------------------------------------------------------
    nombre: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nombre del servicio",
    )
    descripcion: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Descripción del servicio",
    )
    precio: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Precio del servicio",
    )
    duracion: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
        comment="Duración en minutos",
    )

    # ----------------------------------------------------------
    # Relaciones
    # ----------------------------------------------------------
    citas: Mapped[List["Appointment"]] = relationship(
        "Appointment",
        back_populates="service_rel",
        passive_deletes=True,
    )

    # ----------------------------------------------------------
    # Alias de conveniencia (compatibilidad con la UI)
    # ----------------------------------------------------------
    @property
    def activo(self) -> bool:
        """Alias para is_active."""
        return self.is_active

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, nombre={self.nombre}, precio={self.precio})>"