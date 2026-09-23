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
    # Apple Wallet Web Service (actualización dinámica de pases)
    # ----------------------------------------------------------
    # URL base pública del web service de Apple (sin barra final, https).
    # Debe apuntar a la raíz del backend expuesto públicamente; nginx debe
    # proxear /v1/* al contenedor del backend (ver frontend/nginx.conf).
    WALLET_WEB_SERVICE_BASE_URL: str = "https://estetica.tienderu.com"
    # APNs (Apple Push Notification Service). El push es lo que dispara
    # la descarga automática del pase actualizado en el dispositivo.
    # Si se deja APNS_ENABLED=false pero se configuran las credenciales
    # .p8, el push se ACTIVA automáticamente (auto-detección).
    APNS_ENABLED: bool = False
    APNS_SANDBOX: bool = False
    # JWT de proveedor (AuthKey_<id>.p8 que descargas de APNs Keys).
    APNS_KEY_ID: str = ""
    APNS_TEAM_ID: str = ""
    APNS_P8_PATH: str = ""
    # Topic del push = passTypeIdentifier del pase (NO el bundle del app).
    APNS_TOPIC: str = "pass.com.tuuspa.fidelidad"
    # Cabecera apns-push-type: para pases se usa 'background' (push
    # silencioso sin interacción del usuario). 'passkit-update' NO es un
    # valor válido y APNs lo rechaza con 400 BadPushType.
    APNS_PUSH_TYPE: str = "background"
    # apns-priority: para push-type=background DEBE ser 5; 10 es error.
    APNS_PRIORITY: int = 5
    # TTL en segundos del push (APNs lo guarda si el dispositivo está
    # offline y lo entrega al reconectarse). 0 = descartar si offline.
    APNS_EXPIRATION: int = 86400

    # ----------------------------------------------------------
    # Firma del .pkpass (PKCS#7/CMS DER)
    # ----------------------------------------------------------
    # OPCIONAL: si se configuran los tres archivos, el pase se genera
    # firmado (Apple exige la firma en producción). Sin ellos el pase se
    # genera sin firma (para pruebas/dev) con un warning en los logs.
    #   PASS_SIGNER_CERT_PATH -> certificado del Pass Type ID (PEM)
    #   PASS_SIGNER_KEY_PATH  -> clave privada del certificado (PEM)
    #   PASS_WWDR_CERT_PATH   -> certificado intermedio WWDR de Apple (PEM)
    PASS_SIGNER_CERT_PATH: str = ""
    PASS_SIGNER_KEY_PATH: str = ""
    PASS_WWDR_CERT_PATH: str = ""

    # ----------------------------------------------------------
    # Google Wallet (LoyaltyClass / LoyaltyObject - REST API)
    # ----------------------------------------------------------
    # Integración real con Google Wallet API v1 (walletobjects). Habilita
    # crear la clase de fidelidad y objetos por paciente, generar el enlace
    # "Añadir a Google Wallet" (savetowallet JWT) y sincronizar puntos en
    # tiempo real (PATCH + notifyPreference). Mientras no haya credenciales
    # reales de Google Cloud, GOOGLE_WALLET_ENABLED=false: el sistema opera
    # igual (solo Apple Wallet .pkpass) sin llamar a ninguna API de Google.
    GOOGLE_WALLET_ENABLED: bool = False
    # ID del emisor (issuer id) que entrega Google Cloud en "Google Wallet
    # API" -> "Issuer account". Es un número; NUNCA se debe inventar.
    GOOGLE_WALLET_ISSUER_ID: str = ""
    # Id de la clase de fidelidad. Si se deja vacío, se genera automáticamente
    # por tenant (recomendado): "{issuer}.loyalty-class-{tenant_id}".
    GOOGLE_WALLET_CLASS_ID: str = ""
    # Cuenta de servicio de Google Cloud (email del .json de credenciales).
    GOOGLE_WALLET_SERVICE_ACCOUNT_EMAIL: str = ""
    # Clave privada RSA de la cuenta de servicio. Se acepta el PEM tal cual
    # (con saltos de línea) o codificado en base64 (del .json de credenciales).
    GOOGLE_WALLET_PRIVATE_KEY: str = ""
    GOOGLE_WALLET_PRIVATE_KEY_ID: str = ""
    GOOGLE_WALLET_PROJECT_ID: str = ""
    # Ruta al .json de la cuenta de servicio para Application Default
    # Credentials (ADC estándar de google-auth). Es la vía preferida: el
    # archivo se monta como volumen de solo lectura en el contenedor.
    # Prioridad frente a GOOGLE_WALLET_SERVICE_ACCOUNT_FILE / PRIVATE_KEY.
    GOOGLE_APPLICATION_CREDENTIALS: str = "/app/google-credentials/service-account.json"
    # Alternativa: ruta al archivo .json de la cuenta de servicio (montado
    # como secret/volume) si se prefiere una ruta distinta de la ADC.
    GOOGLE_WALLET_SERVICE_ACCOUNT_FILE: str = ""
    # Scope OAuth2 para crear/con servers de wallet objects (valor oficial).
    GOOGLE_WALLET_SCOPE: str = (
        "https://www.googleapis.com/auth/wallet_object.issuer"
    )
    # Dominio permitido para el botón de guardado (claim "origins" del JWT).
    # Vacío => se deriva del host de WALLET_WEB_SERVICE_BASE_URL.
    GOOGLE_WALLET_ORIGIN: str = ""
    # Endpoints de la API de Google (valores oficiales; overridable para QA).
    GOOGLE_WALLET_API_BASE: str = (
        "https://walletobjects.googleapis.com/walletobjects/v1"
    )
    GOOGLE_WALLET_OAUTH_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_WALLET_SAVE_BASE_URL: str = "https://pay.google.com/gp/v/save"

    # ----------------------------------------------------------
    # Asistente IA (FreeLLMAPI - apifreellm.com)
    # ----------------------------------------------------------
    # Asistente de IA para resolver consultas de clientes, dar
    # recomendaciones de servicios y explicar el programa de fidelidad.
    # Integración con FreeLLMAPI (https://apifreellm.com): endpoint
    #   POST {FREELLMAPI_BASE_URL}/chat
    #   Authorization: Bearer {FREELLMAPI_API_KEY}
    #   Body: {"message": "pregunta", "model": "opcional"}
    #   Respuesta: {"success": true, "response": "texto"}
    # Mientras no haya una API key real, FREELLMAPI_ENABLED=false: los
    # endpoints responden 400/disabled y el resto de la app opera igual.
    FREELLMAPI_ENABLED: bool = False
    # API key de FreeLLMAPI (se obtiene registrándose en apifreellm.com
    # con una cuenta de Google). Se envía como Bearer token. NUNCA se
    # registra en logs ni se expone en el frontend.
    FREELLMAPI_API_KEY: str = ""
    # URL base de la API (incluye el prefijo /api/v1). Overridable para
    # apuntar a una instancia propia/proxy de FreeLLMAPI.
    FREELLMAPI_BASE_URL: str = "https://apifreellm.com/api/v1"
    # Modelo opcional (la API usa su modelo por defecto si se omite).
    FREELLMAPI_MODEL: str = ""
    # Timeout en segundos de cada llamada al proveedor (evita bloquear
    # el request del chat ante una respuesta lenta de la IA).
    FREELLMAPI_TIMEOUT: int = 60

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
