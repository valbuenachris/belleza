"""patients, services, appointments

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-20

Crea las tablas patients, services y appointments, alineadas con
los modelos SQLAlchemy de backend/app/models/ y con database/schema.sql.
Incluye las claves foráneas (paciente -> terapeuta -> servicio) y los
índices de tenant necesarios para multitenancy.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------
    # Tabla: patients
    # ------------------------------------------------------------
    op.create_table(
        "patients",
        sa.Column("id", sa.CHAR(length=36), nullable=False, comment="UUID del paciente"),
        sa.Column("tenant_id", sa.CHAR(length=36), nullable=False, comment="FK al tenant"),
        sa.Column("nombre", sa.String(length=100), nullable=False, comment="Nombre del paciente"),
        sa.Column("apellido", sa.String(length=100), nullable=False, comment="Apellido del paciente"),
        sa.Column("email", sa.String(length=255), nullable=True, comment="Email de contacto"),
        sa.Column("telefono", sa.String(length=50), nullable=True, comment="Teléfono"),
        sa.Column("fecha_nacimiento", sa.Date(), nullable=True, comment="Fecha de nacimiento"),
        sa.Column("genero", sa.String(length=30), nullable=True, comment="Género"),
        sa.Column("direccion", sa.String(length=500), nullable=True, comment="Dirección"),
        sa.Column("notas_medicas", sa.Text(), nullable=True, comment="Notas médicas o alergias"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True, comment="Soft delete timestamp"),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE", onupdate="CASCADE", name="fk_patients_tenant"),
        mysql_engine="InnoDB",
        mysql_default_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="Tabla de pacientes del SPA",
    )
    op.create_index("idx_tenant_active", "patients", ["tenant_id", "is_active"])
    op.create_index("idx_patients_tenant", "patients", ["tenant_id"])
    op.create_index("idx_patients_email", "patients", ["email"])
    op.create_index("idx_patients_deleted", "patients", ["deleted_at"])

    # ------------------------------------------------------------
    # Tabla: services
    # ------------------------------------------------------------
    op.create_table(
        "services",
        sa.Column("id", sa.CHAR(length=36), nullable=False, comment="UUID del servicio"),
        sa.Column("tenant_id", sa.CHAR(length=36), nullable=False, comment="FK al tenant"),
        sa.Column("nombre", sa.String(length=255), nullable=False, comment="Nombre del servicio"),
        sa.Column("descripcion", sa.Text(), nullable=True, comment="Descripción del servicio"),
        sa.Column("precio", sa.Numeric(10, 2), server_default="0.00", nullable=False, comment="Precio del servicio"),
        sa.Column("duracion", sa.Integer(), server_default="60", nullable=False, comment="Duración en minutos"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True, comment="Soft delete timestamp"),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE", onupdate="CASCADE", name="fk_services_tenant"),
        mysql_engine="InnoDB",
        mysql_default_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="Tabla de servicios del catálogo del SPA",
    )
    op.create_index("idx_tenant_active", "services", ["tenant_id", "is_active"])
    op.create_index("idx_services_tenant", "services", ["tenant_id"])
    op.create_index("idx_services_deleted", "services", ["deleted_at"])

    # ------------------------------------------------------------
    # Tabla: appointments
    # ------------------------------------------------------------
    op.create_table(
        "appointments",
        sa.Column("id", sa.CHAR(length=36), nullable=False, comment="UUID de la cita"),
        sa.Column("tenant_id", sa.CHAR(length=36), nullable=False, comment="FK al tenant"),
        sa.Column("patient_id", sa.CHAR(length=36), nullable=False, comment="FK al paciente"),
        sa.Column("therapist_id", sa.CHAR(length=36), nullable=False, comment="FK al terapeuta (usuarios)"),
        sa.Column("service_id", sa.CHAR(length=36), nullable=False, comment="FK al servicio"),
        sa.Column("date_time", sa.DateTime(), nullable=False, comment="Fecha y hora de inicio"),
        sa.Column("duracion", sa.Integer(), server_default="60", nullable=False, comment="Duración en minutos"),
        sa.Column("estado", sa.String(length=30), server_default="pending", nullable=False, comment="pending, confirmed, cancelled, completed"),
        sa.Column("precio", sa.Numeric(10, 2), nullable=True, comment="Precio cobrado (si es null se usa el del servicio)"),
        sa.Column("notas", sa.Text(), nullable=True, comment="Notas adicionales"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True, comment="Soft delete timestamp"),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE", onupdate="CASCADE", name="fk_appointments_tenant"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE", onupdate="CASCADE", name="fk_appointments_patient"),
        sa.ForeignKeyConstraint(["therapist_id"], ["users.id"], ondelete="CASCADE", onupdate="CASCADE", name="fk_appointments_therapist"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE", onupdate="CASCADE", name="fk_appointments_service"),
        mysql_engine="InnoDB",
        mysql_default_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="Tabla de citas agendadas en el SPA",
    )
    op.create_index("idx_tenant_active", "appointments", ["tenant_id", "is_active"])
    op.create_index("idx_appointments_tenant", "appointments", ["tenant_id"])
    op.create_index("idx_appointments_patient", "appointments", ["patient_id"])
    op.create_index("idx_appointments_therapist", "appointments", ["therapist_id"])
    op.create_index("idx_appointments_service", "appointments", ["service_id"])
    op.create_index("idx_appointments_date_time", "appointments", ["date_time"])
    op.create_index("idx_appointments_estado", "appointments", ["estado"])
    op.create_index("idx_appointments_deleted", "appointments", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("idx_appointments_deleted", table_name="appointments")
    op.drop_index("idx_appointments_estado", table_name="appointments")
    op.drop_index("idx_appointments_date_time", table_name="appointments")
    op.drop_index("idx_appointments_service", table_name="appointments")
    op.drop_index("idx_appointments_therapist", table_name="appointments")
    op.drop_index("idx_appointments_patient", table_name="appointments")
    op.drop_index("idx_appointments_tenant", table_name="appointments")
    op.drop_index("idx_tenant_active", table_name="appointments")
    op.drop_table("appointments")

    op.drop_index("idx_services_deleted", table_name="services")
    op.drop_index("idx_services_tenant", table_name="services")
    op.drop_index("idx_tenant_active", table_name="services")
    op.drop_table("services")

    op.drop_index("idx_patients_deleted", table_name="patients")
    op.drop_index("idx_patients_email", table_name="patients")
    op.drop_index("idx_patients_tenant", table_name="patients")
    op.drop_index("idx_tenant_active", table_name="patients")
    op.drop_table("patients")