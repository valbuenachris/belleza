"""wallet_updated_at con precisión de microsegundos (DATETIME(6))

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-22

La cabecera HTTP Last-Modified (y la comparación If-Modified-Since del
Apple Wallet Web Service) usa patients.wallet_updated_at como tag de
actualización. Con DATETIME (precisión de 1 segundo), dos escaneos que
suman estrellas dentro del mismo segundo producen el MISMO tag, y el
dispositivo responde 304 Not Modified sin descargar el pase actualizado.

DATETIME(6) guarda microsegundos, eliminando la colisión práctica y
haciendo que cada cambio de puntos/sesiones avance el tag.

Alineado con backend/app/models/patient.py y database/schema.sql.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "patients",
        "wallet_updated_at",
        existing_type=sa.DateTime(),
        type_=mysql.DATETIME(fsp=6),
        existing_nullable=True,
        comment="Última actualización de puntos/sesiones (Last-Modified / If-Modified-Since)",
    )


def downgrade() -> None:
    op.alter_column(
        "patients",
        "wallet_updated_at",
        existing_type=mysql.DATETIME(fsp=6),
        type_=sa.DateTime(),
        existing_nullable=True,
        comment="Última actualización de puntos/sesiones (Last-Modified / If-Modified-Since)",
    )