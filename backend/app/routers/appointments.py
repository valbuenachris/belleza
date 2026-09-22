# ============================================================
# backend/app/routers/appointments.py - Endpoints de Citas
# CRUD de citas con anti-doble reserva y aislamiento por tenant
# ============================================================

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, get_current_tenant_id
from ..models.user import User
from ..schemas.appointment import AppointmentCreate, AppointmentUpdate
from ..services import appointment_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/appointments", tags=["Citas"])


# ============================================================
# GET /api/v1/appointments - Listar citas
# ============================================================

@router.get(
    "",
    summary="Listar citas",
    description="Lista citas del SPA con filtros opcionales por fecha y estado.",
)
def list_appointments(
    skip: int = 0,
    limit: int = 100,
    fecha: Optional[str] = None,
    estado: Optional[str] = None,
    patient_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        appointments = appointment_service.list_appointments(
            db, tenant_id, skip=skip, limit=limit, fecha=fecha, estado=estado, patient_id=patient_id
        )
        total = appointment_service.count_appointments(
            db, tenant_id, fecha=fecha, estado=estado, patient_id=patient_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    items = [appointment_service.build_appointment_response(a) for a in appointments]
    return {"appointments": items, "total": total}


# ============================================================
# GET /api/v1/appointments/stats/summary - Estadísticas
# ============================================================

@router.get(
    "/stats/summary",
    summary="Resumen de citas",
    description="Estadísticas para el dashboard (hoy, pendientes, ingresos).",
)
def get_appointment_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    return appointment_service.get_appointment_summary(db, tenant_id)


# ============================================================
# GET /api/v1/appointments/stats/financial - Reporte financiero
# ============================================================

@router.get(
    "/stats/financial",
    summary="Reporte financiero y de rendimiento",
    description=(
        "KPIs (ingresos, citas, ticket promedio, pacientes nuevos), top servicios "
        "y rendimiento por terapeuta en un rango de fechas."
    ),
)
def get_financial_report(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        return appointment_service.get_financial_report(db, tenant_id, desde=desde, hasta=hasta)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# GET /api/v1/appointments/{id} - Obtener cita
# ============================================================

@router.get(
    "/{appointment_id}",
    summary="Obtener cita",
    description="Retorna una cita específica del SPA.",
)
def get_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    appointment = appointment_service.get_appointment_by_id(db, tenant_id, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada",
        )
    return appointment_service.build_appointment_response(appointment)


# ============================================================
# POST /api/v1/appointments - Crear cita (con anti-doble reserva)
# ============================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crear cita",
    description=(
        "Agenda una nueva cita validando que el terapeuta y el paciente "
        "no tengan otra cita en el mismo horario (anti-doble reserva)."
    ),
)
def create_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        appointment = appointment_service.create_appointment(db, tenant_id, appointment_data)
        return {
            "message": "Cita creada exitosamente",
            "appointment": appointment_service.build_appointment_response(appointment),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# PUT /api/v1/appointments/{id} - Actualizar cita
# ============================================================

@router.put(
    "/{appointment_id}",
    summary="Actualizar cita",
    description="Actualiza una cita re-validando la disponibilidad de horario.",
)
def update_appointment(
    appointment_id: str,
    appointment_data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        appointment = appointment_service.update_appointment(
            db, tenant_id, appointment_id, appointment_data
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada",
        )
    return {
        "message": "Cita actualizada exitosamente",
        "appointment": appointment_service.build_appointment_response(appointment),
    }


# ============================================================
# DELETE /api/v1/appointments/{id} - Cancelar cita
# ============================================================

@router.delete(
    "/{appointment_id}",
    summary="Cancelar cita",
    description="Cancela una cita (estado = cancelled, libera el horario).",
)
def delete_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    appointment = appointment_service.cancel_appointment(db, tenant_id, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada",
        )
    return {
        "message": "Cita cancelada exitosamente",
        "appointment": appointment_service.build_appointment_response(appointment),
    }