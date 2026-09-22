# ============================================================
# backend/app/routers/auth.py - Endpoints de autenticación
# Login, registro, refresh, cambio de contraseña
# ============================================================

import logging
from datetime import datetime
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.user import (
    UserLogin, UserCreate, UserResponse, TokenResponse,
    ChangePassword, ForgotPassword, ResetPassword,
)
from ..schemas.tenant import TenantCreate, TenantResponse
from ..services.auth_service import (
    authenticate_user,
    register_user,
    register_tenant,
    create_tokens,
    refresh_tokens,
    update_last_access,
    get_user_by_email,
)
from ..dependencies import get_current_user
from ..models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def _serialize_tenant(tenant) -> Dict[str, Any]:
    """
    Serializa el tenant completo (incluyendo 'configuracion' y campos de
    contacto/regional) para que el frontend pueda precargar los ajustes
    guardados del SPA sin depender del subdominio.
    """
    return {
        "id": str(tenant.id),
        "nombre": tenant.nombre,
        "subdominio": tenant.subdominio,
        "plan": tenant.plan if hasattr(tenant, "plan") else "basic",
        "activo": getattr(tenant, "is_active", True),
        "fecha_creacion": tenant.created_at.isoformat() if tenant.created_at else datetime.utcnow().isoformat(),
        "fecha_expiracion": (
            tenant.fecha_expiracion.isoformat()
            if getattr(tenant, "fecha_expiracion", None)
            else None
        ),
        "configuracion": tenant.configuracion or None,
        "limite_usuarios": tenant.limite_usuarios if hasattr(tenant, "limite_usuarios") else 10,
        "limite_pacientes": tenant.limite_pacientes if hasattr(tenant, "limite_pacientes") else 100,
        "logo_url": getattr(tenant, "logo_url", None),
        "direccion": getattr(tenant, "direccion", None),
        "telefono": getattr(tenant, "telefono", None),
        "email": getattr(tenant, "email", None),
        "timezone": getattr(tenant, "timezone", "America/Bogota"),
        "moneda": getattr(tenant, "moneda", "USD"),
    }


# ============================================================
# POST /api/v1/auth/login - Iniciar sesión
# ============================================================

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
    description="Autentica un usuario con email y contraseña. Retorna tokens JWT.",
)
def login(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Inicia sesión con email y contraseña.
    Retorna access_token y refresh_token para autenticación posterior.

    Login universal: el usuario puede iniciar sesión desde la root URL
    (sin subdominio). No se necesita el subdominio para resolver el tenant:
    se busca al usuario por email y su tenant_id se inyecta en
    request.state antes de validar la contraseña.
    """
    # 0. Búsqueda por email y resolución del tenant (sin subdominio).
    #    Antes de validar la contraseña se localiza al usuario por email
    #    para extraer su tenant_id y dejarlo disponible en request.state
    #    como contexto del SPA correspondiente.
    user_by_email = get_user_by_email(db, credentials.email)
    if user_by_email:
        request.state.user_id = str(user_by_email.id)
        request.state.user_email = user_by_email.email
        request.state.user_rol = user_by_email.rol
        request.state.tenant_id = str(user_by_email.tenant_id) if user_by_email.tenant_id else None

    # 1. Autenticar usuario
    user = authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
        logger.warning(f"Intento de login fallido: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas. Verifica tu correo y contraseña.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Verificar estado activo
    if not getattr(user, 'is_active', True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta ha sido desactivada. Contacta al administrador.",
        )

    # 2.5. Verificar que el SPA (tenant) del usuario no esté suspendido.
    #      El superadmin no depende de ningún tenant, por lo que no aplica.
    if user.rol != "superadmin":
        tenant = getattr(user, "tenant", None)
        if tenant is not None and not getattr(tenant, "is_active", True):
            logger.warning(
                f"Login bloqueado: SPA suspendido para {credentials.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tu centro de SPA se encuentra suspendido. Por favor contacta al administrador del sistema.",
            )

        # 2.6. Verificar que la suscripción no haya expirado.
        #      null = exento de expiración (ej.: SPA demo o exención explícita).
        if tenant is not None:
            expiracion = getattr(tenant, "fecha_expiracion", None)
            if (
                expiracion is not None
                and datetime.utcnow() > expiracion
            ):
                logger.warning(
                    f"Login bloqueado: suscripción expirada para {credentials.email}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        "Tu periodo de prueba o suscripción ha expirado. "
                        "Por favor contacta al administrador para renovar tu servicio."
                    ),
                )
    
    # 3. Generar tokens
    #    El access_token y refresh_token incluyen el claim 'tenant_id'
    #    correcto (autenticate_user devuelve el usuario con su tenant_id),
    #    de modo que los requests posteriores operen sobre el SPA del
    #    usuario sin depender del subdominio de la URL.
    tokens = create_tokens(user)
    
    # 4. Actualizar último acceso
    update_last_access(db, user)
    
    # 5. Serialización completa con todos los campos requeridos
    user_dict = {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "nombre": user.nombre,
        "apellido": user.apellido,
        "rol": user.rol,
        "activo": getattr(user, 'is_active', True),
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "created_at": user.created_at.isoformat() if user.created_at else datetime.utcnow().isoformat(),
    }
    
    tenant_dict = _serialize_tenant(user.tenant) if hasattr(user, "tenant") and user.tenant else None

    logger.info(f"Login exitoso: {user.email}")
    
    # 6. Retornar diccionario completo
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer",
        "user": user_dict,
        "tenant": tenant_dict,
    }


# ============================================================
# POST /api/v1/auth/register - Registrar nuevo SPA
# ============================================================

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo SPA",
    description="Crea un nuevo tenant (SPA) y su usuario administrador.",
)
def register(
    tenant_data: TenantCreate,
    admin_data: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Registra un nuevo SPA en el sistema.
    Crea el tenant y un usuario administrador en una transacción atómica.
    """
    try:
        result = register_tenant(db, tenant_data, admin_data)
        
        # Generar tokens para el admin recién creado
        tokens = create_tokens(result["user"])
        
        # Serialización completa
        tenant_dict = _serialize_tenant(result["tenant"])
        
        user_dict = {
            "id": str(result["user"].id),
            "username": result["user"].username,
            "email": result["user"].email,
            "nombre": result["user"].nombre,
            "apellido": result["user"].apellido,
            "rol": result["user"].rol,
            "activo": getattr(result["user"], 'is_active', True),
            "tenant_id": str(result["user"].tenant_id),
            "created_at": result["user"].created_at.isoformat() if result["user"].created_at else datetime.utcnow().isoformat(),
        }
        
        return {
            "message": "SPA registrado exitosamente",
            "tenant": tenant_dict,
            "user": user_dict,
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
        }
    
    except ValueError as e:
        logger.error(f"Error en registro: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================
# POST /api/v1/auth/refresh - Refrescar token
# ============================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refrescar token",
    description="Genera nuevos tokens usando un refresh token válido.",
)
def refresh(
    refresh_token: str,
    db: Session = Depends(get_db),
):
    """
    Refresca los tokens de autenticación.
    """
    try:
        result = refresh_tokens(db, refresh_token)
        user = result["user"]
        
        user_dict = {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "nombre": user.nombre,
            "apellido": user.apellido,
            "rol": user.rol,
            "activo": getattr(user, 'is_active', True),
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "created_at": user.created_at.isoformat() if user.created_at else datetime.utcnow().isoformat(),
        }
        
        tenant_dict = _serialize_tenant(user.tenant) if hasattr(user, "tenant") and user.tenant else None

        return {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": result["token_type"],
            "user": user_dict,
            "tenant": tenant_dict,
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================================
# GET /api/v1/auth/me - Usuario actual
# ============================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Usuario actual",
    description="Retorna los datos del usuario autenticado.",
)
def get_me(current_user: User = Depends(get_current_user)):
    """Obtiene los datos del usuario actualmente autenticado."""
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "nombre": current_user.nombre,
        "apellido": current_user.apellido,
        "rol": current_user.rol,
        "activo": getattr(current_user, 'is_active', True),
        "tenant_id": str(current_user.tenant_id) if current_user.tenant_id else None,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else datetime.utcnow().isoformat(),
    }


# ============================================================
# PUT /api/v1/auth/change-password - Cambiar contraseña
# ============================================================

@router.put(
    "/change-password",
    summary="Cambiar contraseña",
    description="Cambia la contraseña del usuario autenticado.",
)
def change_password(
    data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cambia la contraseña del usuario actual.
    Requiere la contraseña actual para validación.
    """
    # Verificar contraseña actual
    if not current_user.verify_password(data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta",
        )
    
    # Verificar que la nueva sea diferente
    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe ser diferente a la actual",
        )
    
    # Actualizar contraseña
    current_user.set_password(data.new_password)
    db.commit()
    
    logger.info(f"Contraseña cambiada para: {current_user.email}")
    
    return {"message": "Contraseña actualizada exitosamente"}


# ============================================================
# POST /api/v1/auth/forgot-password - Solicitar recuperación
# ============================================================

@router.post(
    "/forgot-password",
    summary="Solicitar recuperación de contraseña",
    description="Envía un enlace de recuperación al email proporcionado.",
)
def forgot_password(data: ForgotPassword, db: Session = Depends(get_db)):
    """
    Inicia el proceso de recuperación de contraseña.
    """
    user = get_user_by_email(db, data.email)
    
    # Siempre retornar éxito para no revelar si el email existe (seguridad)
    if user:
        logger.info(f"Solicitud de recuperación de contraseña para: {data.email}")
    
    return {
        "message": "Si el email está registrado, recibirás un enlace de recuperación"
    }


# ============================================================
# POST /api/v1/auth/reset-password - Restablecer contraseña
# ============================================================

@router.post(
    "/reset-password",
    summary="Restablecer contraseña",
    description="Restablece la contraseña usando un token de recuperación.",
)
def reset_password(data: ResetPassword, db: Session = Depends(get_db)):
    """
    Restablece la contraseña usando un token de recuperación.
    """
    # TODO: Implementar validación del token de recuperación
    return {
        "message": "Funcionalidad de restablecimiento de contraseña en desarrollo"
    }


# ============================================================
# POST /api/v1/auth/logout - Cerrar sesión
# ============================================================

@router.post(
    "/logout",
    summary="Cerrar sesión",
    description="Invalida el token actual (opcional con blacklist en Redis).",
)
def logout(current_user: User = Depends(get_current_user)):
    """
    Cierra la sesión del usuario.
    """
    logger.info(f"Logout: {current_user.email}")
    
    return {"message": "Sesión cerrada exitosamente"}