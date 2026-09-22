# ============================================================
# backend/app/config.py - Configuración de la aplicación
# Carga variables de entorno usando pydantic-settings
# ============================================================

import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """
    Configuración global de la aplicación.
    Carga automáticamente desde variables de entorno y archivo .env.
    """
    
    # ----------------------------------------------------------
    # Base de Datos MySQL
    # ----------------------------------------------------------
    DB_HOST: str = "mysql"
    DB_PORT: int = 3306
    DB_USER: str = "spa_user"
    DB_PASSWORD: str = "spa_secure_password"
    DB_NAME: str = "spa_management"
    
    # ----------------------------------------------------------
    # JWT - Autenticación
    # ----------------------------------------------------------
    SECRET_KEY: str = "cambiar-esta-clave-en-produccion-por-una-clave-segura"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ----------------------------------------------------------
    # Aplicación
    # ----------------------------------------------------------
    APP_NAME: str = "SPA Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "production"
    # Habilita /docs, /redoc y /openapi.json de forma explícita.
    # En producción están deshabilitados salvo que ENABLE_DOCS=true.
    ENABLE_DOCS: bool = False
    
    # ----------------------------------------------------------
    # CORS - Orígenes permitidos
    # No usar "*" con allow_credentials=True.
    # Lista separada por comas: esquema+host (sin ruta).
    # ----------------------------------------------------------
    CORS_ORIGINS: str = (
        "http://localhost,http://localhost:80,http://localhost:8088,"
        "http://localhost:5173,http://127.0.0.1,http://127.0.0.1:8088,"
        "http://127.0.0.1:5173"
    )
    # Regex para orígenes locales (cualquier puerto): útil en desarrollo y
    # cuando el frontend se sirve desde localhost/127.0.0.1. Se combina con
    # CORS_ORIGINS, por lo que no reemplaza a los dominios de producción.
    CORS_ORIGIN_REGEX: str = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    
    # ----------------------------------------------------------
    # Tenant por defecto
    # ----------------------------------------------------------
    DEFAULT_TENANT_ID: str = "00000000-0000-0000-0000-000000000001"
    
    # ----------------------------------------------------------
    # Redis
    # ----------------------------------------------------------
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    
    # ----------------------------------------------------------
    # Docker
    # ----------------------------------------------------------
    DOCKER_ENV: bool = False
    
    # ----------------------------------------------------------
    # Configuración de pydantic-settings
    # ----------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # ----------------------------------------------------------
    # Propiedades derivadas
    # ----------------------------------------------------------
    
    @property
    def DATABASE_URL(self) -> str:
        """
        Construye la URL de conexión a MySQL dinámicamente.
        Formato: mysql+pymysql://user:password@host:port/database
        """
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )
    
    @property
    def REDIS_URL(self) -> str:
        """URL de conexión a Redis."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """
        Convierte la cadena de CORS_ORIGINS en una lista.
        Separa por comas y elimina espacios.
        """
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    @property
    def is_docker(self) -> bool:
        """Detecta si está corriendo dentro de Docker."""
        return self.DOCKER_ENV or os.path.exists("/.dockerenv")
    
    @property
    def is_production(self) -> bool:
        """Detecta si está en entorno de producción."""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def docs_available(self) -> bool:
        """
        Indica si la documentación interactiva (/docs, /redoc, /openapi.json)
        debe estar habilitada.
        
        Se habilita cuando:
        - ENABLE_DOCS=true (flag explícito), o
        - el entorno NO es producción (desarrollo/QA)
        """
        return self.ENABLE_DOCS or not self.is_production
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Valida que la clave secreta sea segura en producción."""
        if os.getenv("ENVIRONMENT", "").lower() == "production":
            if len(v) < 32 or v == "cambiar-esta-clave-en-produccion-por-una-clave-segura":
                import warnings
                warnings.warn(
                    "SECRET_KEY debe ser una clave segura de al menos 32 caracteres en producción",
                    UserWarning
                )
        return v


# ============================================================
# Instancia singleton de configuración
# ============================================================
settings = Settings()
