# ============================================================
# backend/app/utils/validators.py - Validadores reutilizables
# Funciones para validar formatos de datos comunes
# ============================================================

import re
import uuid
from typing import Tuple


def validate_email(email: str) -> bool:
    """
    Valida el formato de un correo electrónico.
    
    Args:
        email: Email a validar
        
    Returns:
        True si el formato es válido, False en caso contrario
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """
    Valida el formato de un número de teléfono.
    Acepta formatos internacionales con + y espacios.
    
    Args:
        phone: Teléfono a validar
        
    Returns:
        True si el formato es válido
    """
    # Eliminar espacios y guiones para validación
    cleaned = re.sub(r"[\s\-\(\)]", "", phone)
    pattern = r"^\+?[0-9]{7,15}$"
    return bool(re.match(pattern, cleaned))


def validate_uuid(uuid_str: str) -> bool:
    """
    Valida que un string sea un UUID válido.
    
    Args:
        uuid_str: String a validar
        
    Returns:
        True si es un UUID válido
    """
    try:
        uuid.UUID(uuid_str)
        return True
    except (ValueError, AttributeError):
        return False


def validate_subdomain(subdomain: str) -> bool:
    """
    Valida el formato de un subdominio.
    Solo permite minúsculas, números y guiones.
    Debe empezar y terminar con letra o número.
    
    Args:
        subdomain: Subdominio a validar
        
    Returns:
        True si el formato es válido
    """
    if not subdomain or len(subdomain) < 3 or len(subdomain) > 63:
        return False
    
    pattern = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$"
    return bool(re.match(pattern, subdomain))


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Valida la fortaleza de una contraseña.
    Requisitos: mínimo 8 caracteres, mayúsculas, minúsculas, números, especiales.
    
    Args:
        password: Contraseña a validar
        
    Returns:
        Tupla (es_valida, mensaje_error)
        Si es válida, mensaje_error está vacío
    """
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    
    if not re.search(r"[A-Z]", password):
        return False, "La contraseña debe contener al menos una letra mayúscula"
    
    if not re.search(r"[a-z]", password):
        return False, "La contraseña debe contener al menos una letra minúscula"
    
    if not re.search(r"[0-9]", password):
        return False, "La contraseña debe contener al menos un número"
    
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:',.<>?/`~\\\"", password):
        return False, "La contraseña debe contener al menos un carácter especial"
    
    return True, ""


def sanitize_string(text: str) -> str:
    """
    Sanitiza un string eliminando caracteres peligrosos.
    Elimina etiquetas HTML y caracteres de control.
    
    Args:
        text: Texto a sanitizar
        
    Returns:
        Texto sanitizado
    """
    if not text:
        return ""
    
    # Eliminar etiquetas HTML
    text = re.sub(r"<[^>]+>", "", text)
    
    # Eliminar caracteres de control (excepto saltos de línea y tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    
    # Eliminar scripts peligrosos
    text = re.sub(r"(?i)(javascript|on\w+\s*=|<script)", "", text)
    
    # Limitar longitud
    return text.strip()[:1000]


def validate_plan(plan: str) -> bool:
    """
    Valida que el plan sea uno de los permitidos.
    
    Args:
        plan: Plan a validar
        
    Returns:
        True si es un plan válido
    """
    valid_plans = ["basic", "professional", "enterprise"]
    return plan.lower() in valid_plans


def validate_role(role: str) -> bool:
    """
    Valida que el rol sea uno de los permitidos.
    
    Args:
        role: Rol a validar
        
    Returns:
        True si es un rol válido
    """
    valid_roles = ["superadmin", "admin", "manager", "receptionist", "therapist"]
    return role.lower() in valid_roles
