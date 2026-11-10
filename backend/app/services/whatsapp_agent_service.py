import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..config import settings as s
from ..models.appointment import Appointment, ESTADOS_CITA
from ..models.patient import Patient
from ..models.service import Service
from ..models.user import User
from ..models.whatsapp import WhatsAppConversation, WhatsAppMessage, WhatsAppSettings
from ..services import appointment_service
from ..services.assistant_service import _call_freellmapi
from ..services.whatsapp_service import evolution_client
from ..utils.security import generate_uuid

logger = logging.getLogger(__name__)


def sanitize_text(text: Optional[str], limit: int = 4000) -> Optional[str]:
    """
    Limpia un texto antes de persistirlo en MySQL/WhatsApp:
    - Reemplaza (no descarta) pares surrogate sueltos por su equivalente
      Unicode real (utf-8 'surrogatepass' no está disponible en pymysql).
    - Recorta a `limit` caracteres.
    """
    if not text:
        return text
    try:
        text.encode("utf-8")
        return text[:limit]
    except UnicodeEncodeError:
        cleaned = text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        return cleaned[:limit]


def _cliente_context(conversation: "WhatsAppConversation") -> str:
    """
    Contexto del cliente que el agente debe conocer y NO preguntar:
    su número de teléfono (viene del chat de WhatsApp) y su nombre
    (pushName o nombre del paciente registrado).
    """
    phone_str = conversation.phone or "desconocido"
    nombre = (conversation.push_name or "").strip() or conversation.phone or ""
    return (
        "DATOS DEL CLIENTE QUE TE ESCRIBE (NO volver a preguntarle):\n"
        f"- Número de teléfono del cliente: {phone_str}\n"
        f"- Nombre del cliente: {nombre}\n"
        "Si necesitas identificarlo en el sistema usa SIEMPRE el número anterior, "
        "sin preguntarle."
    )


def _now_context(db: Session, tenant_id: str) -> str:
    """
    Fecha y hora ACTUAL del SPA en la zona horaria del tenant, y horario de
    atención (apertura/cierre) configurado. Sin esto el modelo inventa fechas
    (ej. "mañana = 23 ene") porque no conoce el hoy real del negocio.
    """
    try:
        from ..models.tenant import Tenant
        from zoneinfo import ZoneInfo

        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        tz_name = tenant.timezone or "America/Bogota"
        tz = ZoneInfo(tz_name)
        now = datetime.now(tz)
        day_name = now.strftime("%A")

        config = tenant.configuracion or {}
        if isinstance(config, dict):
            apertura = config.get("horario_apertura") or "08:00"
            cierre = config.get("horario_cierre") or "18:00"
            dias = config.get("dias_operacion") or [0, 1, 2, 3, 4, 5, 6]
        else:
            apertura, cierre = "08:00", "18:00"
            dias = [0, 1, 2, 3, 4, 5, 6]

        return (
            "FECHA Y HORA ACTUAL DEL SPA (en su zona horaria; usa SIEMPRE esto "
            "para calcular 'hoy', 'mañana', días de la semana y horas):\n"
            f"- Ahora: {now.strftime('%Y-%m-%d %H:%M')} ({tz_name})\n"
            f"- Día de la semana de hoy: {day_name}\n"
            f"- Horario de atención: {apertura} a {cierre}\n"
            f"- Días de operación (0=domingo, 6=sábado): {dias}\n"
            "Para 'mañana' suma 1 día al día actual con ESTA fecha.\n"
        )
    except Exception as exc:
        logger.warning(f"[WhatsApp Agent] _now_context error: {exc}")
        now_utc = datetime.utcnow()
        return (
            "FECHA Y HORA ACTUAL (referencia):\n"
            f"- Ahora (UTC): {now_utc.strftime('%Y-%m-%d %H:%M')}\n"
            f"- Día de la semana: {now_utc.strftime('%A')}\n"
        )


FALLBACK_REPLY = (
    "Lo siento, tuve un problema procesando tu solicitud. "
    "Por favor intenta de nuevo o contacta directamente con nuestro personal "
    "al teléfono del SPA. \U0001F64F"
)

FALLBACK_DISABLED_REPLY = (
    "¡Hola! \U0001F44B Gracias por escribirnos. Actualmente nuestro asistente "
    "virtual no está disponible, pero puedes llamarnos o visitarnos para agendar "
    "tu cita. \u2757 "
)

_JSON_CORRECTION = (
    "Tu respuesta no fue JSON válido. Corrige: responde UNA sola línea "
    "JSON: {\"reply\": \"mensaje corto\"} o {\"tool\": \"nombre\", \"args\": {...}}. "
    "Prohibido razonamiento, inglés, pasos o IDs. Solo español."
)


SYSTEM_PROMPT_TEMPLATE = (
    "Eres un asistente virtual de un SPA. Tu nombre es {agent_name}, tono {agent_tone}.\n"
    "{cliente_context}\n"
    "{now_context}\n"
    "OBLIGATORIO: Responde SIEMPRE en ESPAÑOL. Prohibido escribir en inglés.\n"
    "Tu respuesta al sistema debe ser UNA ÚNICA LÍNEA JSON, exactamente en uno de estos formatos:\n"
    '1) {"reply": "mensaje corto y amable para el cliente"}\n'
    '2) {"tool": "find_patient", "args": {"phone": "número"}}\n'
    '3) {"tool": "list_services", "args": {}}\n'
    '4) {"tool": "cancel_appointment", "args": {"appointment_id": "id"}}\n'
    '5) {"tool": "list_my_appointments", "args": {"patient_id": "id"}}\n'
    '6) {"tool": "check_availability", "args": {"date": "YYYY-MM-DD", "service_id": "id"}}\n'
    "REGLAS:\n"
    "- NUNCA expliques pasos, razones, análisis ni planes. Solo el JSON.\n"
    "- NUNCA preguntes por el teléfono del cliente (ya lo conoces).\n"
    "- Si no sabes qué hacer, usa {'reply': '¿En qué más puedo ayudarte?'}\n"
    "- Sé breve (máx 2 líneas).\n"
)


class WhatsAppAgentService:
    """
    Servicio que procesa mensajes de WhatsApp usando FreeLLMAPI como backend
    de IA para gestionar citas. Usa un protocolo JSON estricto para que el
    modelo invoque las herramientas de agenda de forma confiable.
    """

    def __init__(self):
        self.enabled = bool(
            s.WHATSAPP_BOT_ENABLED and s.FREELLMAPI_API_KEY and s.EVOLUTION_API_URL
        )

    def is_enabled(self) -> bool:
        return self.enabled

    async def process_message(
        self,
        db: Session,
        tenant_id: str,
        phone: str,
        text: str,
        push_name: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> Optional[str]:
        """Procesa un mensaje entrante y devuelve la respuesta enviada (o None)."""
        conversation = self._get_or_create_conversation(db, tenant_id, phone, push_name)

        settings = db.query(WhatsAppSettings).filter(
            WhatsAppSettings.tenant_id == tenant_id,
            WhatsAppSettings.deleted_at == None,
        ).first()

        # Deduplicación por message_id
        if message_id:
            existing = db.query(WhatsAppMessage.id).filter(
                WhatsAppMessage.message_id == message_id
            ).first()
            if existing:
                return None

        self._save_message(
            db, conversation.id, tenant_id, "user", sanitize_text(text), message_id
        )

        if not self.enabled:
            logger.warning(
                f"[WhatsApp Agent] Bot deshabilitado globalmente "
                f"(WHATSAPP_BOT_ENABLED/FREELLMAPI/EVOLUTION) para {instance_name(settings)}"
            )
            return None

        if not settings or settings.status != "open":
            logger.warning(
                f"[WhatsApp Agent] Instancia no abierta ({getattr(settings, 'status', 'none')}) o sin settings"
            )
            return None

        if not settings.agent_enabled:
            logger.info(f"[WhatsApp Agent] Agente deshabilitado para tenant {tenant_id}; respuesta cortés.")
            await evolution_client.send_text(settings.instance_name, phone, FALLBACK_DISABLED_REPLY)
            self._save_message(db, conversation.id, tenant_id, "assistant", FALLBACK_DISABLED_REPLY)
            conversation.last_message_at = datetime.utcnow()
            db.commit()
            return FALLBACK_DISABLED_REPLY

        if conversation.status == "human":
            logger.info("[WhatsApp Agent] Conversación en modo humano; no se responde.")
            return None

        # Guard previo a la IA: intenciones directas respondidas sin depender
        # del protocolo JSON (evita respuestas rotas para casos comunes).
        direct_reply = self._handle_direct_intent(db, tenant_id, text, conversation)
        if direct_reply:
            await evolution_client.send_text(settings.instance_name, phone, direct_reply)
            self._save_message(db, conversation.id, tenant_id, "assistant", direct_reply)
            conversation.last_message_at = datetime.utcnow()
            db.commit()
            return direct_reply

        try:
            history = self._build_history(db, conversation.id)
            cliente_context = _cliente_context(conversation)
            now_context = _now_context(db, tenant_id)
            system_prompt = SYSTEM_PROMPT_TEMPLATE.replace(
                "{agent_name}", settings.agent_name or "Asistente del SPA"
            ).replace(
                "{agent_tone}", settings.agent_tone or "amable"
            ).replace(
                "{cliente_context}", cliente_context
            ).replace(
                "{now_context}", now_context
            )

            reply = await self._call_ai_with_tools(
                db, tenant_id, system_prompt, history, conversation
            )
        except Exception as exc:
            logger.error(
                f"[WhatsApp Agent] Excepción en _call_ai_with_tools para tenant {tenant_id}: {exc}",
                exc_info=True,
            )
            reply = FALLBACK_REPLY

        if reply is None:
            reply = FALLBACK_REPLY

        if reply.strip().upper() == "HUMAN":
            conversation.status = "human"
            db.commit()
            human_msg = "Te comunico con un asesor humano. En breve alguien te atenderá. \U00002705"
            await evolution_client.send_text(settings.instance_name, phone, human_msg)
            self._save_message(db, conversation.id, tenant_id, "assistant", human_msg)
            conversation.last_message_at = datetime.utcnow()
            db.commit()
            return human_msg

        reply_clean = sanitize_text(reply) or FALLBACK_REPLY
        try:
            await evolution_client.send_text(settings.instance_name, phone, reply_clean)
        except Exception as exc:
            logger.error(f"[WhatsApp Agent] Error enviando respuesta: {exc}")
            return None

        self._save_message(db, conversation.id, tenant_id, "assistant", reply_clean)
        conversation.last_message_at = datetime.utcnow()
        db.commit()
        return reply_clean

    # ============================================================
    # Conversación y mensajes
    # ============================================================

    def _get_or_create_conversation(
        self, db: Session, tenant_id: str, phone: str, push_name: Optional[str]
    ) -> WhatsAppConversation:
        conv = db.query(WhatsAppConversation).filter(
            WhatsAppConversation.tenant_id == tenant_id,
            WhatsAppConversation.phone == phone,
            WhatsAppConversation.deleted_at == None,
        ).first()

        if conv:
            if push_name and push_name.strip():
                conv.push_name = sanitize_text(push_name.strip())
            return conv

        patient = self._ensure_patient(db, tenant_id, phone, push_name)

        conv = WhatsAppConversation(
            id=generate_uuid(),
            tenant_id=tenant_id,
            phone=phone,
            push_name=sanitize_text((push_name or "").strip()) or None,
            patient_id=patient.id if patient else None,
            status="bot",
            last_message_at=datetime.utcnow(),
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv

    def _ensure_patient(
        self, db: Session, tenant_id: str, phone: str, push_name: Optional[str] = None
    ) -> Optional[Patient]:
        """Crea el paciente si no existe por teléfono, para que haya patient_id."""
        phone_digits = self._normalize_phone(phone)
        if not phone_digits:
            return None

        patient = db.query(Patient).filter(
            Patient.tenant_id == tenant_id,
            Patient.telefono == phone_digits,
            Patient.deleted_at == None,
        ).first()
        if patient:
            return patient

        raw_name = (push_name or "").strip()
        nombre = raw_name if raw_name else f"Cliente {phone_digits[-4:]}"
        apellido = ""
        nombre = sanitize_text(nombre, limit=100) or nombre[:100]

        patient = Patient(
            id=generate_uuid(),
            tenant_id=tenant_id,
            nombre=nombre,
            apellido=apellido,
            telefono=phone_digits,
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        logger.info(f"[WhatsApp Agent] Paciente creado desde WhatsApp: {patient.id} ({phone_digits})")
        return patient

    def _save_message(
        self,
        db: Session,
        conversation_id: str,
        tenant_id: str,
        role: str,
        content: Optional[str],
        message_id: Optional[str] = None,
    ):
        msg = WhatsAppMessage(
            id=generate_uuid(),
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            message_id=message_id,
            role=role,
            content=sanitize_text(content),
        )
        db.add(msg)
        db.commit()

    def _build_history(self, db: Session, conversation_id: str, limit: int = 20) -> list:
        messages = db.query(WhatsAppMessage).filter(
            WhatsAppMessage.conversation_id == conversation_id,
            WhatsAppMessage.deleted_at == None,
        ).order_by(WhatsAppMessage.created_at.desc()).limit(limit).all()

        history = []
        for m in reversed(messages):
            if m.role not in ("user", "assistant") or not m.content:
                continue
            # Saltar mensajes assistant contaminados: fallbacks genéricos o
            # respuestas con prosa larga que contienen {} (razonamiento/IDs).
            # Esto evita que el modelo aprenda de respuestas previas rotas.
            if m.role == "assistant":
                c = m.content.strip()
                if c.startswith("Lo siento, tuve un problema"):
                    continue
                if c.startswith("¡Hola"):
                    continue
                # Si contiene { y es larga (>200 chars) es razonamiento/JSON roto
                if len(c) > 200 and ("{" in c or "}" in c):
                    continue
            history.append({"role": m.role, "content": m.content})
        return history

    # ============================================================
    # Guard previo a la IA (intenciones directas)
    # ============================================================

    def _handle_direct_intent(
        self,
        db: Session,
        tenant_id: str,
        text: str,
        conversation: WhatsAppConversation,
    ) -> Optional[str]:
        """
        Responde directamente (sin IA) a intenciones comunes y evitables:
        - Pregunta por la lista de servicios ("qué servicios ofrecen").
        - Pregunta por terapeutas/masajistas.
        - Respuesta CONFIRMO a un recordatorio (confirmar cita pending).
        Devuelve None si no aplica (y sigue la IA).
        """
        if not text:
            return None

        t = text.strip().lower()

        # 0a) Saludos: detecta "hola", "buenas", "buenos días/tardes/noches"
        if re.search(r"\b(hola|buenas?|buenos?\s*(d[ií]as|tardes|noches?)|saludos|qu[eé] tal)\b", t, re.I):
            return ("\U0001F44B ¡Hola! ¿En qué puedo ayudarte? "
                    "Puedes pedirme agendar una cita, consultar tus citas "
                    "o cancelar alguna.")

        # 0aa) Confirmación "sí/ok/dale" de cancelar TODAS tras pregunta del bot
        if re.search(
            r"\b(s[ií]|si\s+quiero|dale|ok|confirm[ao])\b", t
        ) and conversation.patient_id:
            last_bot = (
                db.query(WhatsAppMessage)
                .filter(
                    WhatsAppMessage.tenant_id == tenant_id,
                    WhatsAppMessage.conversation_id == conversation.id,
                    WhatsAppMessage.role == "assistant",
                    WhatsAppMessage.deleted_at == None,
                )
                .order_by(WhatsAppMessage.created_at.desc())
                .first()
            )
            if last_bot and last_bot.content:
                lb = last_bot.content.lower()
                if "cancelar todas" in lb or (
                    "cancelar" in lb and "todas" in lb
                ):
                    apts = json.loads(
                        self._tool_list_appointments(
                            db, tenant_id, str(conversation.patient_id), conversation
                        )
                    )
                    cancelled = 0
                    if isinstance(apts, list):
                        for ap in list(apts):
                            res = json.loads(
                                self._tool_cancel_appointment(
                                    db, tenant_id, ap.get("id")
                                )
                            )
                            if res.get("success"):
                                cancelled += 1
                    if cancelled:
                        return (
                            f"\u2705 Se cancelaron tus {cancelled} cita(s). "
                            "\U0001F495 ¿Necesitas algo más?"
                        )
                    return "No tenías citas pendientes para cancelar. \U0001F64F"

        # 0) Cancelar una cita: detecta "cancelar/cancela/anular/eliminar + fecha"
        if re.search(r"\b(cancel|cancela|cancelar|anul|elimin)\w*\b", t) and conversation.patient_id:
            import re as re_cancel
            appointments_list = json.loads(
                self._tool_list_appointments(db, tenant_id, str(conversation.patient_id), conversation)
            )
            if not isinstance(appointments_list, list) or not appointments_list:
                return "No tienes citas agendadas para cancelar. \U0001F60A"

            # --- Cancelar TODAS las citas ---
            if re_cancel.search(r"\btodas?\b", t):
                # Si el mensaje incluye confirmación (si/confirmo/ok) o el último
                # mensaje del bot pidió confirmar, procede a cancelar todo.
                user_confirms = bool(
                    re_cancel.search(r"\b(s[ií]|confirmo|confirmar|dale|ok)\b", t)
                )
                last_bot_asked = False
                last_bot = (
                    db.query(WhatsAppMessage)
                    .filter(
                        WhatsAppMessage.tenant_id == tenant_id,
                        WhatsAppMessage.conversation_id == conversation.id,
                        WhatsAppMessage.role == "assistant",
                        WhatsAppMessage.deleted_at == None,
                    )
                    .order_by(WhatsAppMessage.created_at.desc())
                    .first()
                )
                if last_bot and last_bot.content:
                    last_lower = last_bot.content.lower()
                    last_bot_asked = (
                        "cancelar" in last_lower and "todas" in last_lower
                        and "confirm" in last_lower
                    )

                if user_confirms or last_bot_asked:
                    cancelled = 0
                    for ap in list(appointments_list):
                        result = json.loads(
                            self._tool_cancel_appointment(db, tenant_id, ap.get("id"))
                        )
                        if result.get("success"):
                            cancelled += 1
                    if cancelled:
                        return (
                            f"\u2705 Se cancelaron TUS {cancelled} cita(s). "
                            "\U0001F495 ¿Necesitas algo más?"
                        )
                    return "No se pudo cancelar ninguna cita. \U0001F64F"

                # Pedir confirmación
                lines = [f"- {ap.get('service')} el {ap.get('date')} a las {ap.get('time')} ({ap.get('status')})" for ap in appointments_list[:5]]
                return (
                    "\u26A0\uFE0F Vas a cancelar TODAS tus citas:\\n" + "\\n".join(lines) +
                    "\\n\\n¿Confirmas? Responde SI para cancelar todas. \U0001F4AC"
                )

            # Encontrar la posición de "cancelar" en el texto y buscar fecha
            # DESPUÉS de esa palabra (no antes, donde podría estar "confirmar").
            cancel_pos = re_cancel.search(r"\b(cancel|cancela|cancelar|anul|elimin)\w*\b", t).start()
            text_after = t[cancel_pos:]

            cancel_id = None
            cancel_msg = None
            m = re_cancel.search(r"\b(\d{4}-\d{2}-\d{2})\b", text_after)
            if m:
                target = m.group(1)
                for ap in appointments_list:
                    if ap.get("date") == target:
                        cancel_id = ap.get("id")
                        cancel_msg = ap
                        break
            if not cancel_id:
                m = re_cancel.search(r"\bde[l]?\s+(\d{1,2})\b", text_after)
                if m:
                    day_num = int(m.group(1))
                    for ap in appointments_list:
                        try:
                            ap_date = datetime.strptime(ap.get("date", ""), "%Y-%m-%d")
                            if ap_date.day == day_num:
                                cancel_id = ap.get("id")
                                cancel_msg = ap
                                break
                        except Exception:
                            continue
            if cancel_id:
                result = json.loads(
                    self._tool_cancel_appointment(db, tenant_id, cancel_id)
                )
                if result.get("success"):
                    return f"\u274C Cita cancelada: {cancel_msg.get('service')} del {cancel_msg.get('date')} a las {cancel_msg.get('time')}."
                return "No se pudo cancelar la cita. Intenta de nuevo. \U0001F64F"
            # Mostrar lista de citas para elegir
            lines = [f"- {ap.get('service')} el {ap.get('date')} a las {ap.get('time')} ({ap.get('status')})" for ap in appointments_list[:5]]
            return ("Tienes estas citas:\n" + "\n".join(lines) +
                    "\n\n\u2705 ¿Cuál deseas cancelar? Indica la fecha (ej. 'cancelar la del 10').")

        # 0b) Confirmar una cita: detecta "confirmar/confirmo + fecha"
        if re.search(r"\b(confirmar|confirmo)\b", t) and conversation.patient_id:
            try:
                import re as re_cf
                apts = json.loads(self._tool_list_appointments(db, tenant_id, str(conversation.patient_id), conversation))
            except Exception:
                apts = []
            if isinstance(apts, list) and apts:
                pos = re_cf.search(r"\b(confirmar|confirmo)\b", t).start()
                txt_after = t[pos:]
                cid = None
                cmsg = None
                m = re_cf.search(r"\b(\d{4}-\d{2}-\d{2})\b", txt_after)
                if m:
                    for ap in apts:
                        if ap.get("date") == m.group(1):
                            cid, cmsg = ap.get("id"), ap
                            break
                if not cid:
                    m = re_cf.search(r"\bde[l]?\s+(\d{1,2})\b", txt_after)
                    if m:
                        dn = int(m.group(1))
                        for ap in apts:
                            try:
                                if datetime.strptime(ap.get("date",""), "%Y-%m-%d").day == dn:
                                    cid, cmsg = ap.get("id"), ap
                                    break
                            except:
                                continue
                if cid:
                    try:
                        from ..schemas.appointment import AppointmentUpdate
                        upd = appointment_service.update_appointment(db, tenant_id, cid, AppointmentUpdate(estado="confirmed"))
                        if upd:
                            return f"\u2705 Cita CONFIRMADA: {cmsg.get('service')} del {cmsg.get('date')} a las {cmsg.get('time')}."
                    except ValueError as exc:
                        return f"No se pudo confirmar: {str(exc)}"
                lines = [f"- {ap.get('service')} el {ap.get('date')} a las {ap.get('time')} ({ap.get('status')})" for ap in apts[:5]]
                return ("Tienes estas citas:\n" + "\n".join(lines) +
                        "\n\n\u2705 ¿Cuál deseas confirmar? Indica la fecha (ej. 'confirmar la del 10').")
            return "No tienes citas pendientes para confirmar. \U0001F60A"

        # 1) Lista de servicios
        if re.search(
            r"\b(qu[eé]|cuales|cual[es]?) (servicios|tratamientos|masajes)\b|"
            r"\b(servicios|tratamientos) (ofrece[ns]?|tiene[ns]?|hay)\b|"
            r"\bqu[eé] (ofrece[ns]?|tiene[ns]?|vende[ns]?|ofreces?)\b|"
            r"\bagendar\b(.*\b(cita|citas))?|"
            r"\buna\s+cita\b|\bquiero\s+una\s+cita\b|\bs[ií]\b",
            t,
        ):
            try:
                result = json.loads(self._tool_list_services(db, tenant_id) or "[]")
            except Exception:
                result = []
            if not result:
                return (
                    "Actualmente no tenemos servicios disponibles. "
                    "\U0001F495 Llámanos y con gusto te informamos."
                )
            lines = [
                f"\U0001F469\u200D\U0001F3A9 {s.get('name')} "
                f"({s.get('duration')} min) - ${int(s.get('price') or 0):,}".replace(",", ".")
                for s in result[:10]
            ]
            return (
                "Estos son los servicios que ofrecemos:\n" + "\n".join(lines) +
                "\n\n\u2705 ¿Cuál te gustaría reservar?"
            )

        # 2) Terapeutas / masajistas que atienden hoy
        if re.search(
            r"\b(qu[eé]) (terapeutas|masajistas|quien(es)?) (atiende[ns]?|hay|tiene[ns]?)\b|"
            r"\b(terapeutas|masajistas|quienes atienden)\b",
            t,
        ):
            from ..models.user import User as UserModel

            therapists = (
                db.query(UserModel)
                .filter(
                    UserModel.tenant_id == tenant_id,
                    UserModel.rol == "therapist",
                    UserModel.is_active == True,  # noqa: E712
                    UserModel.deleted_at == None,  # noqa: E711
                )
                .all()
            )
            if not therapists:
                return (
                    "Por el momento no hay terapeutas registrados. "
                    "\U0001F64F Llámanos y con gusto te atendemos."
                )
            names = [f"{usr.nombre} {usr.apellido}".strip() for usr in therapists]
            return (
                "Nuestros terapeutas son:\n" + "\n".join(f"- {n}" for n in names) +
                "\n\n\u2705 ¿Con quién te gustaría agendar?"
            )

        # 3) Confirmación tras RECORDATORIO (responde CONFIRMO / CONFIRMAR a una
        #    cita pending; "si" genérico lo gestiona la IA en un agendamiento).
        if re.search(
            r"\b(confirmo|confirmar|confirmada?)\b", t
        ) and conversation.patient_id:
            resp = json.loads(
                self._tool_confirm_pending_appointment(
                    db, tenant_id, str(conversation.patient_id), conversation
                )
            )
            if resp.get("success") is True:
                return resp.get("message")
            # Si no hay recordatorio pendiente (booking en curso), caer a IA.
            return None

        # 4) Consulta de las citas del cliente ("quiero saber si tengo citas",
        #    "mis citas", "próximas citas").
        #    NO si pregunta por disponibilidad ("citas disponibles", "horarios").
        if re.search(
            r"\b(disponibles?|horarios?|cupo|hay\s+citas)\b|\bagendar\b", t, re.I
        ):
            pass  # cae a guard #5 (fecha/hora) o IA
        elif re.search(
            r"\b(quiero saber|tengo|mis|consultar|cu[aá]ntas|cuales|pr[oó]ximas?|"
            r"ver|listar|agendadas|pendientes|m[uú]estrame|mostrar)\b|"
            r"\b(citas|turnos|reservas|agenda|horarios)\b",
            t,
        ) and conversation.patient_id:
            resp = json.loads(
                self._tool_list_appointments(
                    db, tenant_id, str(conversation.patient_id), conversation
                )
            )
            if isinstance(resp, list) and resp:
                lines = [
                    f"- {ap.get('service')} el {ap.get('date')} a las {ap.get('time')} "
                    f"({ap.get('status')})"
                    for ap in resp[:10]
                ]
                return (
                    f"Tienes {len(resp)} cita(s) agendada(s):\n"
                    + "\n".join(lines)
                    + "\n\n¿Quieres modificar o cancelar alguna?"
                )
            return (
                "No tienes citas agendadas por el momento. \U0001F60A "
                "¿Quieres agendar una?"
            )

        # 4b) Agregar servicio a cita existente: detecta "y [servicio]",
        #     "también [servicio]", "además [servicio]" cuando el usuario
        #     ya tiene una cita pending/confirmed reciente.
        if conversation.patient_id and re.search(
            r"\b(y\s+(el|la|un|una)|tambi[eé]n\s+(el|la|un|una)|adem[aá]s\s+(del?|de\s+la)|despu[eé]s\s+(de|del?))\s+\w+",
            t, re.I
        ):
            apt = _last_appointment_for_patient(db, tenant_id, conversation.patient_id)
            if apt:
                svc = _find_service_from_text(db, tenant_id, t)
                if svc:
                    result = json.loads(
                        _tool_add_service_to_appointment(
                            db, tenant_id, str(apt.id), t
                        )
                    )
                    if result.get("success"):
                        extra = _suggest_multi_service(db, tenant_id, apt)
                        return result["message"] + extra
                    return result["message"]
                # Si hay cita pero no se encontró el servicio en el texto,
                # preguntar cuál quiere agregar
                from ..models.service import Service as ServiceModel
                services = (
                    db.query(ServiceModel)
                    .filter(
                        ServiceModel.tenant_id == tenant_id,
                        ServiceModel.is_active == True,
                        ServiceModel.deleted_at == None,
                    )
                    .all()
                )
                if services:
                    lines = [
                        f"\U0001F469\u200D\U0001F3A9 {s.nombre} "
                        f"({s.duracion} min) - ${int(s.precio or 0):,}".replace(",", ".")
                        for s in services[:10]
                    ]
                    return ("He visto que ya tienes una cita. ¿Qué servicio quieres agregarle?\n" + "\n".join(lines) +
                            "\n\nDime el nombre del servicio.")

        # 5) Detectar fecha/hora y agendar servicio (flujo completo sin IA).
        #    VA ANTES que #6 para que "Pa mañana a las 3 de la tarde" no sea
        #    interceptado por el regex de servicio (que contiene "la" y "de").
        booking_time = _parse_booking_time(t, _tenant_now(db, tenant_id))
        if booking_time and (booking_time[1] > 0 or booking_time[2] > 0):
            cita_date, hour, minute = booking_time
            time_str = f"{hour:02d}:{minute:02d}"

            # Buscar servicio mencionado en el texto o en el historial
            matched_svc = _find_service_from_text(db, tenant_id, t)
            if not matched_svc and conversation.id:
                matched_svc = _find_service_in_history(db, tenant_id, conversation.id)
            if not matched_svc:
                return ("¿Para qué servicio te gustaría agendar la cita? "
                        "Dime el nombre y lo busco. \U0001F60A")

            avail_result = self._tool_check_availability(
                db, tenant_id, cita_date, str(matched_svc.id)
            )
            try:
                slots = json.loads(avail_result)
            except Exception:
                slots = []

            if isinstance(slots, dict) and "error" in slots:
                return f"Lo siento, no pude verificar disponibilidad: {slots['error']}"

            matching_slot = None
            if isinstance(slots, list):
                for s in slots:
                    if s.get("time") == time_str:
                        matching_slot = s
                        break

            if matching_slot:
                # Buscar servicio en el texto o historial
                matched_svc = _find_service_from_text(db, tenant_id, t)
                if not matched_svc and conversation.id:
                    matched_svc = _find_service_in_history(db, tenant_id, conversation.id)
                patient_id = conversation.patient_id
                if patient_id and matched_svc and matching_slot.get("therapist_id"):
                    try:
                        from ..schemas.appointment import AppointmentCreate
                        cita_dt = datetime.strptime(
                            f"{cita_date} {time_str}", "%Y-%m-%d %H:%M"
                        )
                        data = AppointmentCreate(
                            patient_id=patient_id,
                            therapist_id=matching_slot["therapist_id"],
                            service_id=str(matched_svc.id),
                            date_time=cita_dt,
                            estado="pending",
                        )
                        appointment = appointment_service.create_appointment(db, tenant_id, data)
                        # Si el mensaje original menciona múltiples servicios,
                        # agregar los adicionales como items a la misma cita
                        from ..models.service import Service as ServiceModel
                        all_matched = _find_all_services_in_text(db, tenant_id, t)
                        second_svc = None
                        for svc in all_matched:
                            if str(svc.id) != str(matched_svc.id):
                                second_svc = svc
                                break
                        if second_svc:
                            try:
                                from decimal import Decimal
                                appointment_service.add_item(
                                    db, tenant_id, appointment,
                                    service_id=str(second_svc.id),
                                    cantidad=1,
                                    descuento=Decimal("0.00"),
                                )
                                extra = _suggest_multi_service(db, tenant_id, appointment)
                                return (
                                    f"\u2705 Cita CONFIRMADA: {appointment.service or matched_svc.nombre} "
                                    f"el {_format_date(appointment.date_time)} a las "
                                    f"{_format_time(appointment.date_time)} con "
                                    f"{matching_slot['therapist']}.\n\n"
                                    f"✅ Además agregué {second_svc.nombre} a tu cita.{extra}"
                                )
                            except ValueError:
                                pass
                        extra = _suggest_multi_service(db, tenant_id, appointment)
                        return (
                            f"\u2705 Cita CONFIRMADA: {appointment.service or matched_svc.nombre} "
                            f"el {_format_date(appointment.date_time)} a las "
                            f"{_format_time(appointment.date_time)} con "
                            f"{matching_slot['therapist']}.\n\n"
                            f"\U0001F495 ¡Te esperamos!{extra}"
                        )
                    except ValueError as exc:
                        return f"Lo siento, no se pudo agendar: {str(exc)}"
                return (f"El horario de las {time_str} del {cita_date} est\u00e1 disponible con "
                        f"{matching_slot['therapist']}. \u2705 "
                        "Responde CONFIRMAR para agendar tu cita.")
            elif isinstance(slots, list) and slots:
                times_list = "\n".join(f"- {s['time']} ({s['therapist']})" for s in slots[:8])
                return (f"La hora {time_str} no est\u00e1 disponible. "
                        f"Horarios libres para {cita_date}:\n{times_list}"
                        "\n\n\u2705 ¿Cuál te gustaría?")
            else:
                return (f"Lo siento, no hay disponibilidad para {cita_date}. "
                        "¿Quieres otro día?")

        # 5b) Día válido pero sin hora -> preguntar hora
        if booking_time and booking_time[1] == 0 and booking_time[2] == 0:
            cita_date = booking_time[0]
            # Nombre legible del día
            from datetime import datetime as dt_mod
            try:
                day_name = dt_mod.strptime(cita_date, "%Y-%m-%d").strftime("%A")
            except Exception:
                day_name = cita_date
            day_map = {"Monday":"lunes","Tuesday":"martes","Wednesday":"miércoles",
                       "Thursday":"jueves","Friday":"viernes","Saturday":"sábado",
                       "Sunday":"domingo"}
            day_name_es = day_map.get(day_name, day_name)
            return (f"¿A qué hora te gustaría tu cita el {day_name_es}? "
                    "\U0001F552")

        # 6) Agendar un servicio específico: detecta "quiero una cita para [servicio]"
        #    "si/sí para [servicio]" o simplemente "limpieza".
        #    NO debe matchear si el texto tiene intención de fecha/hora.
        has_time_intent = bool(
            booking_time  # ya lo capturó guard #5
            or _parse_only_time(t)  # tiene hora explícita
            or re.search(
                r"\b(mañana|manana|hoy|lunes|martes|mi[eé]rcoles|miercoles|"
                r"jueves|viernes|s[aá]bado|sabado|domingo)\b", t, re.I
            )
        )
        match_g6 = re.search(
            r"\b(una|la|esa|ese|el|quiero|reservar|agendar|cita|s[ií])\b.*\b(para|de)\b", t
        )
        if not match_g6 and not has_time_intent:
            # Fallback: solo si el texto ACTUAL contiene un servicio conocido
            if _find_service_from_text(db, tenant_id, t):
                match_g6 = True
        if match_g6 and not booking_time:
            matched = _find_service_from_text(db, tenant_id, t)
            if not matched and conversation.id:
                matched = _find_service_in_history(db, tenant_id, conversation.id)
            if matched:
                return (f"\u2705 Excelente, has elegido {matched.nombre} "
                        f"({matched.duracion} min - ${int(matched.precio or 0)}). "
                        "\U0001F4C5 ¿Qué día y hora te gustaría tu cita?")

        # 7) Elegir un horario de la lista mostrada por el bot (respuesta tipo
        #    "a las 15:00", "15:00", "las 3 de la tarde" SIN repetir el día).
        only_time = _parse_only_time(t)
        if only_time and conversation.id:
            hour_only, minute_only = only_time
            time_only_str = f"{hour_only:02d}:{minute_only:02d}"
            now_local = _tenant_now(db, tenant_id)

            # Recuperar el servicio del historial (guard #5 lo mostró antes)
            matched_svc = _find_service_from_text(db, tenant_id, t)
            if not matched_svc:
                matched_svc = _find_service_in_history(db, tenant_id, conversation.id)
            if not matched_svc:
                # El usuario eligió hora pero no repitió el servicio.
                # Mejor pasar a la IA a que intente interpretar (puede usar
                # el contexto de la conversación).
                return None

            # Obtener la fecha del último mensaje del usuario (el mensaje actual
            # ya se guardó en BD antes de entrar al guard, por eso offset(1)).
            cita_date = None
            last_user = (
                    db.query(WhatsAppMessage)
                    .filter(
                        WhatsAppMessage.tenant_id == tenant_id,
                        WhatsAppMessage.conversation_id == conversation.id,
                        WhatsAppMessage.role == "user",
                        WhatsAppMessage.deleted_at == None,
                    )
                    .order_by(WhatsAppMessage.created_at.desc())
                    .offset(1)
                    .first()
                )
            if last_user and last_user.content:
                parsed = _parse_booking_time(last_user.content, now_local)
                logger.info(
                    f"[WhatsApp Agent] Guard #7 date fallback: "
                    f"last_user='{last_user.content[:80]}' "
                    f"now_local={now_local.strftime('%Y-%m-%d %H:%M')} "
                    f"parsed={parsed}"
                )
                if parsed:
                    cita_date = parsed[0]
            if not cita_date:
                cita_date = now_local.strftime("%Y-%m-%d")
                logger.warning(
                    f"[WhatsApp Agent] Guard #7: usando fecha fallback "
                    f"cita_date={cita_date} (sin día en historial)"
                )

            # Verificar disponibilidad en esa fecha/servicio
            avail_result = self._tool_check_availability(
                db, tenant_id, cita_date, str(matched_svc.id)
            )
            try:
                slots = json.loads(avail_result)
            except Exception:
                slots = []

            if isinstance(slots, dict) and "error" in slots:
                return f"Lo siento, no pude verificar disponibilidad: {slots['error']}"

            matching_slot = None
            if isinstance(slots, list):
                for s in slots:
                    if s.get("time") == time_only_str:
                        matching_slot = s
                        break

            if not matching_slot:
                if isinstance(slots, list) and slots:
                    times_list = "\n".join(f"- {s['time']} ({s['therapist']})" for s in slots[:8])
                    return (f"La hora {time_only_str} no está disponible. "
                            f"Horarios libres para {cita_date}:\n{times_list}"
                            "\n\n\u2705 ¿Cuál te gustaría?")
                return (f"Lo siento, no hay disponibilidad para {cita_date}. "
                        "¿Quieres otro día?")

            # El cliente ya eligió: crear la cita CONFIRMADA directamente
            from ..schemas.appointment import AppointmentCreate

            patient_id = conversation.patient_id
            if not patient_id:
                return ("Lo siento, no pude identificar tu cuenta. "
                        "Escribe tu nombre completo para continuar. \U0001F60A")

            # El cliente ya eligió la hora: crear la cita CONFIRMADA directamente
            try:
                from ..schemas.appointment import AppointmentCreate
                cita_dt = datetime.strptime(
                    f"{cita_date} {time_only_str}", "%Y-%m-%d %H:%M"
                )
                data = AppointmentCreate(
                    patient_id=patient_id,
                    therapist_id=matching_slot["therapist_id"],
                    service_id=str(matched_svc.id),
                    date_time=cita_dt,
                    estado="pending",
                )
                appointment = appointment_service.create_appointment(db, tenant_id, data)
                extra = _suggest_multi_service(db, tenant_id, appointment)
                return (
                    f"\u2705 Cita CONFIRMADA: {appointment.service or matched_svc.nombre} "
                    f"el {_format_date(appointment.date_time)} a las "
                    f"{_format_time(appointment.date_time)} con "
                    f"{matching_slot['therapist']}.\n\n"
                    f"\U0001F495 ¡Te esperamos!{extra}"
                )
            except ValueError as exc:
                return f"Lo siento, no se pudo agendar: {str(exc)}"

        # 8) Confirmar booking tras ver disponibilidad: el usuario responde
        #    "confirmar/si/si/ok" y el último mensaje del bot contenía un slot
        #    disponible. Revalida disponibilidad y crea la cita en BD.
        if re.search(r"\b(confirmar|confirmo|s[ií]|ok|dale|sim|sip)\b", t) and conversation.id:
            logger.info("[WhatsApp Agent] Guard #8: intentando confirmar booking")
            cita_details = _extract_booking_from_history(db, tenant_id, conversation.id)
            if not cita_details:
                logger.error(
                    "[WhatsApp Agent] Guard #8: _extract_booking_from_history retornó None. "
                    f"tenant={tenant_id}, conv={conversation.id}"
                )
            if cita_details:
                cita_date, cita_time, therapist_name, therapist_id, svc = cita_details
                time_str = f"{cita_time // 60}:{cita_time % 60:02d}"
                patient_id = conversation.patient_id
                if patient_id and svc and therapist_id:
                    # Revalidar disponibilidad antes de agendar
                    avail_check = self._tool_check_availability(
                        db, tenant_id, cita_date, str(svc.id)
                    )
                    try:
                        current_slots = json.loads(avail_check)
                    except Exception:
                        current_slots = []
                    still_free = False
                    if isinstance(current_slots, list):
                        for slot in current_slots:
                            if (slot.get("time") == time_str
                                    and slot.get("therapist_id") == therapist_id):
                                still_free = True
                                break

                    if not still_free:
                        return ("Lo siento, el horario ya no está disponible. "
                                "\U0001F64F ¿Quieres consultar otra hora o día?")

                    try:
                        from ..schemas.appointment import AppointmentCreate
                        cita_dt = datetime.strptime(
                            f"{cita_date} {time_str}", "%Y-%m-%d %H:%M"
                        )
                        data = AppointmentCreate(
                            patient_id=patient_id,
                            therapist_id=therapist_id,
                            service_id=str(svc.id),
                            date_time=cita_dt,
                            estado="pending",
                        )
                        appointment = appointment_service.create_appointment(db, tenant_id, data)
                        extra = _suggest_multi_service(db, tenant_id, appointment)
                        return (
                            f"\u2705 Cita CONFIRMADA: {appointment.service or svc.nombre} "
                            f"el {_format_date(appointment.date_time)} a las "
                            f"{_format_time(appointment.date_time)} con "
                            f"{therapist_name}.\n\n"
f"\U0001F495 ¡Te esperamos!{extra}"
                        )
                    except ValueError as exc:
                        return f"Lo siento, no se pudo agendar: {str(exc)}"

        # 9) Multi-servicio: agregar otro servicio a la cita recién creada
        if conversation.patient_id and re.search(
            r"\b(otro\s+servicio|agregar|agrega|a[nñ]ade|m[aá]s\s+servicios|tambi[eé]n\s+quiero|adem[aá]s|otra\s+cosa|despu[eé]s)\b",
            t, re.I
        ):
            apt = _last_appointment_for_patient(db, tenant_id, conversation.patient_id)
            if not apt:
                return None  # no hay cita, deja que la IA lo maneje
            # Si el texto nombra un servicio específico, agregarlo
            svc = _find_service_from_text(db, tenant_id, t)
            if svc:
                result = json.loads(
                    _tool_add_service_to_appointment(
                        db, tenant_id, str(apt.id), t
                    )
                )
                if result.get("success"):
                    extra = _suggest_multi_service(db, tenant_id, apt)
                    return result["message"] + extra
                return result["message"]
            # Si el usuario solo dijo "sí" sin servicio, mostrar lista
            from ..models.service import Service as ServiceModel
            services = (
                db.query(ServiceModel)
                .filter(
                    ServiceModel.tenant_id == tenant_id,
                    ServiceModel.is_active == True,
                    ServiceModel.deleted_at == None,
                )
                .all()
            )
            if services:
                lines = [
                    f"\U0001F469\u200D\U0001F3A9 {s.nombre} "
                    f"({s.duracion} min) - ${int(s.precio or 0):,}".replace(",", ".")
                    for s in services[:10]
                ]
                return ("¿Qué servicio te gustaría agregar a tu cita?\n" + "\n".join(lines) +
                        "\n\nDime el nombre del servicio.")
            return None

        # 10) Cambiar servicio de una cita existente
        if conversation.patient_id and re.search(
            r"\b(cambiar|cambio|remplazar|cambia)\w*\s+.*\b(servicio|tratamiento|masaje)\b",
            t, re.I
        ):
            apts_list = json.loads(
                self._tool_list_appointments(db, tenant_id, str(conversation.patient_id), conversation)
            )
            if not isinstance(apts_list, list) or not apts_list:
                return "No tienes citas agendadas. \U0001F60A"
            # Buscar una fecha/hora mencionada
            import re as re_ch
            m = re_ch.search(r"\b(\d{4}-\d{2}-\d{2})\b", t)
            target_id = None
            target_msg = None
            if m:
                for ap in apts_list:
                    if ap.get("date") == m.group(1):
                        target_id = ap.get("id")
                        target_msg = ap
                        break
            if not target_id:
                m = re_ch.search(r"\bde[l]?\s+(\d{1,2})\b", t)
                if m:
                    dn = int(m.group(1))
                    for ap in apts_list:
                        try:
                            if datetime.strptime(ap.get("date",""), "%Y-%m-%d").day == dn:
                                target_id = ap.get("id")
                                target_msg = ap
                                break
                        except:
                            continue
            if not target_id:
                # Solo la primera pending/confirmed
                for ap in apts_list:
                    if ap.get("status") in ("pending", "confirmed"):
                        target_id = ap.get("id")
                        target_msg = ap
                        break
            if not target_id:
                return "No encontré esa cita. \U0001F60A"

            # Ver si el texto ya menciona un nuevo servicio
            svc = _find_service_from_text(db, tenant_id, t)
            if svc:
                from ..schemas.appointment import AppointmentUpdate
                try:
                    updated = appointment_service.update_appointment(
                        db, tenant_id, target_id,
                        AppointmentUpdate(service_id=str(svc.id))
                    )
                    if updated:
                        return (f"\u2705 Servicio cambiado a {svc.nombre} para tu cita del "
                                f"{target_msg['date']} a las {target_msg['time']}.")
                    return "No se pudo cambiar el servicio."
                except ValueError as exc:
                    return f"Error: {str(exc)}"
            # Mostrar la cita y preguntar nuevo servicio
            lines_list = [f"- {ap.get('service')} el {ap.get('date')} a las {ap.get('time')} ({ap.get('status')})" for ap in apts_list[:5]]
            return ("Tienes estas citas:\n" + "\n".join(lines_list) +
                    "\n\n\u2705 ¿A cuál quieres cambiarle el servicio? Indica la fecha.")

        return None

    # ============================================================
    # Loop IA con herramientas (protocolo JSON)
    # ============================================================

    async def _call_ai_with_tools(
        self,
        db: Session,
        tenant_id: str,
        system_prompt: str,
        history: list,
        conversation: WhatsAppConversation,
    ) -> Optional[str]:
        messages = [{"role": "system", "content": system_prompt}, *history]

        correction_count = 0
        MAX_CORRECTIONS = 3

        for attempt in range(5 + MAX_CORRECTIONS):
            try:
                # _call_freellmapi es síncrono (httpx) y bloquea el event loop:
                # se ejecuta en un hilo para no bloquear el procesamiento de
                # otros webhooks de WhatsApp.
                ai_response = await asyncio.to_thread(
                    _call_freellmapi, messages, 500, 0.2
                )
            except ValueError as exc:
                logger.warning(f"[WhatsApp Agent] FreeLLMAPI error: {exc}")
                return FALLBACK_REPLY

            if not ai_response or not ai_response.strip():
                logger.warning("[WhatsApp Agent] Respuesta vacía de FreeLLMAPI")
                return FALLBACK_REPLY

            logger.info(
                f"[WhatsApp Agent] Respuesta IA (raw): {ai_response[:200]}"
            )

            try:
                decision = self._parse_decision(ai_response)
            except Exception as exc:
                logger.warning(f"[WhatsApp Agent] _parse_decision error: {exc}")
                # _parse_decision falló: reintentar con corrección, nunca enviar crudo.
                if correction_count < MAX_CORRECTIONS:
                    correction_count += 1
                    messages.append({"role": "assistant", "content": ai_response})
                    messages.append({"role": "system", "content": _JSON_CORRECTION})
                    continue
                return FALLBACK_REPLY

            # Toda respuesta que no sea un JSON válido con "reply" o "tool" se
            # considera inválida y se reintenta con corrección. NUNCA se envía
            # texto crudo del modelo al cliente ("saludo natural" via guard).
            if not isinstance(decision, dict):
                if correction_count < MAX_CORRECTIONS:
                    correction_count += 1
                    messages.append({"role": "assistant", "content": ai_response})
                    messages.append({"role": "system", "content": _JSON_CORRECTION})
                    continue
                return FALLBACK_REPLY

            if "reply" in decision:
                raw_reply = decision["reply"]
                if isinstance(raw_reply, str) and raw_reply.strip():
                    return raw_reply.strip()[:4000]
                return FALLBACK_REPLY

            # Tool call
            tool_name = decision.get("tool", "")
            args = decision.get("args") if isinstance(decision.get("args"), dict) else {}
            if not isinstance(tool_name, str) or not tool_name:
                logger.warning(f"[WhatsApp Agent] Respuesta sin tool válida: {ai_response[:200]}")
                if correction_count < MAX_CORRECTIONS:
                    correction_count += 1
                    messages.append({"role": "assistant", "content": ai_response})
                    messages.append({"role": "system", "content": _JSON_CORRECTION})
                    continue
                return FALLBACK_REPLY

            logger.info(
                f"[WhatsApp Agent] Herramienta {tool_name} tenant={tenant_id} args={json.dumps(args, ensure_ascii=False)[:200]}"
            )
            tool_result = self._dispatch_tool(db, tenant_id, tool_name, args, conversation)

            messages.append({"role": "assistant", "content": ai_response})
            messages.append(
                {"role": "system", "content": f"Resultado de la herramienta {tool_name}: {tool_result}"}
            )

        logger.info(f"[WhatsApp Agent] Intento de herramienta agotado ({5+correction_count} intentos), fallback enviado")
        return FALLBACK_REPLY

    def _parse_decision(self, ai_response: str) -> Optional[dict]:
        """
        Extrae el ÚLTIMO bloque JSON {...} balanceado de la respuesta.
        Tolerante a prosa/markdown alrededor. Devuelve dict o None.
        """
        text = ai_response.strip()
        if not text:
            return None

        # Buscar desde el final el último '{' y verificar que su bloque esté
        # balanceado hasta el '}' más próximo que lo cierre.
        start = text.rfind("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    try:
                        data = json.loads(candidate)
                    except json.JSONDecodeError:
                        logger.warning(f"[WhatsApp Agent] JSON inválido en respuesta: {candidate[:200]}")
                        return None
                    if isinstance(data, dict):
                        return data
                    return None
        # Bloque sin cerrar (truncado)
        logger.warning(f"[WhatsApp Agent] JSON truncado (sin cierre) en respuesta: {text[start:start+200]}")
        return None

    # ============================================================
    # Dispatch de herramientas
    # ============================================================

    def _dispatch_tool(
        self,
        db: Session,
        tenant_id: str,
        tool_name: str,
        args: dict,
        conversation: WhatsAppConversation,
    ) -> str:
        try:
            if tool_name == "find_patient":
                phone_arg = args.get("phone") or conversation.phone or ""
                return self._tool_find_patient(db, tenant_id, phone_arg)
            elif tool_name == "list_services":
                return self._tool_list_services(db, tenant_id)
            elif tool_name == "check_availability":
                return self._tool_check_availability(
                    db, tenant_id, args.get("date", ""), args.get("service_id", "")
                )
            elif tool_name == "book_appointment":
                return self._tool_book_appointment(db, tenant_id, args, conversation)
            elif tool_name == "modify_appointment":
                return self._tool_modify_appointment(db, tenant_id, args)
            elif tool_name == "cancel_appointment":
                return self._tool_cancel_appointment(db, tenant_id, args.get("appointment_id", ""))
            elif tool_name == "list_my_appointments":
                return self._tool_list_appointments(
                    db, tenant_id, args.get("patient_id", ""), conversation
                )
            elif tool_name == "confirm_pending_appointment":
                return self._tool_confirm_pending_appointment(
                    db, tenant_id, args.get("patient_id", ""), conversation
                )
        except Exception as exc:
            logger.error(f"[WhatsApp Agent] Error en herramienta {tool_name}: {exc}")
            return json.dumps({"error": f"Error ejecutando {tool_name}: {str(exc)}"}, ensure_ascii=False)

        return json.dumps({"error": f"Herramienta desconocida: {tool_name}"})

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        digits = "".join(c for c in phone if c.isdigit())
        if digits.startswith("57") and len(digits) > 12:
            digits = digits[2:]
        elif digits.startswith("57") and len(digits) > 10:
            digits = digits[2:]
        return digits

    # ----------------------------------------------------------
    # find_patient
    # ----------------------------------------------------------
    def _tool_find_patient(self, db: Session, tenant_id: str, phone: str) -> str:
        phone_digits = self._normalize_phone(phone or "")
        if not phone_digits:
            return json.dumps({"error": "Número de teléfono inválido"})

        patient = db.query(Patient).filter(
            Patient.tenant_id == tenant_id,
            Patient.telefono == phone_digits,
            Patient.deleted_at == None,
        ).first()

        if patient:
            return json.dumps({
                "patient_id": str(patient.id),
                "patient_name": patient.nombre_completo,
                "found": True,
            }, ensure_ascii=False)

        patient = self._ensure_patient(db, tenant_id, phone_digits)
        return json.dumps({
            "patient_id": str(patient.id) if patient else None,
            "patient_name": patient.nombre_completo if patient else f"Cliente {phone_digits[-4:]}",
            "found": False,
        }, ensure_ascii=False)

    # ----------------------------------------------------------
    # list_services
    # ----------------------------------------------------------
    def _tool_list_services(self, db: Session, tenant_id: str) -> str:
        services = db.query(Service).filter(
            Service.tenant_id == tenant_id,
            Service.is_active == True,
            Service.deleted_at == None,
        ).all()
        result = [
            {
                "id": str(srv.id),
                "name": srv.nombre,
                "duration": srv.duracion,
                "price": float(srv.precio) if srv.precio else 0,
            }
            for srv in services
        ]
        return json.dumps(result, ensure_ascii=False)

    # ----------------------------------------------------------
    # check_availability (respeta duración y horario 08:00-18:00)
    # ----------------------------------------------------------
    def _tool_check_availability(
        self, db: Session, tenant_id: str, date: str, service_id: str
    ) -> str:
        try:
            day = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return json.dumps({"error": "Formato de fecha inválido. Usa YYYY-MM-DD."})

        service = db.query(Service).filter(
            Service.id == service_id,
            Service.tenant_id == tenant_id,
            Service.deleted_at == None,
        ).first()
        if not service:
            return json.dumps({"error": "Servicio no encontrado"})

        duration_min = service.duracion or 60

        therapists = db.query(User).filter(
            User.tenant_id == tenant_id,
            User.rol == "therapist",
            User.is_active == True,
            User.deleted_at == None,
        ).all()

        if not therapists:
            return json.dumps({"error": "No hay terapeutas disponibles"})

        available = []

        # Horario de atención del tenant (default 08:00 - 18:00)
        from ..models.tenant import Tenant as TenantModel
        tenant = db.query(TenantModel).filter(TenantModel.id == tenant_id).first()
        config = (tenant.configuracion or {}) if tenant else {}
        if not isinstance(config, dict):
            config = {}
        try:
            apt_hora_ini = int(config.get("horario_apertura", "08:00").split(":")[0])
        except Exception:
            apt_hora_ini = 8
        try:
            apt_hora_fin = int(config.get("horario_cierre", "18:00").split(":")[0])
        except Exception:
            apt_hora_fin = 18
        if apt_hora_fin <= apt_hora_ini:
            apt_hora_fin = apt_hora_ini + 1

        # Ahora en la zona horaria del tenant (los slots se guardan naive en la
        # hora local del negocio, por eso no se compara contra UTC).
        now_local = _tenant_now(db, tenant_id)

        # Slots cada hora (o según duración) dentro del horario de atención,
        # respetando la duración para no sobrepasar el cierre.
        for hour in range(apt_hora_ini, apt_hora_fin):
            slot = day.replace(hour=hour, minute=0, second=0, microsecond=0)
            if slot <= now_local:
                continue
            slot_end = slot + timedelta(minutes=duration_min)
            if slot_end.hour > apt_hora_fin or (slot_end.hour == apt_hora_fin and slot_end.minute > 0):
                continue

            for therapist in therapists:
                conflict = db.query(Appointment.id).filter(
                    Appointment.tenant_id == tenant_id,
                    Appointment.therapist_id == therapist.id,
                    Appointment.date_time == slot,
                    Appointment.estado.notin_(["cancelled"]),
                    Appointment.deleted_at == None,
                ).first()
                if not conflict:
                    available.append({
                        "time": slot.strftime("%H:%M"),
                        "therapist": f"{therapist.nombre} {therapist.apellido}".strip(),
                        "therapist_id": str(therapist.id),
                    })
                    break

        return json.dumps(available[:12], ensure_ascii=False)

    # ----------------------------------------------------------
    # book_appointment
    # ----------------------------------------------------------
    def _tool_book_appointment(
        self, db: Session, tenant_id: str, args: dict, conversation: WhatsAppConversation
    ) -> str:
        from datetime import datetime as dt_mod

        from ..schemas.appointment import AppointmentCreate

        patient_id = args.get("patient_id") or conversation.patient_id
        therapist_id = args.get("therapist_id")
        service_id = args.get("service_id")
        date_time_raw = args.get("date_time")

        if not patient_id:
            return json.dumps({"success": False, "message": "Paciente no identificado"})
        if not therapist_id or not service_id or not date_time_raw:
            return json.dumps({
                "success": False,
                "message": "Faltan datos para agendar (therapist_id, service_id, date_time)",
            })

        estado_arg = (args.get("estado") or "pending").lower()
        if estado_arg not in ESTADOS_CITA:
            estado_arg = "pending"

        try:
            cita_dt = dt_mod.strptime(date_time_raw, "%Y-%m-%d %H:%M")
            if cita_dt <= _tenant_now(db, tenant_id):
                return json.dumps({
                    "success": False,
                    "message": "No se puede agendar en una fecha u hora pasada",
                })
            data = AppointmentCreate(
                patient_id=patient_id,
                therapist_id=therapist_id,
                service_id=service_id,
                date_time=cita_dt,
                estado=estado_arg,
            )
            appointment = appointment_service.create_appointment(db, tenant_id, data)
            estado_label = "CONFIRMADA" if appointment.estado == "confirmed" else "programada"
            suggestion = _suggest_multi_service(db, tenant_id, appointment)
            return json.dumps({
                "success": True,
                "appointment_id": str(appointment.id),
                "message": (
                    f"Cita {estado_label}: {appointment.service or 'Servicio'} el "
                    f"{_format_date(appointment.date_time)} a las "
                    f"{_format_time(appointment.date_time)} con "
                    f"{appointment.therapist or 'terapeuta'}"
                ),
                "suggestion": suggestion,
            }, ensure_ascii=False)
        except ValueError as exc:
            return json.dumps({"success": False, "message": str(exc)}, ensure_ascii=False)

    # ----------------------------------------------------------
    # modify_appointment
    # ----------------------------------------------------------
    def _tool_modify_appointment(self, db: Session, tenant_id: str, args: dict) -> str:
        from ..schemas.appointment import AppointmentUpdate

        appointment_id = args.get("appointment_id")
        if not appointment_id:
            return json.dumps({"error": "ID de cita requerido"})

        update_data = {}
        if args.get("date_time"):
            update_data["date_time"] = args["date_time"]
        if args.get("service_id"):
            update_data["service_id"] = args["service_id"]
        if args.get("therapist_id"):
            update_data["therapist_id"] = args["therapist_id"]

        if not update_data:
            return json.dumps({"error": "No hay cambios que aplicar"})

        try:
            data = AppointmentUpdate(**update_data)
            appointment = appointment_service.update_appointment(db, tenant_id, appointment_id, data)
            if appointment:
                return json.dumps({
                    "success": True,
                    "message": (
                        f"Cita actualizada: {appointment.service or 'Servicio'} el "
                        f"{_format_date(appointment.date_time)} a las "
                        f"{_format_time(appointment.date_time)}"
                    ),
                }, ensure_ascii=False)
            return json.dumps({"success": False, "message": "Cita no encontrada"})
        except ValueError as exc:
            return json.dumps({"success": False, "message": str(exc)}, ensure_ascii=False)

    # ----------------------------------------------------------
    # cancel_appointment
    # ----------------------------------------------------------
    def _tool_cancel_appointment(self, db: Session, tenant_id: str, appointment_id: str) -> str:
        if not appointment_id:
            return json.dumps({"error": "ID de cita requerido"})

        appointment = appointment_service.cancel_appointment(db, tenant_id, appointment_id)
        if appointment:
            return json.dumps({
                "success": True,
                "message": (
                    f"Cita del {_format_date(appointment.date_time)} a las "
                    f"{_format_time(appointment.date_time)} cancelada exitosamente"
                ),
            }, ensure_ascii=False)
        return json.dumps({"success": False, "message": "Cita no encontrada"})

    # ----------------------------------------------------------
    # list_my_appointments
    # ----------------------------------------------------------
    def _tool_list_appointments(
        self,
        db: Session,
        tenant_id: str,
        patient_id: Optional[str],
        conversation: WhatsAppConversation,
    ) -> str:
        pid = patient_id or conversation.patient_id
        if not pid:
            return json.dumps({"error": "Paciente no identificado"})

        appointments = db.query(Appointment).filter(
            Appointment.tenant_id == tenant_id,
            Appointment.patient_id == pid,
            Appointment.deleted_at == None,
            Appointment.estado.in_(["pending", "confirmed"]),
        ).order_by(Appointment.date_time.asc()).limit(10).all()

        result = [
            {
                "id": str(a.id),
                "date": a.fecha or "",
                "time": a.hora_inicio or "",
                "service": a.service or "",
                "therapist": a.therapist or "",
                "status": a.estado,
            }
            for a in appointments
        ]
        return json.dumps(result, ensure_ascii=False)

    # ----------------------------------------------------------
    # confirm_pending_appointment
    # ----------------------------------------------------------
    def _tool_confirm_pending_appointment(
        self,
        db: Session,
        tenant_id: str,
        patient_id: Optional[str],
        conversation: WhatsAppConversation,
    ) -> str:
        pid = patient_id or conversation.patient_id
        if not pid:
            return json.dumps({
                "success": False,
                "message": "Paciente no identificado",
            }, ensure_ascii=False)

        from ..schemas.appointment import AppointmentUpdate

        # SOLO se confirma una cita pending que tenga un recordatorio enviado
        # (message_id = "reminder:{id}"): es decir, cuando el cliente responde
        # CONFIRMO a un recordatorio 24h antes. Nunca confirma una cita recién
        # agendada (eso se hace con estado="pending" en book_appointment).
        appointment = (
            db.query(Appointment)
            .filter(
                Appointment.tenant_id == tenant_id,
                Appointment.patient_id == pid,
                Appointment.deleted_at == None,
                Appointment.estado == "pending",
            )
            .order_by(Appointment.date_time.asc())
            .first()
        )
        if not appointment:
            return json.dumps({
                "success": False,
                "message": "No tienes citas pendientes por confirmar.",
            }, ensure_ascii=False)

        has_reminder = (
            db.query(WhatsAppMessage.id)
            .filter(
                WhatsAppMessage.tenant_id == tenant_id,
                WhatsAppMessage.message_id.in_([
                    f"reminder_eve:{appointment.id}",
                    f"reminder_2h:{appointment.id}",
                ]),
            )
            .first()
        )
        if not has_reminder:
            return json.dumps({
                "success": False,
                "message": "Esta cita no tiene un recordatorio de confirmación pendiente.",
            }, ensure_ascii=False)

        try:
            updated = appointment_service.update_appointment(
                db, tenant_id, str(appointment.id), AppointmentUpdate(estado="confirmed")
            )
            if not updated:
                return json.dumps({
                    "success": False,
                    "message": "No se pudo confirmar la cita.",
                }, ensure_ascii=False)
            return json.dumps({
                "success": True,
                "message": (
                    f"Cita CONFIRMADA: {updated.service or 'Servicio'} el "
                    f"{_format_date(updated.date_time)} a las "
                    f"{_format_time(updated.date_time)} con "
                    f"{updated.therapist or 'terapeuta'}"
                ),
            }, ensure_ascii=False)
        except ValueError as exc:
            return json.dumps({"success": False, "message": str(exc)}, ensure_ascii=False)


# ============================================================
# Multi-servicio y sugerencias
# ============================================================

def _last_appointment_for_patient(db: Session, tenant_id: str, patient_id: str) -> Optional[Appointment]:
    """Última cita pending/confirmed del paciente (más reciente)."""
    return (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.patient_id == patient_id,
            Appointment.deleted_at == None,
            Appointment.estado.in_(["pending", "confirmed"]),
        )
        .order_by(Appointment.created_at.desc())
        .first()
    )


def _get_related_services_text(db: Session, tenant_id: str, service_id: str) -> Optional[str]:
    """Devuelve texto formateado con servicios relacionados, o None."""
    from ..models.service_related import ServiceRelated

    rels = (
        db.query(ServiceRelated)
        .filter(
            ServiceRelated.tenant_id == tenant_id,
            ServiceRelated.service_id == service_id,
            ServiceRelated.deleted_at == None,
        )
        .all()
    )
    if not rels:
        return None
    lines = []
    for r in rels:
        related = (
            db.query(Service)
            .filter(
                Service.id == r.related_service_id,
                Service.tenant_id == tenant_id,
                Service.is_active == True,
                Service.deleted_at == None,
            )
            .first()
        )
        if related:
            lines.append(
                f"- {related.nombre} ({related.duracion} min - "
                f"${int(related.precio or 0):,})".replace(",", ".")
            )
    if not lines:
        return None
    return "Servicios relacionados:\n" + "\n".join(lines[:5])


def _suggest_multi_service(db: Session, tenant_id: str, appointment: Appointment) -> str:
    """Mensaje que pregunta si quiere agregar otro servicio + sugerencias."""
    related = _get_related_services_text(db, tenant_id, appointment.service_id)
    extra = (
        f"\n\n{related}\n" if related else "\n\n"
    )
    return f"{extra}\U0001F4AC ¿Te gustaría agregar otro servicio a tu cita? Puedes decirme el nombre y lo añado."


def _tool_add_service_to_appointment(
    db: Session, tenant_id: str, appointment_id: str, text: str
) -> str:
    """Agrega un servicio a la cita por texto."""
    from ..models.appointment_item import AppointmentItem
    from ..schemas.appointment import AppointmentItemCreate

    service = _find_service_from_text(db, tenant_id, text)
    if not service:
        return json.dumps({
            "success": False,
            "message": "No encontré ese servicio. ¿Puedes decirme el nombre exacto?"
        }, ensure_ascii=False)

    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.tenant_id == tenant_id,
        Appointment.deleted_at == None,
    ).first()
    if not appointment:
        return json.dumps({"success": False, "message": "Cita no encontrada"})

    # Verificar que no esté ya agregado
    existing = (
        db.query(AppointmentItem)
        .filter(
            AppointmentItem.tenant_id == tenant_id,
            AppointmentItem.appointment_id == appointment_id,
            AppointmentItem.service_id == str(service.id),
            AppointmentItem.is_active == True,
            AppointmentItem.deleted_at == None,
        )
        .first()
    )
    if existing:
        return json.dumps({
            "success": True,
            "message": f"El servicio {service.nombre} ya está agregado a tu cita.",
        }, ensure_ascii=False)

    try:
        from decimal import Decimal
        item = appointment_service.add_item(
            db, tenant_id, appointment,
            service_id=str(service.id),
            cantidad=1,
            descuento=Decimal("0.00"),
        )
        return json.dumps({
            "success": True,
            "message": (
                f"\u2705 He agregado {service.nombre} a tu cita del "
                f"{_format_date(appointment.date_time)}. "
            ),
        }, ensure_ascii=False)
    except ValueError as exc:
        return json.dumps({"success": False, "message": str(exc)}, ensure_ascii=False)


def instance_name(settings: Optional[WhatsAppSettings]) -> str:
    return settings.instance_name if settings else "?"


def _tenant_now(db: Session, tenant_id: str) -> datetime:
    """Hora actual del tenant como datetime naive (hora local del negocio)."""
    try:
        from ..models.tenant import Tenant
        from zoneinfo import ZoneInfo

        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        tz_name = tenant.timezone or "America/Bogota"
        tz = ZoneInfo(tz_name)
        now = datetime.now(tz)
        return now.replace(tzinfo=None)
    except Exception as exc:
        logger.warning(f"[WhatsApp Agent] _tenant_now error: {exc}")
        return datetime.utcnow()


def _find_service_from_text(db: Session, tenant_id: str, t: str) -> Optional[Service]:
    """Busca un servicio cuyo nombre coincida con palabras del texto `t`."""
    if not t:
        return None
    services = (
        db.query(Service)
        .filter(
            Service.tenant_id == tenant_id,
            Service.is_active == True,
            Service.deleted_at == None,
        )
        .all()
    )
    t_words = set(t.split())
    for srv in services:
        srv_words = set(srv.nombre.lower().split())
        if srv_words & t_words:
            return srv
    return None


def _find_all_services_in_text(db: Session, tenant_id: str, t: str) -> list:
    """Devuelve TODOS los servicios activos cuyas palabras aparezcan en `t`."""
    if not t:
        return []
    services = (
        db.query(Service)
        .filter(
            Service.tenant_id == tenant_id,
            Service.is_active == True,
            Service.deleted_at == None,
        )
        .all()
    )
    t_words = set(t.split())
    found = []
    for srv in services:
        srv_words = set(srv.nombre.lower().split())
        if srv_words & t_words:
            found.append(srv)
    return found


def _find_service_in_history(db: Session, tenant_id: str, conversation_id: str) -> Optional[Service]:
    """
    Busca el servicio en los últimos 5 mensajes del asistente. Primer intenta
    el mensaje con "\u2705 Excelente, has elegido" (guard #5). Si no, busca
    cualquier mensaje que mencione un nombre de servicio conocido.
    """
    msgs = (
        db.query(WhatsAppMessage)
        .filter(
            WhatsAppMessage.tenant_id == tenant_id,
            WhatsAppMessage.conversation_id == conversation_id,
            WhatsAppMessage.role == "assistant",
            WhatsAppMessage.deleted_at == None,
        )
        .order_by(WhatsAppMessage.created_at.desc())
        .limit(5)
        .all()
    )

    # 1) Buscar mensaje con "✅ Excelente, has elegido"
    pref = "\u2705 Excelente, has elegido "
    for msg in msgs:
        if msg.content and msg.content.startswith(pref):
            name = msg.content[len(pref):].split("(")[0].strip()
            if name:
                services = (
                    db.query(Service)
                    .filter(
                        Service.tenant_id == tenant_id,
                        Service.is_active == True,
                        Service.deleted_at == None,
                    )
                    .all()
                )
                for srv in services:
                    if srv.nombre.lower().strip() == name.lower():
                        return srv
            break  # Solo un mensaje debería tener el prefijo

    # 2) Fallback: buscar palabras de servicios conocidos en los mensajes
    services = (
        db.query(Service)
        .filter(
            Service.tenant_id == tenant_id,
            Service.is_active == True,
            Service.deleted_at == None,
        )
        .all()
    )
    srv_names = {srv.nombre.lower().strip(): srv for srv in services}
    for msg in msgs:
        if not msg.content:
            continue
        content_lower = msg.content.lower()
        for name, srv in srv_names.items():
            if name in content_lower:
                return srv
    return None


def _extract_date_from_history(db: Session, tenant_id: str, conversation_id: str) -> Optional[str]:
    """
    Busca en los últimos mensajes assistant del bot una fecha YYYY-MM-DD que
    haya mostrado (por ejemplo "Horarios libres para 2026-11-10"). El guard #6
    la escribió así, y el guard #7 la necesita para agendar sin que el cliente
    repita el día.
    """
    msgs = (
        db.query(WhatsAppMessage)
        .filter(
            WhatsAppMessage.tenant_id == tenant_id,
            WhatsAppMessage.conversation_id == conversation_id,
            WhatsAppMessage.deleted_at == None,
        )
        .order_by(WhatsAppMessage.created_at.desc())
        .limit(6)
        .all()
    )
    for m in msgs:
        if not m.content:
            continue
        match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", m.content)
        if match:
            return match.group(1)
    return None


def _parse_only_time(t: str) -> Optional[tuple]:
    """
    Extrae SOLO la hora de un mensaje (sin fecha): "a las 15:00", "15:00",
    "las 3", "3 de la tarde", "3 pm".
    Retorna (hour_24, minute) o None.
    """
    if not t:
        return None

    def _period(t: str) -> str:
        if re.search(r"\bde\s+la\s+(tarde|noche)\b|p\.?\s*m\.?|pm\b", t, re.I):
            return "pm"
        if re.search(r"\bde\s+la\s+mañana\b|a\.?\s*m\.?|am\b|madrugada\b", t, re.I):
            return "am"
        return ""

    m = re.search(r"(?:a\s+)?las?\s*(\d{1,2})(?::(\d{2}))?", t, re.I)
    if not m:
        m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(?:de\s+la\s+(?:mañana|tarde|noche)|a\.?\s*m\.?|p\.?\s*m\.?)\b", t, re.I)
    if not m:
        return None

    hour = int(m.group(1))
    minute = int(m.group(2)) if m.group(2) else 0
    period = _period(t)
    if period == "pm" and 1 <= hour <= 11:
        hour += 12
    elif period == "am" and hour == 12:
        hour = 0
    elif period == "" and 1 <= hour <= 5 and re.search(r"\b(tarde|noche)\b", t, re.I):
        hour += 12

    return (hour, minute)


def _parse_booking_time(t: str, now_local: datetime) -> Optional[tuple]:
    """
    Extrae fecha y hora de un mensaje en español.
    Retorna (date_str, hour_24, minute) o None.
    Ej: "mañana a las 2 de la tarde" -> (2026-11-10, 14, 0)
        "hoy a las 11:40" -> (2026-11-09, 11, 40)
        "mañana a las 2 pm" -> (2026-11-10, 14, 0)
    """
    if not t:
        return None

    # Día: mañana (="tomorrow") / hoy / nombre de día de la semana.
    # "mañana" en "de la mañana" significa "morning", no "tomorrow", así que
    # se excluye esa combinación.
    delta = None
    if re.search(r"\bmanana\b", t) or (
        re.search(r"\bmañana\b", t) and not re.search(r"de\s+la\s+mañana", t)
    ):
        delta = timedelta(days=1)
    elif re.search(r"\bhoy\b", t):
        delta = timedelta()
    else:
        # Intentar con día de la semana
        DAY_MAP = {
            "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2,
            "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6,
        }
        for day_name, day_idx in DAY_MAP.items():
            if re.search(rf"\b{day_name}\b", t, re.I):
                today_weekday = now_local.weekday()
                diff = (day_idx - today_weekday) % 7
                if diff == 0:
                    diff = 7  # mismo día semana que viene
                delta = timedelta(days=diff)
                break
    if delta is None:
        return None

    cita_date = (now_local + delta).strftime("%Y-%m-%d")

    # Hora
    minute = 0
    hour12 = None

    # Patrón 1: "a las 2", "a las 2:30", "las 2 de la tarde"
    # Patrón 2: "2 de la tarde", "2:30 pm", "2pm"
    m = re.search(
        r"(?:a\s+)?las?\s*(\d{1,2})(?::(\d{2}))?"
        r"|"
        r"(\d{1,2})(?::(\d{2}))?\s*(?:de\s+la\s*(mañana|tarde|noche)|"
        r"a\.?\s*m\.?|p\.?\s*m\.?)",
        t, re.I,
    )
    if not m:
        return (cita_date, 0, 0)

    if m.group(1) is not None:
        hour12 = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
    elif m.group(3) is not None:
        hour12 = int(m.group(3))
        minute = int(m.group(4)) if m.group(4) else 0

    if hour12 is None:
        return (cita_date, 0, 0)

    # Determinar AM/PM por palabras
    periodo = None
    if re.search(r"\bde\s+la\s+(tarde|noche)\b|p\.?m\.?|pm\b", t, re.I):
        periodo = "pm"
    elif re.search(r"\bde\s+la\s+mañana\b|a\.?m\.?|am\b|madrugada\b", t, re.I):
        periodo = "am"

    if periodo == "pm":
        if hour12 < 12:
            hour12 += 12
    elif periodo == "am":
        if hour12 == 12:
            hour12 = 0
    else:
        # Sin indicación AM/PM: si es hora pequeña (1-5) y el mensaje contiene
        # "tarde" o "noche", asumir PM
        if hour12 <= 5 and re.search(r"\b(tarde|noche)\b", t, re.I):
            hour12 += 12

    return (cita_date, hour12, minute)


def _extract_booking_from_history(
    db: Session, tenant_id: str, conversation_id: str
) -> Optional[tuple]:
    """
    Busca en los últimos mensajes assistant los datos de una disponibilidad
    mostrada por guard #5 y extrae (date_str, hora_en_minutos, therapist_name,
    therapist_id, service_obj) o None.
    """
    msgs = (
        db.query(WhatsAppMessage)
        .filter(
            WhatsAppMessage.tenant_id == tenant_id,
            WhatsAppMessage.conversation_id == conversation_id,
            WhatsAppMessage.role == "assistant",
            WhatsAppMessage.deleted_at == None,
        )
        .order_by(WhatsAppMessage.created_at.desc())
        .limit(8)
        .all()
    )

    cita_date = None
    cita_time_str = None
    therapist_name = None
    therapist_id = None
    service_obj = None

    full_text = "\n".join((m.content or "") for m in msgs)

    # 1) Fecha: "Horarios libres para YYYY-MM-DD" o "para YYYY-MM-DD"
    m = re.search(r"para\s+(\d{4}-\d{2}-\d{2})", full_text)
    if m:
        cita_date = m.group(1)

    # 2) Hora + terapeuta del slot match:
    #    "El horario de las HH:MM del YYYY-MM-DD está disponible con NOMBRE"
    m = re.search(r"horario de las (\d{2}:\d{2})(?: del (\d{4}-\d{2}-\d{2}))? está disponible con ([^\.]+)", full_text)
    if m:
        cita_time_str = m.group(1)
        therapist_name = m.group(3).strip()
        if not cita_date and m.group(2):
            cita_date = m.group(2)
    else:
        # Fallback: buscar en "La hora HH:MM no está disponible" (primer slot
        # de la lista) o en la lista de slots "- HH:MM (nombre)"
        m = re.search(r"(\d{2}:\d{2})", full_text)
        if m:
            cita_time_str = m.group(1)
        m = re.search(r"-\s+\d{2}:\d{2}\s+\(([^)]+)\)", full_text)
        if m:
            therapist_name = m.group(1).strip()

    # 3) therapist_id: buscar en usuarios con rol therapist que coincidan
    if therapist_name:
        from ..models.user import User as UserModel
        therapist = (
            db.query(UserModel)
            .filter(
                UserModel.tenant_id == tenant_id,
                UserModel.rol == "therapist",
                UserModel.is_active == True,
                UserModel.deleted_at == None,
            )
            .filter(
                db.func.concat(UserModel.nombre, " ", UserModel.apellido).ilike(
                    f"%{therapist_name}%"
                )
            )
            .first()
        )
        if therapist:
            therapist_id = str(therapist.id)
        # Si no encuentra por nombre exacto, usa el primer therapist del slot
        if not therapist_id:
            m = re.search(r"-\s+(\d{2}:\d{2})\s+\(([^)]+)\)", full_text)
            if m:
                tn = m.group(2).strip()
                t = (
                    db.query(UserModel)
                    .filter(
                        UserModel.tenant_id == tenant_id,
                        UserModel.rol == "therapist",
                        db.func.concat(UserModel.nombre, " ", UserModel.apellido).ilike(
                            f"%{tn}%"
                        ),
                    )
                    .first()
                )
                if t:
                    therapist_id = str(t.id)

        # Último recurso: buscar por el primer nombre (split del nombre extraído)
        if not therapist_id and therapist_name:
            from ..models.user import User as UserModel
            first_name = therapist_name.split()[0].strip()
            if first_name:
                t = (
                    db.query(UserModel)
                    .filter(
                        UserModel.tenant_id == tenant_id,
                        UserModel.rol == "therapist",
                        UserModel.is_active == True,
                        UserModel.deleted_at == None,
                        UserModel.nombre.ilike(f"%{first_name}%"),
                    )
                    .first()
                )
                if t:
                    therapist_id = str(t.id)

    # 4) Servicio del historial
    service_obj = _find_service_in_history(db, tenant_id, conversation_id)

    if cita_date and cita_time_str and therapist_id and service_obj:
        parts = cita_time_str.split(":")
        hora_min = int(parts[0]) * 60 + int(parts[1])
        logger.info(
            f"[WhatsApp Agent] _extract_booking FOUND: date={cita_date} "
            f"time={cita_time_str} therapist={therapist_name} "
            f"therapist_id={therapist_id} service={service_obj.nombre if service_obj else None}"
        )
        return (cita_date, hora_min, therapist_name or "Terapeuta", therapist_id, service_obj)
    logger.warning(
        f"[WhatsApp Agent] _extract_booking FAILED: "
        f"date={cita_date} time_str={cita_time_str} "
        f"therapist_id={therapist_id} service_obj={'OK' if service_obj else 'NONE'}"
    )
    return None


def _format_date(dt: Optional[datetime]) -> str:
    return dt.strftime("%d/%m/%Y") if dt else ""


def _format_time(dt: Optional[datetime]) -> str:
    return dt.strftime("%H:%M") if dt else ""


whatsapp_agent = WhatsAppAgentService()