# ============================================================
# backend/app/models/user.py - Modelo de Usuario
# Representa los usuarios del sistema (admin, recepcionista, etc.)
# ============================================================

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR

from ..database import Base
from .base import TenantBaseModel
from ..utils.security import hash_password, verify_password

if TYPE_CHECKING:
    from .tenant import Tenant


class User(Base, TenantBaseModel):
    """
    Modelo que representa un usuario del sistema.
    Cada usuario pertenece a un tenant específico (excepto superadmin).
    """
    
    __tablename__ = "users"
    
    # ----------------------------------------------------------
    # Credenciales
    # ----------------------------------------------------------
    username: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Nombre de usuario único dentro del tenant",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Correo electrónico del usuario",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Contraseña hasheada con bcrypt",
    )
    
    # ----------------------------------------------------------
    # Información personal
    # ----------------------------------------------------------
    nombre: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Nombre del usuario",
    )
    apellido: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Apellido del usuario",
    )
    telefono: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Teléfono de contacto",
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL del avatar/foto de perfil",
    )
    
    # ----------------------------------------------------------
    # Rol y estado
    # ----------------------------------------------------------
    rol: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Rol del usuario: superadmin, admin, manager, receptionist, therapist",
    )
    email_verificado: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica si el email ha sido verificado",
    )
    ultimo_acceso: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        comment="Fecha y hora del último acceso al sistema",
    )
    
    # ----------------------------------------------------------
    # Relaciones
    # ----------------------------------------------------------
    tenant: Mapped[Optional["Tenant"]] = relationship(
        "Tenant",
        back_populates="usuarios",
        lazy="joined",
    )
    
    # ----------------------------------------------------------
    # Métodos de contraseña
    # ----------------------------------------------------------
    
    def set_password(self, password: str) -> None:
        """
        Establece la contraseña hasheada.
        Usa bcrypt para el hash.
        """
        self.password_hash = hash_password(password)
    
    def verify_password(self, password: str) -> bool:
        """
        Verifica si una contraseña en texto plano coincide con el hash.
        """
        return verify_password(password, self.password_hash)
    
    # ----------------------------------------------------------
    # Métodos de rol
    # ----------------------------------------------------------
    
    def has_role(self, *roles: str) -> bool:
        """
        Verifica si el usuario tiene alguno de los roles especificados.
        
        Ejemplo:
            user.has_role("admin", "superadmin")
        """
        return self.rol in roles
    
    @property
    def is_superadmin(self) -> bool:
        """Verifica si el usuario es superadministrador."""
        return self.rol == "superadmin"
    
    @property
    def full_name(self) -> str:
        """Retorna el nombre completo del usuario."""
        return f"{self.nombre} {self.apellido}"
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, rol={self.rol})>"
