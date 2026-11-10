# Plan: Traducir estados de cita a español

## Objetivo
Que el bot de WhatsApp y el frontend muestren los estados en español (pendiente, confirmada, cancelada, completada) en lugar de inglés (pending, confirmed, cancelled, completed).

## Cambios

### 1. Backend — `whatsapp_agent_service.py`
- Añadir helper `_format_status(estado)` con mapeo:
  - `pending` → `pendiente`
  - `confirmed` → `confirmada`
  - `cancelled` → `cancelada`
  - `completed` → `completada`
- En `_tool_list_appointments` (línea ~1696), cambiar `"status": a.estado` por `"status": _format_status(a.estado)`
- Con esto, todos los ~10 lugares que usan `ap.get('status')` en el agente muestran español automáticamente.

### 2. Frontend
- Revisar `src/pages/AppointmentsPage.tsx` y `src/types/index.ts` para ver si hay mapeo de estados.
- Si no lo hay, añadir un `ESTADO_LABEL` similar.

### 3. Deploy
- `git add -A && git commit -m "Traducir estados a español en WhatsApp y frontend"`
- `docker compose restart backend`