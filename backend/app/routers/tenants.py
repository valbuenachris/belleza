# ============================================================
# backend/app/routers/tenants.py - Endpoints de gestión de Tenants
# CRUD de tenants (solo superadmin)
# ============================================================

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.tenant import (
    TenantCreate, TenantUpdate, TenantResponse, TenantListResponse,
)
from ..services.tenant_service import (
    create_tenant,
    get_tenant_by_id,
    list_tenants,
    count_tenants,
    update_tenant,
    delete_tenant,
    get_tenant_stats,
    get_global_stats,
)
from ..dependencies import get_superadmin, get_current_active_user, require_role
from ..models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenants", tags=["Tenants"])


# ============================================================
# POST /api/v1/tenants - Crear nuevo tenant
# ============================================================

@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo tenant",
    description=(
        "Crea un nuevo SPA/tenant en el sistema. Solo superadmin. "
        "El subdominio ya no es obligatorio (login universal por email); "
        "si no se envía, se auto-genera. "
        "Si se incluye 'admin' con las credenciales iniciales, se crea el "
        "usuario administrador del tenant vinculado vía tenant_id."
    ),
)
def create_new_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_superadmin),
):
    """
    Crea un nuevo tenant.
    
    Solo accesible para superadministradores.
    """
    try:
        tenant = create_tenant(db, tenant_data)
        logger.info(f"Tenant creado por {current_user.email}: {tenant.nombre}")
        return TenantResponse.model_validate(tenant)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================
# GET /api/v1/tenants - Listar todos los tenants
# ============================================================

@router.get(
    "",
    response_model=List[TenantListResponse],
    summary="Listar tenants",
    description="Lista todos los tenants con paginación y filtros. Solo superadmin.",
)
def get_tenants(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(20, ge=1, le=100, description="Máximo de registros"),
    plan: Optional[str] = Query(None, description="Filtrar por plan"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    search: Optional[str] = Query(None, description="Buscar por nombre o subdominio"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_superadmin),
):
    """
    Lista todos los tenants del sistema con paginación.
    
    Solo accesible para superadministradores.
    """
    tenants = list_tenants(
        db,
        skip=skip,
        limit=limit,
        plan=plan,
        activo=activo,
        search=search,
    )
    return [TenantListResponse.model_validate(t) for t in tenants]


# ============================================================
# GET /api/v1/tenants/count - Contar tenants
# ============================================================

@router.get(
    "/count",
    summary="Contar tenants",
    description="Retorna el número total de tenants. Solo superadmin.",
)
def get_tenants_count(
    plan: Optional[str] = Query(None),
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_superadmin),
):
    """Retorna el conteo total de tenants."""
    total = count_tenants(db, plan=plan, activo=activo)
    return {"total": total}


# ============================================================
# GET /api/v1/tenants/stats/global - Métricas globales
# ============================================================

@router.get(
    "/stats/global",
    summary="Métricas globales de la plataforma",
    description=(
        "KPIs globales para el superadmin: total de SPAs (activos y "
        "suspendidos), usuarios globales, MRR estimado y distribución "
        "por plan de suscripción."
    ),
)
def get_tenants_global_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_superadmin),
):
    """Retorna las métricas globales de la plataforma (solo superadmin)."""
    return get_global_stats(db)


# ============================================================
# GET /api/v1/tenants/{tenant_id} - Obtener tenant específico
# ============================================================

@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Obtener tenant",
    description="Retorna los datos de un tenant específico. Solo superadmin.",
)
def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_superadmin),
):
    """
    Obtiene los datos completos de un tenant por su ID.
    """
    tenant = get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )
    return TenantResponse.model_validate(tenant)


# ============================================================
# PUT /api/v1/tenants/{tenant_id} - Actualizar tenant
# ============================================================

@router.put(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Actualizar tenant",
    description=(
        "Actualiza los datos de un tenant. "
        "El superadmin puede cambiar cualquier campo; el admin del SPA solo "
        "los campos operativos (no plan, activación ni límites del plan)."
    ),
)
def update_existing_tenant(
    tenant_id: str,
    tenant_data: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Actualiza los datos de un tenant existente.

    Restricciones:
    - Solo superadmin o el admin del propio tenant.
    - Campos de suscripción (plan, activo, fecha_expiracion, limite_usuarios,
      limite_pacientes) son exclusivos del superadmin.
    """
    is_superadmin = current_user.rol == "superadmin"
    if not is_superadmin and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este SPA",
        )

    if not is_superadmin:
        campos_restrictivos = {
            "plan", "activo", "fecha_expiracion", "limite_usuarios", "limite_pacientes",
        }
        enviados = {
            k for k, v in tenant_data.model_dump(exclude_unset=True).items() if v is not None
        }
        conflicto = sorted(campos_restrictivos & enviados)
        if conflicto:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Solo el superadministrador puede modificar: "
                    + ", ".join(conflicto)
                ),
            )

    tenant = update_tenant(db, tenant_id, tenant_data)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )
    
    logger.info(f"Tenant actualizado por {current_user.email}: {tenant.nombre}")
    return TenantResponse.model_validate(tenant)


# ============================================================
# DELETE /api/v1/tenants/{tenant_id} - Soft delete
# ============================================================

@router.delete(
    "/{tenant_id}",
    summary="Eliminar tenant",
    description="Elimina un tenant de forma lógica (soft delete). Solo superadmin.",
)
def delete_existing_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_superadmin),
):
    """
    Elimina un tenant de forma lógica.
    
    El tenant no se borra físicamente, solo se marca como inactivo.
    """
    success = delete_tenant(db, tenant_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )
    
    logger.info(f"Tenant eliminado por {current_user.email}: {tenant_id}")
    return {"message": "Tenant eliminado exitosamente"}


# ============================================================
# GET /api/v1/tenants/{tenant_id}/stats - Estadísticas
# ============================================================

@router.get(
    "/{tenant_id}/stats",
    summary="Estadísticas del tenant",
    description="Retorna estadísticas de un tenant específico.",
)
def get_tenant_statistics(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["superadmin", "admin"])),
):
    """
    Obtiene estadísticas de un tenant.
    
    Accesible para superadmin y admin del tenant.
    """
    # Verificar permisos
    if current_user.rol != "superadmin" and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a las estadísticas de este tenant",
        )
    
    tenant = get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )
    
    stats = get_tenant_stats(db, tenant_id)
    return stats
