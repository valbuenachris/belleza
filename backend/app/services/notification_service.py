# ============================================================
# backend/app/services/notification_service.py - Notificaciones
# Lógica de negocio de las notificaciones internas del Dashboard:
# listado/contador por usuario, marcado de lectura y generación de
# notificaciones ante eventos del SPA (nueva cita, recordatorio y
# recompensa de fidelidad). Todo aislado por tenant.
# ============================================================

import logging
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from ..models.appointment import Appointment
from ..models.notification import Notification
from ..models.patient import Patient
from ..models.user import User

logger = logging.getLogger(__name__)


# ============================================================
# Constantes
# ============================================================

TYPE_APPOINTMENT = "appointment"
TYPE_REMINDER = "appointment_reminder"
TYPE_LOYALTY = "loyalty"
TYPE_SYSTEM = "system"

# Personal que debe enterarse de la operación diaria.
STAFF_ROLES = ("admin", "manager", "receptionist")
# Responsables de negocio (recompensas de fidelidad, avisos).
MANAGER_ROLES = ("admin", "manager")


# ============================================================
# Helpers internos
# ============================================================

def _active_users(db: Session, tenant_id: str, roles: Iterable[str]) -> List[User]:
    """Usuarios activos del tenant que pertenecen a alguno de los roles."""
    return (
        db.query(User)
        .filter(
            User.tenant_id == tenant_id,
            User.is_active == True,  # noqa: E712
            User.deleted_at == None,  # noqa: E711
            User.rol.in_(tuple(roles)),
        )
        .all()
    )


def _new_notification(
    tenant_id: str,
    user_id: str,
    title: str,
    message: Optional[str],
    type: str,
) -> Notification:
    """Construye una notificación no leída (sin persistir)."""
    return Notification(
        tenant_id=tenant_id,
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        is_read=False,
        is_active=True,
    )


# ============================================================
# Creación
# ============================================================

def create_notification(
    db: Session,
    tenant_id: str,
    user_id: str,
    title: str,
    message: Optional[str] = None,
    type: str = TYPE_SYSTEM,
) -> Notification:
    """Crea y persiste una notificación para un usuario concreto."""
    notification = _new_notification(tenant_id, user_id, title, message, type)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def create_for_users(
    db: Session,
    tenant_id: str,
    user_ids: Iterable[str],
    title: str,
    message: Optional[str] = None,
    type: str = TYPE_SYSTEM,
) -> int:
    """
    Crea una notificación por cada usuario indicado (sin duplicados).
    Devuelve cuántas notificaciones se crearon.
    """
    unique_ids = list(dict.fromkeys(uid for uid in user_ids if uid))
    if not unique_ids:
        return 0
    for user_id in unique_ids:
        db.add(_new_notification(tenant_id, user_id, title, message, type))
    db.commit()
    return len(unique_ids)


def create_for_roles(
    db: Session,
    tenant_id: str,
    roles: Iterable[str],
    title: str,
    message: Optional[str] = None,
    type: str = TYPE_SYSTEM,
) -> int:
    """Crea una notificación para cada usuario activo con alguno de los roles."""
    return create_for_users(
        db,
        tenant_id,
        [user.id for user in _active_users(db, tenant_id, roles)],
        title,
        message,
        type,
    )


# ============================================================
# Consultas
# ============================================================

def _base_query(db: Session, tenant_id: str, user_id: str):
    """Query base de las notificaciones activas de un usuario del tenant."""
    return db.query(Notification).filter(
        Notification.tenant_id == tenant_id,
        Notification.user_id == user_id,
        Notification.is_active == True,  # noqa: E712
        Notification.deleted_at == None,  # noqa: E711
    )


def get_unread_count(db: Session, tenant_id: str, user_id: str) -> int:
    """Número de notificaciones no leídas del usuario (badge)."""
    return (
        _base_query(db, tenant_id, user_id)
        .filter(Notification.is_read == False)  # noqa: E712
        .count()
    )


def list_user_notifications(
    db: Session,
    tenant_id: str,
    user_id: str,
    is_read: Optional[bool] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict:
    """
    Listado paginado de notificaciones del usuario (más recientes primero),
    con filtro opcional por estado de lectura y contador de no leídas.
    """
    query = _base_query(db, tenant_id, user_id)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)

    total = query.count()
    rows = (
        query.order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "notifications": rows,
        "total": total,
        "unread_count": get_unread_count(db, tenant_id, user_id),
    }


# ============================================================
# Marcado de lectura
# ============================================================

def mark_notification_read(
    db: Session,
    tenant_id: str,
    user_id: str,
    notification_id: str,
) -> Notification:
    """
    Marca una notificación como leída. Lanza ValueError si no existe,
    no es del tenant o no pertenece al usuario.
    """
    notification = (
        _base_query(db, tenant_id, user_id)
        .filter(Notification.id == notification_id)
        .first()
    )
    if not notification:
        raise ValueError("Notificación no encontrada")

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.commit()
        db.refresh(notification)

    return notification


def mark_all_read(db: Session, tenant_id: str, user_id: str) -> int:
    """Marca como leídas todas las notificaciones del usuario. Devuelve el total."""
    updated = (
        _base_query(db, tenant_id, user_id)
        .filter(Notification.is_read == False)  # noqa: E712
        .update(
            {
                Notification.is_read: True,
                Notification.read_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )
    )
    db.commit()
    return int(updated or 0)


# ============================================================
# Generación por eventos del SPA (best-effort)
# ============================================================

def notify_new_appointment(
    db: Session,
    appointment: Appointment,
    actor_user_id: Optional[str] = None,
) -> int:
    """
    Notifica al personal (y al terapeuta asignado) que se agendó una cita.
    Nunca lanza: un fallo de notificación no debe romper la creación.
    """
    try:
        when = (
            appointment.date_time.strftime("%d/%m/%Y %H:%M")
            if appointment.date_time
            else "fecha por confirmar"
        )
        patient_name = appointment.patient or "Paciente"
        service_name = appointment.service or "Servicio"

        recipients = {
            user.id for user in _active_users(db, appointment.tenant_id, STAFF_ROLES)
        }
        if appointment.therapist_id:
            therapist = (
                db.query(User)
                .filter(
                    User.id == appointment.therapist_id,
                    User.tenant_id == appointment.tenant_id,
                    User.is_active == True,  # noqa: E712
                )
                .first()
            )
            if therapist:
                recipients.add(therapist.id)
        if actor_user_id:
            recipients.discard(actor_user_id)

        return create_for_users(
            db,
            appointment.tenant_id,
            recipients,
            title="Nueva cita agendada",
            message=f"{patient_name} — {service_name} · {when}",
            type=TYPE_APPOINTMENT,
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning(f"[Notificaciones] No se pudo notificar la nueva cita: {exc}")
        return 0


def notify_loyalty_reward(
    db: Session,
    patient: Patient,
    reward: str,
    free_sessions: int = 1,
) -> int:
    """
    Notifica a los responsables que un paciente ganó una recompensa de
    fidelidad (sesión/es gratis). Nunca lanza.
    """
    try:
        patient_name = f"{patient.nombre} {patient.apellido}".strip() or "Paciente"
        message = (
            f"{patient_name} alcanzó la meta de estrellas y ganó: "
            f"{reward or 'una sesión gratuita'} "
            f"({free_sessions} sesión(es) gratis)."
        )
        return create_for_roles(
            db,
            patient.tenant_id,
            MANAGER_ROLES,
            title="Recompensa de fidelidad otorgada",
            message=message,
            type=TYPE_LOYALTY,
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning(f"[Notificaciones] No se pudo notificar la recompensa: {exc}")
        return 0


def notify_upcoming_appointments(
    db: Session,
    tenant_id: Optional[str] = None,
    within_hours: int = 24,
) -> int:
    """
    Genera recordatorios para las citas pending/confirmed que comienzan
    dentro de las próximas `within_hours` horas. Pensado para ejecutarse
    periódicamente (cron / job programado).

    Evita duplicados dentro de la ventana consultando si ya existe una
    notificación del mismo tipo y título en las últimas 24 horas.
    Devuelve el número de notificaciones creadas.
    """
    now = datetime.utcnow()
    window_end = now + timedelta(hours=within_hours)

    try:
        query = db.query(Appointment).filter(
            Appointment.date_time >= now,
            Appointment.date_time <= window_end,
            Appointment.estado.in_(("pending", "confirmed")),
            Appointment.is_active == True,  # noqa: E712
            Appointment.deleted_at == None,  # noqa: E711
        )
        if tenant_id:
            query = query.filter(Appointment.tenant_id == tenant_id)

        created = 0
        for appointment in query.all():
            when = appointment.date_time.strftime("%d/%m/%Y %H:%M")
            patient_name = appointment.patient or "Paciente"
            title = f"Recordatorio: {patient_name} · {when}"
            message = (
                f"{appointment.service or 'Servicio'} a las "
                f"{appointment.date_time.strftime('%H:%M')} "
                f"(terapeuta: {appointment.therapist or 'sin asignar'})."
            )

            already_sent = (
                db.query(Notification.id)
                .filter(
                    Notification.tenant_id == appointment.tenant_id,
                    Notification.type == TYPE_REMINDER,
                    Notification.title == title,
                    Notification.created_at >= now - timedelta(hours=24),
                )
                .first()
            )
            if already_sent:
                continue

            recipients = {
                user.id
                for user in _active_users(db, appointment.tenant_id, STAFF_ROLES)
            }
            if appointment.therapist_id:
                recipients.add(appointment.therapist_id)

            created += create_for_users(
                db,
                appointment.tenant_id,
                recipients,
                title=title,
                message=message,
                type=TYPE_REMINDER,
            )
        return created
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning(f"[Notificaciones] No se pudieron generar recordatorios: {exc}")
        return 0


# ============================================================
# Utilidades de serialización
# ============================================================

def to_dict(notification: Notification) -> dict:
    """Serializa una notificación al formato de los schemas."""
    return {
        "id": notification.id,
        "tenant_id": notification.tenant_id,
        "user_id": notification.user_id,
        "title": notification.title,
        "message": notification.message,
        "type": notification.type,
        "is_read": notification.is_read,
        "created_at": notification.created_at,
        "read_at": notification.read_at,
    }
