# ============================================================
# backend/app/models/base.py - Modelo base con campos comunes
# Todos los modelos del sistema heredan de estas clases
# ============================================================

import uuid
from datetime import datetime
from typing import Optional, Any, Dict

from sqlalchemy import String, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import CHAR

from ..database import Base


def generate_uuid() -> str:
    """Genera un UUID4 como string."""
    return str(uuid.uuid4())


class BaseMixin:
    """
    Mixin con campos comunes para todos los modelos.
    Proporciona: id, created_at, updated_at, deleted_at, is_active
    """
    
    id: Mapped[str] = mapped_column(
        CHAR(36),
        primary_key=True,
        default=generate_uuid,
        comment="Identificador único UUID4",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="Fecha y hora de creación",
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=True,
        comment="Fecha y hora de última actualización",
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        comment="Fecha y hora de eliminación lógica (soft delete)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica si el registro está activo",
    )
    
    def soft_delete(self) -> None:
        """
        Marca el registro como eliminado (soft delete).
        Establece deleted_at con la fecha/hora actual.
        """
        self.deleted_at = datetime.utcnow()
        self.is_active = False
    
    def restore(self) -> None:
        """Restaura un registro eliminado (undo soft delete)."""
        self.deleted_at = None
        self.is_active = True
    
    @property
    def is_deleted(self) -> bool:
        """Verifica si el registro ha sido eliminado."""
        return self.deleted_at is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el modelo a un diccionario.
        Útil para serialización JSON.
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat() if value else None
            result[column.name] = value
        return result


class TenantBaseModel(BaseMixin):
    """
    Modelo base para entidades que pertenecen a un tenant.
    Incluye tenant_id para separación multitenant.
    TODAS las queries deben filtrar por este campo.
    """
    
    tenant_id: Mapped[str] = mapped_column(
        CHAR(36),
        nullable=False,
        index=True,
        comment="ID del tenant al que pertenece este registro",
    )
    
    __abstract__ = True
    
    # Índice compuesto para optimizar queries por tenant
    __table_args__ = (
        Index("idx_tenant_active", "tenant_id", "is_active"),
    )


# Clase Base re-exportada para compatibilidad
Base = Base
