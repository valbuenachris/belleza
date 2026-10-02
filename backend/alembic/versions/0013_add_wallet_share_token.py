"""add wallet_share_token to patients

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-02

Añade el token de capacidad y la expiración del enlace público de la
tarjeta de fidelidad (/tarjeta/{token}), que permite al CLIENTE instalar
su tarjeta en su propio Apple/Google Wallet sin iniciar sesión.

- `wallet_share_token`: CSPRNG de 64 caracteres, único (NULL si no hay
  enlace activo; MySQL permite múltiples NULL en un UNIQUE).
- `wallet_share_expires_at`: expiración del enlace (7 días por defecto,
  renovable desde el panel del personal).

Alineado con backend/app/models/patient.py y database/schema.sql.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column(
            "wallet_share_token",
            sa.String(length=64),
            nullable=True,
            comment="Token de capacidad del enlace público /tarjeta/{token} (CSPRNG)",
        ),
    )
    op.add_column(
        "patients",
        sa.Column(
            "wallet_share_expires_at",
            sa.DateTime(),
            nullable=True,
            comment="Expiración del enlace público de la tarjeta (NULL = sin enlace activo)",
        ),
    )
    op.create_unique_constraint(
        "ux_patients_wallet_share",
        "patients",
        ["wallet_share_token"],
    )


def downgrade() -> None:
    op.drop_constraint("ux_patients_wallet_share", "patients", type_="unique")
    op.drop_column("patients", "wallet_share_expires_at")
    op.drop_column("patients", "wallet_share_token")
