"""clinical_records (historia clínica)

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-22

Crea la tabla clinical_records (historia clínica / evoluciones de
tratamiento), alineada con el modelo SQLAlchemy de
backend/app/models/clinical_record.py y con database/schema.sql.
Incluye las claves foráneas (paciente, terapeuta, cita) y los índices
de tenant necesarios para multitenancy.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------
    # Tabla: clinical_records
    # ------------------------------------------------------------
    op.create_table(
        "clinical_records",
        sa.Column("id", sa.CHAR(length=36), nullable=False, comment="UUID del registro"),
        sa.Column("tenant_id", sa.CHAR(length=36), nullable=False, comment="FK al tenant"),
        sa.Column("patient_id", sa.CHAR(length=36), nullable=False, comment="FK al paciente"),
        sa.Column("therapist_id", sa.CHAR(length=36), nullable=True, comment="FK al terapeuta (usuarios)"),
        sa.Column("appointment_id", sa.CHAR(length=36), nullable=True, comment="FK a la cita/sesión asociada"),
        sa.Column("fecha", sa.DateTime(), nullable=False, comment="Fecha y hora de la sesión/evolución"),
        sa.Column("zona_tratada", sa.String(length=255), nullable=True, comment="Zona tratada (ej: Rostro, Espalda)"),
        sa.Column("tratamiento_servicio", sa.String(length=255), nullable=True, comment="Tratamiento o servicio realizado"),
        sa.Column("productos_parametros", sa.Text(), nullable=True, comment="Productos aplicados / parámetros"),
        sa.Column("observaciones", sa.Text(), nullable=True, comment="Observaciones y evolución del paciente"),
        sa.Column("diagnostico", sa.Text(), nullable=True, comment="Diagnóstico o valoración clínica"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True, comment="Soft delete timestamp"),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE", onupdate="CASCADE", name="fk_clinical_records_tenant"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE", onupdate="CASCADE", name="fk_clinical_records_patient"),
        sa.ForeignKeyConstraint(["therapist_id"], ["users.id"], ondelete="SET NULL", onupdate="CASCADE", name="fk_clinical_records_therapist"),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="SET NULL", onupdate="CASCADE", name="fk_clinical_records_appointment"),
        mysql_engine="InnoDB",
        mysql_default_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="Tabla de historia clínica / evoluciones de tratamiento",
    )
    op.create_index("idx_tenant_active", "clinical_records", ["tenant_id", "is_active"])
    op.create_index("idx_clinical_records_tenant", "clinical_records", ["tenant_id"])
    op.create_index("idx_clinical_records_patient", "clinical_records", ["patient_id"])
    op.create_index("idx_clinical_records_therapist", "clinical_records", ["therapist_id"])
    op.create_index("idx_clinical_records_appointment", "clinical_records", ["appointment_id"])
    op.create_index("idx_clinical_records_fecha", "clinical_records", ["fecha"])
    op.create_index("idx_clinical_records_deleted", "clinical_records", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("idx_clinical_records_deleted", table_name="clinical_records")
    op.drop_index("idx_clinical_records_fecha", table_name="clinical_records")
    op.drop_index("idx_clinical_records_appointment", table_name="clinical_records")
    op.drop_index("idx_clinical_records_therapist", table_name="clinical_records")
    op.drop_index("idx_clinical_records_patient", table_name="clinical_records")
    op.drop_index("idx_clinical_records_tenant", table_name="clinical_records")
    op.drop_index("idx_tenant_active", table_name="clinical_records")
    op.drop_table("clinical_records")