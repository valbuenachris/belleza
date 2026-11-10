# ============================================================
# backend/app/models/appointment_item.py - Ítems de Cita
# Un servicio (o línea) dentro de una cita. Una cita puede tener
# N servicios (multi-servicio). La cabecera `appointments` guarda
# el servicio principal (compatibilidad) y `monto_total` se calcula
# como la suma de los items.
# ============================================================

from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Integer, Numeric, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from ..database import Base
from .base import TenantBaseModel

if TYPE_CHECKING:
    from .appointment import Appointment
    from .service import Service


class AppointmentItem(Base, TenantBaseModel):
    __tablename__ = "appointment_items"
    __table_args__ = (
        Index("idx_ai_tenant_appt", "tenant_id", "appointment_id"),
    )

    appointment_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("appointments.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="FK a la cita",
    )
    service_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("services.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="FK al servicio",
    )
    nombre_snapshot: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nombre del servicio al momento del agendamiento",
    )
    precio_unitario: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Precio unitario en el momento de agendar",
    )
    cantidad: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Cantidad (por defecto 1)",
    )
    descuento: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Descuento aplicado a la línea",
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Subtotal de la línea = (precio_unitario*cantidad) - descuento",
    )

    appointment_rel: Mapped[Optional["Appointment"]] = relationship(
        "Appointment",
        back_populates="items_rel",
        lazy="selectin",
    )
    service_rel: Mapped[Optional["Service"]] = relationship(
        "Service",
        lazy="selectin",
    )


class AppointmentPayment(Base, TenantBaseModel):
    __tablename__ = "appointment_payments"
    __table_args__ = (
        Index("idx_ap_tenant_appt", "tenant_id", "appointment_id"),
    )

    appointment_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("appointments.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="FK a la cita",
    )
    monto: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Monto del pago",
    )
    metodo_pago: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="efectivo",
        comment="Método: efectivo, tarjeta, transferencia, nequi, daviplata, credito, otro",
    )
    descuento: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Descuento aplicado en este pago",
    )
    observaciones: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notas del pago",
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        CHAR(36),
        nullable=True,
        comment="Usuario que registró el pago (staff)",
    )

    appointment_rel: Mapped[Optional["Appointment"]] = relationship(
        "Appointment",
        back_populates="pagos_rel",
        lazy="selectin",
    )
