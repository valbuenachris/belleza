# ============================================================
# frontend/Dockerfile - Imagen Nginx para frontend estático
# Sirve HTML5 + CSS3 + JavaScript vanilla
# ============================================================

# Imagen base Alpine (más ligera)
FROM nginx:1.25-alpine

# Metadata
LABEL maintainer="SPA Management System"
LABEL description="Frontend estático servido por Nginx"

# Directorio de trabajo
WORKDIR /usr/share/nginx/html

# Eliminar archivos por defecto de Nginx
RUN rm -rf /usr/share/nginx/html/*

# Copiar todos los archivos estáticos del frontend
COPY . .

# Copiar configuración personalizada de Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exponer puerto 80
EXPOSE 80

# Healthcheck - Verifica que Nginx responda
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost:80/ || exit 1

# Comando por defecto de Nginx
CMD ["nginx", "-g", "daemon off;"]
