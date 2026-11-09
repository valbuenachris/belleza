# ============================================================
# backend/app/services/whatsapp_reminder_service.py
# Recordatorios de citas por WhatsApp (24 horas antes)
# Envía un mensaje al paciente con los detalles de su cita y le
# pide que confirme. La confirmación la procesa el agente
# (whatsapp_agent_service) cuando el paciente responde.
# ============================================================

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..config import settings as s
from ..database import SessionLocal
from ..models.appointment import Appointment
from ..models.patient import Patient
from ..models.whatsapp import WhatsAppMessage, WhatsAppSettings
from ..services.whatsapp_service import evolution_client
from ..utils.security import generate_uuid

logger = logging.getLogger(__name__)

# Ventana: enviar cuando faltan ~24h (más/menos margen para el loop).
REMINDER_WINDOW_MIN = 23.25  # horas antes de la cita
REMINDER_WINDOW_MAX = 24.25  # horas antes de la cita
LOOP_INTERVAL_SECONDS = 300  # 5 minutos

REMINDS_MESSAGE_TEMPLATE = (
    "\U0001F4C5 Hola {nombre}! \U0001F4C5\n\n"
    "Te recordamos tu cita programada:\n"
    "\U0001F4C6 Servicio: {servicio}\n"
    "\U0001F552 Hora: {hora}\n"
    "\U0001F469\u200D\u2695\uFE0F Terapeuta: {terapeuta}\n\n"
    "\u2705 Responde CONFIRMO para confirmar tu cita.\n"
    "\u274C Responde CANCELAR para cancelarla."
)


def _wa_number(phone: str) -> str:
    """Número de WhatsApp en formato internacional para Evolution (dígitos + 57)."""
    digits = "".join(c for c in phone or "" if c.isdigit())
    if not digits:
        return ""
    if digits.startswith("57"):
        return digits
    if len(digits) == 10:
        return f"57{digits}"
    return digits


def _patient_appointments_next_24h(
    db: Session,
    instance: WhatsAppSettings,
    tenant_id: str,
    now: datetime,
) -> list:
    """Citas pending del tenant cuya cita está a ~24h de distancia."""
    start = now + timedelta(hours=REMINDER_WINDOW_MIN)
    end = now + timedelta(hours=REMINDER_WINDOW_MAX)
    return (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.deleted_at == None,  # noqa: E711
            Appointment.estado == "pending",
            Appointment.date_time >= start,
            Appointment.date_time <= end,
        )
        .all()
    )


def _reminder_already_sent(db: Session, appointment_id: str) -> bool:
    mid = f"reminder:{appointment_id}"
    return (
        db.query(WhatsAppMessage.id)
        .filter(WhatsAppMessage.message_id == mid)
        .first()
        is not None
    )


def _save_reminder(
    db: Session,
    tenant_id: str,
    conversation_id: str,
    appointment_id: str,
    content: str,
):
    db.add(WhatsAppMessage(
        id=generate_uuid(),
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        message_id=f"reminder:{appointment_id}",
        role="assistant",
        content=content,
    ))
    db.commit()


def _get_or_create_conversation(db: Session, tenant_id: str, phone: str):
    from ..models.whatsapp import WhatsAppConversation

    conv = (
        db.query(WhatsAppConversation)
        .filter(
            WhatsAppConversation.tenant_id == tenant_id,
            WhatsAppConversation.phone == phone,
            WhatsAppConversation.deleted_at == None,  # noqa: E711
        )
        .first()
    )
    if conv:
        return conv

    patient = (
        db.query(Patient)
        .filter(
            Patient.tenant_id == tenant_id,
            Patient.telefono == phone,
            Patient.deleted_at == None,  # noqa: E711
        )
        .first()
    )

    conv = WhatsAppConversation(
        id=generate_uuid(),
        tenant_id=tenant_id,
        phone=phone,
        patient_id=patient.id if patient else None,
        status="bot",
        last_message_at=datetime.utcnow(),
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def _tenant_now_naive(db: Session, tenant_id: str) -> datetime:
    """Hora actual del tenant como naive (hora local del negocio)."""
    try:
        from ..models.tenant import Tenant
        from zoneinfo import ZoneInfo

        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        tz_name = tenant.timezone or "America/Bogota"
        tz = ZoneInfo(tz_name)
        now = datetime.now(tz)
        return now.replace(tzinfo=None)
    except Exception as exc:
        logger.warning(f"[WhatsApp Reminder] _tenant_now_naive error: {exc}")
        return datetime.utcnow()


async def _process_instance(db: Session, instance: WhatsAppSettings):
    """Envía recordatorios pendientes para una instancia/tenant."""

    # Las citas se guardan en hora local del SPA (naive), por eso el 'now' de
    # la ventana debe ser la hora local del tenant, no UTC.
    now = _tenant_now_naive(db, instance.tenant_id)
    for apt in _patient_appointments_next_24h(db, instance, instance.tenant_id, now):
        if _reminder_already_sent(db, str(apt.id)):
            continue

        patient = (
            db.query(Patient)
            .filter(
                Patient.id == apt.patient_id,
                Patient.tenant_id == instance.tenant_id,
                Patient.deleted_at == None,  # noqa: E711
            )
            .first()
        )
        if not patient or not patient.telefono:
            continue

        number = _wa_number(patient.telefono)
        if not number:
            continue

        nombre = patient.nombre_completo or f"Cliente {patient.telefono[-4:]}"
        content = REMINDS_MESSAGE_TEMPLATE.format(
            nombre=nombre,
            servicio=apt.service or "Servicio",
            hora=apt.hora_inicio or "Hora a confirmar",
            terapeuta=apt.therapist or "Terapeuta",
        )

        try:
            await evolution_client.send_text(instance.instance_name, number, content)
        except Exception as exc:
            logger.error(f"[WhatsApp Reminder] Error enviando recordatorio "
                         f"para cita {apt.id}: {exc}")
            continue

        conv = _get_or_create_conversation(db, instance.tenant_id, patient.telefono)
        _save_reminder(db, instance.tenant_id, conv.id, str(apt.id), content)
        logger.info(f"[WhatsApp Reminder] Recordatorio enviado para cita {apt.id} "
                    f"(paciente {patient.telefono})")


async def run_reminder_check():
    """Revisa una vez las citas a ~24h y envía los recordatorios pendientes."""
    if not (s.WHATSAPP_BOT_ENABLED and s.EVOLUTION_API_URL and s.EVOLUTION_API_KEY):
        logger.info("[WhatsApp Reminder] Bot/Evolution no configurado; se omite.")
        return

    db = SessionLocal()
    try:
        instances = (
            db.query(WhatsAppSettings)
            .filter(
                WhatsAppSettings.status == "open",
                WhatsAppSettings.deleted_at == None,  # noqa: E711
                WhatsAppSettings.instance_name != None,  # noqa: E711
                WhatsAppSettings.agent_enabled == True,  # noqa: E712
            )
            .all()
        )
        for instance in instances:
            await _process_instance(db, instance)
    except Exception as exc:
        db.rollback()
        logger.error(f"[WhatsApp Reminder] Error en run_reminder_check: {exc}")
    finally:
        db.close()


async def reminder_loop():
    """Loop en background iniciado desde el lifespan de la app."""
    logger.info("[WhatsApp Reminder] Loop de recordatorios iniciado")
    while True:
        try:
            await run_reminder_check()
        except Exception as exc:
            logger.error(f"[WhatsApp Reminder] Error en loop: {exc}")
        await asyncio.sleep(LOOP_INTERVAL_SECONDS)