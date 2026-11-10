# Plan: Respuestas limpias y confiables del bot de WhatsApp

## Diagnóstico
1. El modelo no cumple el protocolo de JSON estricto: emite prosa de razonamiento + fragmentos JSON mezclados.
2. `_parse_decision` es frágil: `re.search(r"\{.*\}", DOTALL)` es greedy y toma de la primera `{` a la última `}` → casi siempre JSON inválido → `None`.
3. Sin reintento: al fallar se envía el texto crudo al usuario (razonamiento interno + IDs).
4. `_call_freellmapi` no envía `max_tokens`/`temperature`: respuestas largas se truncan a mitad del JSON.
5. Prompts ambiguos: la regla `confirm_pending_appointment` se activó también durante el agendamiento.

## Cambios

### 1. `_parse_decision` robusto
- Extraer el último bloque `{...}` balanceado (contar llaves), no un greedy `.*`.
- Tolerar prosa inicial/final; si no cierra → `None` y dispara reintento.

### 2. Reintento con corrección en `_call_ai_with_tools`
- Nunca enviar crudo el texto si contiene `{` (JSON intentado/roto).
- Reintentar hasta 3 veces con system message correctivo.
- Si falla → fallback amable.
- Texto sin `{` (saludo real) sí se envía tal cual.

### 3. `_call_freellmapi` con `max_tokens`/`temperature`
- Parámetro opcional `max_tokens` (~600) y `temperature` (0.2) que el bot pasa en el body.

### 4. Prompt reforzado
- Prohibir prosa de razonamiento y mostrar IDs.
- `confirm_pending_appointment` SOLO tras recordatorio 24h (respuesta CONFIRMO), no durante agendamiento nuevo.
- Al preguntar servicios/terapeutas: usar `list_services`/`check_availability` y mostrar el resultado real.

### 5. Flujo de agendamiento confirmado
- `_tool_book_appointment` acepta `estado` opcional: cuando el usuario ya confirmó, crear la cita `estado="confirmed"`.
- Responder resumen corto sin IDs.

### 6. Guard previo a la IA en `process_message`
- Detectar por regex intenciones directas: "qué servicios", "qué terapeutas/masajistas", "a las HH:MM", "CONFIRMO".

## Deploy
`docker compose build backend && docker compose up -d backend`