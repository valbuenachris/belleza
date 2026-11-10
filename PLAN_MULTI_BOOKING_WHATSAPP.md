# Plan: Mejorar bot WhatsApp booking multi-servicio y consecutivo

## Problemas
1. `{extra}` literal en respuestas (falta f-prefix)
2. "y el masaje?" no detecta multi-servicio
3. "quiero la limpieza y el masaje" (mismo msg) ignora segundo servicio
4. "después de la limpieza" no interpreta hora consecutiva
5. `create_appointment` no sincroniza items principal

## Cambios
### A. Fix f-prefix en 3 líneas de booking
### B. Guard #9 regex más amplio
### C. Nuevo guard multi-servicio mismo mensaje
### D. "después de [servicio]" hora consecutiva
### E. sync_item_from_service en create_appointment