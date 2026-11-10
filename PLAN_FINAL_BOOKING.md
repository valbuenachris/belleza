# Plan: Flujo de agendamiento (booking) definitivo

## Diagnóstico
1. Guard #5 no acepta "si/sí" como confirmación de servicio
2. Guard #6 no encuentra servicio cuando el texto no lo repite
3. No se persiste el servicio seleccionado entre turnos
4. Guard #3 (CONFIRMO) solo maneja recordatorios, no booking tras disponibilidad

## Cambios
1. Guard #5: añadir `s[ií]` como trigger de confirmación
2. Helper `_service_from_history`: recupera servicio del historial de mensajes
3. Guard #5/6: usar helper cuando no hay match en texto
4. Guard #3: si cancel_pending no aplica, intentar booking directo