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
from ..models.appointment_item import AppointmentPayment
from ..schemas.appointment import AppointmentCreate, AppointmentUpdate
from ..services import loyalty_service, notification_service
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
# Fidelidad: premio exactamente una vez por cita
# ============================================================

def _award_loyalty_once(db: Session, appointment: Appointment, patient: Patient) -> bool:
    """
    Otorga la estrella de fidelidad de una cita exactamente una vez.

    Bloquea la fila de la cita (SELECT ... FOR UPDATE) y reevalúa
    `loyalty_awarded` tras adquirir el lock, de modo que:
      - alternar completed -> pending -> completed no vuelve a premiar, y
      - dos peticiones concurrentes que completan la misma cita no
        otorgan la estrella dos veces.

    La marca `loyalty_awarded` y el incremento del paciente se confirman
    en el mismo commit (lo hace `award_loyalty_points`), así que la
    operación es atómica.

    Returns:
        True si otorgó la estrella en esta llamada; False si ya estaba
        premiada o la cita no existe.
    """
    locked = (
        db.query(Appointment)
        .filter(Appointment.id == appointment.id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if locked is None or locked.loyalty_awarded:
        return False

    # Marca antes del commit de award_loyalty_points: el flag de la cita y
    # el saldo del paciente entran en la misma transacción.
    locked.loyalty_awarded = True
    loyalty_service.award_loyalty_points(db, patient)
    db.refresh(appointment)
    return True


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

    # Programa de fidelidad: una cita creada directamente como completada
    # también otorga su estrella (una sola vez por cita).
    if appointment.estado == "completed":
        _award_loyalty_once(db, appointment, patient)

    # Notificación interna para el personal (best-effort: nunca rompe la
    # creación de la cita si falla).
    notification_service.notify_new_appointment(db, appointment)

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
        # No permitir completar si la cita no tiene pagos registrados
        if body["estado"] == "completed":
            if appointment.estado_pago == "unpaid":
                raise ValueError(
                    "No se puede completar la cita sin pagos registrados. "
                    "Registra un pago primero o usa 'Estados de pago: crédito'."
                )

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

    # Programa de fidelidad: se otorga 1 estrella al completar la cita,
    # exactamente una vez por cita (loyalty_awarded).
    if appointment.estado == "completed" and not appointment.loyalty_awarded:
        patient = db.query(Patient).filter(
            Patient.id == appointment.patient_id,
            Patient.deleted_at == None,
        ).first()
        if patient:
            _award_loyalty_once(db, appointment, patient)

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


# ============================================================
# Reporte financiero y de rendimiento
# ============================================================

def get_financial_report(
    db: Session,
    tenant_id: str,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
) -> dict:
    """
    Reporte financiero y de rendimiento del SPA en un rango de fechas.

    - KPIs: ingresos, citas (completadas/canceladas), ticket promedio, pacientes nuevos
    - Top servicios por cantidad y por ingresos
    - Rendimiento por terapeuta (citas completadas e ingresos)

    Si `desde`/`hasta` no se indican, se usa el mes actual.
    """
    today = datetime.now()

    def _parse_day(value: Optional[str], label: str) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Formato de {label} inválido (usa YYYY-MM-DD)")

    start = _parse_day(desde, "desde")
    end = _parse_day(hasta, "hasta")

    if start is None:
        start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)

    if end is None:
        end = today.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        end = end.replace(hour=23, minute=59, second=59, microsecond=999999)

    citas = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.deleted_at == None,
            Appointment.date_time >= start,
            Appointment.date_time <= end,
        )
        .all()
    )

    def _effective_precio(a: Appointment, default: float = 0.0) -> float:
        precio = a.precio
        if precio is None and a.service_rel and a.service_rel.precio is not None:
            precio = a.service_rel.precio
        return float(precio or default)

    efectivas = [a for a in citas if a.estado != "cancelled"]

    ingresos = sum(_effective_precio(a) for a in efectivas)
    total_citas = len(citas)
    completadas_count = sum(1 for a in citas if a.estado == "completed")
    canceladas_count = sum(1 for a in citas if a.estado == "cancelled")
    ticket_promedio = ingresos / len(efectivas) if efectivas else 0.0

    # Pacientes nuevos: created_at se guarda en UTC (datetime.utcnow), pero
    # el rango del reporte viene en hora local del tenant. Se convierten los
    # límites local -> UTC para que el conteo coincida con el periodo real.
    from ..models.tenant import Tenant as TenantModel

    tenant_row = db.query(TenantModel).filter(TenantModel.id == tenant_id).first()
    tz_name = (tenant_row.timezone if tenant_row else None) or "America/Bogota"
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(tz_name)
        start_utc = start.replace(tzinfo=tz).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        end_utc = end.replace(tzinfo=tz).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    except Exception:
        start_utc, end_utc = start, end

    pacientes_nuevos = (
        db.query(func.count(Patient.id))
        .filter(
            Patient.tenant_id == tenant_id,
            Patient.deleted_at == None,
            Patient.created_at >= start_utc,
            Patient.created_at <= end_utc,
        )
        .scalar()
        or 0
    )

    # Top servicios (más solicitados y con más ingresos)
    servicios_map: dict = {}
    for a in efectivas:
        name = a.service or "Sin servicio"
        entry = servicios_map.setdefault(name, {"servicio": name, "cantidad": 0, "ingresos": 0.0})
        entry["cantidad"] += 1
        entry["ingresos"] += _effective_precio(a)

    top_servicios = sorted(
        servicios_map.values(), key=lambda s: (s["cantidad"], s["ingresos"]), reverse=True
    )

    # Rendimiento por terapeuta
    terapeutas_map: dict = {}
    for a in efectivas:
        name = a.therapist or "Sin terapeuta"
        entry = terapeutas_map.setdefault(
            name, {"terapeuta": name, "completadas": 0, "ingresos": 0.0}
        )
        if a.estado == "completed":
            entry["completadas"] += 1
        entry["ingresos"] += _effective_precio(a)

    rendimiento_terapeutas = sorted(
        terapeutas_map.values(), key=lambda t: t["ingresos"], reverse=True
    )

    return {
        "desde": start.strftime("%Y-%m-%d"),
        "hasta": end.strftime("%Y-%m-%d"),
        "total_ingresos": round(ingresos, 2),
        "total_citas": total_citas,
        "completadas": completadas_count,
        "canceladas": canceladas_count,
        "ticket_promedio": round(ticket_promedio, 2),
        "pacientes_nuevos": pacientes_nuevos,
        "top_servicios": top_servicios,
        "rendimiento_terapeutas": rendimiento_terapeutas,
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
        # Campos de pago (crédito / parcial / total)
        "monto_total": float(appointment.monto_total) if appointment.monto_total is not None else None,
        "total_pagado": float(appointment.total_pagado) if appointment.total_pagado is not None else 0.0,
        "descuento_total": float(appointment.descuento_total) if appointment.descuento_total is not None else 0.0,
        "estado_pago": appointment.estado_pago or "unpaid",
    }

# ============================================================
# Items (multi-servicio)
# ============================================================

def sync_item_from_service(
    db: Session,
    appointment: Appointment,
    service: Optional[Service] = None,
) -> AppointmentItem:
    """
    Garantiza que la cita tenga al menos un item correspondiente al
    servicio principal (compatibilidad: la UI/envío de citas sigue
    usando service_id de cabecera; los items son la fuente de cálculo
    del precio cuando existen).
    """
    from ..models.appointment_item import AppointmentItem

    svc = service or (
        db.query(Service).filter(Service.id == appointment.service_id).first()
    )
    if not svc:
        return None

    item = (
        db.query(AppointmentItem)
        .filter(
            AppointmentItem.tenant_id == str(appointment.tenant_id),
            AppointmentItem.appointment_id == appointment.id,
            AppointmentItem.is_active == True,
            AppointmentItem.deleted_at == None,
        )
        .first()
    )
    if item:
        return item

    item = AppointmentItem(
        id=generate_uuid(),
        tenant_id=appointment.tenant_id,
        appointment_id=str(appointment.id),
        service_id=str(svc.id),
        nombre_snapshot=svc.nombre,
        precio_unitario=svc.precio or Decimal("0.00"),
        cantidad=1,
        descuento=Decimal("0.00"),
        subtotal=(svc.precio or Decimal("0.00")),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def add_item(
    db: Session,
    tenant_id: str,
    appointment: Appointment,
    service_id: str,
    cantidad: int = 1,
    descuento: Decimal = Decimal("0.00"),
) -> AppointmentItem:
    """Agrega un servicio (item) adicional a la cita."""
    from ..models.appointment_item import AppointmentItem

    service = db.query(Service).filter(
        Service.id == service_id,
        Service.tenant_id == tenant_id,
        Service.deleted_at == None,
    ).first()
    if not service:
        raise ValueError("Servicio no válido para este SPA")

    unit = service.precio or Decimal("0.00")
    subtotal = unit * cantidad - descuento
    item = AppointmentItem(
        id=generate_uuid(),
        tenant_id=tenant_id,
        appointment_id=str(appointment.id),
        service_id=str(service.id),
        nombre_snapshot=service.nombre,
        precio_unitario=unit,
        cantidad=cantidad,
        descuento=descuento,
        subtotal=subtotal,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    _recalc_monto(db, appointment)
    return item


def list_items(db: Session, tenant_id: str, appointment_id: str) -> list:
    from ..models.appointment_item import AppointmentItem

    return (
        db.query(AppointmentItem)
        .filter(
            AppointmentItem.tenant_id == tenant_id,
            AppointmentItem.appointment_id == appointment_id,
            AppointmentItem.is_active == True,
            AppointmentItem.deleted_at == None,
        )
        .order_by(AppointmentItem.created_at.asc())
        .all()
    )


def remove_item(db: Session, tenant_id: str, item_id: str, appointment_id: str):
    from ..models.appointment_item import AppointmentItem

    item = db.query(AppointmentItem).filter(
        AppointmentItem.id == item_id,
        AppointmentItem.tenant_id == tenant_id,
        AppointmentItem.appointment_id == appointment_id,
        AppointmentItem.deleted_at == None,
    ).first()
    if not item:
        return False
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.tenant_id == tenant_id,
        Appointment.deleted_at == None,
    ).first()
    if not appointment:
        return False
    item.soft_delete()
    db.commit()
    _recalc_monto(db, appointment)
    return True


def _recalc_monto(db: Session, appointment: Appointment):
    """Recalcula monto_total, descuento_total y estado_pago de la cita."""
    from sqlalchemy import func as sa_func
    from ..models.appointment_item import AppointmentItem
    from ..models.appointment import Appointment

    items = db.query(AppointmentItem).filter(
        AppointmentItem.appointment_id == appointment.id,
        AppointmentItem.tenant_id == appointment.tenant_id,
        AppointmentItem.is_active == True,
        AppointmentItem.deleted_at == None,
    ).all()

    monto_total = sum((i.subtotal for i in items), Decimal("0.00")) if items else (appointment.precio or Decimal("0.00"))
    descuento_total = sum((i.descuento for i in items), Decimal("0.00")) if items else (appointment.descuento_total or Decimal("0.00"))

    pagado_sum = (
        db.query(sa_func.coalesce(sa_func.sum(AppointmentPayment.monto), 0))
        .filter(
            AppointmentPayment.appointment_id == appointment.id,
            AppointmentPayment.tenant_id == appointment.tenant_id,
            AppointmentPayment.is_active == True,
            AppointmentPayment.deleted_at == None,
        )
        .scalar()
    )
    total_pagado = Decimal(str(pagado_sum or 0))

    appointment.monto_total = monto_total
    appointment.descuento_total = descuento_total
    appointment.total_pagado = total_pagado

    if monto_total is not None and total_pagado >= monto_total:
        appointment.estado_pago = "paid"
    elif total_pagado > 0:
        appointment.estado_pago = "partial"
    else:
        appointment.estado_pago = "unpaid"
    db.commit()
    db.refresh(appointment)


# ============================================================
# Pagos
# ============================================================

def register_payment(
    db: Session,
    tenant_id: str,
    appointment_id: str,
    monto: Decimal,
    metodo_pago: str = "efectivo",
    descuento: Decimal = Decimal("0.00"),
    observaciones: Optional[str] = None,
    user_id: Optional[str] = None,
) -> AppointmentPayment:
    """Registra un pago y actualiza estado_pago (crédito permitido)."""
    from ..models.appointment_item import AppointmentPayment

    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.tenant_id == tenant_id,
        Appointment.deleted_at == None,
    ).first()
    if not appointment:
        raise ValueError("Cita no encontrada")

    payment = AppointmentPayment(
        id=generate_uuid(),
        tenant_id=tenant_id,
        appointment_id=appointment_id,
        monto=monto,
        metodo_pago=metodo_pago,
        descuento=descuento,
        observaciones=observaciones,
        created_by=user_id,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    _recalc_monto(db, appointment)
    return payment


def list_payments(db: Session, tenant_id: str, appointment_id: str) -> list:
    from ..models.appointment_item import AppointmentPayment

    return (
        db.query(AppointmentPayment)
        .filter(
            AppointmentPayment.tenant_id == tenant_id,
            AppointmentPayment.appointment_id == appointment_id,
            AppointmentPayment.is_active == True,
            AppointmentPayment.deleted_at == None,
        )
        .order_by(AppointmentPayment.created_at.desc())
        .all()
    )


def cancel_payment(db: Session, tenant_id: str, appointment_id: str, payment_id: str) -> bool:
    """Anula un pago y recalcula el estado de pago (best-effort)."""
    from ..models.appointment_item import AppointmentPayment

    payment = db.query(AppointmentPayment).filter(
        AppointmentPayment.id == payment_id,
        AppointmentPayment.tenant_id == tenant_id,
        AppointmentPayment.appointment_id == appointment_id,
        AppointmentPayment.deleted_at == None,
    ).first()
    if not payment:
        return False
    appointment_id_p = payment.appointment_id
    payment.soft_delete()
    db.commit()

    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id_p,
        Appointment.tenant_id == tenant_id,
        Appointment.deleted_at == None,
    ).first()
    if appointment:
        _recalc_monto(db, appointment)
    return True


def payment_status(db: Session, tenant_id: str, appointment_id: str) -> dict:
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.tenant_id == tenant_id,
        Appointment.deleted_at == None,
    ).first()
    if not appointment:
        return None
    _recalc_monto(db, appointment)
    monto = appointment.monto_total or Decimal("0.00")
    pagado = appointment.total_pagado or Decimal("0.00")
    return {
        "appointment_id": str(appointment.id),
        "monto_total": appointment.monto_total,
        "total_pagado": appointment.total_pagado,
        "descuento_total": appointment.descuento_total,
        "estado_pago": appointment.estado_pago,
        "saldo_pendiente": (monto - pagado) if monto > 0 else Decimal("0.00"),
    }
