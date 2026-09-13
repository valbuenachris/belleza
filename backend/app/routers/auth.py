# ============================================================
# backend/app/routers/auth.py - Endpoints de autenticación
# Login, registro, refresh, cambio de contraseña
# ============================================================

import logging
from fastapi import APIRouter, Depends, HTTPException, status
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
    db: Session = Depends(get_db),
):
    """
    Inicia sesión con email y contraseña.
    
    Retorna access_token y refresh_token para autenticación posterior.
    """
    # Autenticar usuario
    user = authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas. Verifica tu correo y contraseña.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta ha sido desactivada. Contacta al administrador.",
        )
    
    # Generar tokens
    tokens = create_tokens(user)
    
    # Actualizar último acceso
    update_last_access(db, user)
    
    # Obtener tenant si existe
    tenant_response = None
    if user.tenant:
        tenant_response = TenantResponse.model_validate(user.tenant)
    
    logger.info(f"Login exitoso: {user.email}")
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        user=UserResponse.model_validate(user),
        tenant=tenant_response,
    )


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
        
        tenant_response = TenantResponse.model_validate(result["tenant"])
        user_response = UserResponse.model_validate(result["user"])
        
        return {
            "message": "SPA registrado exitosamente",
            "tenant": tenant_response,
            "user": user_response,
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
        }
    
    except ValueError as e:
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
    
    El refresh token tiene una vida más larga que el access token.
    """
    try:
        result = refresh_tokens(db, refresh_token)
        
        tenant_response = None
        if result["user"].tenant:
            tenant_response = TenantResponse.model_validate(result["user"].tenant)
        
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            user=UserResponse.model_validate(result["user"]),
            tenant=tenant_response,
        )
    
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
    return UserResponse.model_validate(current_user)


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
    
    En producción, esto enviaría un email con un token de recuperación.
    Por ahora solo verifica que el email exista.
    """
    user = get_user_by_email(db, data.email)
    
    # Siempre retornar éxito para no revelar si el email existe
    # (seguridad: no dar información a atacantes)
    if user:
        # TODO: Enviar email con token de recuperación
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
    
    El token se obtiene del email de recuperación.
    """
    # TODO: Implementar validación del token de recuperación
    # Por ahora retornar mensaje informativo
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
    
    En una implementación completa, se agregaría el token a una blacklist en Redis.
    """
    logger.info(f"Logout: {current_user.email}")
    
    return {"message": "Sesión cerrada exitosamente"}
