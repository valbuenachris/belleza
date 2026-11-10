# Plan: Prohibir prosa del modelo — solo JSON o fallback

## Causa raíz
El modelo sigue escribiendo prosa de razonamiento ("We need to respond...") sin `{}`. El código la trata como "saludo natural" y la envía cruda al paciente (cuando `_looks_like_json=False` y `decision=None`).

## Cambios
1. Prohibir toda respuesta no-JSON: retry con corrección en vez de enviar crudo.
2. Intención #6: detectar fecha/hora para agendar directamente.
3. Prompt y correctivo más severos.