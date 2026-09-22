# ============================================================
# backend/app/routers/clinical_records.py - Endpoints de Historia
# Clínica / Evoluciones
# GET/POST bajo /patients/{patient_id}/records y PUT/DELETE bajo
# /clinical-records/{record_id}. Aislamiento por tenant.
# ============================================================

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, get_current_tenant_id
from ..models.user import User
from ..schemas.clinical_record import (
    ClinicalRecordCreate, ClinicalRecordUpdate,
)
from ..services import clinical_record_service

logger = logging.getLogger(__name__)

# Router anidado bajo pacientes (listado y creación)
router = APIRouter(prefix="/patients", tags=["Historia Clínica"])
# Router de recursos individuales
record_router = APIRouter(prefix="/clinical-records", tags=["Historia Clínica"])


# ============================================================
# GET /api/v1/patients/{patient_id}/records - Listar evoluciones
# ============================================================

@router.get(
    "/{patient_id}/records",
    summary="Listar historia clínica de un paciente",
    description="Lista las evoluciones/sesiones de la historia clínica de un paciente.",
)
def list_patient_records(
    patient_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    records = clinical_record_service.list_records(
        db, tenant_id, patient_id=patient_id, skip=skip, limit=limit
    )
    total = clinical_record_service.count_records(db, tenant_id, patient_id=patient_id)

    items = [clinical_record_service.build_record_response(r) for r in records]
    return {"records": items, "total": total}


# ============================================================
# POST /api/v1/patients/{patient_id}/records - Crear evolución
# ============================================================

@router.post(
    "/{patient_id}/records",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar evolución clínica",
    description="Registra una nueva evolución/sesión en la historia clínica del paciente.",
)
def create_patient_record(
    patient_id: str,
    record_data: ClinicalRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        record = clinical_record_service.create_record(
            db, tenant_id, patient_id, record_data, current_user
        )
        return {
            "message": "Evolución registrada exitosamente",
            "record": clinical_record_service.build_record_response(record),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# PUT /api/v1/clinical-records/{record_id} - Actualizar evolución
# ============================================================

@record_router.put(
    "/{record_id}",
    summary="Actualizar evolución clínica",
    description="Actualiza los datos de una evolución de la historia clínica.",
)
def update_clinical_record(
    record_id: str,
    record_data: ClinicalRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        record = clinical_record_service.update_record(
            db, tenant_id, record_id, record_data
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro clínico no encontrado",
        )
    return {
        "message": "Evolución actualizada exitosamente",
        "record": clinical_record_service.build_record_response(record),
    }


# ============================================================
# DELETE /api/v1/clinical-records/{record_id} - Eliminar evolución
# ============================================================

@record_router.delete(
    "/{record_id}",
    summary="Eliminar evolución clínica",
    description="Elimina (soft delete) una evolución de la historia clínica.",
)
def delete_clinical_record(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    deleted = clinical_record_service.delete_record(db, tenant_id, record_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro clínico no encontrado",
        )
    return {"message": "Evolución eliminada exitosamente", "deleted": True}