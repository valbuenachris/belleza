// ============================================================
// Página de Documentación - Arquitectura del Sistema
// ============================================================

import React, { useState } from 'react';
import {
  BookOpen, Server, Database, Container, Shield,
  Code, Terminal, Copy, CheckCircle, Layers, Globe,
  Lock, Cpu, HardDrive, Network
} from 'lucide-react';

export default function DocumentationPage() {
  const [activeSection, setActiveSection] = useState('overview');
  const [copied, setCopied] = useState('');

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(''), 2000);
  };

  const sections = [
    { id: 'overview', label: 'Arquitectura', icon: <Layers size={16} /> },
    { id: 'docker', label: 'Docker', icon: <Container size={16} /> },
    { id: 'backend', label: 'Backend API', icon: <Server size={16} /> },
    { id: 'database', label: 'Base de Datos', icon: <Database size={16} /> },
    { id: 'security', label: 'Seguridad', icon: <Shield size={16} /> },
    { id: 'quickstart', label: 'Inicio Rápido', icon: <Terminal size={16} /> },
  ];

  const CodeBlock = ({ code, id, language = 'bash' }: { code: string; id: string; language?: string }) => (
    <div className="relative group">
      <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={() => copyToClipboard(code, id)}
          className="p-1.5 bg-stone-700 rounded-lg text-stone-300 hover:text-white"
        >
          {copied === id ? <CheckCircle size={14} /> : <Copy size={14} />}
        </button>
      </div>
      <pre className="bg-stone-900 text-stone-100 rounded-xl p-4 text-xs overflow-x-auto leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl lg:text-3xl font-bold text-stone-800">Documentación del Sistema</h1>
        <p className="text-stone-500 mt-1">Arquitectura técnica y guías de implementación</p>
      </div>

      {/* Section tabs */}
      <div className="flex gap-1 bg-white rounded-xl p-1 border border-stone-200 overflow-x-auto">
        {sections.map(section => (
          <button
            key={section.id}
            onClick={() => setActiveSection(section.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
              activeSection === section.id
                ? 'bg-emerald-50 text-emerald-700'
                : 'text-stone-500 hover:text-stone-700 hover:bg-stone-50'
            }`}
          >
            {section.icon}
            {section.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="bg-white rounded-2xl border border-stone-100 p-6 lg:p-8">
        {activeSection === 'overview' && (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-stone-800">Arquitectura del Sistema</h2>
            <p className="text-stone-600">
              El SPA Management System es una aplicación SaaS multitenant diseñada para la gestión integral
              de centros de estética y relajación. Utiliza una arquitectura moderna basada en microservicios
              dockerizados con separación completa de datos entre tenants.
            </p>

            {/* Architecture diagram */}
            <div className="bg-stone-50 rounded-xl p-6 border border-stone-200">
              <h3 className="text-sm font-semibold text-stone-700 mb-4">Diagrama de Arquitectura</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white rounded-xl p-4 border border-stone-200 text-center">
                  <Globe size={24} className="mx-auto text-blue-500 mb-2" />
                  <p className="text-sm font-medium text-stone-800">Nginx Frontend</p>
                  <p className="text-xs text-stone-500 mt-1">Reverse Proxy + Static Files</p>
                  <p className="text-xs text-emerald-600 mt-2">Puerto 80</p>
                </div>
                <div className="bg-white rounded-xl p-4 border border-stone-200 text-center">
                  <Server size={24} className="mx-auto text-emerald-500 mb-2" />
                  <p className="text-sm font-medium text-stone-800">FastAPI Backend</p>
                  <p className="text-xs text-stone-500 mt-1">Python 3.11 + Uvicorn</p>
                  <p className="text-xs text-emerald-600 mt-2">Puerto 8000</p>
                </div>
                <div className="bg-white rounded-xl p-4 border border-stone-200 text-center">
                  <Database size={24} className="mx-auto text-violet-500 mb-2" />
                  <p className="text-sm font-medium text-stone-800">MySQL 8.0</p>
                  <p className="text-xs text-stone-500 mt-1">Base de datos principal</p>
                  <p className="text-xs text-emerald-600 mt-2">Puerto 3306</p>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white rounded-xl p-4 border border-stone-200 text-center">
                  <HardDrive size={24} className="mx-auto text-amber-500 mb-2" />
                  <p className="text-sm font-medium text-stone-800">Redis 7</p>
                  <p className="text-xs text-stone-500 mt-1">Cache + Sesiones</p>
                </div>
                <div className="bg-white rounded-xl p-4 border border-stone-200 text-center">
                  <Network size={24} className="mx-auto text-teal-500 mb-2" />
                  <p className="text-sm font-medium text-stone-800">Docker Network</p>
                  <p className="text-xs text-stone-500 mt-1">Red interna bridge</p>
                </div>
              </div>
            </div>

            {/* Key features */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                { title: 'Multitenancy', desc: 'Base de datos compartida con separación por tenant_id. Middleware automático de filtrado.' },
                { title: 'API REST', desc: 'FastAPI con documentación automática, validación Pydantic v2, y async/await.' },
                { title: 'Autenticación JWT', desc: 'Tokens seguros con python-jose, refresh tokens, y expiración configurable.' },
                { title: 'Dockerizado', desc: 'Todos los servicios en contenedores con healthchecks y redes internas.' },
                { title: 'ORM SQLAlchemy 2.0', desc: 'Modelos con Mapped, mapped_column, y migraciones con Alembic.' },
                { title: 'Seguridad', desc: 'Bcrypt para passwords, CORS configurado, headers de seguridad en Nginx.' },
              ].map((feature, i) => (
                <div key={i} className="p-4 bg-stone-50 rounded-xl">
                  <h4 className="text-sm font-semibold text-stone-800">{feature.title}</h4>
                  <p className="text-xs text-stone-500 mt-1">{feature.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeSection === 'docker' && (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-stone-800">Configuración Docker</h2>
            <p className="text-stone-600">
              El sistema está completamente dockerizado. Basta con ejecutar <code className="bg-stone-100 px-1.5 py-0.5 rounded text-sm">docker-compose up -d</code> para 
              levantar todos los servicios.
            </p>

            <h3 className="text-lg font-semibold text-stone-800">docker-compose.yml</h3>
            <CodeBlock id="docker-compose" code={`# docker-compose.yml - Desarrollo Local
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: spa_backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./backend/app:/app/app  # Hot-reload
    networks:
      - spa_network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: spa_frontend
    ports:
      - "80:80"
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - spa_network
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: spa_mysql
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: root_secure_password
      MYSQL_DATABASE: spa_management
      MYSQL_USER: spa_user
      MYSQL_PASSWORD: spa_secure_password
    volumes:
      - mysql_data:/var/lib/mysql
      - ./database/init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
      - ./database/schema.sql:/docker-entrypoint-initdb.d/02-schema.sql:ro
      - ./database/seed.sql:/docker-entrypoint-initdb.d/03-seed.sql:ro
    command: >
      --default-authentication-plugin=mysql_native_password
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_unicode_ci
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - spa_network
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: spa_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - spa_network
    restart: unless-stopped

  phpmyadmin:
    image: phpmyadmin/phpmyadmin
    container_name: spa_phpmyadmin
    ports:
      - "8080:80"
    environment:
      PMA_HOST: mysql
      PMA_PORT: 3306
      PMA_USER: root
      PMA_PASSWORD: root_secure_password
    depends_on:
      mysql:
        condition: service_healthy
    networks:
      - spa_network
    profiles:
      - development
    restart: unless-stopped

networks:
  spa_network:
    driver: bridge

volumes:
  mysql_data:
    driver: local
  redis_data:
    driver: local`} />

            <h3 className="text-lg font-semibold text-stone-800 mt-8">Backend Dockerfile</h3>
            <CodeBlock id="backend-dockerfile" code={`# backend/Dockerfile - Multi-stage build optimizado
# Stage 1: Builder - Instala dependencias
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Stage 2: Final - Imagen de producción
FROM python:3.11-slim

# Crear usuario no-root para seguridad
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

WORKDIR /app

# Copiar dependencias instaladas del builder
COPY --from=builder /root/.local /home/appuser/.local

# Copiar código de la aplicación
COPY ./app ./app
COPY ./alembic.ini ./

# Variables de entorno
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Healthcheck para Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
  CMD curl -f http://localhost:8000/health || exit 1

# Ejecutar como usuario no-root
USER appuser

# Comando de producción con Gunicorn
CMD gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker \\
  --bind 0.0.0.0:8000 --access-logfile - --error-logfile -`} />
          </div>
        )}

        {activeSection === 'backend' && (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-stone-800">Backend API - Endpoints</h2>
            <p className="text-stone-600">
              API REST construida con FastAPI. Documentación automática disponible en <code className="bg-stone-100 px-1.5 py-0.5 rounded text-sm">/docs</code> (Swagger UI)
              y <code className="bg-stone-100 px-1.5 py-0.5 rounded text-sm">/redoc</code> (ReDoc).
            </p>

            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-stone-700 uppercase tracking-wider">Autenticación</h3>
              {[
                { method: 'POST', path: '/api/v1/auth/login', desc: 'Iniciar sesión con email y contraseña' },
                { method: 'POST', path: '/api/v1/auth/register', desc: 'Registrar nuevo SPA + admin' },
                { method: 'POST', path: '/api/v1/auth/refresh', desc: 'Refrescar token de acceso' },
                { method: 'GET', path: '/api/v1/auth/me', desc: 'Obtener usuario actual' },
                { method: 'PUT', path: '/api/v1/auth/change-password', desc: 'Cambiar contraseña' },
              ].map((endpoint, i) => (
                <div key={i} className="flex items-center gap-3 p-3 bg-stone-50 rounded-xl">
                  <span className={`px-2 py-0.5 text-xs font-bold rounded ${
                    endpoint.method === 'GET' ? 'bg-blue-100 text-blue-700' :
                    endpoint.method === 'POST' ? 'bg-emerald-100 text-emerald-700' :
                    'bg-amber-100 text-amber-700'
                  }`}>{endpoint.method}</span>
                  <code className="text-sm text-stone-700 font-mono">{endpoint.path}</code>
                  <span className="text-xs text-stone-500 ml-auto hidden sm:block">{endpoint.desc}</span>
                </div>
              ))}
            </div>

            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-stone-700 uppercase tracking-wider">Tenants (Solo Superadmin)</h3>
              {[
                { method: 'POST', path: '/api/v1/tenants', desc: 'Crear nuevo tenant' },
                { method: 'GET', path: '/api/v1/tenants', desc: 'Listar todos los tenants' },
                { method: 'GET', path: '/api/v1/tenants/{id}', desc: 'Obtener tenant específico' },
                { method: 'PUT', path: '/api/v1/tenants/{id}', desc: 'Actualizar tenant' },
                { method: 'DELETE', path: '/api/v1/tenants/{id}', desc: 'Soft delete tenant' },
                { method: 'GET', path: '/api/v1/tenants/{id}/stats', desc: 'Estadísticas del tenant' },
                { method: 'POST', path: '/api/v1/tenants/check-subdomain', desc: 'Verificar disponibilidad' },
              ].map((endpoint, i) => (
                <div key={i} className="flex items-center gap-3 p-3 bg-stone-50 rounded-xl">
                  <span className={`px-2 py-0.5 text-xs font-bold rounded ${
                    endpoint.method === 'GET' ? 'bg-blue-100 text-blue-700' :
                    endpoint.method === 'POST' ? 'bg-emerald-100 text-emerald-700' :
                    endpoint.method === 'PUT' ? 'bg-amber-100 text-amber-700' :
                    'bg-red-100 text-red-700'
                  }`}>{endpoint.method}</span>
                  <code className="text-sm text-stone-700 font-mono">{endpoint.path}</code>
                  <span className="text-xs text-stone-500 ml-auto hidden sm:block">{endpoint.desc}</span>
                </div>
              ))}
            </div>

            <h3 className="text-lg font-semibold text-stone-800 mt-6">Ejemplo de Request</h3>
            <CodeBlock id="api-example" code={`# Login
curl -X POST http://localhost:8000/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "admin@demo.com",
    "password": "Admin123!"
  }'

# Respuesta
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "00000000-0000-0000-0000-000000000002",
    "email": "admin@demo.com",
    "nombre": "María",
    "apellido": "González",
    "rol": "admin"
  },
  "tenant": {
    "id": "00000000-0000-0000-0000-000000000001",
    "nombre": "Serenity Spa & Wellness",
    "subdominio": "demo",
    "plan": "professional"
  }
}

# Request autenticado
curl -X GET http://localhost:8000/api/v1/tenants \\
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."`} />
          </div>
        )}

        {activeSection === 'database' && (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-stone-800">Esquema de Base de Datos</h2>
            <p className="text-stone-600">
              MySQL 8.0 con charset utf8mb4. Estrategia multitenant: base de datos compartida con
              separación por tenant_id en cada tabla. Todos los IDs son UUIDs.
            </p>

            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-stone-700 uppercase tracking-wider">Tabla: tenants</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-stone-200">
                      <th className="text-left py-2 px-3 text-stone-600">Campo</th>
                      <th className="text-left py-2 px-3 text-stone-600">Tipo</th>
                      <th className="text-left py-2 px-3 text-stone-600">Restricciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-100">
                    {[
                      ['id', 'UUID', 'PRIMARY KEY'],
                      ['nombre', 'VARCHAR(255)', 'NOT NULL'],
                      ['subdominio', 'VARCHAR(100)', 'UNIQUE, NOT NULL, INDEX'],
                      ['plan', 'ENUM(basic,professional,enterprise)', 'DEFAULT basic'],
                      ['activo', 'BOOLEAN', 'DEFAULT TRUE'],
                      ['fecha_creacion', 'DATETIME', 'DEFAULT NOW()'],
                      ['fecha_expiracion', 'DATETIME', 'NULLABLE'],
                      ['configuracion', 'JSON', 'NULLABLE'],
                      ['limite_usuarios', 'INT', 'DEFAULT 10'],
                      ['limite_pacientes', 'INT', 'DEFAULT 1000'],
                      ['timezone', 'VARCHAR(50)', 'DEFAULT America/Bogota'],
                      ['moneda', 'VARCHAR(3)', 'DEFAULT USD'],
                    ].map(([field, type, constraints], i) => (
                      <tr key={i} className="hover:bg-stone-50">
                        <td className="py-2 px-3 font-mono text-xs text-stone-800">{field}</td>
                        <td className="py-2 px-3 text-xs text-stone-600">{type}</td>
                        <td className="py-2 px-3 text-xs text-stone-500">{constraints}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-stone-700 uppercase tracking-wider">Tabla: users</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-stone-200">
                      <th className="text-left py-2 px-3 text-stone-600">Campo</th>
                      <th className="text-left py-2 px-3 text-stone-600">Tipo</th>
                      <th className="text-left py-2 px-3 text-stone-600">Restricciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-100">
                    {[
                      ['id', 'UUID', 'PRIMARY KEY'],
                      ['tenant_id', 'UUID', 'FK → tenants.id, NOT NULL, INDEX'],
                      ['username', 'VARCHAR(100)', 'NOT NULL, INDEX'],
                      ['email', 'VARCHAR(255)', 'NOT NULL, INDEX'],
                      ['password_hash', 'VARCHAR(255)', 'NOT NULL'],
                      ['nombre', 'VARCHAR(100)', 'NOT NULL'],
                      ['apellido', 'VARCHAR(100)', 'NOT NULL'],
                      ['rol', 'ENUM(...)', 'NOT NULL'],
                      ['activo', 'BOOLEAN', 'DEFAULT TRUE'],
                      ['ultimo_acceso', 'DATETIME', 'NULLABLE'],
                      ['email_verificado', 'BOOLEAN', 'DEFAULT FALSE'],
                    ].map(([field, type, constraints], i) => (
                      <tr key={i} className="hover:bg-stone-50">
                        <td className="py-2 px-3 font-mono text-xs text-stone-800">{field}</td>
                        <td className="py-2 px-3 text-xs text-stone-600">{type}</td>
                        <td className="py-2 px-3 text-xs text-stone-500">{constraints}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeSection === 'security' && (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-stone-800">Seguridad</h2>
            <p className="text-stone-600">
              El sistema implementa múltiples capas de seguridad para proteger los datos de cada tenant.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                {
                  title: 'Autenticación JWT',
                  items: ['Tokens con expiración configurable', 'Refresh tokens con vida más larga', 'Algoritmo HS256', 'Payload incluye tenant_id'],
                },
                {
                  title: 'Contraseñas',
                  items: ['Hash con bcrypt (passlib)', 'Validación de fortaleza', 'Mínimo 8 caracteres', 'Mayúsculas, minúsculas, números, especiales'],
                },
                {
                  title: 'Multitenancy',
                  items: ['Filtrado automático por tenant_id', 'Middleware de validación', 'Sin posibilidad de fuga de datos', 'UUIDs para todos los IDs'],
                },
                {
                  title: 'Infraestructura',
                  items: ['Contenedores no-root', 'Variables de entorno para secrets', 'Headers de seguridad en Nginx', 'Rate limiting (pendiente)'],
                },
              ].map((section, i) => (
                <div key={i} className="p-4 bg-stone-50 rounded-xl">
                  <h4 className="text-sm font-semibold text-stone-800 mb-3 flex items-center gap-2">
                    <Lock size={14} className="text-emerald-600" />
                    {section.title}
                  </h4>
                  <ul className="space-y-1.5">
                    {section.items.map((item, j) => (
                      <li key={j} className="flex items-center gap-2 text-xs text-stone-600">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
              <h4 className="text-sm font-semibold text-amber-800 mb-2">⚠️ Consideraciones de Producción</h4>
              <ul className="space-y-1.5 text-xs text-amber-700">
                <li>• Cambiar SECRET_KEY por una clave segura de al menos 32 caracteres</li>
                <li>• Usar HTTPS en producción (configurar certificados SSL en Nginx)</li>
                <li>• Implementar rate limiting con Redis</li>
                <li>• Configurar backups automáticos de la base de datos</li>
                <li>• Rotar logs y configurar monitoreo</li>
                <li>• No exponer puertos de MySQL y Redis externamente</li>
              </ul>
            </div>
          </div>
        )}

        {activeSection === 'quickstart' && (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-stone-800">Inicio Rápido</h2>
            <p className="text-stone-600">
              Levanta todo el sistema con un solo comando. Asegúrate de tener Docker y Docker Compose instalados.
            </p>

            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-stone-700 mb-2">1. Clonar el repositorio</h3>
                <CodeBlock id="qs-1" code={`git clone https://github.com/tu-usuario/spa-management-system.git
cd spa-management-system`} />
              </div>

              <div>
                <h3 className="text-sm font-semibold text-stone-700 mb-2">2. Configurar variables de entorno</h3>
                <CodeBlock id="qs-2" code={`cp .env.example .env
# Editar .env con tus valores (especialmente SECRET_KEY)`} />
              </div>

              <div>
                <h3 className="text-sm font-semibold text-stone-700 mb-2">3. Levantar los servicios</h3>
                <CodeBlock id="qs-3" code={`# Desarrollo (con phpMyAdmin)
docker-compose --profile development up -d

# Producción
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d`} />
              </div>

              <div>
                <h3 className="text-sm font-semibold text-stone-700 mb-2">4. Verificar servicios</h3>
                <CodeBlock id="qs-4" code={`docker-compose ps
# Todos los servicios deben mostrar "healthy" o "running"

# Verificar health del backend
curl http://localhost:8000/health`} />
              </div>

              <div>
                <h3 className="text-sm font-semibold text-stone-700 mb-2">5. Acceder al sistema</h3>
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                  <p className="text-sm text-emerald-800 font-medium">🌐 Frontend: http://localhost</p>
                  <p className="text-sm text-emerald-800 font-medium mt-1">📡 API: http://localhost:8000</p>
                  <p className="text-sm text-emerald-800 font-medium mt-1">📚 Docs: http://localhost:8000/docs</p>
                  <p className="text-sm text-emerald-800 font-medium mt-1">🗄️ phpMyAdmin: http://localhost:8080</p>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-stone-700 mb-2">Credenciales por defecto</h3>
                <div className="bg-stone-50 rounded-xl p-4">
                  <div className="space-y-2">
                    <div className="flex items-center gap-4">
                      <span className="text-xs font-medium text-stone-500 w-24">Superadmin:</span>
                      <code className="text-xs text-stone-700">superadmin@spa.com / Admin123!</code>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-xs font-medium text-stone-500 w-24">Admin Demo:</span>
                      <code className="text-xs text-stone-700">admin@demo.com / Admin123!</code>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-stone-50 rounded-xl p-4">
              <h4 className="text-sm font-semibold text-stone-700 mb-2">Comandos útiles</h4>
              <CodeBlock id="qs-commands" code={`# Ver logs en tiempo real
docker-compose logs -f backend

# Ejecutar comandos en el contenedor
docker-compose exec backend python -c "print('hello')"

# Acceder a MySQL
docker-compose exec mysql mysql -u spa_user -p spa_management

# Reiniciar un servicio
docker-compose restart backend

# Detener todo
docker-compose down

# Detener y eliminar volúmenes (¡cuidado!)
docker-compose down -v`} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
