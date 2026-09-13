# ============================================================
# backend/Dockerfile - Imagen multi-stage optimizada para producción
# Sistema de Gestión SPA - Backend FastAPI
# ============================================================

# ------------------------------------------------------------
# Stage 1: Builder - Instala dependencias Python
# ------------------------------------------------------------
FROM python:3.11-slim AS builder

# Directorio de trabajo para la instalación
WORKDIR /build

# Copiar solo el archivo de dependencias (aprovecha cache de Docker)
COPY requirements.txt .

# Instalar dependencias en el directorio del usuario
# --no-cache-dir reduce el tamaño de la imagen
# --user instala en ~/.local para no necesitar root
RUN pip install --no-cache-dir --user -r requirements.txt

# ------------------------------------------------------------
# Stage 2: Final - Imagen de producción mínima
# ------------------------------------------------------------
FROM python:3.11-slim

# Metadata de la imagen
LABEL maintainer="SPA Management System"
LABEL description="Backend FastAPI para gestión integral de SPAs"
LABEL version="1.0.0"

# Crear usuario no-root para seguridad
# UID 1000 es estándar para usuarios de aplicación
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 -d /home/appuser -s /sbin/nologin appuser && \
    mkdir -p /home/appuser && \
    chown -R appuser:appuser /home/appuser

# Instalar curl para healthchecks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Directorio de trabajo de la aplicación
WORKDIR /app

# Copiar dependencias instaladas desde el builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copiar código fuente de la aplicación
COPY --chown=appuser:appuser ./app ./app

# Copiar configuración de Alembic para migraciones
COPY --chown=appuser:appuser ./alembic.ini ./

# Variables de entorno para optimización de Python
# PYTHONUNBUFFERED=1 - No buffer en stdout/stderr (importante para Docker logs)
# PYTHONDONTWRITEBYTECODE=1 - No generar archivos .pyc
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Puerto que expone la aplicación
EXPOSE 8000

# Healthcheck - Verifica que la API responda correctamente
# --start-period da tiempo para que la app se inicialice
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Ejecutar como usuario no-root (seguridad)
USER appuser

# Comando de producción con Gunicorn + Uvicorn workers
# -w 4: 4 workers (ajustar según CPU disponible)
# -k uvicorn.workers.UvicornWorker: worker ASGI para FastAPI
# --bind 0.0.0.0:8000: escuchar en todas las interfaces
# --access-logfile - : logs de acceso a stdout (Docker los captura)
# --error-logfile - : logs de error a stderr (Docker los captura)
CMD ["gunicorn", "app.main:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--timeout", "120", \
     "--keep-alive", "5"]
