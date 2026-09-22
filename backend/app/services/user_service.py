# ============================================================
# backend/app/services/user_service.py - Lógica de usuarios del tenant
# CRUD de personal (staff) con whitelist de roles y límites del plan
# ============================================================

import logging
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from ..models.user import User
from ..models.tenant import Tenant
from ..schemas.user import UserCreate, UserUpdate
from ..utils.security import generate_uuid

logger = logging.getLogger(__name__)

# Whitelist de roles asignables a usuarios de un tenant
ROLES_PERMITIDOS = ("admin", "manager", "receptionist", "therapist")


# ============================================================
# Límites del tenant
# ============================================================

def get_tenant_user_limit(db: Session, tenant_id: str) -> int:
    """Obtiene el limite_usuarios del tenant (default: 10)."""
    tenant = db.query(Tenant).filter(
        Tenant.id == tenant_id,
        Tenant.deleted_at == None,
    ).first()
    return tenant.limite_usuarios if (tenant and tenant.limite_usuarios) else 10


def count_tenant_active_users(db: Session, tenant_id: str) -> int:
    """Cuenta los usuarios activos (no eliminados) del tenant."""
    return db.query(func.count(User.id)).filter(
        User.tenant_id == tenant_id,
        User.deleted_at == None,
    ).scalar() or 0


# ============================================================
# Crear usuario del tenant
# ============================================================

def create_tenant_user(db: Session, tenant_id: str, data: UserCreate) -> User:
    """
    Crea un usuario para el tenant, validando:
      - Rol dentro de la whitelist (nunca 'superadmin')
      - Único username / email dentro del tenant
      - Límite de usuarios del plan (tenant.limite_usuarios)

    Raises:
        ValueError: Si alguna validación falla
    """
    rol = (data.rol or "receptionist").lower()
    if rol not in ROLES_PERMITIDOS:
        raise ValueError(
            f"Rol inválido para un SPA. Opciones: {', '.join(ROLES_PERMITIDOS)}"
        )

    # El tenant_id siempre es el del request (no se permite escalar a otro)
    if data.tenant_id and data.tenant_id != tenant_id:
        raise ValueError("No puedes crear usuarios para otro SPA")

    # Verificar límite de usuarios del plan
    limite = get_tenant_user_limit(db, tenant_id)
    actuales = count_tenant_active_users(db, tenant_id)
    if actuales >= limite:
        raise ValueError(
            f"Se alcanzó el límite de {limite} usuarios de tu plan. "
            "Contacta a soporte para aumentarlo."
        )

    # Unicidad dentro del tenant
    username = data.username.lower()
    existing = db.query(User).filter(
        User.tenant_id == tenant_id,
        or_(
            User.username == username,
            User.email == data.email.lower(),
        ),
        User.deleted_at == None,
    ).first()
    if existing:
        raise ValueError("Ya existe un usuario con ese username o email en este SPA")

    user = User(
        id=generate_uuid(),
        tenant_id=tenant_id,
        username=username,
        email=data.email.lower(),
        nombre=data.nombre,
        apellido=data.apellido,
        telefono=data.telefono,
        rol=rol,
    )
    user.set_password(data.password)

    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"Usuario creado: {user.email} ({user.id})")
    return user


# ============================================================
# Obtener usuario
# ============================================================

def get_tenant_user(db: Session, tenant_id: str, user_id: str) -> Optional[User]:
    """Obtiene un usuario del tenant (excluye superadmin)."""
    return db.query(User).filter(
        User.id == user_id,
        User.tenant_id == tenant_id,
        User.deleted_at == None,
    ).first()


# ============================================================
# Listar usuarios del tenant
# ============================================================

def list_tenant_users(
    db: Session,
    tenant_id: str,
    skip: int = 0,
    limit: int = 50,
    rol: Optional[str] = None,
    activo: Optional[bool] = None,
    search: Optional[str] = None,
) -> List[User]:
    """Lista usuarios del tenant con filtros opcionales."""
    query = db.query(User).filter(
        User.tenant_id == tenant_id,
        User.deleted_at == None,
    )

    if rol:
        query = query.filter(User.rol == rol.lower())
    if activo is not None:
        query = query.filter(User.is_active == activo)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.nombre.ilike(pattern),
                User.apellido.ilike(pattern),
                User.email.ilike(pattern),
                User.username.ilike(pattern),
            )
        )

    return query.order_by(User.nombre.asc(), User.apellido.asc()).offset(skip).limit(limit).all()


def count_tenant_users(db: Session, tenant_id: str, activo: Optional[bool] = None) -> int:
    """Cuenta usuarios del tenant (permanentes)."""
    query = db.query(func.count(User.id)).filter(
        User.tenant_id == tenant_id,
        User.deleted_at == None,
    )
    if activo is not None:
        query = query.filter(User.is_active == activo)
    return query.scalar() or 0


# ============================================================
# Actualizar usuario del tenant
# ============================================================

def update_tenant_user(
    db: Session,
    tenant_id: str,
    user_id: str,
    data: UserUpdate,
    acting_user: User,
) -> Optional[User]:
    """
    Actualiza un usuario del tenant.

    Guardas:
      - Rol dentro de la whitelist
      - No se puede desactivar ni eliminar la propia cuenta
      - No se puede quitar el rol admin si es el último admin del tenant
      - No se puede cambiar el rol de un usuario a superadmin

    Raises:
        ValueError: Si alguna validación falla
    """
    user = get_tenant_user(db, tenant_id, user_id)
    if not user:
        return None

    body = data.model_dump(exclude_unset=True)

    # No permitir escalar a superadmin
    if "rol" in body and body["rol"]:
        if body["rol"].lower() not in ROLES_PERMITIDOS:
            raise ValueError(
                f"Rol inválido para un SPA. Opciones: {', '.join(ROLES_PERMITIDOS)}"
            )
        body["rol"] = body["rol"].lower()

    # No desactivar la propia cuenta
    if "activo" in body and body["activo"] is False and str(user.id) == str(acting_user.id):
        raise ValueError("No puedes desactivar tu propia cuenta")

    # No quitar el último admin del tenant
    if "rol" in body and user.rol == "admin" and body["rol"] != "admin":
        admins = db.query(func.count(User.id)).filter(
            User.tenant_id == tenant_id,
            User.rol == "admin",
            User.is_active == True,
            User.deleted_at == None,
        ).scalar() or 0
        if admins <= 1:
            raise ValueError("No puedes quitar el rol admin al último administrador del SPA")

    if "activo" in body:
        body["is_active"] = body.pop("activo")

    # Si viene password nueva, hasharla
    if "password" in body:
        user.set_password(body.pop("password"))

    for field, value in body.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    logger.info(f"Usuario actualizado: {user.email} ({user.id})")
    return user


# ============================================================
# Eliminar usuario (soft delete)
# ============================================================

def delete_tenant_user(
    db: Session,
    tenant_id: str,
    user_id: str,
    acting_user: User,
) -> bool:
    """
    Elimina (soft delete) un usuario del tenant.
    No permite eliminar la propia cuenta.
    """
    user = get_tenant_user(db, tenant_id, user_id)
    if not user:
        return False

    if str(user.id) == str(acting_user.id):
        raise ValueError("No puedes eliminar tu propia cuenta")

    user.soft_delete()
    db.commit()

    logger.info(f"Usuario eliminado (soft delete): {user.email} ({user.id})")
    return True


def build_user_response(user: User) -> dict:
    """Construye el diccionario de respuesta de usuario."""
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "nombre": user.nombre,
        "apellido": user.apellido,
        "telefono": user.telefono,
        "rol": user.rol,
        "activo": user.is_active,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "avatar_url": user.avatar_url,
        "ultimo_acceso": user.ultimo_acceso.isoformat() if user.ultimo_acceso else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }