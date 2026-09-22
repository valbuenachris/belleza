"""backfill default tenant config

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-21

Rellena la columna configuracion de los tenants existentes que la
tienen NULL con la configuración por defecto (equivalente a
TenantConfig()), para que horarios, onboarding y notificaciones
tengan valores consistentes con los nuevos registros.
"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_CONFIG = {
    "horario_apertura": "08:00",
    "horario_cierre": "20:00",
    "dias_operacion": [1, 2, 3, 4, 5, 6],
    "duracion_cita_default": 60,
    "recordatorio_citas": True,
    "confirmacion_citas": True,
}


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE tenants SET configuracion = CAST(:cfg AS JSON) "
            "WHERE configuracion IS NULL AND deleted_at IS NULL"
        ),
        {"cfg": json.dumps(DEFAULT_CONFIG)},
    )


def downgrade() -> None:
    # El backfill no se revierte: no hay forma segura de restaurar qué
    # tenants tenían configuracion NULL (no-op intencional).
    pass