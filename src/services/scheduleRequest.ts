// ============================================================
// Puente para solicitar "Agendar Cita" desde otra página (Ficha del Paciente).
// AppointmentsPage registra un listener; quien quiera abrir el modal de nueva
// cita preseleccionando un paciente llama a requestScheduleAppointment(id).
// ============================================================

type Listener = (patientId: string) => void;

let listener: Listener | null = null;
let pending: string | null = null;

export function setScheduleListener(fn: Listener | null): void {
  listener = fn;
  if (listener && pending) {
    const patientId = pending;
    pending = null;
    listener(patientId);
  }
}

export function requestScheduleAppointment(patientId: string): void {
  pending = patientId;
  if (listener) {
    const id = pending;
    pending = null;
    listener(id as string);
  }
}