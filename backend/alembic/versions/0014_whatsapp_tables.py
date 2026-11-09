"""add whatsapp tables for evolution integration

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-09

WhatsApp / Evolution API integration:
- whatsapp_settings: per-tenant WhatsApp instance config
- whatsapp_conversations: per-phone conversation tracking
- whatsapp_messages: message history with dedup by message_id

Alineado con backend/app/models/whatsapp.py.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----------------------------------------------------------
    # whatsapp_settings
    # ----------------------------------------------------------
    op.create_table(
        "whatsapp_settings",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("tenant_id", mysql.CHAR(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("instance_name", sa.String(length=100), nullable=True, unique=True),
        sa.Column("status", sa.String(length=20), nullable=False, default="close"),
        sa.Column("connected_at", sa.DateTime(), nullable=True),
        sa.Column("qr_code", sa.Text(), nullable=True),
        sa.Column("agent_enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False, default="Asistente del SPA"),
        sa.Column("agent_tone", sa.String(length=20), nullable=False, default="amable"),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("webhook_registered", sa.Boolean(), nullable=False, default=False),
        sa.PrimaryKeyConstraint("id"),
        mysql_comment="Configuración de WhatsApp por tenant",
    )
    op.create_index("idx_wa_settings_tenant", "whatsapp_settings", ["tenant_id"])
    op.create_index("idx_wa_settings_instance", "whatsapp_settings", ["instance_name"])

    # ----------------------------------------------------------
    # whatsapp_conversations
    # ----------------------------------------------------------
    op.create_table(
        "whatsapp_conversations",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("tenant_id", mysql.CHAR(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("push_name", sa.String(length=100), nullable=True),
        sa.Column("patient_id", mysql.CHAR(36), nullable=True, index=True),
        sa.Column("status", sa.String(length=20), nullable=False, default="bot"),
        sa.Column("last_message_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"],
            ondelete="SET NULL", onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_comment="Conversaciones de WhatsApp",
    )
    op.create_index("idx_wa_conv_tenant_phone", "whatsapp_conversations", ["tenant_id", "phone"])
    op.create_index("idx_wa_conv_status", "whatsapp_conversations", ["status"])

    # ----------------------------------------------------------
    # whatsapp_messages
    # ----------------------------------------------------------
    op.create_table(
        "whatsapp_messages",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("tenant_id", mysql.CHAR(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("conversation_id", mysql.CHAR(36), nullable=False, index=True),
        sa.Column("message_id", sa.String(length=100), nullable=True, unique=True),
        sa.Column("role", sa.String(length=20), nullable=False, default="user"),
        sa.Column("content", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["whatsapp_conversations.id"],
            ondelete="CASCADE", onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_comment="Mensajes de WhatsApp",
    )
    op.create_index("idx_wa_msg_conv", "whatsapp_messages", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("whatsapp_messages")
    op.drop_table("whatsapp_conversations")
    op.drop_table("whatsapp_settings")