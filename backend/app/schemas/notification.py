# ============================================================
# backend/app/schemas/notification.py - Schemas de Notificaciones
# Validación de request/response para el router /api/v1/notifications
# (campana de notificaciones internas del Dashboard).
# ============================================================

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------
# Responses
# ------------------------------------------------------------

class NotificationResponse(BaseModel):
    """Notificación interna de un usuario del tenant."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    user_id: str
    title: str
    message: Optional[str] = None
    type: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None


class NotificationListResponse(BaseModel):
    """Lista paginada de notificaciones + contador de no leídas."""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadNotificationsCountResponse(BaseModel):
    """Contador de notificaciones no leídas (badge de la campana)."""
    unread_count: int


class NotificationMarkAllReadResponse(BaseModel):
    """Resultado de marcar todas las notificaciones como leídas."""
    updated: int = Field(..., description="Número de notificaciones actualizadas")
    unread_count: int = Field(..., description="No leídas restantes (0 tras la operación)")
