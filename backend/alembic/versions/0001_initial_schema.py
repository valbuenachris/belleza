"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-20

Crea las tablas iniciales tenants y users, alineadas con los
modelos SQLAlchemy de backend/app/models/ y con database/schema.sql.

Revision ID: 0001
Revises:
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------
    # Tabla: tenants
    # ------------------------------------------------------------
    op.create_table(
        "tenants",
        sa.Column("id", sa.CHAR(length=36), nullable=False, comment="UUID del tenant"),
        sa.Column("nombre", sa.String(length=255), nullable=False, comment="Nombre del SPA"),
        sa.Column("subdominio", sa.String(length=100), nullable=False, comment="Subdominio único"),
        sa.Column("plan", sa.String(length=50), server_default="basic", nullable=False, comment="Plan: basic, professional, enterprise"),
        sa.Column("fecha_creacion", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("fecha_expiracion", sa.DateTime(), nullable=True),
        sa.Column("configuracion", sa.JSON(), nullable=True),
        sa.Column("limite_usuarios", sa.Integer(), server_default="10", nullable=False),
        sa.Column("limite_pacientes", sa.Integer(), server_default="1000", nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("direccion", sa.String(length=500), nullable=True),
        sa.Column("telefono", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=50), server_default="America/Bogota", nullable=False),
        sa.Column("moneda", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True, comment="Soft delete timestamp"),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subdominio", name="uk_tenants_subdominio"),
        mysql_engine="InnoDB",
        mysql_default_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="Tabla de tenants (SPAs registrados)",
    )
    op.create_index("idx_tenants_activo", "tenants", ["is_active"])
    op.create_index("idx_tenants_plan", "tenants", ["plan"])
    op.create_index("idx_tenants_deleted", "tenants", ["deleted_at"])

    # ------------------------------------------------------------
    # Tabla: users
    # ------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.CHAR(length=36), nullable=False, comment="UUID del usuario"),
        sa.Column("tenant_id", sa.CHAR(length=36), nullable=True, comment="FK al tenant (NULL para superadmin global)"),
        sa.Column("username", sa.String(length=100), nullable=False, comment="Nombre de usuario"),
        sa.Column("email", sa.String(length=255), nullable=False, comment="Correo electrónico"),
        sa.Column("password_hash", sa.String(length=255), nullable=False, comment="Contraseña hasheada (bcrypt)"),
        sa.Column("nombre", sa.String(length=100), nullable=False, comment="Nombre"),
        sa.Column("apellido", sa.String(length=100), nullable=False, comment="Apellido"),
        sa.Column("rol", sa.String(length=50), nullable=False, comment="Rol: superadmin, admin, manager, receptionist, therapist"),
        sa.Column("ultimo_acceso", sa.DateTime(), nullable=True, comment="Último acceso al sistema"),
        sa.Column("telefono", sa.String(length=50), nullable=True, comment="Teléfono"),
        sa.Column("avatar_url", sa.String(length=500), nullable=True, comment="URL del avatar"),
        sa.Column("email_verificado", sa.Boolean(), server_default="0", nullable=False, comment="Email verificado"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True, comment="Soft delete timestamp"),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE", onupdate="CASCADE", name="fk_users_tenant"),
        mysql_engine="InnoDB",
        mysql_default_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="Tabla de usuarios del sistema",
    )
    op.create_index("idx_users_tenant", "users", ["tenant_id"])
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_username", "users", ["username"])
    op.create_index("idx_users_rol", "users", ["rol"])
    op.create_index("idx_tenant_active", "users", ["tenant_id", "is_active"])
    op.create_index("idx_users_deleted", "users", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("idx_users_deleted", table_name="users")
    op.drop_index("idx_tenant_active", table_name="users")
    op.drop_index("idx_users_rol", table_name="users")
    op.drop_index("idx_users_username", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_index("idx_users_tenant", table_name="users")
    op.drop_table("users")
    op.drop_index("idx_tenants_deleted", table_name="tenants")
    op.drop_index("idx_tenants_plan", table_name="tenants")
    op.drop_index("idx_tenants_activo", table_name="tenants")
    op.drop_table("tenants")