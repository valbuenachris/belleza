# ============================================================
# backend/alembic/env.py - Entorno de ejecución de Alembic
# Configura migraciones on-line/off-line usando los modelos y
# la configuración de la aplicación (app.config.settings).
# ============================================================

import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Asegurar que el paquete app sea importable
# (en el contenedor, PYTHONPATH=/app; localmente se puede
#  ejecutar con: alembic -c alembic.ini upgrade head)
sys.path.insert(0, ".")

from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402

# Importar los modelos para que se registren en Base.metadata
from app.models import tenant, user, patient, service, appointment, clinical_record, pass_registration, assistant  # noqa: E402, F401

# ------------------------------------------------------------
# Configuración de Alembic
# ------------------------------------------------------------
config = context.config

# Inyectar la URL real de la base de datos desde la aplicación
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configurar logging según alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ------------------------------------------------------------
# Migraciones offline (generar SQL con -sql)
# ------------------------------------------------------------
def run_migrations_offline() -> None:
    """Ejecuta las migraciones en modo 'offline' (genera SQL)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ------------------------------------------------------------
# Migraciones online (ejecutar directamente contra la BD)
# ------------------------------------------------------------
def run_migrations_online() -> None:
    """Ejecuta las migraciones en modo 'online' (conectado a la BD)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()