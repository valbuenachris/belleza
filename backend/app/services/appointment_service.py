# ============================================================
# backend/app/services/appointment_service.py - Lógica de negocio de Citas
# CRUD de citas con validación de doble reserva (anti-double-booking)
# ============================================================

import logging
from typing import Optional, List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from ..models.appointment import Appointment, ESTADOS_CITA
from ..models.patient import Patient
from ..models.user import User
from ..models.service import Service
from ..schemas.appointment import AppointmentCreate, AppointmentUpdate
from ..utils.security import generate_uuid

logger = logging.getLogger(__name__)

# Estados que NO bloquean el horario del terapeuta
ESTADOS_NO_CONFLICTO = ("cancelled",)


# ============================================================
# Validación de disponibilidad (anti-double-booking)
# ============================================================

def _check_overlap(
    db: Session,
    tenant_id: str,
    therapist_id: str,
    patient_id: str,
    start: datetime,
    duracion: int,
    exclude_id: Optional[str] = None,
) -> None:
    """
    Verifica que la cita [start, start+duracion) no se solape con otra
    cita del mismo terapeuta o del mismo paciente (que no esté cancelada).

    Raises:
        ValueError: Si existe conflicto de horario
    """
    end = start + timedelta(minutes=duracion)

    # Ventana de búsqueda acotada (1 día antes de la cita)
    query = db.query(Appointment).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.deleted_at == None,
        Appointment.estado.notin_(ESTADOS_NO_CONFLICTO),
        Appointment.date_time < end,
        Appointment.date_time >= start - timedelta(days=1),
    )
    if exclude_id:
        query = query.filter(Appointment.id != exclude_id)

    overlap = query.all()

    for apt in overlap:
        apt_end = apt.date_time + timedelta(minutes=apt.duracion or 0)
        if apt_end > start:
            if apt.therapist_id == therapist_id:
                raise ValueError(
                    "El terapeuta ya tiene una cita agendada en ese horario. "
                    f"Se superpone con la cita {apt.id} de {apt.date_time}."
                )
            if apt.patient_id == patient_id:
                raise ValueError(
                    "El paciente ya tiene una cita agendada en ese horario. "
                    f"Se superpone con la cita de {apt.date_time}."
                )


# ============================================================
# Resolución de campos legacy (compatibilidad con la UI actual)
# ============================================================

def resolve_therapist(db: Session, tenant_id: str, therapist_id: str, therapist_name: str) -> str:
    """Devuelve el therapist_id a partir del id o, si no viene, del nombre."""
    if therapist_id:
        user = db.query(User).filter(
            User.id == therapist_id,
            User.tenant_id == tenant_id,
            User.deleted_at == None,
            User.rol == "therapist",
        ).first()
        if not user:
            raise ValueError("Terapeuta no válido para este SPA")
        return user.id

    if therapist_name:
        name_parts = therapist_name.strip().lower().split()
        user = db.query(User).filter(
            User.tenant_id == tenant_id,
            User.rol == "therapist",
            User.deleted_at == None,
        ).filter(
            or_(*[User.nombre.ilike(f"%{p}%") for p in name_parts])
        ).first()
        if user:
            return user.id
        raise ValueError("No se encontró un terapeuta con ese nombre")

    raise ValueError("Debes indicar el terapeuta (therapist_id o therapist)")


def resolve_service(db: Session, tenant_id: str, service_id: str, service_name: str) -> Service:
    """Devuelve el Service a partir del id o, si no viene, del nombre."""
    if service_id:
        service = db.query(Service).filter(
            Service.id == service_id,
            Service.tenant_id == tenant_id,
            Service.deleted_at == None,
        ).first()
        if not service:
            raise ValueError("Servicio no válido para este SPA")
        return service

    if service_name:
        service = db.query(Service).filter(
            Service.tenant_id == tenant_id,
            Service.nombre.ilike(f"%{service_name.strip()}%"),
            Service.deleted_at == None,
        ).first()
        if service:
            return service
        raise ValueError("No se encontró un servicio con ese nombre")

    raise ValueError("Debes indicar el servicio (service_id o service)")


def resolve_date_time(date_time: Optional[datetime], fecha: Optional[str], time: Optional[str]) -> datetime:
    """Devuelve un datetime combinando date_time o los campos legacy fecha+time."""
    if date_time:
        return date_time

    if fecha and time:
        try:
            return datetime.strptime(f"{fecha} {time}", "%Y-%m-%d %H:%M")
        except ValueError:
            raise ValueError("Formato de fecha/hora inválido (usa fecha='YYYY-MM-DD', time='HH:MM')")

    raise ValueError("Debes indicar date_time o los campos fecha y time")


# ============================================================
# Crear cita
# ============================================================

def create_appointment(db: Session, tenant_id: str, data: AppointmentCreate) -> Appointment:
    """
    Crea una cita validando disponibilidad del terapeuta y del paciente.
    Acepta campos legacy (service/therapist/fecha/time) además de los nuevos.

    Raises:
        ValueError: Si hay conflictos de horario o referencias inválidas
    """
    # Validar paciente
    patient = db.query(Patient).filter(
        Patient.id == data.patient_id,
        Patient.tenant_id == tenant_id,
        Patient.deleted_at == None,
    ).first()
    if not patient:
        raise ValueError("Paciente no válido para este SPA")

    service_data = None

    # Elevar datos del body
    body = data.model_dump()

    # date_time compuesto
    date_time = resolve_date_time(data.date_time, body.get("fecha"), body.get("time"))

    # terapéuta (id o nombre legacy)
    therapist_id = resolve_therapist(
        db, tenant_id, body.get("therapist_id"), body.get("therapist")
    )

    # servicio (id o nombre legacy)
    service_data = resolve_service(
        db, tenant_id, body.get("service_id"), body.get("service")
    )

    duracion = body.get("duracion") or service_data.duracion
    estado = (body.get("estado") or "pending").lower()
    if estado not in ESTADOS_CITA:
        raise ValueError(f"Estado inválido. Opciones: {', '.join(ESTADOS_CITA)}")

    # Precio efectivo (cita o servicio)
    precio = body.get("precio")
    if precio is None:
        precio = service_data.precio

    # Validar anti-doble reserva
    _check_overlap(db, tenant_id, therapist_id, str(patient.id), date_time, duracion)

    appointment = Appointment(
        id=generate_uuid(),
        tenant_id=tenant_id,
        patient_id=str(patient.id),
        therapist_id=therapist_id,
        service_id=str(service_data.id),
        date_time=date_time,
        duracion=duracion,
        estado=estado,
        precio=precio,
        notas=body.get("notas"),
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    logger.info(f"Cita creada: {appointment.id} para {appointment.patient} ({date_time})")
    return appointment


# ============================================================
# Obtener cita
# ============================================================

def get_appointment_by_id(db: Session, tenant_id: str, appointment_id: str) -> Optional[Appointment]:
    """Obtiene una cita por su ID (filtrada por tenant)."""
    return db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.tenant_id == tenant_id,
        Appointment.deleted_at == None,
    ).first()


# ============================================================
# Listar citas
# ============================================================

def list_appointments(
    db: Session,
    tenant_id: str,
    skip: int = 0,
    limit: int = 100,
    fecha: Optional[str] = None,
    estado: Optional[str] = None,
    patient_id: Optional[str] = None,
) -> List[Appointment]:
    """
    Lista citas del tenant con filtros opcionales.
    `fecha` filtra por día (formato YYYY-MM-DD) y `patient_id` por paciente.
    """
    query = db.query(Appointment).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.deleted_at == None,
    )

    if fecha:
        try:
            day = datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            return []
        query = query.filter(
            Appointment.date_time >= day,
            Appointment.date_time < day + timedelta(days=1),
        )

    if estado:
        query = query.filter(Appointment.estado == estado.lower())

    if patient_id:
        query = query.filter(Appointment.patient_id == patient_id)

    return query.order_by(Appointment.date_time.asc()).offset(skip).limit(limit).all()


def count_appointments(
    db: Session,
    tenant_id: str,
    fecha: Optional[str] = None,
    estado: Optional[str] = None,
    patient_id: Optional[str] = None,
) -> int:
    """Cuenta el total de citas con filtros opcionales."""
    query = db.query(func.count(Appointment.id)).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.deleted_at == None,
    )
    if fecha:
        try:
            day = datetime.strptime(fecha, "%Y-%m-%d")
            query = query.filter(
                Appointment.date_time >= day,
                Appointment.date_time < day + timedelta(days=1),
            )
        except ValueError:
            return 0
    if estado:
        query = query.filter(Appointment.estado == estado.lower())
    if patient_id:
        query = query.filter(Appointment.patient_id == patient_id)
    return query.scalar() or 0


# ============================================================
# Actualizar cita (re-valida disponibilidad si cambia horario/terapeuta)
# ============================================================

def update_appointment(
    db: Session,
    tenant_id: str,
    appointment_id: str,
    data: AppointmentUpdate,
) -> Optional[Appointment]:
    """Actualiza una cita re-validando el anti-doble reserva."""
    appointment = get_appointment_by_id(db, tenant_id, appointment_id)
    if not appointment:
        return None

    body = data.model_dump(exclude_unset=True)

    if "estado" in body:
        body["estado"] = body["estado"].lower()
        if body["estado"] not in ESTADOS_CITA:
            raise ValueError(f"Estado inválido. Opciones: {', '.join(ESTADOS_CITA)}")

    # Nueva fecha/hora: solo se reconstruye si el payload trae date_time o fecha+time.
    # Una actualización parcial (p. ej. solo estado) no debe exigir horario.
    if any(k in body for k in ("date_time", "fecha", "time")):
        date_time = resolve_date_time(body.get("date_time"), body.get("fecha"), body.get("time"))
        body["date_time"] = date_time
    else:
        date_time = appointment.date_time

    therapist_id = body.get("therapist_id")
    if not therapist_id and body.get("therapist"):
        therapist_id = resolve_therapist(db, tenant_id, "", body["therapist"])

    patient_id = body.get("patient_id")

    # Si cambia horario/terapeuta/paciente, validar disponibilidad
    if (
        date_time != appointment.date_time
        or (therapist_id and therapist_id != appointment.therapist_id)
        or (patient_id and patient_id != appointment.patient_id)
    ):
        _check_overlap(
            db,
            tenant_id,
            therapist_id or appointment.therapist_id,
            patient_id or appointment.patient_id,
            date_time,
            body.get("duracion") if body.get("duracion") else appointment.duracion,
            exclude_id=appointment.id,
        )

    for field, value in body.items():
        if field in ("fecha", "time"):
            continue
        setattr(appointment, field, value)

    db.commit()
    db.refresh(appointment)

    logger.info(f"Cita actualizada: {appointment.id}")
    return appointment


# ============================================================
# Cancelar cita (soft, estado = cancelled)
# ============================================================

def cancel_appointment(db: Session, tenant_id: str, appointment_id: str) -> Optional[Appointment]:
    """Cancela una cita (la libera del horario del terapeuta)."""
    appointment = get_appointment_by_id(db, tenant_id, appointment_id)
    if not appointment:
        return None

    appointment.estado = "cancelled"
    db.commit()
    db.refresh(appointment)

    logger.info(f"Cita cancelada: {appointment.id}")
    return appointment


# ============================================================
# Resumen de estadísticas para el dashboard
# ============================================================

def get_appointment_summary(db: Session, tenant_id: str) -> dict:
    """
    Estadísticas para las tarjetas del dashboard.

    Returns:
        dict con total_citas_hoy, pendientes, confirmadas, ingresos_hoy
    """
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    citas_hoy = db.query(Appointment).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.deleted_at == None,
        Appointment.date_time >= today,
        Appointment.date_time < tomorrow,
    ).all()

    total_citas_hoy = len(citas_hoy)

    # Ingresos: suma del precio efectivo de las citas hoy
    total_ingresos_hoy = 0
    for apt in citas_hoy:
        if apt.estado == "cancelled":
            continue
        precio = apt.precio
        if precio is None and apt.service_rel and apt.service_rel.precio is not None:
            precio = apt.service_rel.precio
        total_ingresos_hoy += float(precio or 0)

    pendientes = db.query(func.count(Appointment.id)).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.deleted_at == None,
        Appointment.estado == "pending",
    ).scalar() or 0

    confirmadas = db.query(func.count(Appointment.id)).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.deleted_at == None,
        Appointment.estado == "confirmed",
    ).scalar() or 0

    return {
        "total_citas_hoy": total_citas_hoy,
        "pendientes": pendientes,
        "confirmadas": confirmadas,
        "ingresos_hoy": round(total_ingresos_hoy, 2),
    }


def build_appointment_response(appointment: Appointment) -> dict:
    """
    Construye el diccionario de respuesta con los campos calculados
    que espera la UI (patient, service, therapist, time, etc.).
    """
    precio = appointment.precio
    if precio is None and appointment.service_rel and appointment.service_rel.precio is not None:
        precio = appointment.service_rel.precio

    return {
        "id": str(appointment.id),
        "tenant_id": str(appointment.tenant_id),
        "patient_id": str(appointment.patient_id),
        "therapist_id": str(appointment.therapist_id),
        "service_id": str(appointment.service_id),
        "date_time": appointment.date_time.isoformat() if appointment.date_time else None,
        "fecha": appointment.fecha,
        "hora_inicio": appointment.hora_inicio,
        "time": appointment.time,
        "duracion": appointment.duracion,
        "estado": appointment.estado,
        "precio": float(precio) if precio is not None else None,
        "total_precio": float(precio) if precio is not None else None,
        "notas": appointment.notas,
        "patient": appointment.patient,
        "service": appointment.service,
        "therapist": appointment.therapist,
        "created_at": appointment.created_at.isoformat() if appointment.created_at else None,
    }