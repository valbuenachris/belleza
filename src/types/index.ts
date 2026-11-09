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
  /** Programa de fidelidad personalizable por tenant */
  puntos_meta: number;
  premio_fidelidad: string;
  tarjeta_color_hex: string;
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

export interface GlobalTenantStats {
  total_spas: number;
  activos: number;
  inactivos: number;
  total_usuarios_globales: number;
  mrr_estimado: number;
  distribucion_planes: Record<string, number>;
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
  puntos?: number;
  sesiones_gratis?: number;
  wallet_pass_id?: string | null;
}

export interface WalletPassData {
  patient_id: string;
  wallet_pass_id: string;
  puntos: number;
  sesiones_gratis: number;
  estrellas: string;
  progreso: number;
  tiene_sesion_gratis: boolean;
  pase: {
    tipo: string;
    formato: string;
    organization_name: string;
    serial_number: string;
    pass_type_identifier: string;
    team_identifier: string;
  };
}

export interface RedeemSessionResult {
  message: string;
  patient_id: string;
  wallet_pass_id: string | null;
  puntos: number;
  sesiones_gratis: number;
}

export interface ScanLoyaltyResult {
  message: string;
  patient_id: string;
  patient_nombre?: string;
  wallet_pass_id: string | null;
  puntos: number;
  sesiones_gratis: number;
  puntos_meta?: number;
  premio?: string;
  estrellas?: string;
  sesion_gratis_otorgada?: boolean;
}

export interface GoogleWalletSaveData {
  enabled: boolean;
  patient_id?: string;
  message?: string;
  save_url?: string;
  object_id?: string;
  class_id?: string;
  wallet_pass_id?: string | null;
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

// ============================================================
// Historia Clínica / Evoluciones
// ============================================================

export interface ClinicalRecord {
  id: string;
  tenant_id: string;
  patient_id: string;
  therapist_id: string | null;
  appointment_id: string | null;
  fecha: string | null;
  zona_tratada: string | null;
  tratamiento_servicio: string | null;
  productos_parametros: string | null;
  observaciones: string | null;
  diagnostico: string | null;
  therapist_name: string;
  patient_name: string;
  servicio: string;
  activo: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface ClinicalRecordCreateInput {
  fecha?: string;
  zona_tratada?: string;
  tratamiento_servicio?: string;
  productos_parametros?: string;
  observaciones?: string;
  diagnostico?: string;
  therapist_id?: string;
  appointment_id?: string;
}

export type ClinicalRecordUpdateInput = Partial<ClinicalRecordCreateInput> & { activo?: boolean };

export interface ClinicalRecordsResponse {
  records: ClinicalRecord[];
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

// ============================================================
// Asistente IA (FreeLLMAPI)
// ============================================================

export interface AssistantQuery {
  id: string;
  tenant_id: string;
  user_id: string | null;
  user_name?: string | null;
  question: string;
  response: string | null;
  is_understood: boolean | null;
  created_at: string;
  updated_at: string | null;
}

export interface AssistantChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

export interface AssistantAskResponse {
  id: string;
  question: string;
  response: string;
  is_understood: boolean | null;
  created_at: string;
}

export interface AssistantHistoryResponse {
  queries: AssistantQuery[];
  total: number;
}

export interface AssistantStatsResponse {
  total_queries: number;
  total_answered: number;
  understood: number;
  not_understood: number;
  pending_feedback: number;
  unique_users: number;
  avg_response_chars: number;
}

export interface AssistantStatusResponse {
  enabled: boolean;
  configured: boolean;
  active: boolean;
  base_url: string | null;
  model: string | null;
  missing: string[];
}

// ============================================================
// Notificaciones internas (campana del Dashboard)
// ============================================================

export type NotificationType = 'appointment' | 'appointment_reminder' | 'loyalty' | 'system' | 'info' | string;

export interface AppNotification {
  id: string;
  tenant_id: string;
  user_id: string;
  title: string;
  message: string | null;
  type: NotificationType;
  is_read: boolean;
  created_at: string;
  read_at: string | null;
}

export interface NotificationsResponse {
  notifications: AppNotification[];
  total: number;
  unread_count: number;
}

export interface UnreadNotificationsCountResponse {
  unread_count: number;
}

export interface NotificationMarkAllReadResponse {
  updated: number;
  unread_count: number;
}

// ============================================================
// Tarjeta pública de fidelidad (/tarjeta/{token})
// ============================================================

export interface PublicWalletInfo {
  tenant_name: string;
  tenant_logo_url: string | null;
  tarjeta_color_hex: string;
  puntos_actuales: number;
  puntos_meta: number;
  premio_fidelidad: string;
}

export interface PublicGoogleWalletResponse {
  enabled: boolean;
  save_url: string | null;
  message: string | null;
}

export interface WalletShareLink {
  url: string;
  token: string;
  expires_at: string | null;
}

export type Page = 'dashboard' | 'tenants' | 'users' | 'appointments' | 'patients' | 'services' | 'settings' | 'reports' | 'docs' | 'assistant' | 'whatsapp';

// ============================================================
// WhatsApp / Evolution API
// ============================================================

export interface WhatsAppSettings {
  instance_name: string | null;
  status: string;
  connected_at: string | null;
  qr_code: string | null;
  agent_enabled: boolean;
  agent_name: string;
  agent_tone: string;
  notifications_enabled: boolean;
  webhook_registered: boolean;
}

export interface WhatsAppStatusResponse {
  connected: boolean;
  state: string | null;
  instance_name: string | null;
}

export interface WhatsAppConnectResponse {
  instance_name: string;
  state: string | null;
  qr: string | null;
}

export interface WhatsAppConversation {
  id: string;
  phone: string;
  push_name: string | null;
  patient_id: string | null;
  patient_name: string | null;
  status: string;
  last_message_at: string | null;
  last_message_content: string | null;
  last_message_role: string | null;
  created_at: string;
}

export interface WhatsAppConversationListResponse {
  conversations: WhatsAppConversation[];
  total: number;
}

export interface WhatsAppMessage {
  id: string;
  role: string;
  content: string | null;
  created_at: string;
}

export interface WhatsAppMessageListResponse {
  messages: WhatsAppMessage[];
  total: number;
}
