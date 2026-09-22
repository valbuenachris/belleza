# ============================================================
# backend/app/services/clinical_record_service.py - Lógica de negocio
# de registros clínicos (historia clínica / evoluciones)
# CRUD estrictamente aislado por tenant
# ============================================================

import logging
from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.clinical_record import ClinicalRecord
from ..models.patient import Patient
from ..models.appointment import Appointment
from ..models.user import User
from ..schemas.clinical_record import ClinicalRecordCreate, ClinicalRecordUpdate
from ..utils.security import generate_uuid

logger = logging.getLogger(__name__)


# ============================================================
# Crear registro clínico
# ============================================================

def create_record(
    db: Session,
    tenant_id: str,
    patient_id: str,
    record_data: ClinicalRecordCreate,
    current_user: User,
) -> ClinicalRecord:
    """
    Crea una nueva evolución/sesión clínica para el paciente indicado.

    Valida que el paciente, el terapeuta y la cita pertenezcan al tenant.
    Si no se indica un terapeuta, se usa el usuario autenticado.

    Raises:
        ValueError: Si el paciente no existe en el tenant o las
            referencias opcionales no pertenecen al tenant/paciente.
    """
    # El paciente debe pertenecer al tenant
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.tenant_id == tenant_id,
        Patient.deleted_at == None,
    ).first()
    if not patient:
        raise ValueError("Paciente no encontrado en este SPA")

    therapist_id = record_data.therapist_id or str(current_user.id)

    # El terapeuta (si se indicó) debe pertenecer al tenant
    if record_data.therapist_id:
        therapist = db.query(User).filter(
            User.id == record_data.therapist_id,
            User.tenant_id == tenant_id,
            User.deleted_at == None,
        ).first()
        if not therapist:
            raise ValueError("Terapeuta no encontrado en este SPA")
        therapist_id = record_data.therapist_id

    # La cita asociada (si se indica) debe pertenecer al tenant y al paciente
    if record_data.appointment_id:
        appointment = db.query(Appointment).filter(
            Appointment.id == record_data.appointment_id,
            Appointment.tenant_id == tenant_id,
            Appointment.deleted_at == None,
        ).first()
        if not appointment:
            raise ValueError("Cita no encontrada en este SPA")
        if appointment.patient_id != patient_id:
            raise ValueError("La cita indicada no pertenece a este paciente")

    record = ClinicalRecord(
        id=generate_uuid(),
        tenant_id=tenant_id,
        patient_id=patient_id,
        therapist_id=therapist_id,
        appointment_id=record_data.appointment_id,
        fecha=record_data.fecha or datetime.utcnow(),
        zona_tratada=record_data.zona_tratada,
        tratamiento_servicio=record_data.tratamiento_servicio,
        productos_parametros=record_data.productos_parametros,
        observaciones=record_data.observaciones,
        diagnostico=record_data.diagnostico,
        is_active=True,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(
        f"Registro clínico creado para paciente {patient_id} por {current_user.email} ({record.id})"
    )
    return record


# ============================================================
# Obtener registro clínico
# ============================================================

def get_record(db: Session, tenant_id: str, record_id: str) -> Optional[ClinicalRecord]:
    """
    Obtiene un registro clínico por su ID (filtrado por tenant).
    """
    return db.query(ClinicalRecord).filter(
        ClinicalRecord.id == record_id,
        ClinicalRecord.tenant_id == tenant_id,
        ClinicalRecord.deleted_at == None,
    ).first()


# ============================================================
# Listar registros clínicos de un paciente
# ============================================================

def list_records(
    db: Session,
    tenant_id: str,
    patient_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[ClinicalRecord]:
    """
    Lista los registros clínicos del tenant. Si se pasa patient_id,
    filtra por ese paciente. Ordena por fecha descendente (más reciente primero).
    """
    query = db.query(ClinicalRecord).filter(
        ClinicalRecord.tenant_id == tenant_id,
        ClinicalRecord.deleted_at == None,
    )

    if patient_id:
        query = query.filter(ClinicalRecord.patient_id == patient_id)

    return query.order_by(ClinicalRecord.fecha.desc()).offset(skip).limit(limit).all()


def count_records(
    db: Session,
    tenant_id: str,
    patient_id: Optional[str] = None,
) -> int:
    """Cuenta los registros clínicos del tenant (con filtro opcional por paciente)."""
    query = db.query(func.count(ClinicalRecord.id)).filter(
        ClinicalRecord.tenant_id == tenant_id,
        ClinicalRecord.deleted_at == None,
    )

    if patient_id:
        query = query.filter(ClinicalRecord.patient_id == patient_id)

    return query.scalar() or 0


# ============================================================
# Actualizar registro clínico
# ============================================================

def update_record(
    db: Session,
    tenant_id: str,
    record_id: str,
    record_data: ClinicalRecordUpdate,
) -> Optional[ClinicalRecord]:
    """
    Actualiza un registro clínico del tenant.

    Raises:
        ValueError: Si las referencias opcionales no pertenecen al tenant.
    """
    record = get_record(db, tenant_id, record_id)
    if not record:
        return None

    update_data = record_data.model_dump(exclude_unset=True)

    # "activo" es una property de solo lectura en el modelo
    if "activo" in update_data:
        update_data["is_active"] = update_data.pop("activo")

    # Validar terapeuta si cambia (debe pertenecer al tenant)
    if "therapist_id" in update_data and update_data.get("therapist_id"):
        therapist = db.query(User).filter(
            User.id == update_data["therapist_id"],
            User.tenant_id == tenant_id,
            User.deleted_at == None,
        ).first()
        if not therapist:
            raise ValueError("Terapeuta no encontrado en este SPA")

    # Validar cita si cambia (debe pertenecer al tenant y al paciente)
    if "appointment_id" in update_data and update_data.get("appointment_id"):
        appointment = db.query(Appointment).filter(
            Appointment.id == update_data["appointment_id"],
            Appointment.tenant_id == tenant_id,
            Appointment.deleted_at == None,
        ).first()
        if not appointment:
            raise ValueError("Cita no encontrada en este SPA")
        if appointment.patient_id != record.patient_id:
            raise ValueError("La cita indicada no pertenece a este paciente")

    for field, value in update_data.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)

    logger.info(f"Registro clínico actualizado: {record.id}")
    return record


# ============================================================
# Eliminar registro clínico (soft delete)
# ============================================================

def delete_record(db: Session, tenant_id: str, record_id: str) -> bool:
    """
    Elimina un registro clínico de forma lógica (soft delete).
    """
    record = get_record(db, tenant_id, record_id)
    if not record:
        return False

    record.soft_delete()
    db.commit()

    logger.info(f"Registro clínico eliminado (soft delete): {record.id}")
    return True


# ============================================================
# Serialización
# ============================================================

def build_record_response(record: ClinicalRecord) -> dict:
    """
    Construye el diccionario de respuesta para la UI.
    """
    return {
        "id": str(record.id),
        "tenant_id": str(record.tenant_id),
        "patient_id": str(record.patient_id),
        "therapist_id": str(record.therapist_id) if record.therapist_id else None,
        "appointment_id": str(record.appointment_id) if record.appointment_id else None,
        "fecha": record.fecha.isoformat() if record.fecha else None,
        "zona_tratada": record.zona_tratada,
        "tratamiento_servicio": record.tratamiento_servicio,
        "productos_parametros": record.productos_parametros,
        "observaciones": record.observaciones,
        "diagnostico": record.diagnostico,
        "therapist_name": record.therapist_name,
        "patient_name": record.patient_name,
        "servicio": record.servicio,
        "activo": record.is_active,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }