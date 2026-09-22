# ============================================================
# backend/app/routers/patients.py - Endpoints de Pacientes
# CRUD completo de pacientes con aislamiento por tenant
# ============================================================

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, get_current_tenant_id
from ..models.user import User
from ..schemas.patient import PatientCreate, PatientUpdate, PatientResponse
from ..services import patient_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/patients", tags=["Pacientes"])


# ============================================================
# GET /api/v1/patients - Listar pacientes
# ============================================================

@router.get(
    "",
    summary="Listar pacientes",
    description="Lista pacientes del SPA con búsqueda y paginación.",
)
def list_patients(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    activo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    patients = patient_service.list_patients(
        db, tenant_id, skip=skip, limit=limit, search=search, activo=activo
    )
    total = patient_service.count_patients(db, tenant_id, search=search, activo=activo)

    items = []
    for p in patients:
        stats = patient_service.get_patient_stats(db, tenant_id, str(p.id))
        items.append(patient_service.build_patient_response(p, stats))

    return {"patients": items, "total": total}


# ============================================================
# GET /api/v1/patients/{id} - Obtener un paciente
# ============================================================

@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Obtener paciente",
    description="Retorna los datos de un paciente específico del SPA.",
)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    patient = patient_service.get_patient_by_id(db, tenant_id, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado",
        )
    stats = patient_service.get_patient_stats(db, tenant_id, patient_id)
    return patient_service.build_patient_response(patient, stats)


# ============================================================
# POST /api/v1/patients - Crear paciente
# ============================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crear paciente",
    description="Crea un nuevo paciente en el SPA.",
)
def create_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        patient = patient_service.create_patient(db, tenant_id, patient_data)
        return {
            "message": "Paciente creado exitosamente",
            "patient": patient_service.build_patient_response(patient, {"total_citas": 0, "ultima_cita": None}),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# PUT /api/v1/patients/{id} - Actualizar paciente
# ============================================================

@router.put(
    "/{patient_id}",
    summary="Actualizar paciente",
    description="Actualiza los datos de un paciente del SPA.",
)
def update_patient(
    patient_id: str,
    patient_data: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        patient = patient_service.update_patient(db, tenant_id, patient_id, patient_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado",
        )

    stats = patient_service.get_patient_stats(db, tenant_id, patient_id)
    return {
        "message": "Paciente actualizado exitosamente",
        "patient": patient_service.build_patient_response(patient, stats),
    }


# ============================================================
# DELETE /api/v1/patients/{id} - Eliminar paciente
# ============================================================

@router.delete(
    "/{patient_id}",
    summary="Eliminar paciente",
    description="Elimina un paciente (soft delete).",
)
def delete_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    deleted = patient_service.delete_patient(db, tenant_id, patient_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado",
        )
    return {"message": "Paciente eliminado exitosamente", "deleted": True}