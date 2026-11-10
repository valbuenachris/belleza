# Plan: Pagos, Multi-servicios, Recordatorios, Cambio y Sugerencias

## Arquitectura
- `appointments` (cabecera) -> `appointment_items` (N servicios) -> `appointment_payments` (N pagos)
- `services` ++ `service_related` (sugerencias)

## Decisiones del usuario
1. Pagos: personal registra (dashboard); WhatsApp solo informa.
2. Cita con pago parcial puede atenderse/completarse (crédito).
3. Reembolsos: pendiente para otra iteración.
4. Multi-servicio: 1 bloque en calendario (terapeuta/horario únicos); N servicios en detalle.

## Puntos
1. **Pago antes de atención**: estado_pago (unpaid/partial/paid), appointment_payments, endpoints GET/POST/DELETE, regla: completar requiere estado_pago != unpaid (partial permitido).
2. **Recordatorios**: noche anterior 19h (mañana) + 2h antes (hoy) en vez de 24h.
3. **Cambiar servicio**: guard WhatsApp + PUT service en cita.
4. **Sugerir relacionados**: tabla service_related, bot sugiere al agendar y al cambiar.
5. **Multi-servicio**: tabla appointment_items, monto_total = Σ items.

## Migración 0015
- appointments ++ monto_total, total_pagado, estado_pago, descuento_total
- appointment_payments (id, tenant_id, appointment_id FK, monto, metodo_pago, descuento, observaciones, created_at, created_by)
- appointment_items (id, tenant_id, appointment_id FK, service_id FK, nombre_snapshot, precio_unitario, cantidad, descuento, subtotal)
- service_related (id, tenant_id, service_id FK, related_service_id FK)

## Deploy
`docker compose down backend && docker compose build backend && docker compose up -d backend`
