import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_tenant_id, require_role
from ..models.user import User
from ..models.whatsapp import WhatsAppConversation, WhatsAppMessage, WhatsAppSettings
from ..schemas.whatsapp import (
    WhatsAppConnectResponse,
    WhatsAppConversationListResponse,
    WhatsAppConversationResponse,
    WhatsAppMessageListResponse,
    WhatsAppMessageResponse,
    WhatsAppSettingsResponse,
    WhatsAppSettingsUpdate,
    WhatsAppStatusResponse,
)
from ..services.whatsapp_service import evolution_client
from ..config import settings as app_settings
from ..utils.security import generate_uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

ADMIN_ROLES = ["admin", "manager"]


# ============================================================
# Helpers
# ============================================================

def _get_settings_or_create(db: Session, tenant_id: str) -> WhatsAppSettings:
    settings = db.query(WhatsAppSettings).filter(
        WhatsAppSettings.tenant_id == tenant_id,
        WhatsAppSettings.deleted_at == None,
    ).first()
    if not settings:
        settings = WhatsAppSettings(
            id=generate_uuid(),
            tenant_id=tenant_id,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


async def _register_webhook(instance_name: str, settings: WhatsAppSettings):
    """Registra el webhook en Evolution para la instancia."""
    public_url = app_settings.PUBLIC_API_URL.strip().rstrip("/") if app_settings.PUBLIC_API_URL else ""
    webhook_token = app_settings.EVOLUTION_WEBHOOK_TOKEN.strip() if app_settings.EVOLUTION_WEBHOOK_TOKEN else ""
    if not public_url or not webhook_token:
        logger.warning("PUBLIC_API_URL o EVOLUTION_WEBHOOK_TOKEN no configurados; webhook no registrado.")
        return
    webhook_url = f"{public_url}/webhooks/evolution/{instance_name}?token={webhook_token}"
    try:
        await evolution_client.set_webhook(instance_name, webhook_url)
        settings.webhook_registered = True
        logger.info(f"Webhook registrado para {instance_name}")
    except ValueError as e:
        logger.warning(f"No se pudo registrar webhook en Evolution: {e}")


def _serialize_settings(s: WhatsAppSettings) -> dict:
    return {
        "instance_name": s.instance_name,
        "status": s.status,
        "connected_at": s.connected_at,
        "qr_code": s.qr_code,
        "agent_enabled": s.agent_enabled,
        "agent_name": s.agent_name,
        "agent_tone": s.agent_tone,
        "notifications_enabled": s.notifications_enabled,
        "webhook_registered": s.webhook_registered,
    }


def _serialize_conversation(
    c: WhatsAppConversation,
    last_message_content: Optional[str] = None,
    last_message_role: Optional[str] = None,
) -> dict:
    patient_name = None
    if c.patient_rel:
        patient_name = c.patient_rel.nombre_completo or None
    return {
        "id": str(c.id),
        "phone": c.phone,
        "push_name": c.push_name,
        "patient_id": str(c.patient_id) if c.patient_id else None,
        "patient_name": patient_name,
        "status": c.status,
        "last_message_at": c.last_message_at,
        "last_message_content": last_message_content,
        "last_message_role": last_message_role,
        "created_at": c.created_at,
    }


def _last_message_of(db: Session, conversation_id: str) -> tuple[Optional[str], Optional[str]]:
    """Devuelve (content, role) del último mensaje de la conversación."""
    msg = (
        db.query(WhatsAppMessage)
        .filter(
            WhatsAppMessage.conversation_id == conversation_id,
            WhatsAppMessage.deleted_at == None,
        )
        .order_by(WhatsAppMessage.created_at.desc())
        .first()
    )
    if not msg:
        return None, None
    return msg.content, msg.role


# ============================================================
# GET /whatsapp/settings
# ============================================================

@router.get(
    "/settings",
    summary="Obtener configuración de WhatsApp",
    description="Devuelve la configuración de WhatsApp del tenant actual.",
)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN_ROLES)),
    tenant_id: str = Depends(get_current_tenant_id),
):
    settings = _get_settings_or_create(db, tenant_id)
    return _serialize_settings(settings)


# ============================================================
# PUT /whatsapp/settings
# ============================================================

@router.put(
    "/settings",
    summary="Actualizar configuración de WhatsApp",
    description="Actualiza la configuración del agente (nombre, tono, notificaciones).",
)
async def update_settings(
    body: WhatsAppSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN_ROLES)),
    tenant_id: str = Depends(get_current_tenant_id),
):
    settings = _get_settings_or_create(db, tenant_id)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)

    # Al activar el agente, registrar webhook en Evolution
    if body.agent_enabled is True and settings.instance_name and settings.status == "open":
        await _register_webhook(settings.instance_name, settings)
        db.commit()

    return _serialize_settings(settings)


# ============================================================
# POST /whatsapp/instance
# ============================================================

@router.post(
    "/instance",
    summary="Crear instancia de WhatsApp",
    description="Crea una instancia en Evolution para el tenant actual. Idempotente.",
)
async def create_instance(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN_ROLES)),
    tenant_id: str = Depends(get_current_tenant_id),
):
    if not evolution_client.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servidor de WhatsApp (Evolution) no está configurado.",
        )

    settings = _get_settings_or_create(db, tenant_id)
    instance_name = settings.instance_name

    if not instance_name:
        from ..models.tenant import Tenant
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        slug = (tenant.nombre or "spa").lower().replace(" ", "-").replace("_", "-")[:20]
        instance_name = f"spa-{slug}-{tenant_id[:8]}"
        settings.instance_name = instance_name

    try:
        result = await evolution_client.create_instance(instance_name)
        settings.status = result.get("state") or "close"
        settings.agent_enabled = True
        if result.get("qr"):
            settings.qr_code = result["qr"]
        db.commit()

        # Registrar webhook en Evolution
        if settings.instance_name and settings.status == "open":
            await _register_webhook(settings.instance_name, settings)

        return {
            "instance_name": instance_name,
            "state": result.get("state"),
            "qr": result.get("qr"),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# POST /whatsapp/connect
# ============================================================

@router.post(
    "/connect",
    summary="Conectar instancia de WhatsApp",
    description="Conecta la instancia (devuelve QR si es necesario).",
)
async def connect_instance(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN_ROLES)),
    tenant_id: str = Depends(get_current_tenant_id),
):
    settings = _get_settings_or_create(db, tenant_id)
    if not settings.instance_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primero debes crear la instancia.",
        )

    try:
        result = await evolution_client.connect(settings.instance_name)
        if result.get("qr"):
            settings.qr_code = result["qr"]
        if result.get("state"):
            settings.status = result["state"]
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# GET /whatsapp/status
# ============================================================

@router.get(
    "/status",
    summary="Estado de conexión",
    description="Consulta el estado de la conexión con WhatsApp.",
)
async def get_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN_ROLES)),
    tenant_id: str = Depends(get_current_tenant_id),
):
    settings = _get_settings_or_create(db, tenant_id)
    if not settings.instance_name:
        return {"connected": False, "state": None, "instance_name": None}

    state = await evolution_client.connection_state(settings.instance_name)
    if state is None:
        settings.status = "close"
    elif state != settings.status:
        settings.status = state
        if state == "open" and not settings.connected_at:
            from datetime import datetime
            settings.connected_at = datetime.utcnow()
    db.commit()

    # Si está conectado: auto-habilitar agente y registrar webhook
    if settings.status == "open" and settings.instance_name:
        if not settings.agent_enabled:
            settings.agent_enabled = True
        if not settings.webhook_registered:
            await _register_webhook(settings.instance_name, settings)
        db.commit()

    return {
        "connected": settings.status == "open",
        "state": settings.status,
        "instance_name": settings.instance_name,
    }


# ============================================================
# POST /whatsapp/disconnect
# ============================================================

@router.post(
    "/disconnect",
    summary="Desconectar instancia",
    description="Desconecta (logout) la instancia de WhatsApp pero la conserva.",
)
async def disconnect_instance(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN_ROLES)),
    tenant_id: str = Depends(get_current_tenant_id),
):
    settings = _get_settings_or_create(db, tenant_id)
    if not settings.instance_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay instancia para desconectar.",
        )

    try:
        await evolution_client.logout(settings.instance_name)
        settings.status = "close"
        settings.qr_code = None
        db.commit()
        return {"message": "Instancia desconectada exitosamente"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# GET /whatsapp/conversations
# ============================================================

@router.get(
    "/conversations",
    summary="Listar conversaciones",
    description="Lista las conversaciones de WhatsApp del tenant.",
)
def list_conversations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN_ROLES)),
    tenant_id: str = Depends(get_current_tenant_id),
):
    query = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.tenant_id == tenant_id,
        WhatsAppConversation.deleted_at == None,
    )
    if status_filter:
        query = query.filter(WhatsAppConversation.status == status_filter)

    total = query.count()
    convs = query.order_by(
        WhatsAppConversation.last_message_at.desc(),
        WhatsAppConversation.created_at.desc(),
    ).offset(offset).limit(limit).all()

    result = []
    for c in convs:
        last_content, last_role = _last_message_of(db, c.id)
        result.append(_serialize_conversation(c, last_content, last_role))

    return {
        "conversations": result,
        "total": total,
    }


# ============================================================
# GET /whatsapp/conversations/{id}/messages
# ============================================================

@router.get(
    "/conversations/{conversation_id}/messages",
    summary="Mensajes de una conversación",
    description="Historial de mensajes de una conversación de WhatsApp.",
)
def list_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN_ROLES)),
    tenant_id: str = Depends(get_current_tenant_id),
):
    conv = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.id == conversation_id,
        WhatsAppConversation.tenant_id == tenant_id,
        WhatsAppConversation.deleted_at == None,
    ).first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada",
        )

    total = db.query(WhatsAppMessage.id).filter(
        WhatsAppMessage.conversation_id == conversation_id,
        WhatsAppMessage.deleted_at == None,
    ).count()

    msgs = db.query(WhatsAppMessage).filter(
        WhatsAppMessage.conversation_id == conversation_id,
        WhatsAppMessage.deleted_at == None,
    ).order_by(WhatsAppMessage.created_at.asc()).offset(offset).limit(limit).all()

    return {
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in msgs
        ],
        "total": total,
    }