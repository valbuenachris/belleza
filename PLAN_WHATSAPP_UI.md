# Plan: Chat WhatsApp estilo WhatsApp + Zona horaria del tenant

## Visión General
Mejorar la pestaña de Conversaciones para que se comporte como cualquier chat de WhatsApp (muestra siempre el último mensaje, vista previa en la lista, auto-scroll y polling en vivo) y ajustar toda la hora del sitio para usar la zona horaria configurada en la información general del tenant.

## Parte 1 — Pestaña de Conversaciones "como WhatsApp"

### Backend — `backend/app/routers/whatsapp.py`
- `_serialize_conversation`: agregar `last_message_content` (texto del último mensaje) y `last_message_role` para que la lista muestre la vista previa del último mensaje.

### Frontend — tipos — `src/types/index.ts`
- Añadir `last_message_content` y `last_message_role` a `WhatsAppConversation`.

### Frontend — `src/pages/WhatsAppPage.tsx`
- **Lista de conversaciones**: mostrar vista previa del último mensaje truncada + hora bajo el nombre.
- **Panel de mensajes**: auto-scroll al final al cargar y con mensajes nuevos (stick-to-bottom si ya está cerca del final).
- **Polling**: refrescar mensajes de la conversación seleccionada cada 5s y la lista cada 10s mientras esté la pestaña activa.

## Parte 2 — Zona horaria del tenant

### Frontend — util compartida — `src/utils/dateTime.ts` (CREAR)
- `fmtTime(iso, tz)`, `fmtDate(iso, tz)` con `Intl.DateTimeFormat('es-ES', { timeZone: tz, ... })`.
- `getTenantTimezone(tenant)` → `tenant?.timezone || 'America/Bogota'`.

### Páginas con reloj visible
- `WhatsAppPage.tsx`: timestamps de mensajes, `last_message_at` de conversaciones y "Conectado desde".
- `DashboardPage.tsx`: fecha del header.
- `AppointmentsPage.tsx`: horas de citas.

## Archivos
| Archivo | Acción |
|---|---|
| `backend/app/routers/whatsapp.py` | + `last_message_content`/`last_message_role` |
| `src/types/index.ts` | + campos en `WhatsAppConversation` |
| `src/utils/dateTime.ts` | **CREAR** util de formato con timezone |
| `src/pages/WhatsAppPage.tsx` | preview, auto-scroll, polling, timezone |
| `src/pages/DashboardPage.tsx` | timezone en fecha del header |
| `src/pages/AppointmentsPage.tsx` | timezone en horas |

## Deploy
`docker compose build backend frontend && docker compose up -d backend frontend`