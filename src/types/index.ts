// ============================================================
// Tipos del Sistema de Gestión SPA Multitenant
// ============================================================

export interface Tenant {
  id: string;
  nombre: string;
  subdominio: string;
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
  total_ingresos_mes: number;
  citas_semana: number[];
  ingresos_mes: number[];
}

export interface User {
  id: string;
  tenant_id: string;
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
  rol: User['rol'];
  tenant_id?: string;
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

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
}

export type Page = 'dashboard' | 'tenants' | 'users' | 'appointments' | 'patients' | 'services' | 'settings' | 'reports' | 'docs';
