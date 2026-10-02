# ============================================================
# backend/app/routers/assistant.py - Asistente IA (FreeLLMAPI)
# Endpoints del asistente digital del SPA: chat (ask), historial del
# usuario y panel de administración (listado, estadísticas, feedback
# y eliminación de consultas). Todo aislado por tenant y protegido
# por la dependencia require_assistant_access (admin/manager).
# ============================================================

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_tenant_id, require_assistant_access
from ..models.assistant import AssistantQuery
from ..models.user import User
from ..schemas.assistant import (
    AssistantAskRequest,
    AssistantAskResponse,
    AssistantDeleteResponse,
    AssistantFeedbackRequest,
    AssistantHistoryResponse,
    AssistantQueryResponse,
    AssistantStatsResponse,
    AssistantStatusResponse,
)
from ..services import assistant_service
from ..utils.rate_limit import limiter, user_or_ip_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["Asistente IA"])


# ============================================================
# Helpers
# ============================================================

def _get_query_or_404(db: Session, tenant_id: str, query_id: str) -> AssistantQuery:
    """Busca una consulta del tenant (404 si no existe o está borrada)."""
    query_row = db.query(AssistantQuery).filter(
        AssistantQuery.id == query_id,
        AssistantQuery.tenant_id == tenant_id,
        AssistantQuery.deleted_at == None,  # noqa: E711
    ).first()
    if not query_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consulta del asistente no encontrada",
        )
    return query_row


# ============================================================
# Estado de la integración
# ============================================================

@router.get(
    "/status",
    response_model=AssistantStatusResponse,
    summary="Estado de la integración del Asistente IA",
    description=(
        "Indica si el asistente está habilitado y configurado "
        "(sin exponer la API key)."
    ),
)
def assistant_status(
    current_user: User = Depends(require_assistant_access),
):
    return assistant_service.status_info()


# ============================================================
# Chat: pregunta al asistente
# ============================================================

@router.post(
    "/ask",
    response_model=AssistantAskResponse,
    summary="Preguntar al Asistente IA",
    description=(
        "Envía una pregunta del usuario al asistente (FreeLLMAPI) y "
        "devuelve la respuesta generada. La consulta y su respuesta se "
        "guardan en el historial del tenant para analítica."
    ),
)
@limiter.limit("20/minute", key_func=user_or_ip_key)
def ask_assistant(
    body: AssistantAskRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_assistant_access),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        return assistant_service.ask_assistant(
            db, tenant_id, current_user, body.question, body.history
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# Historial del usuario actual
# ============================================================

@router.get(
    "/history",
    response_model=AssistantHistoryResponse,
    summary="Historial de consultas del usuario",
    description=(
        "Devuelve el historial de consultas del usuario autenticado "
        "(más recientes primero), paginado con limit/offset."
    ),
)
def get_history(
    limit: int = Query(50, ge=1, le=200, description="Máximo de registros"),
    offset: int = Query(0, ge=0, description="Desplazamiento (paginación)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_assistant_access),
    tenant_id: str = Depends(get_current_tenant_id),
):
    return assistant_service.get_user_history(
        db, tenant_id, current_user.id, limit=limit, offset=offset
    )


# ============================================================
# Panel de administración
# ============================================================

@router.get(
    "/queries",
    response_model=AssistantHistoryResponse,
    summary="Listar consultas del tenant (administración)",
    description=(
        "Lista todas las consultas del asistente del tenant con filtros "
        "opcionales (usuario, feedback, búsqueda de texto) y paginación. "
        "Uso exclusivo del panel de administración."
    ),
)
def list_tenant_queries(
    user_id: Optional[str] = Query(None, description="Filtrar por usuario"),
    is_understood: Optional[bool] = Query(None, description="Filtrar por feedback"),
    search: Optional[str] = Query(None, description="Búsqueda por texto (pregunta o respuesta)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_assistant_access),
    tenant_id: str = Depends(get_current_tenant_id),
):
    return assistant_service.list_queries(
        db,
        tenant_id,
        user_id=user_id,
        is_understood=is_understood,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/queries/stats",
    response_model=AssistantStatsResponse,
    summary="Estadísticas del asistente en el tenant",
    description=(
        "Indicadores de uso y calidad de las respuestas de la IA "
        "(totales, feedback de entendimiento y usuarios únicos)."
    ),
)
def get_queries_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_assistant_access),
    tenant_id: str = Depends(get_current_tenant_id),
):
    return assistant_service.get_stats(db, tenant_id)


@router.post(
    "/queries/{query_id}/feedback",
    response_model=AssistantQueryResponse,
    summary="Registrar feedback de una respuesta",
    description=(
        "Permite valorar si la respuesta de la IA fue entendida/útil "
        "(is_understood=true) o no (is_understood=false)."
    ),
)
def submit_feedback(
    query_id: str,
    body: AssistantFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_assistant_access),
    tenant_id: str = Depends(get_current_tenant_id),
):
    query_row = _get_query_or_404(db, tenant_id, query_id)
    query_row = assistant_service.set_feedback(db, query_row, body.is_understood)
    return _serialize_joined(query_row)


def _serialize_joined(query: AssistantQuery) -> dict:
    """Serializa la consulta para el response model (sin join de usuario)."""
    return {
        "id": query.id,
        "tenant_id": query.tenant_id,
        "user_id": query.user_id,
        "user_name": None,
        "question": query.question,
        "response": query.response,
        "is_understood": query.is_understood,
        "created_at": query.created_at,
        "updated_at": query.updated_at,
    }


@router.delete(
    "/queries/{query_id}",
    response_model=AssistantDeleteResponse,
    summary="Eliminar consulta del historial",
    description=(
        "Eliminación lógica (soft delete) de una consulta del asistente "
        "para gestionar el historial."
    ),
)
def delete_query(
    query_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_assistant_access),
    tenant_id: str = Depends(get_current_tenant_id),
):
    query_row = _get_query_or_404(db, tenant_id, query_id)
    assistant_service.soft_delete_query(db, query_row)
    return {"deleted": True, "message": "Consulta eliminada del historial"}