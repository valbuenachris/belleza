# backend/app/models/__init__.py
# Registro de todos los modelos del sistema
from .base import Base, TenantBaseModel
from .tenant import Tenant
from .user import User

__all__ = ["Base", "TenantBaseModel", "Tenant", "User"]
