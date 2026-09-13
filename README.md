# 🧖 SPA Management System

Sistema de gestión integral para SPAs (centros de estética y relajación) con arquitectura **multitenant SaaS**. Diseñado para ser vendido a múltiples spas, donde cada uno tiene sus datos completamente aislados compartiendo la misma infraestructura.

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose                          │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌────────┐ │
│  │ Frontend │→ │   Backend    │→ │  MySQL   │  │ Redis  │ │
│  │  (Nginx) │  │  (FastAPI)   │  │   8.0    │  │   7    │ │
│  │ Puerto 80│  │ Puerto 8000  │  │ Puerto   │  │Puerto  │ │
│  │          │  │              │  │   3306   │  │  6379  │ │
│  └──────────┘  └──────────────┘  └──────────┘  └────────┘ │
│       ↑               ↑              ↑            ↑        │
│       └───────────────┴──────────────┴────────────┘        │
│                    spa_network (bridge)                     │
└─────────────────────────────────────────────────────────────┘
```

## ✨ Características

- **Multitenancy**: Base de datos compartida con separación por `tenant_id`
- **Autenticación JWT**: Tokens seguros con refresh tokens
- **API REST**: FastAPI con documentación automática (Swagger/ReDoc)
- **Dockerizado**: Todo el sistema en contenedores con healthchecks
- **Seguridad**: Bcrypt, CORS, headers de seguridad, usuarios no-root
- **Frontend minimalista**: HTML5 + CSS3 + JavaScript vanilla
- **Escalable**: Diseñado para miles de tenants

## 📋 Requisitos

- Docker 20.10+
- Docker Compose 2.0+
- 2GB RAM mínimo recomendado

## 🚀 Inicio Rápido

```bash
# 1. Clonar repositorio
git clone https://github.com/tu-usuario/spa-management-system.git
cd spa-management-system

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con valores seguros (especialmente SECRET_KEY)

# 3. Levantar todos los servicios
docker-compose up -d

# 4. Verificar que todo esté funcionando
docker-compose ps
# Todos los servicios deben mostrar "running" o "healthy"

# 5. Acceder al sistema
# Frontend: http://localhost
# API:      http://localhost:8000
# Docs:     http://localhost:8000/docs
# phpMyAdmin: http://localhost:8080 (solo con perfil development)
```

## 🔑 Credenciales por Defecto

| Rol | Email | Contraseña |
|-----|-------|------------|
| Superadmin | superadmin@spa.com | Admin123! |
| Admin Demo | admin@demo.com | Admin123! |

> ⚠️ **IMPORTANTE**: Cambia estas credenciales inmediatamente en producción.

## 📁 Estructura del Proyecto

```
spa-management-system/
├── docker-compose.yml          # Orquestación principal
├── docker-compose.dev.yml      # Override desarrollo
├── docker-compose.prod.yml     # Override producción
├── .env                        # Variables de entorno
├── backend/
│   ├── Dockerfile              # Imagen Python multi-stage
│   ├── requirements.txt        # Dependencias Python
│   ├── alembic.ini             # Configuración migraciones
│   └── app/
│       ├── main.py             # Punto de entrada FastAPI
│       ├── config.py           # Configuración (pydantic-settings)
│       ├── database.py         # Conexión SQLAlchemy
│       ├── dependencies.py     # Inyección de dependencias
│       ├── middleware/         # Tenant + Auth middleware
│       ├── models/             # Modelos SQLAlchemy
│       ├── schemas/            # Schemas Pydantic
│       ├── routers/            # Endpoints API
│       ├── services/           # Lógica de negocio
│       └── utils/              # Utilidades (security, validators)
├── frontend/
│   ├── Dockerfile              # Imagen Nginx
│   ├── nginx.conf              # Configuración Nginx
│   ├── index.html              # Dashboard principal
│   ├── login.html              # Página de login
│   ├── css/                    # Estilos CSS3
│   └── js/                     # JavaScript vanilla
└── database/
    ├── init.sql                # Inicialización DB
    ├── schema.sql              # Esquema de tablas
    └── seed.sql                # Datos iniciales
```

## 🔌 Endpoints Principales

### Autenticación
- `POST /api/v1/auth/login` - Iniciar sesión
- `POST /api/v1/auth/register` - Registrar nuevo SPA
- `POST /api/v1/auth/refresh` - Refrescar token
- `GET  /api/v1/auth/me` - Usuario actual

### Tenants (Solo Superadmin)
- `POST   /api/v1/tenants` - Crear tenant
- `GET    /api/v1/tenants` - Listar tenants
- `GET    /api/v1/tenants/{id}` - Obtener tenant
- `PUT    /api/v1/tenants/{id}` - Actualizar tenant
- `DELETE /api/v1/tenants/{id}` - Eliminar tenant (soft delete)

## 🛠️ Comandos Útiles

```bash
# Ver logs en tiempo real
docker-compose logs -f backend

# Acceder a MySQL
docker-compose exec mysql mysql -u spa_user -p spa_management

# Reiniciar un servicio
docker-compose restart backend

# Detener todo
docker-compose down

# Detener y eliminar volúmenes (¡cuidado! borra datos)
docker-compose down -v

# Levantar con phpMyAdmin (desarrollo)
docker-compose --profile development up -d

# Producción
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 🔒 Seguridad

- Contraseñas hasheadas con bcrypt
- Tokens JWT con expiración configurable
- Filtrado automático por tenant_id (no hay fuga de datos)
- Headers de seguridad en Nginx (X-Frame-Options, CSP, etc.)
- Contenedores con usuarios no-root
- Variables de entorno para secrets

## 📊 Tecnologías

| Componente | Tecnología |
|------------|------------|
| Backend | Python 3.11 + FastAPI |
| Frontend | HTML5 + CSS3 + JavaScript Vanilla |
| Base de datos | MySQL 8.0 |
| Cache | Redis 7 |
| ORM | SQLAlchemy 2.0 |
| Migraciones | Alembic |
| Auth | JWT (python-jose) |
| Contenedores | Docker + Docker Compose |
| Proxy | Nginx |

## 🗺️ Roadmap

- [ ] Módulo de Citas (agenda, calendario)
- [ ] Gestión de Pacientes (historial clínico)
- [ ] Catálogo de Servicios
- [ ] Sistema de Pagos
- [ ] Reportes y Analíticas
- [ ] Notificaciones (Email/SMS/WhatsApp)
- [ ] App Móvil (React Native)
- [ ] Rate Limiting con Redis
- [ ] Multi-idioma (i18n)
- [ ] Integración con pasarelas de pago

## 📄 Licencia

MIT License - Ver archivo LICENSE para más detalles.
