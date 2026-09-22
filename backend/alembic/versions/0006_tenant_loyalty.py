"""tenant loyalty customization (puntos_meta, premio_fidelidad, tarjeta_color_hex)

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-22

Agrega la personalización del programa de fidelidad por tenant a la tabla
tenants: puntos_meta (estrellas meta para la sesión gratuita),
premio_fidelidad (texto del premio) y tarjeta_color_hex (color de fondo
de la tarjeta / pase digital de fidelidad).
Alineado con backend/app/models/tenant.py y database/schema.sql.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "puntos_meta",
            sa.Integer(),
            server_default=sa.text("10"),
            nullable=False,
            comment="Estrellas necesarias para obtener una sesión gratuita",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "premio_fidelidad",
            sa.String(length=255),
            server_default="Sesión de Spa gratis",
            nullable=False,
            comment="Premio que se otorga al alcanzar las estrellas meta",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "tarjeta_color_hex",
            sa.String(length=9),
            server_default="#0D9488",
            nullable=False,
            comment="Color de fondo de la tarjeta de fidelidad (pase digital)",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "tarjeta_color_hex")
    op.drop_column("tenants", "premio_fidelidad")
    op.drop_column("tenants", "puntos_meta")