# ============================================================
# backend/app/models/assistant.py - Modelo de Consultas al Asistente IA
# Almacena cada pregunta realizada al asistente de la IA (integración
# con FreeLLMAPI) y su respuesta, para seguimiento (historial) y
# analítica (calidad del feedback: is_understood).
# Aislamiento total por tenant (TenantBaseModel).
# ============================================================

from typing import Optional

from sqlalchemy import Boolean, Text, ForeignKey, Index, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import CHAR

from ..database import Base
from .base import TenantBaseModel


class AssistantQuery(Base, TenantBaseModel):
    """
    Consulta de un usuario del SPA al asistente de IA (FreeLLMAPI).

    Cada fila guarda la pregunta original, la respuesta generada y el
    feedback del usuario (is_understood), con triple estado:
      - NULL      -> el usuario aún no valoró la respuesta
      - True      -> la respuesta fue útil / entendida
      - False     -> la respuesta NO fue útil / no se entendió

    Permite a los administradores revisar (listado/estadísticas) y
    gestionar (soft delete) el historial de preguntas del tenant.
    """

    __tablename__ = "assistant_queries"
    __table_args__ = (
        # Índice compuesto equivalente al definido por TenantBaseModel
        Index("idx_tenant_active", "tenant_id", "is_active"),
        # Optimiza el listado del historial ordenado por fecha
        Index("idx_assistant_tenant_created", "tenant_id", "created_at"),
    )

    # ----------------------------------------------------------
    # Referencias
    # ----------------------------------------------------------
    user_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="FK al usuario que realizó la consulta (SET NULL si se elimina)",
    )

    # ----------------------------------------------------------
    # Pregunta y respuesta
    # ----------------------------------------------------------
    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Pregunta formulada por el usuario",
    )
    response: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Respuesta generada por el asistente IA (FreeLLMAPI)",
    )

    # ----------------------------------------------------------
    # Feedback de calidad (tri-estado, ver docstring de la clase)
    # ----------------------------------------------------------
    is_understood: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        default=None,
        comment=(
            "Feedback del usuario: NULL = sin valorar, "
            "TRUE = útil, FALSE = no útil"
        ),
    )

    # ----------------------------------------------------------
    # Campos de estado y auditoría (heredados de TenantBaseModel pero
    # declarados explícitamente para mayor claridad y control)
    # ----------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Estado activo del registro (soft delete lógico)",
    )

    deleted_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        comment="Fecha de eliminación soft (NULL si no está eliminado)",
    )

    # created_at y updated_at ya están definidos en TenantBaseModel
    # pero los incluimos aquí para mayor claridad en la documentación
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
        comment="Fecha de creación del registro",
    )

    updated_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        server_default="CURRENT_TIMESTAMP",
        onupdate="CURRENT_TIMESTAMP",
        comment="Fecha de última actualización del registro",
    )
