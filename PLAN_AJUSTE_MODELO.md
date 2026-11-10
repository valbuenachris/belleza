# Plan: Completar el diálogo sin IA + simplificar el modelo

## Diagnóstico
`_parse_booking_time` exige `mañana`/`hoy`. Cuando el cliente responde "A las 15:00"
(eligiendo un slot ya mostrado), el guard #6 no entra -> cae en la IA -> el modelo
escribe prosa/inglés -> FALLBACK_REPLY.

## Cambios
1. Guard #7 "Elegir horario de los slots": regex sin exigir día; extrae fecha del
   último mensaje assistant; servicio del historial; book_appointment con
   estado="confirmed".
2. Guard #8 "Confirmar/sí" tras elegir horario: confirmar cita pending sin recordatorio.
3. Simplificar prompt: español obligatorio, prohibir razonamiento, few-shot de 2
   ejemplos, recortar herramientas a las usadas por IA.
4. Mantener reintentos y logging.

## Deploy
`docker compose build backend && docker compose up -d backend`
