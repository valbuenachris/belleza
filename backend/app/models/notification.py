# ============================================================
# backend/app/models/notification.py - Modelo de Notificaciones
# Notificaciones internas dirigidas a un usuario del tenant
# (campana del Dashboard). Aislamiento total por tenant.
# ============================================================

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import CHAR

from ..database import Base
from .base import TenantBaseModel


class Notification(Base, TenantBaseModel):
    """
    Notificación interna para un usuario del SPA.

    Cada fila pertenece a un tenant y a un usuario destinatario; el
    estado de lectura es individual (is_read/read_at), de modo que dos
    usuarios pueden recibir la misma notificación de forma independiente.

    Tipos usados por notification_service:
      - appointment          -> nueva cita agendada
      - appointment_reminder -> recordatorio de cita próxima
      - loyalty              -> recompensa de fidelidad otorgada
      - system               -> avisos generales
    """

    __tablename__ = "notifications"
    __table_args__ = (
        # Índice compuesto equivalente al definido por TenantBaseModel
        Index("idx_tenant_active", "tenant_id", "is_active"),
        # Optimiza el badge: contar no leídas de un usuario
        Index("idx_notifications_user_read", "tenant_id", "user_id", "is_read"),
        # Optimiza el listado ordenado por fecha
        Index("idx_notifications_tenant_created", "tenant_id", "created_at"),
    )

    # ----------------------------------------------------------
    # Destinatario
    # ----------------------------------------------------------
    user_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="FK al usuario destinatario de la notificación",
    )

    # ----------------------------------------------------------
    # Contenido
    # ----------------------------------------------------------
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Título corto de la notificación",
    )
    message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detalle o cuerpo de la notificación",
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="info",
        index=True,
        comment="Tipo: appointment, appointment_reminder, loyalty, system",
    )

    # ----------------------------------------------------------
    # Estado de lectura
    # ----------------------------------------------------------
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="TRUE si el usuario ya la leyó",
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        comment="Fecha/hora en la que se marcó como leída (NULL si no leída)",
    )

    # created_at, updated_at, deleted_at e is_active vienen de
    # TenantBaseModel (id, tenant_id y auditoría).
