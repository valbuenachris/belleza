# ============================================================
# backend/app/routers/notifications.py - Notificaciones internas
# Endpoints de la campana del Dashboard: listado paginado, contador
# de no leídas, marcado individual y masivo como leídas. Todo
# aislado por tenant y por usuario autenticado.
# ============================================================

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_tenant_id, get_current_user
from ..models.user import User
from ..schemas.notification import (
    NotificationListResponse,
    NotificationMarkAllReadResponse,
    NotificationResponse,
    UnreadNotificationsCountResponse,
)
from ..services import notification_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["Notificaciones"])


# ============================================================
# Listado y contador
# ============================================================

@router.get(
    "",
    response_model=NotificationListResponse,
    summary="Listar notificaciones del usuario",
    description=(
        "Devuelve las notificaciones del usuario autenticado "
        "(más recientes primero), con filtro opcional por estado de "
        "lectura, paginación y contador de no leídas."
    ),
)
def list_notifications(
    is_read: Optional[bool] = Query(None, description="Filtrar por leídas/no leídas"),
    limit: int = Query(20, ge=1, le=100, description="Máximo de registros"),
    offset: int = Query(0, ge=0, description="Desplazamiento (paginación)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    return notification_service.list_user_notifications(
        db,
        tenant_id,
        current_user.id,
        is_read=is_read,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/unread-count",
    response_model=UnreadNotificationsCountResponse,
    summary="Contador de notificaciones no leídas",
    description="Número de notificaciones no leídas del usuario (badge de la campana).",
)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    return {
        "unread_count": notification_service.get_unread_count(
            db, tenant_id, current_user.id
        )
    }


# ============================================================
# Marcado de lectura
# ============================================================

@router.put(
    "/read-all",
    response_model=NotificationMarkAllReadResponse,
    summary="Marcar todas las notificaciones como leídas",
    description="Marca como leídas todas las notificaciones pendientes del usuario.",
)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    updated = notification_service.mark_all_read(db, tenant_id, current_user.id)
    return {"updated": updated, "unread_count": 0}


@router.put(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Marcar una notificación como leída",
    description="Marca como leída una notificación concreta del usuario autenticado.",
)
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        return notification_service.mark_notification_read(
            db, tenant_id, current_user.id, notification_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
