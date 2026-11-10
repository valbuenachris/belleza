# ============================================================
# backend/app/models/service_related.py - Servicios relacionados
# Permite sugerir servicios complementarios (ej. Limpieza -> Dermapen)
# ============================================================

from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from ..database import Base
from .base import TenantBaseModel

if TYPE_CHECKING:
    from .service import Service


class ServiceRelated(Base, TenantBaseModel):
    __tablename__ = "service_related"
    __table_args__ = (
        Index("idx_sr_tenant_service", "tenant_id", "service_id"),
    )

    service_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("services.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="Servicio origen",
    )
    related_service_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("services.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="Servicio sugerido/relacionado",
    )

    service_rel: Mapped[Optional["Service"]] = relationship(
        "Service",
        foreign_keys="[ServiceRelated.service_id]",
        lazy="selectin",
    )
    related_rel: Mapped[Optional["Service"]] = relationship(
        "Service",
        foreign_keys="[ServiceRelated.related_service_id]",
        lazy="selectin",
    )
