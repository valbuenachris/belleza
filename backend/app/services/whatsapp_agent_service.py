import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..config import settings as s
from ..models.appointment import Appointment
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

SYSTEM_PROMPT_TEMPLATE = (
    "Eres un asistente virtual de un SPA (centro de estética y relajación). "
    "Tu nombre es {agent_name}. Tu tono de comunicación es {agent_tone}.\n\n"
    "{cliente_context}\n\n"
    "{now_context}\n\n"
    "Tu función es ayudar a los clientes a gestionar sus citas a través de WhatsApp: "
    "agendar, modificar o cancelar citas, y consultar disponibilidad.\n"
    "Debes responder SIEMPRE en español, de forma amable, clara y concisa.\n\n"
    "Dispones de herramientas que puedes invocar. Tu respuesta DEBE SER "
    "SIEMPRE UNA ÚNICA LÍNEA CON JSON VÁLIDO, exactamente en uno de estos dos formatos:\n\n"
    "1. Para responder directamente al cliente (saludo, pregunta, confirmación, etc.):\n"
    '   {"reply": "tu mensaje al cliente"}\n\n'
    "2. Para ejecutar una herramienta:\n"
    '   {"tool": "nombre", "args": {...}}\n\n'
    "HERRAMIENTAS DISPONIBLES:\n"
    '1. find_patient(phone)->dict: identifica al cliente por su número de teléfono. '
    "Es la herramienta que debes usar para obtener el patient_id del cliente cuando lo "
    "necesites. Args: {\"phone\": \"número\"}. Retorna patient_id y patient_name (o los crea).\n"
    '2. list_services()->list: lista servicios del SPA. Args: {}. '
    "Retorna [{id, name, duration, price}].\n"
    '3. check_availability(date, service_id)->list: horarios libres para un servicio '
    "en una fecha (YYYY-MM-DD). Args: {\"date\": \"YYYY-MM-DD\", \"service_id\": \"id\"}. "
    "Retorna [{time, therapist, therapist_id}].\n"
    '4. book_appointment(patient_id, service_id, therapist_id, date_time)->dict: '
    "agenda la cita. Args: {\"patient_id\": id, \"service_id\": id, \"therapist_id\": id, "
    "\"date_time\": \"YYYY-MM-DD HH:MM\"}. Retorna {success, appointment_id, message}.\n"
    '5. modify_appointment(appointment_id, date_time?, service_id?)->dict: modifica una '
    "cita. Args: {\"appointment_id\": id, \"date_time\"?: \"YYYY-MM-DD HH:MM\", "
    "\"service_id\"?: id}. Retorna {success, message}.\n"
    '6. cancel_appointment(appointment_id)->dict: cancela una cita. '
    "Args: {\"appointment_id\": id}. Retorna {success, message}.\n"
    '7. list_my_appointments(patient_id)->list: próximas citas del cliente. '
    "Args: {\"patient_id\": id}. Retorna [{date, time, service, therapist, status, id}].\n"
    '8. confirm_pending_appointment(patient_id)->dict: confirma la próxima cita '
    "pendiente (pending) del cliente, cambiando su estado a confirmed. "
    "Args: {\"patient_id\": id}. Retorna {success, message}.\n\n"
    "REGLAS DE ORO:\n"
    "- NUNCA escribas texto fuera del JSON. Tu mensaje completo debe ser UNA línea JSON.\n"
    '- Si NO vas a ejecutar herramienta, usa {"reply": "..."} con el mensaje al cliente.\n'
    "- Ya conoces el número de teléfono del cliente (CLIENTE). NUNCA le preguntes por su "
    "número: usa find_patient con ese mismo número para identificarlo cuando lo necesites.\n"
    "- Para agendar: identifica al cliente con find_patient, pregunta servicio y horario "
    "si no los ha indicado, verifica disponibilidad con check_availability y CONFIRMA "
    "antes de book_appointment.\n"
    "- Para modificar/cancelar: lista sus citas con list_my_appointments y confirma antes "
    "de modificar/cancelar.\n"
    "- Si falta información, usa {\"reply\": ...} para pedirla amablemente (no inventar).\n"
    "- Si el cliente pide hablar con un humano, responde {\"reply\": \"HUMAN\"}.\n"
    "- Sé breve y amable; usa emojis con moderación.\n"
    "- No expongas IDs internos crudos al cliente salvo que sean necesarios para la gestión.\n"
    "- Nunca inventes datos; si algo falla, indícalo con amabilidad.\n"
    "- Para responder sobre días/horas, usa SIEMPRE la FECHA Y HORA ACTUAL del SPA\n"
    "  (contexto) para calcular hoy/mañana y los días de la semana. Nunca inventes\n"
    "  fechas ni propongas horarios: primero llama a check_availability y ofrece\n"
    "  SOLO los horarios que devuelva esa herramienta.\n"
    "- Cuando el cliente responda CONFIRMO, CONFIRMAR, SI, SÍ o similar (p. ej. tras\n"
    "  un recordatorio 24h antes), llama a confirm_pending_appointment para cambiar\n"
    "  su próxima cita pendiente a CONFIRMADA e indícale los detalles.\n"
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
            if m.role in ("user", "assistant") and m.content:
                history.append({"role": m.role, "content": m.content})
        return history

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

        for attempt in range(5):
            try:
                # _call_freellmapi es síncrono (httpx) y bloquea el event loop:
                # se ejecuta en un hilo para no bloquear el procesamiento de
                # otros webhooks de WhatsApp.
                ai_response = await asyncio.to_thread(_call_freellmapi, messages)
            except ValueError as exc:
                logger.warning(f"[WhatsApp Agent] FreeLLMAPI error: {exc}")
                return FALLBACK_REPLY

            if not ai_response or not ai_response.strip():
                return FALLBACK_REPLY

            logger.info(
                f"[WhatsApp Agent] Respuesta IA (raw): {ai_response[:200]}"
            )

            try:
                decision = self._parse_decision(ai_response)
            except Exception as exc:
                logger.warning(f"[WhatsApp Agent] _parse_decision error: {exc}")
                return ai_response.strip()[:4000]

            # Respuesta directa
            if not isinstance(decision, dict):
                reply = ai_response.strip()
                return reply[:4000] if reply else FALLBACK_REPLY

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
                return ai_response.strip()[:4000]

            logger.info(
                f"[WhatsApp Agent] Herramienta {tool_name} tenant={tenant_id} args={json.dumps(args, ensure_ascii=False)[:200]}"
            )
            tool_result = self._dispatch_tool(db, tenant_id, tool_name, args, conversation)

            messages.append({"role": "assistant", "content": ai_response})
            messages.append(
                {"role": "system", "content": f"Resultado de la herramienta {tool_name}: {tool_result}"}
            )

        return FALLBACK_REPLY

    def _parse_decision(self, ai_response: str) -> Optional[dict]:
        """
        Extrae el primer objeto JSON {...} de la respuesta. Tolera ruido
        (markdown, comillas, texto alrededor). Devuelve dict o None.
        """
        text = ai_response.strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            logger.warning(f"[WhatsApp Agent] JSON inválido en respuesta: {ai_response[:200]}")
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
            dias_op = config.get("dias_operacion") or [0, 1, 2, 3, 4, 5, 6]
        except Exception:
            dias_op = [0, 1, 2, 3, 4, 5, 6]
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

        # El tenant no atiende ese día de la semana (0=domingo, 6=sábado)
        if isinstance(dias_op, (list, tuple)) and day.weekday() not in dias_op:
            return json.dumps({"error": "El SPA no atiende ese día de la semana"})

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
            )
            appointment = appointment_service.create_appointment(db, tenant_id, data)
            return json.dumps({
                "success": True,
                "appointment_id": str(appointment.id),
                "message": (
                    f"Cita creada: {appointment.service or 'Servicio'} el "
                    f"{_format_date(appointment.date_time)} a las "
                    f"{_format_time(appointment.date_time)} con "
                    f"{appointment.therapist or 'terapeuta'}"
                ),
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


def _format_date(dt: Optional[datetime]) -> str:
    return dt.strftime("%d/%m/%Y") if dt else ""


def _format_time(dt: Optional[datetime]) -> str:
    return dt.strftime("%H:%M") if dt else ""


whatsapp_agent = WhatsAppAgentService()