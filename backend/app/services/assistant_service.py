# ============================================================
# backend/app/services/assistant_service.py - Asistente IA (FreeLLMAPI)
# Lógica de negocio del asistente: genera respuestas con la IA,
# guarda el historial de consultas (pregunta + respuesta + feedback)
# y expone operaciones de gestión para administradores.
#
# Integración con FreeLLMAPI (https://apifreellm.com):
#   POST {FREELLMAPI_BASE_URL}/chat          (FREELLMAPI_BASE_URL por
#                                             defecto: https://apifreellm.com/api/v1)
#   Authorization: Bearer {FREELLMAPI_API_KEY}
#   Body: {"message": "<prompt>", "model": "<opcional>"}
#   Respuesta 200: {"success": true, "response": "<texto>", ...}
#
# REGLAS:
#   - La API key NUNCA sale del backend (no se registra ni se expone).
#   - Los errores del proveedor se clasifican (401/400/429/timeout) y
#     se devuelven con mensajes seguros al usuario; los detalles se
#     registran en el log del backend para debugging.
#   - El historial es por tenant y por usuario; los administradores
#     pueden revisarlo y gestionarlo (soft delete).
# ============================================================

import logging
import time
from datetime import datetime
from typing import List, Optional

import httpx
from sqlalchemy import func, or_
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from ..config import settings
from ..models.assistant import AssistantQuery
from ..models.tenant import Tenant
from ..models.user import User

logger = logging.getLogger(__name__)


# ============================================================
# Estado de la integración
# ============================================================

def is_enabled() -> bool:
    """True si el asistente está activo (enabled + API key configurada)."""
    return bool(settings.FREELLMAPI_ENABLED and settings.FREELLMAPI_API_KEY)


def is_configured() -> bool:
    """True si la API key de FreeLLMAPI está configurada (aunque esté off)."""
    return bool(settings.FREELLMAPI_API_KEY)


def missing_config_fields() -> List[str]:
    """Campos requeridos sin valor (para el endpoint de diagnóstico)."""
    missing: List[str] = []
    if not settings.FREELLMAPI_API_KEY:
        missing.append("FREELLMAPI_API_KEY")
    if not settings.FREELLMAPI_ENABLED:
        missing.append("FREELLMAPI_ENABLED=true")
    return missing


def status_info() -> dict:
    """Estado de la integración (sin exponer secretos)."""
    return {
        "enabled": bool(settings.FREELLMAPI_ENABLED),
        "configured": is_configured(),
        "active": is_enabled(),
        "base_url": settings.FREELLMAPI_BASE_URL if is_configured() else None,
        "model": settings.FREELLMAPI_MODEL or None,
        "missing": [] if is_configured() else missing_config_fields(),
    }


# ============================================================
# Cliente de FreeLLMAPI
# ============================================================

def _call_freellmapi(prompt: str) -> str:
    """
    Llama a FreeLLMAPI y devuelve el texto de la respuesta.

    Raises:
        ValueError: Con un mensaje seguro y accionable para el usuario.
    """
    if not is_enabled():
        raise ValueError(
            "El asistente IA no está habilitado. "
            "Activa FREELLMAPI_ENABLED y configura FREELLMAPI_API_KEY en el backend."
        )

    url = f"{settings.FREELLMAPI_BASE_URL.rstrip('/')}/chat"
    body: dict = {"message": prompt}
    if settings.FREELLMAPI_MODEL:
        body["model"] = settings.FREELLMAPI_MODEL

    started = time.monotonic()
    try:
        with httpx.Client(
            timeout=settings.FREELLMAPI_TIMEOUT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.FREELLMAPI_API_KEY}",
                # Identificación del cliente (buena práctica de la API)
                "User-Agent": "spa-management-backend/1.0",
            },
        ) as client:
            response = client.post(url, json=body)
        duration_ms = int((time.monotonic() - started) * 1000)
    except httpx.TimeoutException:
        logger.error(
            f"[Assistant] Timeout llamando a FreeLLMAPI ({settings.FREELLMAPI_TIMEOUT}s)"
        )
        raise ValueError(
            "El asistente IA tardó demasiado en responder; inténtalo de nuevo."
        )
    except httpx.HTTPError as exc:
        logger.error(f"[Assistant] Error de red con FreeLLMAPI: {_exc_summary(exc)}")
        raise ValueError(
            "No se pudo contactar con el asistente IA; inténtalo de nuevo."
        )

    # ----------------------------------------------------------
    # Clasificación segura de errores HTTP (sin exponer la key)
    # ----------------------------------------------------------
    if response.status_code == 401:
        logger.error(
            "[Assistant] FreeLLMAPI rechazó la API key (401); "
            "revisa FREELLMAPI_API_KEY"
        )
        raise ValueError(
            "La configuración del asistente IA es inválida "
            "(API key rechazada). Contacta al administrador."
        )
    if response.status_code == 429:
        logger.warning("[Assistant] FreeLLMAPI rate-limit (429)")
        raise ValueError(
            "El asistente IA alcanzó su límite de uso; "
            "espera unos segundos e inténtalo de nuevo."
        )
    if response.status_code != 200:
        body_preview = response.text[:200] if response.text else "sin detalle"
        logger.error(
            f"[Assistant] FreeLLMAPI error {response.status_code}: {body_preview}"
        )
        raise ValueError(
            "El asistente IA no está disponible en este momento; "
            "inténtalo más tarde."
        )

    # ----------------------------------------------------------
    # Parseo defensivo de la respuesta JSON
    # ----------------------------------------------------------
    try:
        data = response.json()
    except Exception as exc:
        logger.error(f"[Assistant] Respuesta de FreeLLMAPI no es JSON: {_exc_summary(exc)}")
        raise ValueError("El asistente IA respondió de forma inesperada.")

    answer = (data.get("response") or "").strip() if isinstance(data, dict) else ""
    success = bool(data.get("success")) if isinstance(data, dict) else False

    logger.info(
        f"[Assistant] FreeLLMAPI OK en {duration_ms}ms "
        f"(success={success}, chars={len(answer)})"
    )
    if not answer:
        logger.warning(f"[Assistant] FreeLLMAPI respondió sin texto: {str(data)[:200]}")
        raise ValueError("El asistente IA no generó una respuesta; inténtalo de nuevo.")

    return answer


def _exc_summary(exc: Exception) -> str:
    """Resumen seguro de una excepción HTTP (sin credenciales)."""
    return str(exc)[:300]


# ============================================================
# Prompt con contexto del tenant
# ============================================================

def _build_prompt(tenant: Optional[Tenant], user: Optional[User], question: str) -> str:
    """
    Construye el prompt del sistema con el contexto del SPA:
    el asistente actúa como experto de recepción/fidelidad del negocio
    (servicios, recomendaciones y programa de fidelidad) y responde
    SIEMPRE en español, de forma amable y concisa.
    """
    tenant_name = tenant.nombre if tenant else "el SPA"
    user_rol = user.rol if user else "usuario"
    meta = 0
    premio = ""
    if tenant:
        meta = tenant.puntos_meta or 0
        premio = tenant.premio_fidelidad or ""
    return (
        "Eres el asistente IA de un sistema de gestión para centros de "
        "estética y relajación (SPAs). Ayudas al personal del SPA a:\n"
        "  - Resolver consultas sobre clientes y servicios del SPA.\n"
        "  - Recomendar servicios/tratamientos según las necesidades.\n"
        "  - Explicar el programa de fidelidad (estrellas, canjes y "
        "sesiones gratuitas).\n\n"
        f"Contexto actual: SPA '{tenant_name}'. El programa de fidelidad "
        f"otorga {meta} estrellas por cada sesión y, al alcanzar la meta, "
        f"se premia con: '{premio or 'una sesión gratuita'}'. El rol del "
        "usuario que pregunta es: " + user_rol + ".\n\n"
        "Reglas de respuesta:\n"
        "  - Responde SIEMPRE en español, de forma amable, clara y concisa.\n"
        "  - Si no conoces un dato específico, indícalo y sugiere consultar"
        " el sistema o al administrador.\n"
        "  - No inventes precios ni datos de clientes.\n\n"
        f"Pregunta del usuario: {question}"
    )


# ============================================================
# Operaciones principales
# ============================================================

def ask_assistant(db: Session, tenant_id: str, user: User, question: str) -> dict:
    """
    Genera la respuesta de la IA a una pregunta y la guarda en el
    historial (assistant_queries) asociada al tenant y al usuario.

    Raises:
        ValueError: Si no está habilitado o la pregunta es inválida.

    Returns:
        dict con id, question, response, is_understood y created_at.
    """
    question = (question or "").strip()
    if not question:
        raise ValueError("La pregunta no puede estar vacía.")
    if len(question) > 2000:
        raise ValueError("La pregunta es demasiado extensa (máximo 2000 caracteres).")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    # Genera la respuesta con FreeLLMAPI (puede lanzar ValueError).
    prompt = _build_prompt(tenant, user, question)
    ai_response = _call_freellmapi(prompt)

    # Persistencia SOLO si la IA respondió correctamente.
    try:
        query_row = AssistantQuery(
            tenant_id=tenant_id,
            user_id=user.id,
            question=question,
            response=ai_response,
            is_understood=None,
            is_active=True,
        )
        db.add(query_row)
        db.commit()
        db.refresh(query_row)

        logger.info(
            f"[Assistant] Consulta registrada: id={query_row.id}, "
            f"user={user.id}, tenant={tenant_id}, chars={len(ai_response)}"
        )

        return {
            "id": query_row.id,
            "question": query_row.question,
            "response": query_row.response or "",
            "is_understood": query_row.is_understood,
            "created_at": query_row.created_at,
        }
    except ProgrammingError as e:
        logger.warning(f"[Assistant] Tabla assistant_queries no existe: {e}")
        # Devuelve la respuesta de la IA sin guardar en el historial
        # (para que el usuario pueda verla aunque no se guarde)
        return {
            "id": None,
            "question": question,
            "response": ai_response,
            "is_understood": None,
            "created_at": datetime.utcnow(),
        }


def get_user_history(
    db: Session,
    tenant_id: str,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Historial del propio usuario (más recientes primero), paginado."""
    try:
        total = db.query(func.count(AssistantQuery.id)).filter(
            AssistantQuery.tenant_id == tenant_id,
            AssistantQuery.user_id == user_id,
            AssistantQuery.deleted_at == None,  # noqa: E711
        ).scalar() or 0

        rows = db.query(AssistantQuery).filter(
            AssistantQuery.tenant_id == tenant_id,
            AssistantQuery.user_id == user_id,
            AssistantQuery.deleted_at == None,  # noqa: E711
        ).order_by(AssistantQuery.created_at.desc()).offset(offset).limit(limit).all()

        return {
            "queries": [_to_dict(q) for q in rows],
            "total": total,
        }
    except ProgrammingError as e:
        logger.warning(f"[Assistant] Tabla assistant_queries no existe: {e}")
        return {
            "queries": [],
            "total": 0,
        }


def list_queries(
    db: Session,
    tenant_id: str,
    user_id: Optional[str] = None,
    is_understood: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    Lista paginada de TODAS las consultas del tenant (panel de
    administración), con filtros opcionales y nombre del usuario.
    """
    try:
        conditions = [
            AssistantQuery.tenant_id == tenant_id,
            AssistantQuery.deleted_at == None,  # noqa: E711
        ]
        if user_id:
            conditions.append(AssistantQuery.user_id == user_id)
        if is_understood is not None:
            conditions.append(AssistantQuery.is_understood == is_understood)
        if search:
            like = f"%{search.strip()}%"
            conditions.append(
                or_(
                    AssistantQuery.question.like(like),
                    AssistantQuery.response.like(like),
                )
            )

        total = db.query(func.count(AssistantQuery.id)).filter(*conditions).scalar() or 0

        # Join con users para mostrar quién preguntó (nombre del usuario).
        rows = (
            db.query(AssistantQuery, User)
            .outerjoin(User, User.id == AssistantQuery.user_id)
            .filter(*conditions)
            .order_by(AssistantQuery.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        queries = []
        for query_row, creator in rows:
            item = _to_dict(query_row)
            if creator:
                item["user_name"] = f"{creator.nombre} {creator.apellido}".strip() or creator.username
            queries.append(item)

        return {"queries": queries, "total": total}
    except ProgrammingError as e:
        logger.warning(f"[Assistant] Tabla assistant_queries no existe: {e}")
        return {"queries": [], "total": 0}


def set_feedback(db: Session, query: AssistantQuery, is_understood: bool) -> AssistantQuery:
    """
    Registra el feedback de calidad del usuario sobre una respuesta.
    Actualiza is_understood (True = útil, False = no útil).
    """
    query.is_understood = bool(is_understood)
    query.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(query)
    logger.info(
        f"[Assistant] Feedback registrado: id={query.id}, "
        f"is_understood={query.is_understood}"
    )
    return query


def soft_delete_query(db: Session, query: AssistantQuery) -> None:
    """Eliminación lógica de una consulta (panel de administración)."""
    query.soft_delete()
    db.commit()
    logger.info(f"[Assistant] Consulta eliminada (soft): id={query.id}")


def get_stats(db: Session, tenant_id: str) -> dict:
    """
    Estadísticas de uso y calidad del asistente en el tenant:
    total, respondidas, feedbacks y usuarios únicos.
    """
    try:
        conditions = [
            AssistantQuery.tenant_id == tenant_id,
            AssistantQuery.deleted_at == None,  # noqa: E711
        ]
        total = db.query(func.count(AssistantQuery.id)).filter(*conditions).scalar() or 0

        answered = db.query(func.count(AssistantQuery.id)).filter(
            *conditions,
            AssistantQuery.response != None,  # noqa: E711
        ).scalar() or 0

        understood = db.query(func.count(AssistantQuery.id)).filter(
            *conditions,
            AssistantQuery.is_understood == True,  # noqa: E712
        ).scalar() or 0

        not_understood = db.query(func.count(AssistantQuery.id)).filter(
            *conditions,
            AssistantQuery.is_understood == False,  # noqa: E712
        ).scalar() or 0

        unique_users = db.query(func.count(func.distinct(AssistantQuery.user_id))).filter(
            *conditions,
            AssistantQuery.user_id != None,  # noqa: E711
        ).scalar() or 0

        avg_len = db.query(func.avg(func.length(AssistantQuery.response))).filter(
            *conditions,
            AssistantQuery.response != None,  # noqa: E711
        ).scalar()
        avg_response_chars = int(round(avg_len or 0))

        logger.info(f"[Assistant] Stats tenant={tenant_id}: total={total}, understood={understood}")

        return {
            "total_queries": total,
            "total_answered": answered,
            "understood": understood,
            "not_understood": not_understood,
            "pending_feedback": answered - understood - not_understood,
            "unique_users": unique_users,
            "avg_response_chars": avg_response_chars,
        }
    except ProgrammingError as e:
        logger.warning(f"[Assistant] Tabla assistant_queries no existe: {e}")
        return {
            "total_queries": 0,
            "total_answered": 0,
            "understood": 0,
            "not_understood": 0,
            "pending_feedback": 0,
            "unique_users": 0,
            "avg_response_chars": 0,
        }


# ============================================================
# Utilidades
# ============================================================

def _to_dict(query: AssistantQuery) -> dict:
    """Serializa un AssistantQuery al formato de los esquemas."""
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