# Plan: Permitir pagos en $0 (Crédito) para completar citas

## Objetivo
Permitir registrar pagos de **$0** como crédito en el modal de pagos, actualizando el estado a `partial` y permitiendo completar la cita sin exigir un pago mayor a 0.

## Cambios
1. **Schema (`backend/app/schemas/appointment.py`)**: `monto: Decimal = Field(..., ge=0)` (permite `>= 0`).
2. **Service (`backend/app/services/appointment_service.py`)**: 
   - En `register_payment`, si `monto == 0` y la cita está en `unpaid`, marcar `estado_pago = "partial"`.
   - En `update_appointment`, permitir pasar a `completed` si `estado_pago == "partial"` aunque `total_pagado == 0`.
3. **Frontend (`src/pages/AppointmentsPage.tsx`)**:
   - Cambiar `min={1}` a `min={0}` en el input de monto del `PaymentModal`.
   - Permitir submit con `monto === 0` y mostrar un aviso de crédito.
