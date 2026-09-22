"""google_wallet_* columns en patients (integración Google Wallet)

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-22

Añade a patients las columnas de la integración REAL con Google Wallet
API (LoyaltyClass / LoyaltyObject):

- google_wallet_object_id: id del LoyaltyObject creado en Google Wallet
  (formato "{issuer_id}.{patient_id}"). Se persiste para no duplicar
  objetos y para el diagnóstico (estado/sincronización).
- google_wallet_class_id: id del LoyaltyClass usado (per-tenant,
  "{issuer_id}.loyalty-class-{tenant_id}").
- google_wallet_updated_at DATETIME(6): última sincronización exitosa
  con Google Wallet (diagnóstico; mismo fsp=6 que wallet_updated_at).

No es destructiva y no afecta al flujo de Apple Wallet. Alineado con
backend/app/models/patient.py y database/schema.sql.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column(
            "google_wallet_object_id",
            sa.String(length=255),
            nullable=True,
            comment=(
                "Id del LoyaltyObject en Google Wallet "
                "(formato {issuer_id}.{patient_id})."
            ),
        ),
    )
    op.add_column(
        "patients",
        sa.Column(
            "google_wallet_class_id",
            sa.String(length=255),
            nullable=True,
            comment=(
                "Id del LoyaltyClass usado para este objeto "
                "(per-tenant: {issuer_id}.loyalty-class-{tenant_id})."
            ),
        ),
    )
    op.add_column(
        "patients",
        sa.Column(
            "google_wallet_updated_at",
            mysql.DATETIME(fsp=6),
            nullable=True,
            comment=(
                "Última sincronización exitosa con Google Wallet "
                "(para diagnóstico)."
            ),
        ),
    )
    op.create_unique_constraint(
        "ux_patients_google_wallet_object",
        "patients",
        ["google_wallet_object_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "ux_patients_google_wallet_object", "patients", type_="unique"
    )
    op.drop_column("patients", "google_wallet_updated_at")
    op.drop_column("patients", "google_wallet_class_id")
    op.drop_column("patients", "google_wallet_object_id")