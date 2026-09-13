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
    
    # ----------------------------------------------------------
    # CORS - Orígenes permitidos
    # ----------------------------------------------------------
    CORS_ORIGINS: str = "http://localhost:80,http://localhost"
    
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
