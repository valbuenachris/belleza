# ============================================================
# backend/app/routers/appointments.py - Endpoints de Citas
# CRUD de citas con anti-doble reserva y aislamiento por tenant
# ============================================================

import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, get_current_tenant_id
from ..models.user import User
from ..schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentItemCreate,
    AppointmentPaymentCreate,
)
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

# ============================================================
# Pagos de una cita (crédito / parcial / total)
# ============================================================

@router.get(
    "/{appointment_id}/payments",
    summary="Historial de pagos de una cita",
    description="Lista los pagos registrados de una cita.",
)
def list_payments(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    appointment = appointment_service.get_appointment_by_id(db, tenant_id, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    payments = appointment_service.list_payments(db, tenant_id, appointment_id)
    return {
        "appointment_id": appointment_id,
        "payments": [
            {
                "id": str(p.id),
                "appointment_id": str(p.appointment_id),
                "monto": float(p.monto),
                "metodo_pago": p.metodo_pago,
                "descuento": float(p.descuento or 0),
                "observaciones": p.observaciones,
                "created_at": p.created_at,
            }
            for p in payments
        ],
    }


@router.post(
    "/{appointment_id}/payments",
    summary="Registrar pago de una cita",
    description=(
        "Registra un pago (total o parcial/crédito). Acepta descuentos y "
        "ajustes al precio. Si el saldo queda en parcial, la cita puede "
        "atenderse (crédito)."
    ),
)
def register_payment(
    appointment_id: str,
    body: AppointmentPaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        payment = appointment_service.register_payment(
            db,
            tenant_id,
            appointment_id,
            monto=body.monto,
            metodo_pago=body.metodo_pago,
            descuento=body.descuento if body.descuento is not None else Decimal("0.00"),
            observaciones=body.observaciones,
            user_id=str(current_user.id),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {
        "message": "Pago registrado",
        "payment": {
            "id": str(payment.id),
            "appointment_id": str(payment.appointment_id),
            "monto": float(payment.monto),
            "metodo_pago": payment.metodo_pago,
            "descuento": float(payment.descuento or 0),
            "observaciones": payment.observaciones,
            "created_at": payment.created_at,
        },
        "status": appointment_service.payment_status(db, tenant_id, appointment_id),
    }


@router.delete(
    "/{appointment_id}/payments/{payment_id}",
    summary="Anular pago de una cita",
    description="Anula (soft delete) un pago y recalcula saldo y estado.",
)
def cancel_payment(
    appointment_id: str,
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    ok = appointment_service.cancel_payment(db, tenant_id, appointment_id, payment_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")
    return {"message": "Pago anulado", "status": appointment_service.payment_status(db, tenant_id, appointment_id)}


@router.get(
    "/{appointment_id}/payment-status",
    summary="Estado de pago de una cita",
    description="Devuelve monto total, pagado y saldo.",
)
def payment_status(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    status = appointment_service.payment_status(db, tenant_id, appointment_id)
    if not status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    return status


# ============================================================
# Ítems de cita (multi-servicio)
# ============================================================

@router.get(
    "/{appointment_id}/items",
    summary="Servicios de una cita",
    description="Lista los servicios (items) de una cita.",
)
def list_items(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    items = appointment_service.list_items(db, tenant_id, appointment_id)
    return {
        "appointment_id": appointment_id,
        "items": [
            {
                "id": str(i.id),
                "appointment_id": str(i.appointment_id),
                "service_id": str(i.service_id),
                "nombre_snapshot": i.nombre_snapshot,
                "precio_unitario": float(i.precio_unitario),
                "cantidad": i.cantidad,
                "descuento": float(i.descuento or 0),
                "subtotal": float(i.subtotal),
            }
            for i in items
        ],
    }


@router.post(
    "/{appointment_id}/items",
    summary="Agregar servicio a una cita",
    description="Agrega un servicio adicional a una cita existente (multi-servicio).",
)
def add_item(
    appointment_id: str,
    body: AppointmentItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    appointment = appointment_service.get_appointment_by_id(db, tenant_id, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    try:
        item = appointment_service.add_item(
            db,
            tenant_id,
            appointment,
            service_id=body.service_id,
            cantidad=body.cantidad,
            descuento=body.descuento if body.descuento is not None else Decimal("0.00"),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"message": "Servicio agregado a la cita", "item": {"id": str(item.id), "nombre": item.nombre_snapshot}}


@router.delete(
    "/{appointment_id}/items/{item_id}",
    summary="Quitar servicio de una cita",
    description="Elimina un servicio de una cita.",
)
def remove_item(
    appointment_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    ok = appointment_service.remove_item(db, tenant_id, item_id, appointment_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ítem no encontrado")
    return {"message": "Servicio eliminado de la cita", "status": appointment_service.payment_status(db, tenant_id, appointment_id)}
