# ============================================================
# backend/app/services/service_service.py - Lógica de negocio de Servicios
# CRUD del catálogo de servicios del SPA
# ============================================================

import logging
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from ..models.service import Service
from ..schemas.service import ServiceCreate, ServiceUpdate
from ..utils.security import generate_uuid

logger = logging.getLogger(__name__)


# ============================================================
# Crear servicio
# ============================================================

def create_service(db: Session, tenant_id: str, service_data: ServiceCreate) -> Service:
    """
    Crea un nuevo servicio para el tenant indicado.
    
    Raises:
        ValueError: Si ya existe un servicio con el mismo nombre en el tenant
    """
    existing = db.query(Service).filter(
        Service.tenant_id == tenant_id,
        Service.nombre == service_data.nombre.strip(),
        Service.deleted_at == None,
    ).first()
    if existing:
        raise ValueError("Ya existe un servicio con este nombre")

    service = Service(
        id=generate_uuid(),
        tenant_id=tenant_id,
        nombre=service_data.nombre.strip(),
        descripcion=service_data.descripcion,
        precio=service_data.precio,
        duracion=service_data.duracion,
        is_active=True,
    )

    db.add(service)
    db.commit()
    db.refresh(service)

    logger.info(f"Servicio creado: {service.nombre} ({service.id})")
    return service


# ============================================================
# Obtener servicio
# ============================================================

def get_service_by_id(db: Session, tenant_id: str, service_id: str) -> Optional[Service]:
    """
    Obtiene un servicio por su ID (filtrado por tenant).
    """
    return db.query(Service).filter(
        Service.id == service_id,
        Service.tenant_id == tenant_id,
        Service.deleted_at == None,
    ).first()


# ============================================================
# Listar servicios
# ============================================================

def list_services(
    db: Session,
    tenant_id: str,
    skip: int = 0,
    limit: int = 100,
    activo: Optional[bool] = None,
    search: Optional[str] = None,
) -> List[Service]:
    """
    Lista servicios del tenant con paginación y filtros opcionales.
    """
    query = db.query(Service).filter(
        Service.tenant_id == tenant_id,
        Service.deleted_at == None,
    )

    if activo is not None:
        query = query.filter(Service.is_active == activo)

    if search:
        pattern = f"%{search}%"
        query = query.filter(Service.nombre.ilike(pattern))

    return query.order_by(Service.nombre.asc()).offset(skip).limit(limit).all()


def count_services(
    db: Session,
    tenant_id: str,
    activo: Optional[bool] = None,
) -> int:
    """Cuenta el total de servicios del tenant."""
    query = db.query(func.count(Service.id)).filter(
        Service.tenant_id == tenant_id,
        Service.deleted_at == None,
    )
    if activo is not None:
        query = query.filter(Service.is_active == activo)
    return query.scalar() or 0


# ============================================================
# Actualizar servicio
# ============================================================

def update_service(
    db: Session,
    tenant_id: str,
    service_id: str,
    service_data: ServiceUpdate,
) -> Optional[Service]:
    """
    Actualiza los datos de un servicio.
    """
    service = get_service_by_id(db, tenant_id, service_id)
    if not service:
        return None

    update_data = service_data.model_dump(exclude_unset=True)

    # Evitar duplicado de nombre
    new_nombre = update_data.get("nombre")
    if new_nombre:
        new_nombre = new_nombre.strip()
        existing = db.query(Service).filter(
            Service.tenant_id == tenant_id,
            Service.nombre == new_nombre,
            Service.id != service_id,
            Service.deleted_at == None,
        ).first()
        if existing:
            raise ValueError("Ya existe otro servicio con este nombre")
        update_data["nombre"] = new_nombre

    if "activo" in update_data:
        update_data["is_active"] = update_data.pop("activo")

    for field, value in update_data.items():
        setattr(service, field, value)

    db.commit()
    db.refresh(service)

    logger.info(f"Servicio actualizado: {service.nombre} ({service.id})")
    return service


# ============================================================
# Eliminar servicio (soft delete)
# ============================================================

def delete_service(db: Session, tenant_id: str, service_id: str) -> bool:
    """
    Elimina un servicio de forma lógica (soft delete).
    """
    service = get_service_by_id(db, tenant_id, service_id)
    if not service:
        return False

    service.soft_delete()
    db.commit()

    logger.info(f"Servicio eliminado (soft delete): {service.nombre} ({service.id})")
    return True