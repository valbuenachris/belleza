"""assistant_queries - Tabla del Asistente IA (FreeLLMAPI)

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-22

Crea la tabla `assistant_queries` que almacena las consultas de los
usuarios del SPA al asistente de IA (integración con FreeLLMAPI) junto
con sus respuestas y el feedback de calidad (is_understood). Los datos
están 100% aislados por tenant.

Alineado con backend/app/models/assistant.py y database/schema.sql.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------
    # Tabla: assistant_queries
    # ------------------------------------------------------------
    op.create_table(
        "assistant_queries",
        sa.Column("id", sa.CHAR(length=36), nullable=False, comment="UUID de la consulta"),
        sa.Column("tenant_id", sa.CHAR(length=36), nullable=False, comment="FK al tenant"),
        sa.Column("user_id", sa.CHAR(length=36), nullable=True, comment="FK al usuario que realizó la consulta (SET NULL si se elimina)"),
        sa.Column("question", sa.Text(), nullable=False, comment="Pregunta formulada por el usuario"),
        sa.Column("response", sa.Text(), nullable=True, comment="Respuesta generada por el asistente IA (FreeLLMAPI)"),
        sa.Column("is_understood", sa.Boolean(), nullable=True, comment="Feedback del usuario: NULL = sin valorar, TRUE = útil, FALSE = no útil"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True, comment="Soft delete timestamp"),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE", onupdate="CASCADE", name="fk_assistant_queries_tenant"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL", onupdate="CASCADE", name="fk_assistant_queries_user"),
        mysql_engine="InnoDB",
        mysql_default_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="Tabla de consultas al asistente IA (historial y feedback)",
    )
    op.create_index("idx_tenant_active", "assistant_queries", ["tenant_id", "is_active"])
    op.create_index("idx_assistant_queries_user", "assistant_queries", ["user_id"])
    op.create_index("idx_assistant_tenant_created", "assistant_queries", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_assistant_tenant_created", table_name="assistant_queries")
    op.drop_index("idx_assistant_queries_user", table_name="assistant_queries")
    op.drop_index("idx_tenant_active", table_name="assistant_queries")
    op.drop_table("assistant_queries")