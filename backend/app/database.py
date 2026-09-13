# ============================================================
# backend/app/database.py - Conexión a base de datos SQLAlchemy
# Configuración del motor, sesión y utilidades de inicialización
# ============================================================

import logging
import time
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool

from .config import settings

# Logger para mensajes de la base de datos
logger = logging.getLogger(__name__)


# ============================================================
# Motor de base de datos (Engine)
# ============================================================

# Configuración del pool de conexiones
# pool_size: número de conexiones persistentes en el pool
# max_overflow: conexiones adicionales permitidas cuando el pool está lleno
# pool_pre_ping: verifica que las conexiones estén vivas antes de usarlas
# pool_recycle: recicla conexiones cada 3600s (importante para Docker/MySQL)
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,
    echo=settings.DEBUG,  # Solo log SQL en modo debug
    connect_args={
        "charset": "utf8mb4",
        "connect_timeout": 10,
    },
)


# ============================================================
# SessionLocal - Fábrica de sesiones de base de datos
# ============================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


# ============================================================
# Base declarativa para los modelos
# ============================================================

class Base(DeclarativeBase):
    """
    Clase base para todos los modelos SQLAlchemy.
    Todos los modelos del sistema deben heredar de esta clase.
    """
    pass


# ============================================================
# Funciones de utilidad
# ============================================================

def get_db() -> Generator:
    """
    Generador para inyección de dependencias de FastAPI.
    Proporciona una sesión de base de datos y la cierra al finalizar.
    
    Uso en endpoints:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> bool:
    """
    Verifica que la conexión a la base de datos esté disponible.
    Retorna True si la conexión es exitosa, False en caso contrario.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Error al verificar conexión a DB: {e}")
        return False


def create_tables() -> None:
    """
    Crea todas las tablas definidas en los modelos.
    IMPORTANTE: En producción se recomienda usar Alembic para migraciones.
    Esto es útil solo para desarrollo y pruebas.
    """
    try:
        # Importar todos los modelos para que se registren en Base.metadata
        from .models import tenant, user  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas creadas/verificadas exitosamente")
    except Exception as e:
        logger.error(f"Error al crear tablas: {e}")
        raise


def init_db(max_retries: int = 30, retry_delay: int = 2) -> None:
    """
    Inicializa la base de datos con lógica de reintentos.
    Especialmente útil en Docker donde MySQL puede tardar en estar listo.
    
    Args:
        max_retries: Número máximo de intentos de conexión
        retry_delay: Segundos entre cada intento
    """
    logger.info("Inicializando base de datos...")
    
    for attempt in range(1, max_retries + 1):
        try:
            if check_connection():
                logger.info(f"Conexión a base de datos exitosa (intento {attempt})")
                create_tables()
                return
        except Exception as e:
            logger.warning(
                f"Intento {attempt}/{max_retries} - "
                f"Base de datos no disponible: {e}"
            )
        
        if attempt < max_retries:
            logger.info(f"Reintentando en {retry_delay} segundos...")
            time.sleep(retry_delay)
    
    # Si llegamos aquí, no se pudo conectar después de todos los intentos
    raise RuntimeError(
        f"No se pudo conectar a la base de datos después de {max_retries} intentos. "
        f"Verifica que MySQL esté corriendo y accesible."
    )
