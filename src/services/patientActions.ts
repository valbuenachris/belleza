// ============================================================
// patientActions.ts - Puente entre páginas para abrir la Ficha
// del Paciente (usado por el buscador global del header)
// ============================================================

type PatientFichaListener = (patientId: string) => void;

let patientFichaListener: PatientFichaListener | null = null;

export function setPatientFichaListener(fn: PatientFichaListener | null): void {
  patientFichaListener = fn;
}

export function requestPatientFicha(patientId: string): void {
  if (patientFichaListener) {
    patientFichaListener(patientId);
  }
}