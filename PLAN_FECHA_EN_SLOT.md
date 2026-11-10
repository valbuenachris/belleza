# Plan: Incluir fecha en mensajes de slot match

## Diagnóstico
`_extract_booking_from_history` busca la fecha con `"para YYYY-MM-DD"` en los
mensajes recientes del bot. Cuando guard #5 encuentra un slot que matchea
directamente, su mensaje es "El horario de las 15:00 está disponible..."
SIN la fecha. El historial no contiene la fecha → helper retorna None → guard #8
cae → IA alucina → la cita no se guarda en BD.

## Cambios
1. Guard #5: agregar `del {cita_date}` al mensaje cuando el slot matchea.
2. Guard #7: misma corrección.

## Deploy
`docker compose build backend && docker compose up -d backend`