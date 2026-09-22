"""patient loyalty fields (puntos, sesiones_gratis, wallet_pass_id)

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-22

Agrega los campos del programa de fidelidad (Loyalty Rewards) a la
tabla patients: puntos (estrellas), sesiones_gratis y wallet_pass_id
(identificador único del pase digital de Apple Wallet / Google Wallet).
Alineado con backend/app/models/patient.py y database/schema.sql.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column(
            "puntos",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
            comment="Estrellas/puntos de fidelidad acumulados (10 = 1 sesión gratis)",
        ),
    )
    op.add_column(
        "patients",
        sa.Column(
            "sesiones_gratis",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
            comment="Sesiones gratuitas disponibles",
        ),
    )
    op.add_column(
        "patients",
        sa.Column(
            "wallet_pass_id",
            sa.String(length=128),
            nullable=True,
            comment="Identificador único del pase digital (Apple Wallet / Google Wallet)",
        ),
    )
    op.create_index(
        "ux_patients_wallet_pass",
        "patients",
        ["wallet_pass_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_patients_wallet_pass", table_name="patients")
    op.drop_column("patients", "wallet_pass_id")
    op.drop_column("patients", "sesiones_gratis")
    op.drop_column("patients", "puntos")