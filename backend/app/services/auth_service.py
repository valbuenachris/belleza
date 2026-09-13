# ============================================================
# backend/app/services/auth_service.py - Lógica de autenticación
# Manejo de login, registro, tokens y recuperación de contraseña
# ============================================================

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from jose import JWTError

from ..models.user import User
from ..models.tenant import Tenant
from ..schemas.user import UserCreate, UserLogin, TokenResponse, UserResponse
from ..schemas.tenant import TenantCreate, TenantResponse
from ..utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_uuid,
)
from ..utils.validators import validate_email

logger = logging.getLogger(__name__)


# ============================================================
# Autenticación de usuarios
# ============================================================

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Valida las credenciales de un usuario.
    
    Args:
        db: Sesión de base de datos
        email: Email del usuario
        password: Contraseña en texto plano
        
    Returns:
        Usuario si las credenciales son válidas, None en caso contrario
    """
    user = db.query(User).filter(
        User.email == email.lower(),
        User.is_active == True,
        User.deleted_at == None,
    ).first()
    
    if not user:
        logger.warning(f"Intento de login con email no encontrado: {email}")
        return None
    
    if not user.verify_password(password):
        logger.warning(f"Intento de login con contraseña incorrecta: {email}")
        return None
    
    return user


# ============================================================
# Registro de usuarios
# ============================================================

def register_user(db: Session, user_data: UserCreate) -> User:
    """
    Crea un nuevo usuario en la base de datos.
    
    Args:
        db: Sesión de base de datos
        user_data: Datos del usuario a crear
        
    Returns:
        Usuario creado
        
    Raises:
        ValueError: Si el email o username ya existen
    """
    # Verificar que el email no exista
    existing_email = db.query(User).filter(User.email == user_data.email.lower()).first()
    if existing_email:
        raise ValueError("Ya existe un usuario con este correo electrónico")
    
    # Verificar que el username no exista en el tenant
    if user_data.tenant_id:
        existing_username = db.query(User).filter(
            User.username == user_data.username,
            User.tenant_id == user_data.tenant_id,
        ).first()
        if existing_username:
            raise ValueError("Ya existe un usuario con este nombre de usuario en este tenant")
    
    # Crear el usuario
    user = User(
        id=generate_uuid(),
        tenant_id=user_data.tenant_id or "",
        username=user_data.username,
        email=user_data.email.lower(),
        nombre=user_data.nombre,
        apellido=user_data.apellido,
        rol=user_data.rol,
        telefono=user_data.telefono,
        is_active=True,
    )
    user.set_password(user_data.password)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"Usuario registrado exitosamente: {user.email}")
    return user


def register_tenant(
    db: Session,
    tenant_data: TenantCreate,
    admin_data: UserCreate,
) -> Dict[str, Any]:
    """
    Crea un nuevo tenant y su usuario administrador en una transacción.
    
    Args:
        db: Sesión de base de datos
        tenant_data: Datos del tenant
        admin_data: Datos del usuario administrador
        
    Returns:
        Diccionario con 'tenant' y 'user' creados
        
    Raises:
        ValueError: Si el subdominio ya existe
    """
    try:
        # Verificar subdominio único
        existing_subdomain = db.query(Tenant).filter(
            Tenant.subdominio == tenant_data.subdominio.lower()
        ).first()
        if existing_subdomain:
            raise ValueError("El subdominio ya está en uso. Elige otro.")
        
        # Crear tenant
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
        db.flush()  # Para obtener el ID antes del commit
        
        # Crear usuario admin del tenant
        admin_user = User(
            id=generate_uuid(),
            tenant_id=tenant.id,
            username=admin_data.username,
            email=admin_data.email.lower(),
            nombre=admin_data.nombre,
            apellido=admin_data.apellido,
            rol="admin",
            telefono=admin_data.telefono,
            email_verificado=False,
            is_active=True,
        )
        admin_user.set_password(admin_data.password)
        db.add(admin_user)
        
        # Commit de la transacción completa
        db.commit()
        db.refresh(tenant)
        db.refresh(admin_user)
        
        logger.info(f"Tenant registrado: {tenant.nombre} ({tenant.subdominio})")
        logger.info(f"Admin creado: {admin_user.email}")
        
        return {"tenant": tenant, "user": admin_user}
    
    except ValueError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al registrar tenant: {e}")
        raise ValueError(f"Error al crear el tenant: {str(e)}")


# ============================================================
# Gestión de tokens
# ============================================================

def create_tokens(user: User) -> Dict[str, str]:
    """
    Genera access token y refresh token para un usuario.
    
    Args:
        user: Usuario autenticado
        
    Returns:
        Diccionario con access_token, refresh_token y token_type
    """
    token_data = {
        "sub": user.id,
        "email": user.email,
        "rol": user.rol,
    }
    
    access_token = create_access_token(token_data, tenant_id=user.tenant_id)
    refresh_token = create_refresh_token(token_data, tenant_id=user.tenant_id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def refresh_tokens(db: Session, refresh_token: str) -> Dict[str, Any]:
    """
    Valida un refresh token y genera nuevos tokens.
    
    Args:
        db: Sesión de base de datos
        refresh_token: Refresh token a validar
        
    Returns:
        Diccionario con nuevos tokens y usuario
        
    Raises:
        ValueError: Si el token es inválido o el usuario no existe
    """
    try:
        payload = decode_token(refresh_token)
        
        # Verificar que sea un refresh token
        if payload.get("type") != "refresh":
            raise ValueError("Token inválido: no es un refresh token")
        
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Token inválido: sin identificador de usuario")
        
        # Buscar usuario
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True,
        ).first()
        
        if not user:
            raise ValueError("Usuario no encontrado o inactivo")
        
        # Generar nuevos tokens
        tokens = create_tokens(user)
        return {**tokens, "user": user}
    
    except JWTError as e:
        raise ValueError(f"Token inválido o expirado: {str(e)}")


# ============================================================
# Consultas de usuarios
# ============================================================

def get_user_by_email(db: Session, email: str, tenant_id: Optional[str] = None) -> Optional[User]:
    """
    Busca un usuario por email, opcionalmente filtrando por tenant.
    """
    query = db.query(User).filter(
        User.email == email.lower(),
        User.is_active == True,
        User.deleted_at == None,
    )
    
    if tenant_id:
        query = query.filter(User.tenant_id == tenant_id)
    
    return query.first()


def get_user_by_id(db: Session, user_id: str, tenant_id: Optional[str] = None) -> Optional[User]:
    """
    Busca un usuario por ID, opcionalmente filtrando por tenant.
    """
    query = db.query(User).filter(
        User.id == user_id,
        User.is_active == True,
    )
    
    if tenant_id:
        query = query.filter(User.tenant_id == tenant_id)
    
    return query.first()


def update_last_access(db: Session, user: User) -> None:
    """
    Actualiza la fecha del último acceso del usuario.
    """
    user.ultimo_acceso = datetime.utcnow()
    db.commit()
