# Plan: Nueva Sección de Gestión de Pagos

## Objetivo
Crear una página **Pagos** en el sidebar con tarjetas de métricas y un listado filtrable de servicios facturados con acciones de pago en línea.

## Cambios
1. `src/types/index.ts` — Agregar `'payments'` al `type Page`.
2. `src/components/Layout.tsx` — Agregar ítem `Pagos` al `navItems`.
3. `src/App.tsx` — Importar y rutear `PaymentsPage`.
4. `src/pages/PaymentsPage.tsx` — **CREAR**: tarjetas de métricas + tabla filtrable + modal de pago.