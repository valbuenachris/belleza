# ============================================================
# backend/app/models/clinical_record.py - Modelo de Registro Clínico
# Representa una evolución/sesión de tratamiento registrada en la
# historia clínica de un paciente
# ============================================================

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from ..database import Base
from .base import TenantBaseModel

if TYPE_CHECKING:
    from .patient import Patient
    from .user import User
    from .appointment import Appointment


class ClinicalRecord(Base, TenantBaseModel):
    """
    Modelo que representa un registro de la historia clínica de un
    paciente: cada evolución/sesión registrada durante el tratamiento.
    Todos los datos pertenecen a un solo tenant (aislamiento total).
    """

    __tablename__ = "clinical_records"
    __table_args__ = (
        # Índice compuesto para optimizar queries por tenant
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
    therapist_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="FK al terapeuta que registró la evolución (usuario del tenant)",
    )
    appointment_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36),
        ForeignKey("appointments.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="FK a la cita/sesión de la cual se registra la evolución",
    )

    # ----------------------------------------------------------
    # Contenido clínico
    # ----------------------------------------------------------
    fecha: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Fecha y hora de la sesión/evolución",
    )
    zona_tratada: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Zona tratada (ej: Rostro, Espalda)",
    )
    tratamiento_servicio: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Tratamiento o servicio realizado",
    )
    productos_parametros: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Productos aplicados / parámetros (ej: Ácido hialurónico 2ml)",
    )
    observaciones: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Observaciones y evolución del paciente",
    )
    diagnostico: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Diagnóstico o valoración clínica",
    )

    # ----------------------------------------------------------
    # Relaciones
    # ----------------------------------------------------------
    patient_rel: Mapped[Optional["Patient"]] = relationship(
        "Patient",
        foreign_keys="[ClinicalRecord.patient_id]",
        lazy="selectin",
    )
    therapist_rel: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys="[ClinicalRecord.therapist_id]",
        lazy="selectin",
    )
    appointment_rel: Mapped[Optional["Appointment"]] = relationship(
        "Appointment",
        foreign_keys="[ClinicalRecord.appointment_id]",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Propiedades de serialización (compatibilidad con la UI)
    # ----------------------------------------------------------

    @property
    def patient_name(self) -> str:
        """Nombre completo del paciente."""
        rel = self.patient_rel
        return f"{rel.nombre} {rel.apellido}".strip() if rel else ""

    @property
    def therapist_name(self) -> str:
        """Nombre completo del terapeuta."""
        rel = self.therapist_rel
        return f"{rel.nombre} {rel.apellido}".strip() if rel else ""

    @property
    def servicio(self) -> str:
        """Nombre del servicio de la cita asociada (si existe)."""
        if self.appointment_rel and self.appointment_rel.service_rel:
            return self.appointment_rel.service_rel.nombre
        return ""

    def __repr__(self) -> str:
        return (
            f"<ClinicalRecord(id={self.id}, patient={self.patient_name}, "
            f"fecha={self.fecha}, zona={self.zona_tratada})>"
        )