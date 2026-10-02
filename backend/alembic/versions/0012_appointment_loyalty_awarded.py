"""add loyalty_awarded to appointments

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-02

Añade la columna `loyalty_awarded` a `appointments` para garantizar que la
estrella de fidelidad se otorgue EXACTAMENTE UNA VEZ por cita. Evita el
doble premio al alternar el estado (completed -> pending -> completed) y
sirve de soporte al bloqueo por fila (SELECT ... FOR UPDATE) frente a
completados concurrentes.

Alineado con backend/app/models/appointment.py y database/schema.sql.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "appointments",
        sa.Column(
            "loyalty_awarded",
            sa.Boolean(),
            server_default="0",
            nullable=False,
            comment=(
                "TRUE si la estrella de fidelidad ya se otorgó por esta cita "
                "(evita dobles premios al alternar estados)"
            ),
        ),
    )

    # Backfill: las citas ya completadas premiaron su estrella con la
    # lógica anterior; se marcan para no volver a premiarlas.
    op.execute(
        "UPDATE appointments SET loyalty_awarded = 1 WHERE estado = 'completed'"
    )


def downgrade() -> None:
    op.drop_column("appointments", "loyalty_awarded")
