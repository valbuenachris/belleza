// ============================================================
// Tipos del Sistema de Gestión SPA Multitenant
// ============================================================

export interface Tenant {
  id: string;
  nombre: string;
  /** Subdominio opcional (ya no se usa para enrutamiento; login universal por email) */
  subdominio?: string;
  plan: 'basic' | 'professional' | 'enterprise';
  activo: boolean;
  fecha_creacion: string;
  fecha_expiracion: string | null;
  configuracion: TenantConfig | null;
  limite_usuarios: number;
  limite_pacientes: number;
  logo_url: string | null;
  direccion: string | null;
  telefono: string | null;
  email: string | null;
  timezone: string;
  moneda: string;
  estadisticas?: TenantStats;
}

export interface TenantConfig {
  horario_apertura: string;
  horario_cierre: string;
  dias_operacion: number[];
  duracion_cita_default: number;
  recordatorio_citas: boolean;
  confirmacion_citas: boolean;
}

export interface TenantStats {
  total_usuarios: number;
  total_pacientes: number;
  total_citas_hoy: number;
  total_ingresos_hoy: number;
  total_ingresos_mes: number;
  citas_semana: number[];
  ingresos_mes: number[];
}

export interface User {
  id: string;
  tenant_id: string | null;
  username: string;
  email: string;
  nombre: string;
  apellido: string;
  rol: 'superadmin' | 'admin' | 'manager' | 'receptionist' | 'therapist';
  activo: boolean;
  ultimo_acceso: string | null;
  telefono: string | null;
  avatar_url: string | null;
  email_verificado: boolean;
  created_at: string;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  nombre: string;
  apellido: string;
  rol: Exclude<User['rol'], 'superadmin'>;
  telefono?: string | null;
}

export interface UserUpdate {
  nombre?: string;
  apellido?: string;
  telefono?: string | null;
  rol?: Exclude<User['rol'], 'superadmin'>;
  activo?: boolean;
  password?: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
  tenant: Tenant | null;
}

// ============================================================
// Pacientes
// ============================================================

export interface Patient {
  id: string;
  tenant_id: string;
  nombre: string;
  apellido: string;
  email: string | null;
  telefono: string | null;
  fecha_nacimiento: string | null;
  genero: string | null;
  direccion: string | null;
  notas_medicas: string | null;
  activo: boolean;
  created_at: string | null;
  total_citas?: number;
  ultima_cita?: string | null;
}

export interface PatientCreateInput {
  nombre: string;
  apellido: string;
  email?: string | null;
  telefono?: string | null;
  fecha_nacimiento?: string | null;
  genero?: string | null;
  direccion?: string | null;
  notas_medicas?: string | null;
}

export interface PatientsResponse {
  patients: Patient[];
  total: number;
}

// ============================================================
// Servicios
// ============================================================

export interface Service {
  id: string;
  tenant_id: string;
  nombre: string;
  descripcion: string | null;
  precio: number;
  duracion: number;
  activo: boolean;
  created_at: string | null;
}

export interface ServiceCreateInput {
  nombre: string;
  descripcion?: string | null;
  precio: number;
  duracion: number;
}

export interface ServicesResponse {
  services: Service[];
  total: number;
}

// ============================================================
// Citas
// ============================================================

export type AppointmentStatus = 'pending' | 'confirmed' | 'completed' | 'cancelled';

export interface Appointment {
  id: string;
  tenant_id: string;
  patient_id: string;
  therapist_id: string;
  service_id: string;
  date_time: string | null;
  fecha: string | null;
  hora_inicio: string | null;
  time: string | null;
  duracion: number;
  estado: string;
  precio: number | null;
  total_precio: number | null;
  notas: string | null;
  patient: string;
  service: string;
  therapist: string;
  created_at: string | null;
}

export interface AppointmentCreateInput {
  patient_id: string;
  therapist_id: string;
  service_id: string;
  date_time: string;
  duracion?: number;
  estado?: string;
  precio?: number;
  notas?: string;
}

export interface AppointmentUpdateInput {
  patient_id?: string;
  therapist_id?: string;
  service_id?: string;
  date_time?: string;
  duracion?: number;
  estado?: string;
  precio?: number;
  notas?: string;
}

export interface AppointmentsResponse {
  appointments: Appointment[];
  total: number;
}

export interface AppointmentSummary {
  total_citas_hoy: number;
  pendientes: number;
  confirmadas: number;
  ingresos_hoy: number;
}

// ============================================================
// Reportes financieros y de rendimiento
// ============================================================

export interface FinancialReportTopService {
  servicio: string;
  cantidad: number;
  ingresos: number;
}

export interface FinancialReportTherapist {
  terapeuta: string;
  completadas: number;
  ingresos: number;
}

export interface FinancialReport {
  desde: string;
  hasta: string;
  total_ingresos: number;
  total_citas: number;
  completadas: number;
  canceladas: number;
  ticket_promedio: number;
  pacientes_nuevos: number;
  top_servicios: FinancialReportTopService[];
  rendimiento_terapeutas: FinancialReportTherapist[];
}

// ============================================================
// Respuestas paginadas de usuarios
// ============================================================

export interface UsersResponse {
  users: User[];
  total: number;
}

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
}

export type Page = 'dashboard' | 'tenants' | 'users' | 'appointments' | 'patients' | 'services' | 'settings' | 'reports' | 'docs';
