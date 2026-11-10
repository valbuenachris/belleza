# Plan: El bot debe saber si el cliente tiene citas

## Diagnóstico
"quiero saber si tengo citas agendadas" NO coincide con los guards previos a la IA
(solo cubren servicios, terapeutas y CONFIRMO). Pasa al modelo, y la IA (dada su
tendencia a producir prosa + JSON roto vista en los logs) agota los reintentos
correctivos -> FALLBACK_REPLY. Además, el historial contiene mensajes crudos
anteriores (razonamiento/IDs) que incentivan al modelo a imitar ese formato.

## Cambios

### 1. Intención "mis citas" en `_handle_direct_intent`
- Regex: `(quiero saber|tengo|mis|consultar|cuántas|cuales|próximas).* (citas|turnos|agendadas?|pendientes)`.
- Ejecuta `_tool_list_appointments` con `conversation.patient_id` y renderiza:
  - Con citas -> lista amigable (servicio, fecha, hora, terapeuta, estado).
  - Sin citas -> "No tienes citas agendadas por el momento. ¿Quieres agendar una?"

### 2. Reforzar prompt (REGLAS DE ORO)
- "Si el cliente pregunta por sus citas/turnos, llama a list_my_appointments y
  muestra la lista real; nunca fallback."

### 3. Filtrar historial contaminado en `_build_history`
- Saltar mensajes assistant que contengan `{`/`}` malformados o fallbacks
  genéricos, para no incentivar al modelo a imitar razonamiento crudo.

## Deploy
`docker compose build backend && docker compose up -d backend`