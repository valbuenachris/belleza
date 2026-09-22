# ============================================================
# backend/app/services/patient_service.py - Lógica de negocio de Pacientes
# CRUD y operaciones de pacientes del SPA
# ============================================================

import logging
from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func, select, or_

from ..models.patient import Patient
from ..models.appointment import Appointment
from ..schemas.patient import PatientCreate, PatientUpdate
from ..utils.security import generate_uuid

logger = logging.getLogger(__name__)


# ============================================================
# Crear paciente
# ============================================================

def create_patient(db: Session, tenant_id: str, patient_data: PatientCreate) -> Patient:
    """
    Crea un nuevo paciente para el tenant indicado.
    
    Args:
        db: Sesión de base de datos
        tenant_id: ID del tenant (de request.state.tenant_id)
        patient_data: Datos del paciente
        
    Returns:
        Patient creado
        
    Raises:
        ValueError: Si el email ya existe en este tenant
    """
    if patient_data.email:
        existing = db.query(Patient).filter(
            Patient.tenant_id == tenant_id,
            Patient.email == patient_data.email.lower(),
            Patient.deleted_at == None,
        ).first()
        if existing:
            raise ValueError("Ya existe un paciente con este email")

    patient = Patient(
        id=generate_uuid(),
        tenant_id=tenant_id,
        nombre=patient_data.nombre.strip(),
        apellido=patient_data.apellido.strip(),
        email=patient_data.email.lower() if patient_data.email else None,
        telefono=patient_data.telefono,
        fecha_nacimiento=patient_data.fecha_nacimiento,
        genero=patient_data.genero,
        direccion=patient_data.direccion,
        notas_medicas=patient_data.notas_medicas,
        is_active=True,
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)

    logger.info(f"Paciente creado: {patient.nombre_completo} ({patient.id})")
    return patient


# ============================================================
# Obtener paciente
# ============================================================

def get_patient_by_id(db: Session, tenant_id: str, patient_id: str) -> Optional[Patient]:
    """
    Obtiene un paciente por su ID (filtrado por tenant).
    """
    return db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.tenant_id == tenant_id,
        Patient.deleted_at == None,
    ).first()


# ============================================================
# Listar pacientes con paginación y búsqueda
# ============================================================

def list_patients(
    db: Session,
    tenant_id: str,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    activo: Optional[bool] = None,
) -> List[Patient]:
    """
    Lista pacientes del tenant con paginación y filtros.
    
    Args:
        db: Sesión de base de datos
        tenant_id: ID del tenant
        skip: Registros a saltar
        limit: Máximo de registros
        search: Búsqueda por nombre, apellido, email o teléfono
        activo: Filtrar por estado activo
        
    Returns:
        Lista de pacientes
    """
    query = db.query(Patient).filter(
        Patient.tenant_id == tenant_id,
        Patient.deleted_at == None,
    )

    if activo is not None:
        query = query.filter(Patient.is_active == activo)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Patient.nombre.ilike(pattern),
                Patient.apellido.ilike(pattern),
                Patient.email.ilike(pattern),
                Patient.telefono.ilike(pattern),
            )
        )

    # Ordenar por apellido y nombre
    return query.order_by(Patient.apellido.asc(), Patient.nombre.asc()).offset(skip).limit(limit).all()


def count_patients(
    db: Session,
    tenant_id: str,
    search: Optional[str] = None,
    activo: Optional[bool] = None,
) -> int:
    """Cuenta el total de pacientes del tenant con filtros opcionales."""
    query = db.query(func.count(Patient.id)).filter(
        Patient.tenant_id == tenant_id,
        Patient.deleted_at == None,
    )

    if activo is not None:
        query = query.filter(Patient.is_active == activo)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Patient.nombre.ilike(pattern),
                Patient.apellido.ilike(pattern),
                Patient.email.ilike(pattern),
                Patient.telefono.ilike(pattern),
            )
        )

    return query.scalar() or 0


# ============================================================
# Actualizar paciente
# ============================================================

def update_patient(
    db: Session,
    tenant_id: str,
    patient_id: str,
    patient_data: PatientUpdate,
) -> Optional[Patient]:
    """
    Actualiza los datos de un paciente.
    
    Raises:
        ValueError: Si el email nuevo ya existe en otro paciente del tenant
    """
    patient = get_patient_by_id(db, tenant_id, patient_id)
    if not patient:
        return None

    update_data = patient_data.model_dump(exclude_unset=True)

    # Evitar duplicado de email
    new_email = update_data.get("email")
    if new_email:
        new_email = new_email.lower()
        existing = db.query(Patient).filter(
            Patient.tenant_id == tenant_id,
            Patient.email == new_email,
            Patient.id != patient_id,
            Patient.deleted_at == None,
        ).first()
        if existing:
            raise ValueError("Ya existe otro paciente con este email")
        update_data["email"] = new_email

    if "activo" in update_data:
        update_data["is_active"] = update_data.pop("activo")

    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)

    logger.info(f"Paciente actualizado: {patient.nombre_completo} ({patient.id})")
    return patient


# ============================================================
# Eliminar paciente (soft delete)
# ============================================================

def delete_patient(db: Session, tenant_id: str, patient_id: str) -> bool:
    """
    Elimina un paciente de forma lógica (soft delete).
    """
    patient = get_patient_by_id(db, tenant_id, patient_id)
    if not patient:
        return False

    patient.soft_delete()
    db.commit()

    logger.info(f"Paciente eliminado (soft delete): {patient.nombre_completo} ({patient.id})")
    return True


# ============================================================
# Estadísticas por paciente (para el listado de la UI)
# ============================================================

def get_patient_stats(db: Session, tenant_id: str, patient_id: str) -> dict:
    """
    Calcula total_citas y ultima_cita de un paciente.
    
    Returns:
        dict con total_citas (int) y ultima_cita (str ISO o None)
    """
    rows = db.query(
        func.count(Appointment.id),
        func.max(Appointment.date_time),
    ).filter(
        Appointment.patient_id == patient_id,
        Appointment.tenant_id == tenant_id,
        Appointment.deleted_at == None,
    ).first()

    total_citas = rows[0] or 0
    ultima_cita = rows[1].isoformat() if rows[1] else None

    return {
        "total_citas": total_citas,
        "ultima_cita": ultima_cita,
    }


def build_patient_response(patient: Patient, stats: Optional[dict] = None) -> dict:
    """
    Construye el diccionario de respuesta con los campos esperados por la UI.
    """
    data = {
        "id": str(patient.id),
        "tenant_id": str(patient.tenant_id),
        "nombre": patient.nombre,
        "apellido": patient.apellido,
        "email": patient.email,
        "telefono": patient.telefono,
        "fecha_nacimiento": patient.fecha_nacimiento.isoformat() if patient.fecha_nacimiento else None,
        "genero": patient.genero,
        "direccion": patient.direccion,
        "notas_medicas": patient.notas_medicas,
        "activo": patient.is_active,
        "puntos": patient.puntos or 0,
        "sesiones_gratis": patient.sesiones_gratis or 0,
        "wallet_pass_id": patient.wallet_pass_id,
        "created_at": patient.created_at.isoformat() if patient.created_at else None,
    }
    if stats:
        data["total_citas"] = stats.get("total_citas", 0)
        data["ultima_cita"] = stats.get("ultima_cita")
    return data