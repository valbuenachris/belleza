# ============================================================
# backend/app/routers/services.py - Endpoints de Servicios
# CRUD del catálogo de servicios con aislamiento por tenant
# ============================================================

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, get_current_tenant_id
from ..models.user import User
from ..schemas.service import ServiceCreate, ServiceUpdate
from ..services import service_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/services", tags=["Servicios"])


# ============================================================
# GET /api/v1/services - Listar servicios
# ============================================================

@router.get(
    "",
    summary="Listar servicios",
    description="Lista el catálogo de servicios del SPA.",
)
def list_services(
    skip: int = 0,
    limit: int = 100,
    activo: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    services = service_service.list_services(
        db, tenant_id, skip=skip, limit=limit, activo=activo, search=search
    )
    total = service_service.count_services(db, tenant_id, activo=activo)

    items = []
    for s in services:
        items.append({
            "id": str(s.id),
            "tenant_id": str(s.tenant_id),
            "nombre": s.nombre,
            "descripcion": s.descripcion,
            "precio": float(s.precio) if s.precio is not None else None,
            "duracion": s.duracion,
            "activo": s.is_active,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    return {"services": items, "total": total}


# ============================================================
# GET /api/v1/services/{id} - Obtener servicio
# ============================================================

@router.get(
    "/{service_id}",
    summary="Obtener servicio",
    description="Retorna un servicio específico del SPA.",
)
def get_service(
    service_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    service = service_service.get_service_by_id(db, tenant_id, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return {
        "id": str(service.id),
        "tenant_id": str(service.tenant_id),
        "nombre": service.nombre,
        "descripcion": service.descripcion,
        "precio": float(service.precio) if service.precio is not None else None,
        "duracion": service.duracion,
        "activo": service.is_active,
        "created_at": service.created_at.isoformat() if service.created_at else None,
    }


# ============================================================
# POST /api/v1/services - Crear servicio
# ============================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crear servicio",
    description="Agrega un nuevo servicio al catálogo del SPA.",
)
def create_service(
    service_data: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        service = service_service.create_service(db, tenant_id, service_data)
        return {
            "message": "Servicio creado exitosamente",
            "service": {
                "id": str(service.id),
                "tenant_id": str(service.tenant_id),
                "nombre": service.nombre,
                "descripcion": service.descripcion,
                "precio": float(service.precio) if service.precio is not None else None,
                "duracion": service.duracion,
                "activo": service.is_active,
                "created_at": service.created_at.isoformat() if service.created_at else None,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# PUT /api/v1/services/{id} - Actualizar servicio
# ============================================================

@router.put(
    "/{service_id}",
    summary="Actualizar servicio",
    description="Actualiza los datos de un servicio del SPA.",
)
def update_service(
    service_id: str,
    service_data: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        service = service_service.update_service(db, tenant_id, service_id, service_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return {"message": "Servicio actualizado exitosamente", "service_id": str(service.id)}


# ============================================================
# DELETE /api/v1/services/{id} - Eliminar servicio
# ============================================================

@router.delete(
    "/{service_id}",
    summary="Eliminar servicio",
    description="Elimina un servicio (soft delete).",
)
def delete_service(
    service_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    deleted = service_service.delete_service(db, tenant_id, service_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return {"message": "Servicio eliminado exitosamente", "deleted": True}