from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from ..database import Base
from .base import TenantBaseModel

if TYPE_CHECKING:
    from .patient import Patient


class WhatsAppSettings(Base, TenantBaseModel):
    __tablename__ = "whatsapp_settings"
    __table_args__ = (
        Index("idx_wa_settings_tenant", "tenant_id"),
        Index("idx_wa_settings_instance", "instance_name"),
    )

    instance_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        comment="Nombre de la instancia en Evolution (único global)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="close",
        comment="Estado: close, open, syncing",
    )
    connected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Última vez que se conectó exitosamente",
    )
    qr_code: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="QR en base64 para escanear (se limpia tras conectar)",
    )
    agent_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True si el agente IA está activo para este tenant",
    )
    agent_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Asistente del SPA",
        comment="Nombre del asistente virtual",
    )
    agent_tone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="amable",
        comment="Tono del agente: amable, profesional, vendedor, cercano",
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Notificar al personal por WhatsApp cuando se agenda una cita",
    )
    webhook_registered: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True si el webhook se registró exitosamente en Evolution",
    )


class WhatsAppConversation(Base, TenantBaseModel):
    __tablename__ = "whatsapp_conversations"
    __table_args__ = (
        Index("idx_wa_conv_tenant_phone", "tenant_id", "phone"),
        Index("idx_wa_conv_status", "status"),
    )

    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Número de teléfono (solo dígitos)",
    )
    push_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Nombre mostrado por WhatsApp",
    )
    patient_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36),
        ForeignKey("patients.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="FK al paciente si se identificó",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="bot",
        comment="Estado: bot, human",
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp del último mensaje",
    )

    patient_rel: Mapped[Optional["Patient"]] = relationship(
        "Patient",
        foreign_keys="[WhatsAppConversation.patient_id]",
        lazy="selectin",
    )
    messages: Mapped[List["WhatsAppMessage"]] = relationship(
        "WhatsAppMessage",
        back_populates="conversation",
        passive_deletes=True,
        order_by="WhatsAppMessage.created_at",
    )


class WhatsAppMessage(Base, TenantBaseModel):
    __tablename__ = "whatsapp_messages"
    __table_args__ = (
        Index("idx_wa_msg_conv", "conversation_id"),
    )

    conversation_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("whatsapp_conversations.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="FK a la conversación",
    )
    message_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        comment="ID del mensaje en Evolution (para dedup)",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="user",
        comment="Rol: user, assistant, system",
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Texto del mensaje",
    )

    conversation: Mapped[Optional["WhatsAppConversation"]] = relationship(
        "WhatsAppConversation",
        back_populates="messages",
        lazy="selectin",
    )