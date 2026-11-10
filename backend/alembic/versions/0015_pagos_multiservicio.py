"""add payments, items and related services

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-10

Pagos y multi-servicio:
- appointments: monto_total, total_pagado, descuento_total, estado_pago
- appointment_items: servicios de una cita (N servicios por cita)
- appointment_payments: ledger de pagos por cita
- service_related: servicios sugeridos/relacionados
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Columnas de pago en appointments
    op.add_column(
        "appointments",
        sa.Column("monto_total", sa.Numeric(10, 2), nullable=True, comment="Monto total de la cita"),
    )
    op.add_column(
        "appointments",
        sa.Column("total_pagado", sa.Numeric(10, 2), nullable=True, comment="Total pagado"),
    )
    op.add_column(
        "appointments",
        sa.Column("descuento_total", sa.Numeric(10, 2), nullable=True, comment="Descuento total"),
    )
    op.add_column(
        "appointments",
        sa.Column(
            "estado_pago",
            sa.String(length=20),
            nullable=False,
            server_default="unpaid",
            comment="Estado de pago: unpaid, partial, paid",
        ),
    )

    # appointment_items
    op.create_table(
        "appointment_items",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("tenant_id", mysql.CHAR(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("appointment_id", mysql.CHAR(36), nullable=False, index=True),
        sa.Column("service_id", mysql.CHAR(36), nullable=False, index=True),
        sa.Column("nombre_snapshot", sa.String(length=255), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("descuento", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="RESTRICT", onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        mysql_comment="Ítems de una cita (multi-servicio)",
    )
    op.create_index("idx_ai_tenant_appt", "appointment_items", ["tenant_id", "appointment_id"])

    # appointment_payments
    op.create_table(
        "appointment_payments",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("tenant_id", mysql.CHAR(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("appointment_id", mysql.CHAR(36), nullable=False, index=True),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column("metodo_pago", sa.String(length=30), nullable=False, server_default="efectivo"),
        sa.Column("descuento", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("created_by", mysql.CHAR(36), nullable=True),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        mysql_comment="Pagos registrados por cita",
    )
    op.create_index("idx_ap_tenant_appt", "appointment_payments", ["tenant_id", "appointment_id"])

    # service_related
    op.create_table(
        "service_related",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("tenant_id", mysql.CHAR(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("service_id", mysql.CHAR(36), nullable=False, index=True),
        sa.Column("related_service_id", mysql.CHAR(36), nullable=False, index=True),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["related_service_id"], ["services.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        mysql_comment="Servicios relacionados/sugeridos",
    )
    op.create_index("idx_sr_tenant_service", "service_related", ["tenant_id", "service_id"])


def downgrade() -> None:
    op.drop_index("idx_sr_tenant_service", table_name="service_related")
    op.drop_table("service_related")
    op.drop_index("idx_ap_tenant_appt", table_name="appointment_payments")
    op.drop_table("appointment_payments")
    op.drop_index("idx_ai_tenant_appt", table_name="appointment_items")
    op.drop_table("appointment_items")
    op.drop_column("appointments", "estado_pago")
    op.drop_column("appointments", "descuento_total")
    op.drop_column("appointments", "total_pagado")
    op.drop_column("appointments", "monto_total")
