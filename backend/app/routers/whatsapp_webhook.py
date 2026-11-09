import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..config import settings as s
from ..models.whatsapp import WhatsAppSettings
from ..services.whatsapp_webhook_service import parse_evolution_webhook, token_matches
from ..services.whatsapp_agent_service import whatsapp_agent

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Webhooks WhatsApp"])


@router.get(
    "/webhooks/evolution/{instance_name}",
    summary="Verificar webhook (GET)",
    description="Endpoint GET para probar que el webhook es accesible.",
)
async def evolution_webhook_get(
    instance_name: str,
    token: Optional[str] = None,
):
    webhook_token = s.EVOLUTION_WEBHOOK_TOKEN.strip() if s.EVOLUTION_WEBHOOK_TOKEN else ""
    if not token or not token_matches(token, webhook_token):
        return {"status": "unauthorized", "message": "Token inválido"}
    return {"status": "ok", "instance": instance_name, "message": "Webhook endpoint accesible"}


@router.post(
    "/webhooks/evolution/{instance_name}",
    summary="Webhook de Evolution",
    description="Endpoint público que recibe los webhooks de Evolution API.",
)
async def evolution_webhook(
    instance_name: str,
    request: Request,
    token: Optional[str] = None,
):
    logger.info(f"Webhook recibido: instance={instance_name}, has_token={bool(token)}, method={request.method}")

    if not token:
        query_params = request.query_params
        token = query_params.get("token")
        logger.info(f"Token desde query_params: has_token={bool(token)}")

    webhook_token = s.EVOLUTION_WEBHOOK_TOKEN.strip() if s.EVOLUTION_WEBHOOK_TOKEN else ""
    if not webhook_token:
        logger.warning("EVOLUTION_WEBHOOK_TOKEN no configurado; webhook ignorado.")
        return {"status": "ignored"}

    if not token or not token_matches(token, webhook_token):
        logger.warning(f"Token inválido para instancia {instance_name}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )

    try:
        body = await request.json()
    except Exception:
        body = None

    event = parse_evolution_webhook(body)
    kind = event.get("kind", "ignored")

    # Procesar en background: ACK 200 inmediato evita timeouts de Evolution
    # y la pérdida de mensajes cuando la IA tarda.
    asyncio.create_task(_process_event(instance_name, kind, event))

    return {"status": "ok"}


async def _process_event(instance_name: str, kind: str, event: dict):
    try:
        if kind == "connection":
            state = event.get("state")
            logger.info(f"Webhook connection.update: {instance_name} -> {state}")
            await _handle_connection(instance_name, state)

        elif kind == "message":
            phone = event.get("phone", "")
            text = event.get("text", "")
            from_me = event.get("fromMe", False)
            message_id = event.get("messageId")
            push_name = event.get("pushName")

            if from_me:
                logger.info(
                    f"ignorando mensaje saliente (fromMe=true) de {phone} "
                    f"a {instance_name}: {text[:40] if text else 'sin texto'}..."
                )
            elif text:
                logger.info(f"Mensaje de {phone} a {instance_name}: {text[:50]}...")
                await _handle_incoming_message(instance_name, phone, text, push_name, message_id)
            else:
                logger.info(f"Mensaje sin texto (ignorado) de {phone} a {instance_name}")
    except Exception as e:
        logger.error(f"Error procesando evento en background: {e}")


async def _handle_connection(instance_name: str, state: Optional[str]):
    db = SessionLocal()
    try:
        settings = db.query(WhatsAppSettings).filter(
            WhatsAppSettings.instance_name == instance_name,
            WhatsAppSettings.deleted_at == None,
        ).first()
        if settings:
            old_state = settings.status
            settings.status = state or old_state
            if state == "open" and old_state != "open":
                from datetime import datetime
                settings.connected_at = datetime.utcnow()
                # Auto-habilitar el agente al conectarse
                if not settings.agent_enabled:
                    settings.agent_enabled = True
                if not settings.webhook_registered:
                    await _try_register_webhook(db, settings)
                    settings.webhook_registered = True
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error procesando connection.update: {e}")
    finally:
        db.close()


async def _handle_incoming_message(
    instance_name: str,
    phone: str,
    text: str,
    push_name: Optional[str],
    message_id: Optional[str],
):
    db = SessionLocal()
    try:
        settings = db.query(WhatsAppSettings).filter(
            WhatsAppSettings.instance_name == instance_name,
            WhatsAppSettings.deleted_at == None,
        ).first()
        if settings:
            await whatsapp_agent.process_message(
                db, settings.tenant_id, phone, text, push_name, message_id
            )
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}", exc_info=True)
    finally:
        db.close()


async def _try_register_webhook(db: Session, settings: WhatsAppSettings):
    from ..services.whatsapp_service import evolution_client

    public_url = s.PUBLIC_API_URL.strip().rstrip("/") if s.PUBLIC_API_URL else ""
    if not public_url or not settings.instance_name:
        return

    webhook_url = f"{public_url}/webhooks/evolution/{settings.instance_name}?token={s.EVOLUTION_WEBHOOK_TOKEN}"
    try:
        await evolution_client.set_webhook(settings.instance_name, webhook_url)
        logger.info(f"Webhook registrado para {settings.instance_name}: {webhook_url[:60]}...")
    except Exception as e:
        logger.warning(f"No se pudo registrar webhook para {settings.instance_name}: {e}")