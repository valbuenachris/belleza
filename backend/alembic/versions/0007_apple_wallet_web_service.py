"""apple wallet web service (wallet_auth_token, wallet_updated_at, pass_registrations)

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-22

Agrega el soporte del Apple Wallet Web Service para actualizar los
pases dinámicamente cuando cambian las estrellas/sesiones:

- patients.wallet_auth_token: authenticationToken que el dispositivo
  envía en la cabecera 'Authorization: ApplePass <token>' (requerido
  si el pase declara webServiceURL).
- patients.wallet_updated_at: marca de última actualización de
  puntos/sesiones, usada con If-Modified-Since / Last-Modified.
- pass_registrations: dispositivos registrados para recibir el pase
  y sus push tokens APNs (para notificar cambios).

Alineado con backend/app/models/{patient,pass_registration}.py y
con database/schema.sql.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column(
            "wallet_auth_token",
            sa.String(length=128),
            nullable=True,
            comment="authenticationToken del pase (cabecera ApplePass del web service)",
        ),
    )
    op.create_index(
        "ux_patients_wallet_auth",
        "patients",
        ["wallet_auth_token"],
        unique=True,
    )
    op.add_column(
        "patients",
        sa.Column(
            "wallet_updated_at",
            sa.DateTime(),
            nullable=True,
            comment="Última actualización de puntos/sesiones (Last-Modified / If-Modified-Since)",
        ),
    )

    op.create_table(
        "pass_registrations",
        sa.Column("id", sa.CHAR(length=36), nullable=False, comment="Identificador único UUID4"),
        sa.Column(
            "tenant_id",
            sa.CHAR(length=36),
            nullable=False,
            comment="ID del tenant al que pertenece este registro",
        ),
        sa.Column("patient_id", sa.String(length=36), nullable=False, comment="Paciente dueño del pase"),
        sa.Column(
            "pass_type_identifier",
            sa.String(length=128),
            nullable=False,
            comment="passTypeIdentifier del pase (p.ej. pass.com.tuuspa.fidelidad)",
        ),
        sa.Column(
            "serial_number",
            sa.String(length=128),
            nullable=False,
            comment="serialNumber del pase (wallet_pass_id del paciente)",
        ),
        sa.Column(
            "device_library_identifier",
            sa.String(length=255),
            nullable=False,
            comment="Identificador único del dispositivo en Apple Wallet",
        ),
        sa.Column(
            "push_token",
            sa.String(length=255),
            nullable=True,
            comment="Token APNs del dispositivo para notificar actualizaciones del pase",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True, comment="Soft delete timestamp"),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "device_library_identifier",
            "pass_type_identifier",
            "serial_number",
            name="ux_pass_registration",
        ),
    )
    op.create_index("idx_pass_reg_tenant", "pass_registrations", ["tenant_id"])
    op.create_index("idx_pass_reg_patient", "pass_registrations", ["patient_id"])
    op.create_index("idx_pass_reg_device", "pass_registrations", ["device_library_identifier"])


def downgrade() -> None:
    op.drop_index("idx_pass_reg_device", table_name="pass_registrations")
    op.drop_index("idx_pass_reg_patient", table_name="pass_registrations")
    op.drop_index("idx_pass_reg_tenant", table_name="pass_registrations")
    op.drop_table("pass_registrations")
    op.drop_column("patients", "wallet_updated_at")
    op.drop_index("ux_patients_wallet_auth", table_name="patients")
    op.drop_column("patients", "wallet_auth_token")