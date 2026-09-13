# ============================================================
# backend/app/dependencies.py - Dependencias de FastAPI
# Inyección de dependencias para endpoints
# ============================================================

from typing import List, Optional, Generator, Callable
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from .database import get_db
from .config import settings
from .models.user import User
from .models.tenant import Tenant
from .utils.security import decode_token
from .services.auth_service import get_user_by_id
from .services.tenant_service import get_tenant_by_id

# Esquema de seguridad HTTP Bearer
security = HTTPBearer(auto_error=False)


# ============================================================
# Dependencia: Obtener sesión de base de datos
# ============================================================

def get_database() -> Generator:
    """
    Proporciona una sesión de base de datos.
    Alias de get_db para claridad en los endpoints.
    """
    yield from get_db()


# ============================================================
# Dependencia: Obtener el tenant actual
# ============================================================

def get_current_tenant(
    request: Request,
    db: Session = Depends(get_db),
) -> Tenant:
    """
    Obtiene el tenant actual desde request.state (inyectado por middleware).
    Valida que exista en la base de datos.
    
    Raises:
        HTTPException 403: Si el tenant no existe o está inactivo
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    
    # Superadmin puede no tener tenant
    user_rol = getattr(request.state, "user_rol", None)
    if user_rol == "superadmin":
        # Para superadmin, retornar un tenant dummy o None según el caso
        # Los endpoints de superadmin manejan esto
        return None
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se encontró tenant asociado a tu cuenta",
        )
    
    tenant = get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El tenant no existe o ha sido eliminado",
        )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El tenant está desactivado",
        )
    
    return tenant


# ============================================================
# Dependencia: Obtener el usuario actual
# ============================================================

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Obtiene el usuario autenticado desde el token JWT.
    Valida que exista en la base de datos.
    
    Raises:
        HTTPException 401: Si el token es inválido
        HTTPException 403: Si el usuario no existe o está inactivo
    """
    user_id = getattr(request.state, "user_id", None)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo identificar al usuario",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Para superadmin, no filtrar por tenant
    user_rol = getattr(request.state, "user_rol", None)
    tenant_id = getattr(request.state, "tenant_id", None)
    
    user = get_user_by_id(db, user_id, tenant_id=None if user_rol == "superadmin" else tenant_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no encontrado o sin acceso a este tenant",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta ha sido desactivada. Contacta al administrador.",
        )
    
    return user


# ============================================================
# Dependencia: Usuario activo
# ============================================================

def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """
    Obtiene el usuario actual verificando que esté activo.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta inactiva",
        )
    return user


# ============================================================
# Dependencia: Verificar roles específicos
# ============================================================

def require_role(roles: List[str]) -> Callable:
    """
    Dependencia que verifica que el usuario tenga uno de los roles especificados.
    
    Uso:
        @router.get("/admin-only")
        def admin_endpoint(user: User = Depends(require_role(["admin", "superadmin"]))):
            ...
    """
    def role_checker(user: User = Depends(get_current_active_user)) -> User:
        if user.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes permisos para acceder a este recurso. "
                       f"Roles requeridos: {', '.join(roles)}",
            )
        return user
    
    return role_checker


# ============================================================
# Dependencia: Superadmin
# ============================================================

def get_superadmin(
    user: User = Depends(get_current_active_user),
) -> User:
    """
    Verifica que el usuario sea superadministrador.
    """
    if user.rol != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a superadministradores",
        )
    return user


# ============================================================
# Dependencia: Admin o superior
# ============================================================

def get_admin_or_superadmin(
    user: User = Depends(get_current_active_user),
) -> User:
    """
    Verifica que el usuario sea admin o superadmin.
    """
    if user.rol not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a administradores",
        )
    return user
