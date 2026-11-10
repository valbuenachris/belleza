# ============================================================
# backend/app/models/appointment.py - Modelo de Cita
# Representa una cita entre un paciente, un terapeuta y un servicio
# ============================================================

from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, Integer, Text, Numeric, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from ..database import Base
from .base import TenantBaseModel

if TYPE_CHECKING:
    from .patient import Patient
    from .user import User
    from .service import Service
    from .appointment_item import AppointmentItem, AppointmentPayment


# Roles permitidos para el estado de una cita
ESTADOS_CITA = ("pending", "confirmed", "cancelled", "completed")


class Appointment(Base, TenantBaseModel):
    """
    Modelo que representa una cita agendada en el SPA.
    Siempre está asociada a un paciente, un terapeuta (usuario) y
    un servicio, todos dentro del mismo tenant.
    """

    __tablename__ = "appointments"
    __table_args__ = (
        # Índice compuesto para optimizar queries por tenant (paridad con
        # la migración 0002 y con database/schema.sql)
        Index("idx_tenant_active", "tenant_id", "is_active"),
    )

    # ----------------------------------------------------------
    # Referencias
    # ----------------------------------------------------------
    patient_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("patients.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="FK al paciente",
    )
    therapist_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="FK al terapeuta (usuario del tenant)",
    )
    service_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("services.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="FK al servicio",
    )

    # ----------------------------------------------------------
    # Agendamiento
    # ----------------------------------------------------------
    date_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
        comment="Fecha y hora de inicio de la cita",
    )
    duracion: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
        comment="Duración de la cita en minutos",
    )
    estado: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        index=True,
        comment="Estado: pending, confirmed, cancelled, completed",
    )
    precio: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Precio cobrado (si es null se usa el del servicio)",
    )
    notas: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notas adicionales de la cita",
    )

    # ----------------------------------------------------------
    # Pagos (crédito / pago total / parcial)
    # ----------------------------------------------------------
    monto_total: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Monto total de la cita (suma de items sin descuentos)",
    )
    total_pagado: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        default=Decimal("0.00"),
        comment="Total efectivamente pagado",
    )
    descuento_total: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        default=Decimal("0.00"),
        comment="Descuento total aplicado a la cita",
    )
    estado_pago: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unpaid",
        server_default="unpaid",
        comment="Estado de pago: unpaid, partial, paid (partial = crédito)",
    )

    # ----------------------------------------------------------
    # Programa de fidelidad
    # ----------------------------------------------------------
    loyalty_awarded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment=(
            "TRUE si la estrella de fidelidad ya se otorgó por esta cita "
            "(evita dobles premios al alternar estados)"
        ),
    )

    # ----------------------------------------------------------
    # Relaciones
    # ----------------------------------------------------------
    patient_rel: Mapped[Optional["Patient"]] = relationship(
        "Patient",
        back_populates="citas",
        foreign_keys="[Appointment.patient_id]",
        lazy="selectin",
    )
    therapist_rel: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys="[Appointment.therapist_id]",
        lazy="selectin",
    )
    service_rel: Mapped[Optional["Service"]] = relationship(
        "Service",
        back_populates="citas",
        foreign_keys="[Appointment.service_id]",
        lazy="selectin",
    )
    items_rel: Mapped[list["AppointmentItem"]] = relationship(
        "AppointmentItem",
        back_populates="appointment_rel",
        lazy="selectin",
        passive_deletes=True,
    )
    pagos_rel: Mapped[list["AppointmentPayment"]] = relationship(
        "AppointmentPayment",
        back_populates="appointment_rel",
        lazy="selectin",
        passive_deletes=True,
    )

    # ----------------------------------------------------------
    # Propiedades de serialización (compatibilidad con la UI)
    # ----------------------------------------------------------

    @property
    def patient(self) -> str:
        """Nombre completo del paciente."""
        rel = self.patient_rel
        return f"{rel.nombre} {rel.apellido}".strip() if rel else ""

    @property
    def service(self) -> str:
        """Nombre del servicio."""
        return self.service_rel.nombre if self.service_rel else ""

    @property
    def therapist(self) -> str:
        """Nombre completo del terapeuta."""
        rel = self.therapist_rel
        return f"{rel.nombre} {rel.apellido}".strip() if rel else ""

    @property
    def fecha(self) -> Optional[str]:
        """Fecha (YYYY-MM-DD) de la cita."""
        return self.date_time.strftime("%Y-%m-%d") if self.date_time else None

    @property
    def hora_inicio(self) -> Optional[str]:
        """Hora (HH:MM) de inicio de la cita."""
        return self.date_time.strftime("%H:%M") if self.date_time else None

    @property
    def time(self) -> Optional[str]:
        """Alias de hora_inicio (compatibilidad con la UI)."""
        return self.hora_inicio

    @property
    def total_precio(self) -> Optional[Decimal]:
        """Precio efectivo: el de la cita o el del servicio."""
        if self.precio is not None:
            return self.precio
        if self.service_rel and self.service_rel.precio is not None:
            return self.service_rel.precio
        return None

    def __repr__(self) -> str:
        return (
            f"<Appointment(id={self.id}, patient={self.patient}, "
            f"date_time={self.date_time}, estado={self.estado})>"
        )