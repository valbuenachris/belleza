# ============================================================
# backend/app/services/whatsapp_reminder_service.py
# Recordatorios de citas por WhatsApp:
#   1) La NOCHE ANTERIOR a las 19:00 (citas para mañana)
#   2) DOS HORAS ANTES de la cita
# Envía un mensaje al paciente con los detalles de su cita y le
# pide que confirme. La confirmación la procesa el agente
# (whatsapp_agent_service) cuando el paciente responde.
# ============================================================

import asyncio
import logging
from datetime import datetime, date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import settings as s
from ..database import SessionLocal
from ..models.appointment import Appointment
from ..models.patient import Patient
from ..models.whatsapp import WhatsAppMessage, WhatsAppSettings
from ..services.whatsapp_service import evolution_client
from ..utils.security import generate_uuid

logger = logging.getLogger(__name__)

LOOP_INTERVAL_SECONDS = 300  # 5 minutos

# Hora del recordatorio de la noche anterior (hora local del tenant)
EVENING_HOUR = 19  # 7:00 p.m.
# Máximo de horas que se espera después de las 19:00 para considerar la cita
# "de mañana" (ventana para el loop: no enviar pasada la medianoche).
EVENING_WINDOW_HOURS = 5  # hasta las 24:00 aprox (19:00 + 5)

# Ventana 2 horas antes (más/menos margen para el loop de 5 min)
REMINDER_2H_MIN = 1.92  # ~2h antes (margen por el loop)
REMINDER_2H_MAX = 2.08  # ~2h antes

EVENING_MESSAGE_TEMPLATE = (
    "\U0001F4C5 Hola {nombre}! \U0001F4C5\n\n"
    "Te recordamos que mañana tienes tu cita programada:\n"
    "\U0001F4C6 Servicio: {servicio}\n"
    "\U0001F552 Hora: {hora}\n"
    "\U0001F469\u200D\u2695\uFE0F Terapeuta: {terapeuta}\n\n"
    "\u2705 Responde CONFIRMO para confirmar tu cita.\n"
    "\u274C Responde CANCELAR para cancelarla."
)

REMINDER_2H_MESSAGE_TEMPLATE = (
    "\U000023F0 Hola {nombre}! Tu cita es en 2 horas:\n"
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


def _appointments_for_tomorrow(
    db: Session, tenant_id: str, now: datetime, target_day: date
) -> list:
    """Citas (pending/confirmed) que cayeron 'mañana' y aún no recordadas por la noche."""
    day_start = datetime(target_day.year, target_day.month, target_day.day, 0, 0)
    day_end = day_start + timedelta(days=1)
    return (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.deleted_at == None,  # noqa: E711
            Appointment.estado.in_(["pending", "confirmed"]),
            Appointment.date_time >= day_start,
            Appointment.date_time < day_end,
        )
        .all()
    )


def _appointments_in_2h(
    db: Session, tenant_id: str, now: datetime
) -> list:
    """Citas entre ahora y ~2 horas (ventana)."""
    start = now + timedelta(hours=REMINDER_2H_MIN)
    end = now + timedelta(hours=REMINDER_2H_MAX)
    return (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.deleted_at == None,  # noqa: E711
            Appointment.estado.in_(["pending", "confirmed"]),
            Appointment.date_time >= start,
            Appointment.date_time <= end,
        )
        .all()
    )


def _reminder_already_sent(db: Session, tag: str) -> bool:
    return (
        db.query(WhatsAppMessage.id)
        .filter(WhatsAppMessage.message_id == tag)
        .first()
        is not None
    )


def _save_reminder(
    db: Session,
    tenant_id: str,
    conversation_id: str,
    tag: str,
    content: str,
):
    db.add(WhatsAppMessage(
        id=generate_uuid(),
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        message_id=tag,
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


def _patient_for_appointment(db: Session, apt: Appointment):
    return (
        db.query(Patient)
        .filter(
            Patient.id == apt.patient_id,
            Patient.deleted_at == None,  # noqa: E711
        )
        .first()
    )


def _build_content(apt: Appointment, patient: Patient, template: str) -> str:
    nombre = patient.nombre_completo or f"Cliente {patient.telefono[-4:]}"
    return template.format(
        nombre=nombre,
        servicio=apt.service or "Servicio",
        hora=apt.hora_inicio or "Hora a confirmar",
        terapeuta=apt.therapist or "Terapeuta",
    )


async def _send_reminder(db: Session, instance: WhatsAppSettings, apt: Appointment, tag: str, content: str):
    """Envía el recordatorio y lo deduplica. Best-effort; nunca lanza."""
    patient = _patient_for_appointment(db, apt)
    if not patient or not patient.telefono:
        return

    number = _wa_number(patient.telefono)
    if not number:
        return

    if _reminder_already_sent(db, tag):
        return

    try:
        await evolution_client.send_text(instance.instance_name, number, content)
    except Exception as exc:
        logger.error(f"[WhatsApp Reminder] Error enviando ({tag}) para cita {apt.id}: {exc}")
        return

    conv = _get_or_create_conversation(db, instance.tenant_id, patient.telefono)
    _save_reminder(db, instance.tenant_id, conv.id, tag, content)
    logger.info(f"[WhatsApp Reminder] Enviado [{tag}] para cita {apt.id} ({patient.telefono})")


async def _process_instance(db: Session, instance: WhatsAppSettings):
    """Procesa recordatorios para una instancia/tenant."""
    now = _tenant_now_naive(db, instance.tenant_id)

    # 1) Noche anterior: si la hora local >= 19:00, recordar citas de mañana
    if now.hour >= EVENING_HOUR:
        tomorrow = (now + timedelta(days=1)).date()
        for apt in _appointments_for_tomorrow(db, instance.tenant_id, now, tomorrow):
            tag = f"reminder_eve:{apt.id}"
            if _reminder_already_sent(db, tag):
                continue
            patient = _patient_for_appointment(db, apt)
            if not patient or not patient.telefono:
                continue
            content = _build_content(apt, patient, EVENING_MESSAGE_TEMPLATE)
            await _send_reminder(db, instance, apt, tag, content)

    # 2) Dos horas antes
    for apt in _appointments_in_2h(db, instance.tenant_id, now):
        tag = f"reminder_2h:{apt.id}"
        if _reminder_already_sent(db, tag):
            continue
        patient = _patient_for_appointment(db, apt)
        if not patient or not patient.telefono:
            continue
        content = _build_content(apt, patient, REMINDER_2H_MESSAGE_TEMPLATE)
        await _send_reminder(db, instance, apt, tag, content)


async def run_reminder_check():
    """Revisa una vez y envía los recordatorios pendientes."""
    if not (s.WHATSAPP_BOT_ENABLED and s.EVOLUTION_API_URL and s.EVOLUTION_API_KEY):
        logger.info("[WhatsApp Reminder] Bot/Evolution no configurado; se omite.")
        return

    db = SessionLocal()
    try:
        locked = db.execute(text("SELECT GET_LOCK('wa_reminder', 0)")).scalar()
        if locked != 1:
            logger.info("[WhatsApp Reminder] Otro worker ya está ejecutando; se omite esta ronda.")
            return

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
        finally:
            db.execute(text("SELECT RELEASE_LOCK('wa_reminder')"))
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
