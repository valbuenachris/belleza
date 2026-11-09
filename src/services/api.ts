// ============================================================
// Servicio API - Cliente HTTP real del backend FastAPI
// Base URL relativa (/api/v1) para ser proxyada por Nginx en
// producción o por Vite en desarrollo.
// ============================================================

import {
  Tenant,
  User,
  TokenResponse,
  TenantStats,
  GlobalTenantStats,
  Patient,
  PatientCreateInput,
  PatientsResponse,
  Service,
  ServiceCreateInput,
  ServicesResponse,
  Appointment,
  AppointmentCreateInput,
  AppointmentUpdateInput,
  AppointmentsResponse,
  AppointmentSummary,
  FinancialReport,
  ClinicalRecord,
  ClinicalRecordCreateInput,
  ClinicalRecordUpdateInput,
  ClinicalRecordsResponse,
  WalletPassData,
  RedeemSessionResult,
  ScanLoyaltyResult,
  GoogleWalletSaveData,
  UserCreate,
  UserUpdate,
  UsersResponse,
  AssistantStatusResponse,
  AssistantChatTurn,
  AssistantAskResponse,
  AssistantHistoryResponse,
  AssistantQuery,
  AssistantStatsResponse,
  AppNotification,
  NotificationsResponse,
  UnreadNotificationsCountResponse,
  NotificationMarkAllReadResponse,
  PublicWalletInfo,
  PublicGoogleWalletResponse,
  WalletShareLink,
  WhatsAppSettings,
  WhatsAppConnectResponse,
  WhatsAppStatusResponse,
  WhatsAppConversationListResponse,
  WhatsAppMessageListResponse,
} from '../types';

// ============================================================
// Configuración
// ============================================================

const API_BASE = '/api/v1';

const STORAGE_KEYS = {
  accessToken: 'spa_access_token',
  refreshToken: 'spa_refresh_token',
  user: 'spa_user',
  tenant: 'spa_tenant',
} as const;

export const SESSION_EXPIRED_EVENT = 'spa:session_expired';

// ============================================================
// Error API
// ============================================================

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: unknown;

  constructor(message: string, status: number, code?: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

interface HttpOptions {
  auth?: boolean;
  retryOnAuth?: boolean;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  headers?: Record<string, string>;
  /** Modo de caché del fetch (p.ej. 'no-store' para polling). */
  cache?: RequestCache;
}

// ============================================================
// Sesión en localStorage
// ============================================================

function getTokens(): { accessToken: string | null; refreshToken: string | null } {
  return {
    accessToken: localStorage.getItem(STORAGE_KEYS.accessToken),
    refreshToken: localStorage.getItem(STORAGE_KEYS.refreshToken),
  };
}

function persistSession(
  tokens: Pick<TokenResponse, 'access_token' | 'refresh_token'>,
  user: User | null,
  tenant: Tenant | null
): void {
  if (tokens.access_token) localStorage.setItem(STORAGE_KEYS.accessToken, tokens.access_token);
  if (tokens.refresh_token) localStorage.setItem(STORAGE_KEYS.refreshToken, tokens.refresh_token);
  persistUser(user);
  if (tenant) {
    localStorage.setItem(STORAGE_KEYS.tenant, JSON.stringify(tenant));
  } else {
    localStorage.removeItem(STORAGE_KEYS.tenant);
  }
}

function persistUser(user: User | null): void {
  if (user) localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(user));
  else localStorage.removeItem(STORAGE_KEYS.user);
}

function readStoredTenant(): Tenant | null {
  const raw = localStorage.getItem(STORAGE_KEYS.tenant);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Tenant;
  } catch {
    return null;
  }
}

function clearSession(): void {
  Object.values(STORAGE_KEYS).forEach((key) => localStorage.removeItem(key));
}

function notifySessionExpired(): void {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
  }
}

// ============================================================
// Normalización de respuestas del backend
// ============================================================

function normalizeUser(data: any): User {
  return {
    id: data.id,
    tenant_id: data.tenant_id ?? null,
    username: data.username ?? '',
    email: data.email ?? '',
    nombre: data.nombre ?? '',
    apellido: data.apellido ?? '',
    rol: data.rol ?? 'receptionist',
    activo: data.activo ?? true,
    ultimo_acceso: data.ultimo_acceso ?? null,
    telefono: data.telefono ?? null,
    avatar_url: data.avatar_url ?? null,
    email_verificado: data.email_verificado ?? false,
    created_at: data.created_at ?? new Date().toISOString(),
  };
}

function normalizeTenant(data: any): Tenant {
  return {
    id: data.id,
    nombre: data.nombre ?? '',
    subdominio: data.subdominio ?? '',
    plan: data.plan ?? 'basic',
    activo: data.activo ?? true,
    fecha_creacion: data.fecha_creacion ?? new Date().toISOString(),
    fecha_expiracion: data.fecha_expiracion ?? null,
    configuracion: data.configuracion ?? null,
    limite_usuarios: data.limite_usuarios ?? 10,
    limite_pacientes: data.limite_pacientes ?? 1000,
    logo_url: data.logo_url ?? null,
    direccion: data.direccion ?? null,
    telefono: data.telefono ?? null,
    email: data.email ?? null,
    timezone: data.timezone ?? 'America/Bogota',
    moneda: data.moneda ?? 'USD',
    puntos_meta: data.puntos_meta ?? 10,
    premio_fidelidad: data.premio_fidelidad ?? 'Sesión de Spa gratis',
    tarjeta_color_hex: data.tarjeta_color_hex ?? '#0D9488',
    estadisticas: data.estadisticas ?? undefined,
  };
}

// ============================================================
// Cliente HTTP con refresh automático de tokens (single-flight)
// ============================================================

let refreshPromise: Promise<{ access_token: string; refresh_token: string } | null> | null = null;

async function tryRefresh(): Promise<{ access_token: string; refresh_token: string } | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const tokens = getTokens();
      if (!tokens.refreshToken) {
        clearSession();
        return null;
      }
      try {
        const res = await fetch(
          `${API_BASE}/auth/refresh?refresh_token=${encodeURIComponent(tokens.refreshToken)}`,
          { method: 'POST', credentials: 'include' }
        );
        if (!res.ok) {
          clearSession();
          notifySessionExpired();
          return null;
        }
        const payload = await res.json();
        const user = payload.user ? normalizeUser(payload.user) : null;
        const tenant = payload.tenant ? normalizeTenant(payload.tenant) : null;
        persistSession(payload, user, tenant);
        return { access_token: payload.access_token, refresh_token: payload.refresh_token };
      } catch {
        clearSession();
        notifySessionExpired();
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

async function toApiError(res: Response): Promise<ApiError> {
  let message = res.statusText || `Error ${res.status}`;
  let code: string | undefined;
  let details: unknown;
  try {
    const payload = await res.json();
    if (typeof payload?.detail === 'string') {
      message = payload.detail;
    } else if (Array.isArray(payload?.detail)) {
      details = payload.detail;
      const msgs = payload.detail.map((d: any) => typeof d === 'string' ? d : d?.msg).filter(Boolean);
      if (msgs.length) message = msgs.join('; ');
    } else if (payload?.detail && typeof payload.detail === 'object') {
      details = payload.detail;
    }
    if (payload?.errors) {
      const errors = Array.isArray(payload.errors) ? payload.errors : [];
      const msgs = errors
        .map((e: any) => e?.message ?? (e?.field ? `${e.field}: ${e.msg ?? ''}` : e?.msg).trim())
        .filter(Boolean);
      if (msgs.length) message = msgs.join('; ');
      details = errors;
    }
    code = payload?.code;
  } catch {
    // Sin cuerpo aprovechable
  }
  return new ApiError(message, res.status, code, details);
}

async function request<T>(path: string, options: HttpOptions = {}): Promise<T> {
  const {
    auth = true,
    retryOnAuth = true,
    method = 'GET',
    body,
    headers = {},
    cache,
  } = options;

  const buildFetch = (token?: string | null): Promise<Response> => {
    // Cabeceras normalizadas a minúsculas para evitar duplicados
    // (ej: Content-Type + content-type con valores distintos).
    const reqHeaders: Record<string, string> = {};
    Object.entries(headers).forEach(([k, v]) => {
      reqHeaders[k.toLowerCase()] = v;
    });
    if (auth && token) reqHeaders['authorization'] = `Bearer ${token}`;
    if (body !== undefined) {
      // Content-Type limpio (sin charset): el backend espera JSON puro
      reqHeaders['content-type'] = 'application/json';
    }
    const init: RequestInit = { method, headers: reqHeaders, credentials: 'include' };
    if (cache) init.cache = cache;
    if (body !== undefined) {
      init.body = JSON.stringify(body);
    }
    return fetch(`${API_BASE}${path}`, init);
  };

  let token = auth ? getTokens().accessToken : null;
  let res = await buildFetch(token);

  if (res.status === 401 && auth && retryOnAuth) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      res = await buildFetch(refreshed.access_token);
    }
  }

  if (!res.ok) throw await toApiError(res);
  return res.json() as Promise<T>;
}

// ============================================================
// API Client
// ============================================================

export const api = {
  // ----------------------------------------------------------
  // Autenticación
  // ----------------------------------------------------------
  async login(email: string, password: string): Promise<TokenResponse> {
    const data = await request<any>('/auth/login', {
      auth: false,
      method: 'POST',
      body: { email, password },
    });
    const user = data.user ? normalizeUser(data.user) : null;
    const tenant = data.tenant ? normalizeTenant(data.tenant) : null;
    if (user) persistSession(data, user, tenant);
    return { ...data, user, tenant };
  },

  async logout(): Promise<void> {
    const tokens = getTokens();
    try {
      if (tokens.accessToken) {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${tokens.accessToken}` },
          credentials: 'include',
        });
      }
    } catch {
      // Ignorar errores de red: la sesión local se limpia igual
    }
    clearSession();
  },

  async getCurrentUser(): Promise<{ user: User; tenant: Tenant | null } | null> {
    const tokens = getTokens();
    if (!tokens.accessToken && !tokens.refreshToken) return null;
    try {
      const data = await request<any>('/auth/me');
      const user = normalizeUser(data);
      persistUser(user);
      return { user, tenant: readStoredTenant() };
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) return null;
      throw err;
    }
  },

  async registerSpa(payload: {
    tenant_data: {
      nombre: string;
      plan: string;
      email?: string;
      telefono?: string | null;
      direccion?: string | null;
    };
    admin_data: {
      email: string;
      password: string;
      username?: string;
      nombre?: string;
      apellido?: string;
    };
  }): Promise<{ tenant: Tenant; user: User }> {
    const { tenant_data, admin_data } = payload;
    const base = admin_data.email.split('@')[0].toLowerCase().replace(/[^a-z0-9]/g, '');
    const username = admin_data.username || (base.length >= 3 ? base : base.padEnd(3, 'x') + 'admin');

    const data = await request<any>('/auth/register', {
      auth: false,
      method: 'POST',
      body: {
        tenant_data: {
          nombre: tenant_data.nombre,
          plan: tenant_data.plan,
          email: tenant_data.email ?? admin_data.email,
          telefono: tenant_data.telefono ?? null,
          direccion: tenant_data.direccion ?? null,
        },
        admin_data: {
          username,
          email: admin_data.email,
          password: admin_data.password,
          nombre: admin_data.nombre || 'Administrador',
          apellido: admin_data.apellido || 'Principal',
          rol: 'admin',
        },
      },
    });

    const user = data.user ? normalizeUser(data.user) : null;
    const tenant = data.tenant ? normalizeTenant(data.tenant) : null;
    if (data.access_token && user) {
      persistSession(data, user, tenant);
    }
    return { tenant: tenant!, user: user! };
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
    return request<any>('/auth/change-password', {
      method: 'PUT',
      body: { current_password: currentPassword, new_password: newPassword },
    });
  },

  // ----------------------------------------------------------
  // Tenants
  // ----------------------------------------------------------
  async getTenants(): Promise<Tenant[]> {
    const data = await request<any[]>('/tenants?limit=100');
    const items = data.map((t) => normalizeTenant(t));
    // Adjuntar estadísticas de usuarios por tenant (superadmin)
    const withStats = await Promise.all(
      items.map(async (t) => {
        try {
          const stats = await request<{ total_usuarios: number }>(`/tenants/${t.id}/stats`);
          return { ...t, estadisticas: { ...(t.estadisticas || {}), total_usuarios: stats.total_usuarios } };
        } catch {
          return t;
        }
      })
    );
    return withStats;
  },

  async getTenantById(id: string): Promise<Tenant | null> {
    try {
      const data = await request<any>(`/tenants/${id}`);
      const tenant = normalizeTenant(data);
      try {
        const stats = await request<{ total_usuarios: number }>(`/tenants/${id}/stats`);
        tenant.estadisticas = { ...(tenant.estadisticas || {}), total_usuarios: stats.total_usuarios };
      } catch {
        // Sin estadísticas del tenant
      }
      return tenant;
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  },

  async getTenantGlobalStats(): Promise<GlobalTenantStats> {
    return request<GlobalTenantStats>('/tenants/stats/global');
  },

  async createTenant(
    data: Partial<Tenant> & {
      admin?: {
        nombre: string;
        apellido: string;
        email: string;
        password: string;
        rol?: string;
      };
    }
  ): Promise<Tenant> {
    const res = await request<any>('/tenants', {
      method: 'POST',
      body: {
        nombre: data.nombre,
        plan: data.plan || 'basic',
        email: data.email ?? null,
        telefono: data.telefono ?? null,
        direccion: data.direccion ?? null,
        timezone: data.timezone || 'America/Bogota',
        moneda: data.moneda || 'USD',
        admin: data.admin ?? null,
      },
    });
    return normalizeTenant(res);
  },

  async updateTenant(id: string, data: Record<string, unknown>): Promise<Tenant> {
    const res = await request<any>(`/tenants/${id}`, { method: 'PUT', body: data });
    return normalizeTenant(res);
  },

  async renewTenant(id: string): Promise<Tenant> {
    const res = await request<any>(`/tenants/${id}/renew`, { method: 'PUT' });
    return normalizeTenant(res);
  },

  async deleteTenant(id: string): Promise<void> {
    await request<{ message: string }>(`/tenants/${id}`, { method: 'DELETE' });
  },

  // ----------------------------------------------------------
  // Usuarios del SPA
  // ----------------------------------------------------------
  async getUsers(): Promise<User[]> {
    const data = await request<UsersResponse>('/users?limit=100');
    return (data.users || []).map(normalizeUser);
  },

  async createUser(data: UserCreate): Promise<User> {
    const res = await request<{ user: any }>('/users', { method: 'POST', body: data });
    return normalizeUser(res.user);
  },

  async updateUser(id: string, data: UserUpdate): Promise<User> {
    const res = await request<{ user: any }>(`/users/${id}`, { method: 'PUT', body: data });
    return normalizeUser(res.user);
  },

  async deleteUser(id: string): Promise<void> {
    await request<{ deleted: boolean }>(`/users/${id}`, { method: 'DELETE' });
  },

  // ----------------------------------------------------------
  // Pacientes
  // ----------------------------------------------------------
  async getPatients(): Promise<PatientsResponse> {
    return request<PatientsResponse>('/patients?limit=100');
  },

  async createPatient(data: PatientCreateInput): Promise<Patient> {
    const res = await request<{ patient: Patient }>('/patients', { method: 'POST', body: data });
    return res.patient;
  },

  async updatePatient(id: string, data: Partial<PatientCreateInput> & { activo?: boolean }): Promise<Patient> {
    const res = await request<{ patient: Patient }>(`/patients/${id}`, { method: 'PUT', body: data });
    return res.patient;
  },

  async deletePatient(id: string): Promise<void> {
    await request<{ deleted: boolean }>(`/patients/${id}`, { method: 'DELETE' });
  },

  // ----------------------------------------------------------
  // Servicios
  // ----------------------------------------------------------
  async getServices(): Promise<ServicesResponse> {
    return request<ServicesResponse>('/services?limit=100');
  },

  async createService(data: ServiceCreateInput): Promise<Service> {
    const res = await request<{ service: Service }>('/services', { method: 'POST', body: data });
    return res.service;
  },

  async updateService(id: string, data: Partial<ServiceCreateInput> & { activo?: boolean }): Promise<string> {
    const res = await request<{ service_id: string }>(`/services/${id}`, { method: 'PUT', body: data });
    return res.service_id;
  },

  async deleteService(id: string): Promise<void> {
    await request<{ deleted: boolean }>(`/services/${id}`, { method: 'DELETE' });
  },

  // ----------------------------------------------------------
  // Citas
  // ----------------------------------------------------------
  async getAppointments(params?: { fecha?: string; estado?: string; patient_id?: string; limit?: number }): Promise<AppointmentsResponse> {
    const query = new URLSearchParams({ limit: String(params?.limit ?? 100) });
    if (params?.fecha) query.set('fecha', params.fecha);
    if (params?.estado) query.set('estado', params.estado);
    if (params?.patient_id) query.set('patient_id', params.patient_id);
    return request<AppointmentsResponse>(`/appointments?${query.toString()}`);
  },

  async createAppointment(data: AppointmentCreateInput): Promise<Appointment> {
    const res = await request<{ appointment: Appointment }>('/appointments', {
      method: 'POST',
      body: data,
    });
    return res.appointment;
  },

  async updateAppointment(id: string, data: AppointmentUpdateInput): Promise<Appointment> {
    const res = await request<{ appointment: Appointment }>(`/appointments/${id}`, {
      method: 'PUT',
      body: data,
    });
    return res.appointment;
  },

  async cancelAppointment(id: string): Promise<Appointment> {
    const res = await request<{ appointment: Appointment }>(`/appointments/${id}`, { method: 'DELETE' });
    return res.appointment;
  },

  async getAppointmentSummary(): Promise<AppointmentSummary> {
    return request<AppointmentSummary>('/appointments/stats/summary');
  },

  async getFinancialReport(params?: { desde?: string; hasta?: string }): Promise<FinancialReport> {
    const query = new URLSearchParams();
    if (params?.desde) query.set('desde', params.desde);
    if (params?.hasta) query.set('hasta', params.hasta);
    const qs = query.toString();
    return request<FinancialReport>(`/appointments/stats/financial${qs ? `?${qs}` : ''}`);
  },

  // ----------------------------------------------------------
  // Historia Clínica / Evoluciones
  // ----------------------------------------------------------
  async getPatientRecords(patientId: string): Promise<ClinicalRecordsResponse> {
    return request<ClinicalRecordsResponse>(`/patients/${patientId}/records`);
  },

  async createClinicalRecord(patientId: string, data: ClinicalRecordCreateInput): Promise<ClinicalRecord> {
    const res = await request<{ record: ClinicalRecord }>(`/patients/${patientId}/records`, {
      method: 'POST',
      body: data,
    });
    return res.record;
  },

  async updateClinicalRecord(id: string, data: ClinicalRecordUpdateInput): Promise<ClinicalRecord> {
    const res = await request<{ record: ClinicalRecord }>(`/clinical-records/${id}`, {
      method: 'PUT',
      body: data,
    });
    return res.record;
  },

  async deleteClinicalRecord(id: string): Promise<void> {
    await request<{ deleted: boolean }>(`/clinical-records/${id}`, { method: 'DELETE' });
  },

  // ----------------------------------------------------------
  // Programa de Fidelidad (Loyalty Rewards / Wallet)
  // ----------------------------------------------------------
  async getWalletPass(patientId: string): Promise<WalletPassData> {
    const res = await request<{ message: string } & WalletPassData>(`/patients/${patientId}/wallet-pass?formato=json`);
    return {
      ...res,
      pase: res.pase ?? {
        tipo: 'storeCard',
        formato: 'json',
        organization_name: 'SPA',
        serial_number: res.wallet_pass_id,
        pass_type_identifier: '',
        team_identifier: '',
      },
    };
  },

  async downloadWalletPass(patientId: string): Promise<void> {
    const token = getTokens().accessToken;
    const res = await fetch(`${API_BASE}/patients/${patientId}/wallet-pass?formato=pkpass`, {
      method: 'GET',
      headers: token ? { authorization: `Bearer ${token}` } : {},
      credentials: 'include',
    });
    if (!res.ok) throw await toApiError(res);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fidelidad-${patientId.slice(0, 8)}.pkpass`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  async getGoogleWalletSaveLink(patientId: string): Promise<GoogleWalletSaveData> {
    return request<GoogleWalletSaveData>(`/patients/${patientId}/google-wallet`);
  },

  async createWalletShareLink(patientId: string): Promise<WalletShareLink> {
    return request<WalletShareLink>(`/patients/${patientId}/wallet-share-link`, { method: 'POST' });
  },

  async redeemSession(patientId: string): Promise<RedeemSessionResult> {
    return request<RedeemSessionResult>(`/patients/${patientId}/redeem-session`, { method: 'POST' });
  },

  // ----------------------------------------------------------
  // Escáner de tarjetas de fidelidad (por wallet_pass_id)
  // ----------------------------------------------------------
  async scanAddPoint(walletPassId: string): Promise<ScanLoyaltyResult> {
    return request<ScanLoyaltyResult>(`/loyalty/scan/${encodeURIComponent(walletPassId)}/add-point`, {
      method: 'POST',
    });
  },

  async scanRedeem(walletPassId: string): Promise<ScanLoyaltyResult> {
    return request<ScanLoyaltyResult>(`/loyalty/scan/${encodeURIComponent(walletPassId)}/redeem`, {
      method: 'POST',
    });
  },

  // ----------------------------------------------------------
  // Tarjeta pública de fidelidad (SIN autenticación)
  // El token de la URL es la única credencial: estas llamadas NUNCA
  // adjuntan el JWT (auth: false).
  // ----------------------------------------------------------
  async getPublicWalletInfo(token: string): Promise<PublicWalletInfo> {
    return request<PublicWalletInfo>(`/public/wallet/${encodeURIComponent(token)}`, {
      auth: false,
    });
  },

  async downloadPublicPkpass(token: string): Promise<void> {
    // fetch directo SIN cabecera Authorization (endpoint público).
    const res = await fetch(`${API_BASE}/public/wallet/${encodeURIComponent(token)}/pkpass`, {
      method: 'GET',
    });
    if (!res.ok) throw await toApiError(res);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'tarjeta-fidelidad.pkpass';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  async getPublicGoogleWalletLink(token: string): Promise<PublicGoogleWalletResponse> {
    return request<PublicGoogleWalletResponse>(
      `/public/wallet/${encodeURIComponent(token)}/google`,
      { auth: false },
    );
  },

  // ----------------------------------------------------------
  // Dashboard (agregado de estadísticas reales del SPA)
  // ----------------------------------------------------------
  async getDashboardStats(): Promise<TenantStats> {
    const [usersRes, patientsRes, summary, apptsRes] = await Promise.all([
      request<UsersResponse>('/users?limit=1'),
      request<PatientsResponse>('/patients?limit=1'),
      request<AppointmentSummary>('/appointments/stats/summary'),
      request<AppointmentsResponse>('/appointments?limit=100'),
    ]);

    const citasSemana = [0, 0, 0, 0, 0, 0, 0];
    const ingresosMes = Array(12).fill(0) as number[];

    for (const apt of apptsRes.appointments || []) {
      if (apt.estado === 'cancelled') continue;
      const dt = apt.date_time ? new Date(apt.date_time) : null;
      if (dt && !isNaN(dt.getTime())) {
        const dow = (dt.getDay() + 6) % 7; // 0 = Lunes
        citasSemana[dow] += 1;
        ingresosMes[dt.getMonth()] += apt.precio ?? 0;
      }
    }

    return {
      total_usuarios: usersRes.total ?? 0,
      total_pacientes: patientsRes.total ?? 0,
      total_citas_hoy: summary?.total_citas_hoy ?? 0,
      total_ingresos_hoy: summary?.ingresos_hoy ?? 0,
      total_ingresos_mes: ingresosMes[new Date().getMonth()] ?? 0,
      citas_semana: citasSemana,
      ingresos_mes: ingresosMes.map((v) => Math.round(v)),
    };
  },

  // ----------------------------------------------------------
  // Asistente IA (FreeLLMAPI)
  // ----------------------------------------------------------
  async getAssistantStatus(): Promise<AssistantStatusResponse> {
    return request<AssistantStatusResponse>('/assistant/status');
  },

  async assistantAsk(
    question: string,
    history: AssistantChatTurn[] = [],
  ): Promise<AssistantAskResponse> {
    return request<AssistantAskResponse>('/assistant/ask', {
      method: 'POST',
      body: { question, history },
    });
  },

  async getAssistantHistory(params?: { limit?: number; offset?: number }): Promise<AssistantHistoryResponse> {
    const query = new URLSearchParams({ limit: String(params?.limit ?? 50) });
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    return request<AssistantHistoryResponse>(`/assistant/history?${query.toString()}`);
  },

  async getAssistantQueries(params?: {
    search?: string;
    is_understood?: string;
    limit?: number;
    offset?: number;
  }): Promise<AssistantHistoryResponse> {
    const query = new URLSearchParams({ limit: String(params?.limit ?? 50) });
    if (params?.search) query.set('search', params.search);
    if (params?.is_understood) query.set('is_understood', params.is_understood);
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    return request<AssistantHistoryResponse>(`/assistant/queries?${query.toString()}`);
  },

  async getAssistantStats(): Promise<AssistantStatsResponse> {
    return request<AssistantStatsResponse>('/assistant/queries/stats');
  },

  async sendAssistantFeedback(queryId: string, is_understood: boolean): Promise<AssistantQuery> {
    return request<AssistantQuery>(`/assistant/queries/${queryId}/feedback`, {
      method: 'POST',
      body: { is_understood },
    });
  },

  async deleteAssistantQuery(queryId: string): Promise<{ deleted: boolean; message: string }> {
    return request<{ deleted: boolean; message: string }>(`/assistant/queries/${queryId}`, {
      method: 'DELETE',
    });
  },

  // ----------------------------------------------------------
  // Notificaciones internas (campana del Dashboard)
  // ----------------------------------------------------------
  async getNotifications(params?: {
    is_read?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<NotificationsResponse> {
    const query = new URLSearchParams({ limit: String(params?.limit ?? 20) });
    if (params?.is_read !== undefined) query.set('is_read', String(params.is_read));
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    return request<NotificationsResponse>(`/notifications?${query.toString()}`, {
      // Polling: impedir que el navegador/proxy sirvan una respuesta cacheada.
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    });
  },

  async getUnreadNotificationsCount(): Promise<UnreadNotificationsCountResponse> {
    return request<UnreadNotificationsCountResponse>('/notifications/unread-count', {
      // Polling: impedir que el navegador/proxy sirvan una respuesta cacheada.
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' },
    });
  },

  async markNotificationRead(id: string): Promise<AppNotification> {
    return request<AppNotification>(`/notifications/${id}/read`, { method: 'PUT' });
  },

  async markAllNotificationsRead(): Promise<NotificationMarkAllReadResponse> {
    return request<NotificationMarkAllReadResponse>('/notifications/read-all', {
      method: 'PUT',
    });
  },

  // ----------------------------------------------------------
  // WhatsApp / Evolution API
  // ----------------------------------------------------------
  async getWhatsAppSettings(): Promise<WhatsAppSettings> {
    return request<WhatsAppSettings>('/whatsapp/settings');
  },

  async updateWhatsAppSettings(data: {
    agent_enabled?: boolean;
    agent_name?: string;
    agent_tone?: string;
    notifications_enabled?: boolean;
  }): Promise<WhatsAppSettings> {
    return request<WhatsAppSettings>('/whatsapp/settings', {
      method: 'PUT',
      body: data,
    });
  },

  async createWhatsAppInstance(): Promise<WhatsAppConnectResponse> {
    return request<WhatsAppConnectResponse>('/whatsapp/instance', {
      method: 'POST',
    });
  },

  async connectWhatsApp(): Promise<WhatsAppConnectResponse> {
    return request<WhatsAppConnectResponse>('/whatsapp/connect', {
      method: 'POST',
    });
  },

  async getWhatsAppStatus(): Promise<WhatsAppStatusResponse> {
    return request<WhatsAppStatusResponse>('/whatsapp/status');
  },

  async disconnectWhatsApp(): Promise<{ message: string }> {
    return request<{ message: string }>('/whatsapp/disconnect', {
      method: 'POST',
    });
  },

  async getWhatsAppConversations(params?: {
    limit?: number;
    offset?: number;
    status?: string;
  }): Promise<WhatsAppConversationListResponse> {
    const query = new URLSearchParams({ limit: String(params?.limit ?? 50) });
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    if (params?.status) query.set('status', params.status);
    return request<WhatsAppConversationListResponse>(`/whatsapp/conversations?${query.toString()}`);
  },

  async getWhatsAppMessages(
    conversationId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<WhatsAppMessageListResponse> {
    const query = new URLSearchParams({ limit: String(params?.limit ?? 50) });
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    return request<WhatsAppMessageListResponse>(
      `/whatsapp/conversations/${conversationId}/messages?${query.toString()}`
    );
  },
};

export { SESSION_EXPIRED_EVENT as SESSION_EXPIRED };