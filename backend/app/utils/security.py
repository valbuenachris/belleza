# ============================================================
# backend/app/utils/security.py - Funciones de seguridad
# Hash de contraseñas, generación y validación de tokens JWT
# ============================================================

import uuid
import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import settings

# ============================================================
# Contexto de hash de contraseñas (bcrypt)
# ============================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================
# Funciones de contraseña
# ============================================================

def hash_password(password: str) -> str:
    """
    Encripta una contraseña en texto plano usando bcrypt.
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        Hash bcrypt de la contraseña
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su hash.
    
    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Hash bcrypt almacenado
        
    Returns:
        True si la contraseña es correcta, False en caso contrario
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================
# Funciones de tokens JWT
# ============================================================

def create_access_token(data: Dict[str, Any], tenant_id: Optional[str] = None) -> str:
    """
    Crea un token JWT de acceso con expiración.
    
    Args:
        data: Datos a incluir en el token (debe contener 'sub')
        tenant_id: ID del tenant del usuario
        
    Returns:
        Token JWT codificado como string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    })
    
    if tenant_id:
        to_encode["tenant_id"] = tenant_id
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], tenant_id: Optional[str] = None) -> str:
    """
    Crea un refresh token JWT con expiración más larga.
    
    Args:
        data: Datos a incluir en el token
        tenant_id: ID del tenant del usuario
        
    Returns:
        Refresh token JWT codificado
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    })
    
    if tenant_id:
        to_encode["tenant_id"] = tenant_id
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodifica y valida un token JWT.
    
    Args:
        token: Token JWT a decodificar
        
    Returns:
        Diccionario con los datos del payload
        
    Raises:
        JWTError: Si el token es inválido o ha expirado
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        raise JWTError(f"Token inválido: {str(e)}")


# ============================================================
# Funciones de generación de IDs y tokens
# ============================================================

def generate_uuid() -> str:
    """
    Genera un UUID4 como string.
    Usado para IDs de entidades.
    """
    return str(uuid.uuid4())


def generate_random_string(length: int = 32) -> str:
    """
    Genera una cadena aleatoria segura.
    Útil para tokens de recuperación de contraseña, etc.
    
    Args:
        length: Longitud de la cadena (default: 32)
        
    Returns:
        Cadena aleatoria de caracteres alfanuméricos
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_password_reset_token(email: str) -> str:
    """
    Genera un token específico para recuperación de contraseña.
    
    Args:
        email: Email del usuario
        
    Returns:
        Token JWT con expiración de 1 hora
    """
    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode = {
        "exp": expire,
        "sub": email,
        "type": "password_reset",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
