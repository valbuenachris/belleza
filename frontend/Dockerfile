# ============================================================
# frontend/Dockerfile - Build React App & Serve with Nginx
# ============================================================

# Paso 1: Construir la aplicación de React usando Node 20 (Slim)
FROM node:20-slim AS builder

WORKDIR /app

# Copiar UNICAMENTE package.json para evitar conflictos de bloqueo de plataforma (lockfile bug)
COPY package.json ./

# Instalar dependencias limpias para el entorno actual
RUN npm install --legacy-peer-deps

# Copiar el código fuente de React y su configuración
COPY index.html tsconfig.json vite.config.js ./
COPY src/ ./src/

# Construir para producción sin heredar bindings corruptos
RUN npm run build

# Paso 2: Servir con Nginx (Alpine para que la imagen final sea ultra ligera)
FROM nginx:1.25-alpine

# Copiar los archivos compilados desde el builder al directorio de Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar configuración personalizada de Nginx
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
