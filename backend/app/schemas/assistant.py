# ============================================================
# backend/app/schemas/assistant.py - Schemas del Asistente IA
# Validación de request/response para el router /api/v1/assistant
# (integración con FreeLLMAPI).
# ============================================================

from datetime import datetime
from typing import List, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict


# ------------------------------------------------------------
# Requests
# ------------------------------------------------------------

class AssistantAskRequest(BaseModel):
    """Pregunta del usuario hacia el asistente IA."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Pregunta o consulta del usuario hacia el asistente IA"
    )
    history: List[Dict[str, str]] = Field(
        default=[],
        description="Historial de la conversación previa para contexto del asistente"
    )


class AssistantFeedbackRequest(BaseModel):
    """Feedback de calidad de una respuesta del asistente IA."""
    is_understood: bool = Field(
        ...,
        description=(
            "True si la respuesta fue útil/entendida, "
            "False si no fue útil"
        ),
    )


# ------------------------------------------------------------
# Responses
# ------------------------------------------------------------

class AssistantAskResponse(BaseModel):
    """Respuesta inmediata del asistente tras registrar la consulta."""
    id: str
    question: str
    response: str
    is_understood: Optional[bool] = None
    created_at: datetime


class AssistantQueryResponse(BaseModel):
    """Consulta del historial (pregunta + respuesta + feedback)."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    user_id: Optional[str] = None
    # Nombre de usuario (join, para el panel de administración)
    user_name: Optional[str] = None
    question: str
    response: Optional[str] = None
    is_understood: Optional[bool] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class AssistantHistoryResponse(BaseModel):
    """Lista paginada de consultas del asistente."""
    queries: List[AssistantQueryResponse]
    total: int


class AssistantStatsResponse(BaseModel):
    """Estadísticas de uso/calidad del asistente IA en el tenant."""
    total_queries: int
    total_answered: int
    understood: int
    not_understood: int
    pending_feedback: int
    unique_users: int
    avg_response_chars: int


class AssistantDeleteResponse(BaseModel):
    """Confirmación de eliminación de una consulta."""
    deleted: bool
    message: str


# ------------------------------------------------------------
# Estado de la integración
# ------------------------------------------------------------

class AssistantStatusResponse(BaseModel):
    """Estado de la integración con FreeLLMAPI (sin exponer secretos)."""
    enabled: bool
    configured: bool
    active: bool
    base_url: Optional[str] = None
    model: Optional[str] = None
    missing: List[str]