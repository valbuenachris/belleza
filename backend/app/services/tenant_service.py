# ============================================================
# backend/app/services/tenant_service.py - Lógica de negocio de Tenants
# CRUD y operaciones de tenants (SPAs)
# ============================================================

import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.tenant import Tenant
from ..models.user import User
from ..schemas.tenant import TenantCreate, TenantUpdate
from ..utils.security import generate_uuid

logger = logging.getLogger(__name__)


# ============================================================
# Crear tenant
# ============================================================

def create_tenant(db: Session, tenant_data: TenantCreate) -> Tenant:
    """
    Crea un nuevo tenant validando subdominio único.
    
    Args:
        db: Sesión de base de datos
        tenant_data: Datos del tenant a crear
        
    Returns:
        Tenant creado
        
    Raises:
        ValueError: Si el subdominio ya existe
    """
    # Verificar subdominio único
    if not validate_subdomain_available(db, tenant_data.subdominio):
        raise ValueError(f"El subdominio '{tenant_data.subdominio}' ya está en uso")
    
    tenant = Tenant(
        id=generate_uuid(),
        nombre=tenant_data.nombre,
        subdominio=tenant_data.subdominio.lower(),
        plan=tenant_data.plan,
        limite_usuarios=tenant_data.limite_usuarios,
        limite_pacientes=tenant_data.limite_pacientes,
        email=tenant_data.email,
        telefono=tenant_data.telefono,
        direccion=tenant_data.direccion,
        timezone=tenant_data.timezone,
        moneda=tenant_data.moneda,
        is_active=True,
    )
    
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    
    logger.info(f"Tenant creado: {tenant.nombre} ({tenant.id})")
    return tenant


# ============================================================
# Obtener tenant
# ============================================================

def get_tenant_by_id(db: Session, tenant_id: str) -> Optional[Tenant]:
    """
    Obtiene un tenant por su ID.
    """
    return db.query(Tenant).filter(
        Tenant.id == tenant_id,
        Tenant.deleted_at == None,
    ).first()


def get_tenant_by_subdomain(db: Session, subdomain: str) -> Optional[Tenant]:
    """
    Obtiene un tenant por su subdominio.
    """
    return db.query(Tenant).filter(
        Tenant.subdominio == subdomain.lower(),
        Tenant.deleted_at == None,
    ).first()


# ============================================================
# Listar tenants con paginación
# ============================================================

def list_tenants(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    plan: Optional[str] = None,
    activo: Optional[bool] = None,
    search: Optional[str] = None,
) -> List[Tenant]:
    """
    Lista tenants con paginación y filtros opcionales.
    
    Args:
        db: Sesión de base de datos
        skip: Número de registros a saltar
        limit: Máximo de registros a retornar
        plan: Filtrar por plan
        activo: Filtrar por estado activo
        search: Buscar por nombre o subdominio
        
    Returns:
        Lista de tenants
    """
    query = db.query(Tenant).filter(Tenant.deleted_at == None)
    
    if plan:
        query = query.filter(Tenant.plan == plan)
    
    if activo is not None:
        query = query.filter(Tenant.is_active == activo)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Tenant.nombre.ilike(search_pattern)) |
            (Tenant.subdominio.ilike(search_pattern))
        )
    
    return query.order_by(Tenant.fecha_creacion.desc()).offset(skip).limit(limit).all()


def count_tenants(
    db: Session,
    plan: Optional[str] = None,
    activo: Optional[bool] = None,
) -> int:
    """Cuenta el total de tenants con filtros opcionales."""
    query = db.query(func.count(Tenant.id)).filter(Tenant.deleted_at == None)
    
    if plan:
        query = query.filter(Tenant.plan == plan)
    if activo is not None:
        query = query.filter(Tenant.is_active == activo)
    
    return query.scalar() or 0


# ============================================================
# Actualizar tenant
# ============================================================

def update_tenant(db: Session, tenant_id: str, tenant_data: TenantUpdate) -> Optional[Tenant]:
    """
    Actualiza los datos de un tenant.
    
    Args:
        db: Sesión de base de datos
        tenant_id: ID del tenant a actualizar
        tenant_data: Datos a actualizar (solo campos no None)
        
    Returns:
        Tenant actualizado o None si no existe
    """
    tenant = get_tenant_by_id(db, tenant_id)
    if not tenant:
        return None
    
    # Actualizar solo los campos proporcionados
    update_data = tenant_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)
    
    db.commit()
    db.refresh(tenant)
    
    logger.info(f"Tenant actualizado: {tenant.nombre} ({tenant.id})")
    return tenant


# ============================================================
# Eliminar tenant (soft delete)
# ============================================================

def delete_tenant(db: Session, tenant_id: str) -> bool:
    """
    Elimina un tenant de forma lógica (soft delete).
    
    Args:
        db: Sesión de base de datos
        tenant_id: ID del tenant a eliminar
        
    Returns:
        True si se eliminó correctamente, False si no existe
    """
    tenant = get_tenant_by_id(db, tenant_id)
    if not tenant:
        return False
    
    tenant.soft_delete()
    db.commit()
    
    logger.info(f"Tenant eliminado (soft delete): {tenant.nombre} ({tenant.id})")
    return True


# ============================================================
# Validación de subdominio
# ============================================================

def validate_subdomain_available(db: Session, subdomain: str) -> bool:
    """
    Verifica si un subdominio está disponible.
    
    Args:
        db: Sesión de base de datos
        subdomain: Subdominio a verificar
        
    Returns:
        True si está disponible, False si ya está en uso
    """
    existing = db.query(Tenant).filter(
        Tenant.subdominio == subdomain.lower(),
        Tenant.deleted_at == None,
    ).first()
    return existing is None


# ============================================================
# Estadísticas del tenant
# ============================================================

def get_tenant_stats(db: Session, tenant_id: str) -> Dict[str, Any]:
    """
    Obtiene estadísticas de un tenant.
    
    Args:
        db: Sesión de base de datos
        tenant_id: ID del tenant
        
    Returns:
        Diccionario con estadísticas
    """
    # Contar usuarios activos
    total_usuarios = db.query(func.count(User.id)).filter(
        User.tenant_id == tenant_id,
        User.is_active == True,
        User.deleted_at == None,
    ).scalar() or 0
    
    # Contar usuarios por rol
    usuarios_por_rol = dict(
        db.query(User.rol, func.count(User.id))
        .filter(User.tenant_id == tenant_id, User.is_active == True)
        .group_by(User.rol)
        .all()
    )
    
    return {
        "total_usuarios": total_usuarios,
        "usuarios_por_rol": usuarios_por_rol,
    }
