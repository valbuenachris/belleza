"""notifications - Tabla de notificaciones internas del Dashboard

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-02

Crea la tabla `notifications` que almacena las notificaciones internas
destinadas a un usuario del tenant (campana del Dashboard): nuevas citas,
recordatorios, recompensas de fidelidad y avisos del sistema. El estado
de lectura es por usuario y los datos están 100% aislados por tenant.

Alineado con backend/app/models/notification.py y database/schema.sql.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------
    # Tabla: notifications
    # ------------------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column("id", sa.CHAR(length=36), nullable=False, comment="UUID de la notificación"),
        sa.Column("tenant_id", sa.CHAR(length=36), nullable=False, comment="FK al tenant"),
        sa.Column("user_id", sa.CHAR(length=36), nullable=False, comment="FK al usuario destinatario"),
        sa.Column("title", sa.String(length=200), nullable=False, comment="Título corto de la notificación"),
        sa.Column("message", sa.Text(), nullable=True, comment="Detalle o cuerpo de la notificación"),
        sa.Column("type", sa.String(length=50), server_default="info", nullable=False, comment="Tipo: appointment, appointment_reminder, loyalty, system"),
        sa.Column("is_read", sa.Boolean(), server_default="0", nullable=False, comment="TRUE si el usuario ya la leyó"),
        sa.Column("read_at", sa.DateTime(), nullable=True, comment="Fecha/hora en la que se marcó como leída (NULL si no leída)"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True, comment="Soft delete timestamp"),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE", onupdate="CASCADE", name="fk_notifications_tenant"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", onupdate="CASCADE", name="fk_notifications_user"),
        mysql_engine="InnoDB",
        mysql_default_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="Tabla de notificaciones internas por usuario (campana del Dashboard)",
    )
    op.create_index("idx_tenant_active", "notifications", ["tenant_id", "is_active"])
    op.create_index("idx_notifications_user_read", "notifications", ["tenant_id", "user_id", "is_read"])
    op.create_index("idx_notifications_tenant_created", "notifications", ["tenant_id", "created_at"])
    op.create_index("idx_notifications_user", "notifications", ["user_id"])
    op.create_index("idx_notifications_type", "notifications", ["type"])


def downgrade() -> None:
    op.drop_index("idx_notifications_type", table_name="notifications")
    op.drop_index("idx_notifications_user", table_name="notifications")
    op.drop_index("idx_notifications_tenant_created", table_name="notifications")
    op.drop_index("idx_notifications_user_read", table_name="notifications")
    op.drop_index("idx_tenant_active", table_name="notifications")
    op.drop_table("notifications")
