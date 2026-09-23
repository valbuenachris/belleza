# ============================================================
# backend/app/models/pass_registration.py - Registro de pases en
# dispositivos (Apple Wallet Web Service).
# Guarda qué dispositivo (deviceLibraryIdentifier) tiene registrado
# el pase de un paciente y su push token de APNs, para poder
# notificarle cuando cambien los puntos/sesiones y descargar la
# última versión del pase (/v1/passes/...).
# ============================================================

from typing import Optional

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .base import TenantBaseModel


class PassRegistration(Base, TenantBaseModel):
    """Registro device <-> pase del paciente (Apple Wallet Web Service)."""

    __tablename__ = "pass_registrations"
    __table_args__ = (
        # Un dispositivo solo se registra una vez por pase (paridad con
        # la migración 0007 y con database/schema.sql).
        UniqueConstraint(
            "device_library_identifier",
            "pass_type_identifier",
            "serial_number",
            name="ux_pass_registration",
        ),
    )

    patient_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="Paciente dueño del pase",
    )
    pass_type_identifier: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="passTypeIdentifier del pase (p.ej. pass.com.tuuspa.fidelidad)",
    )
    serial_number: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="serialNumber del pase (wallet_pass_id del paciente)",
    )
    device_library_identifier: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Identificador único del dispositivo en Apple Wallet",
    )
    push_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Token APNs del dispositivo para notificar actualizaciones del pase",
    )

    def __repr__(self) -> str:
        return (
            f"<PassRegistration(device={self.device_library_identifier}, "
            f"serial={self.serial_number})>"
        )