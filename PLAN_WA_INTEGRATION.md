# Plan: Integración WhatsApp + Gestión de Agenda (Scheduling Bot)

## Visión General
Conectar cada tenant a una instancia de WhatsApp vía **Evolution API** (servicio self-hosted externo). Los pacientes podrán escribir al número del SPA y un agente IA (usando FreeLLMAPI existente) gestionará el ciclo completo de citas: **agendar, modificar, cancelar y consultar**.

## 1. Configuración (Backend)
Nuevas variables de entorno — `config.py`, `.env.example`, `docker-compose.yml`:

| Variable | Propósito |
|---|---|
| `EVOLUTION_API_URL` | URL del servidor Evolution API |
| `EVOLUTION_API_KEY` | API key global de Evolution |
| `EVOLUTION_WEBHOOK_TOKEN` | Token HMAC para validar webhooks |
| `WHATSAPP_BOT_ENABLED` | Switch global del bot |
| `PUBLIC_API_URL` | URL pública del backend para registrar webhooks |

## 2. Base de Datos — Migración `0014_whatsapp.py`
Tres tablas multitenant:
- `whatsapp_settings` — Una fila por tenant (instance_name, status, connected_at, agent config)
- `whatsapp_conversations` — Una fila por número activo (phone, patient_id, status bot/human)
- `whatsapp_messages` — Historial con dedup por message_id (role, content)

## 3. Backend — Servicios
- **whatsapp_service.py** — Evolution HTTP Client (httpx): create_instance, connect, connection_state, logout, send_text, set_webhook
- **whatsapp_agent_service.py** — Bot de agendamiento vía FreeLLMAPI con 6 herramientas: find_patient, list_services, check_availability, book_appointment, modify_appointment, cancel_appointment, list_my_appointments
- **whatsapp_webhook_service.py** — Parser de webhooks Evolution (connection.update, messages.upsert)

## 4. Backend — Routers
- **whatsapp.py** — Endpoints admin protegidos (CRUD settings, instance lifecycle, QR)
- **whatsapp_webhook.py** — Endpoint público POST /webhooks/evolution/{instance} con validación token

## 5. Frontend — WhatsAppPage.tsx
- Pestañas: Instancia (QR, conectar/desconectar), Agente (toggle, nombre, tono), Notificaciones
- Tipos, api methods, registro en App.tsx y Layout.tsx

## 6. Archivos Modificados
- `backend/app/config.py`, `.env.example`, `docker-compose.yml`
- `backend/app/main.py`, `models/__init__.py`
- `src/types/index.ts`, `src/services/api.ts`, `src/App.tsx`, `src/components/Layout.tsx`

## 7. Archivos Creados
- `backend/app/models/whatsapp.py`, `backend/app/schemas/whatsapp.py`
- `backend/app/services/whatsapp_service.py`
- `backend/app/services/whatsapp_agent_service.py`
- `backend/app/services/whatsapp_webhook_service.py`
- `backend/app/routers/whatsapp.py`, `backend/app/routers/whatsapp_webhook.py`
- `backend/alembic/versions/0014_whatsapp_tables.py`
- `src/pages/WhatsAppPage.tsx`