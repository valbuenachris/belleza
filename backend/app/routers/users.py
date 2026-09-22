# ============================================================
# backend/app/routers/users.py - Endpoints de Usuarios del tenant
# CRUD de personal con whitelist de roles y límites del plan
# ============================================================

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, get_current_tenant_id, get_admin_or_superadmin
from ..models.user import User
from ..schemas.user import UserCreate, UserUpdate
from ..services import user_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Usuarios"])


# ============================================================
# GET /api/v1/users - Listar usuarios del SPA
# ============================================================

@router.get(
    "",
    summary="Listar usuarios",
    description="Lista el personal del SPA con filtros opcionales.",
)
def list_users(
    skip: int = 0,
    limit: int = 50,
    rol: Optional[str] = None,
    activo: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    users = user_service.list_tenant_users(
        db, tenant_id, skip=skip, limit=limit, rol=rol, activo=activo, search=search
    )
    total = user_service.count_tenant_users(db, tenant_id, activo=activo)

    items = [user_service.build_user_response(u) for u in users]
    return {"users": items, "total": total}


# ============================================================
# GET /api/v1/users/{id} - Obtener usuario
# ============================================================

@router.get(
    "/{user_id}",
    summary="Obtener usuario",
    description="Retorna los datos de un usuario del SPA.",
)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    user = user_service.get_tenant_user(db, tenant_id, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return user_service.build_user_response(user)


# ============================================================
# POST /api/v1/users - Crear usuario (solo admin/superadmin)
# ============================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario",
    description=(
        "Crea un nuevo usuario del SPA. Solo admin o superadmin. "
        "Validación de rol permitido y límite de usuarios del plan."
    ),
)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_superadmin),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        user = user_service.create_tenant_user(db, tenant_id, user_data)
        return {
            "message": "Usuario creado exitosamente",
            "user": user_service.build_user_response(user),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# PUT /api/v1/users/{id} - Actualizar usuario
# ============================================================

@router.put(
    "/{user_id}",
    summary="Actualizar usuario",
    description="Actualiza un usuario del SPA (rol, datos, contraseña, estado).",
)
def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_superadmin),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        user = user_service.update_tenant_user(db, tenant_id, user_id, user_data, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return {
        "message": "Usuario actualizado exitosamente",
        "user": user_service.build_user_response(user),
    }


# ============================================================
# DELETE /api/v1/users/{id} - Eliminar usuario
# ============================================================

@router.delete(
    "/{user_id}",
    summary="Eliminar usuario",
    description="Elimina (soft delete) a un usuario del SPA.",
)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_superadmin),
    tenant_id: str = Depends(get_current_tenant_id),
):
    try:
        deleted = user_service.delete_tenant_user(db, tenant_id, user_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return {"message": "Usuario eliminado exitosamente", "deleted": True}