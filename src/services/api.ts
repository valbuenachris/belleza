// ============================================================
// Servicio API - Simulación del Backend FastAPI
// En producción, este módulo se conectaría al backend real
// ============================================================

import { Tenant, User, TokenResponse, UserCreate, TenantStats } from '../types';
import { v4 as uuidv4 } from 'uuid';

// Datos de demostración precargados
const DEMO_USERS: User[] = [
  {
    id: '00000000-0000-0000-0000-000000000001',
    tenant_id: '',
    username: 'superadmin',
    email: 'superadmin@spa.com',
    nombre: 'Super',
    apellido: 'Administrador',
    rol: 'superadmin',
    activo: true,
    ultimo_acceso: new Date().toISOString(),
    telefono: '+57 300 123 4567',
    avatar_url: null,
    email_verificado: true,
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: '00000000-0000-0000-0000-000000000002',
    tenant_id: '00000000-0000-0000-0000-000000000001',
    username: 'admin',
    email: 'admin@demo.com',
    nombre: 'María',
    apellido: 'González',
    rol: 'admin',
    activo: true,
    ultimo_acceso: new Date().toISOString(),
    telefono: '+57 300 987 6543',
    avatar_url: null,
    email_verificado: true,
    created_at: '2024-01-15T00:00:00Z',
  },
  {
    id: '00000000-0000-0000-0000-000000000003',
    tenant_id: '00000000-0000-0000-0000-000000000001',
    username: 'recepcionista',
    email: 'recepcion@demo.com',
    nombre: 'Laura',
    apellido: 'Martínez',
    rol: 'receptionist',
    activo: true,
    ultimo_acceso: null,
    telefono: '+57 300 456 7890',
    avatar_url: null,
    email_verificado: true,
    created_at: '2024-02-01T00:00:00Z',
  },
  {
    id: '00000000-0000-0000-0000-000000000004',
    tenant_id: '00000000-0000-0000-0000-000000000001',
    username: 'terapeuta1',
    email: 'terapeuta@demo.com',
    nombre: 'Ana',
    apellido: 'Rodríguez',
    rol: 'therapist',
    activo: true,
    ultimo_acceso: null,
    telefono: '+57 300 111 2233',
    avatar_url: null,
    email_verificado: true,
    created_at: '2024-02-10T00:00:00Z',
  },
];

const DEMO_TENANTS: Tenant[] = [
  {
    id: '00000000-0000-0000-0000-000000000001',
    nombre: 'Serenity Spa & Wellness',
    subdominio: 'demo',
    plan: 'professional',
    activo: true,
    fecha_creacion: '2024-01-01T00:00:00Z',
    fecha_expiracion: '2025-12-31T23:59:59Z',
    configuracion: {
      horario_apertura: '08:00',
      horario_cierre: '20:00',
      dias_operacion: [1, 2, 3, 4, 5, 6],
      duracion_cita_default: 60,
      recordatorio_citas: true,
      confirmacion_citas: true,
    },
    limite_usuarios: 10,
    limite_pacientes: 1000,
    logo_url: null,
    direccion: 'Calle 100 #15-20, Bogotá, Colombia',
    telefono: '+57 601 555 0100',
    email: 'info@serenityspa.com',
    timezone: 'America/Bogota',
    moneda: 'USD',
  },
  {
    id: '00000000-0000-0000-0000-000000000002',
    nombre: 'Zen Garden Spa',
    subdominio: 'zengarden',
    plan: 'basic',
    activo: true,
    fecha_creacion: '2024-03-01T00:00:00Z',
    fecha_expiracion: '2025-03-01T23:59:59Z',
    configuracion: null,
    limite_usuarios: 5,
    limite_pacientes: 500,
    logo_url: null,
    direccion: 'Av. Principal 45, Medellín, Colombia',
    telefono: '+57 604 555 0200',
    email: 'contacto@zengarden.com',
    timezone: 'America/Bogota',
    moneda: 'USD',
  },
  {
    id: '00000000-0000-0000-0000-000000000003',
    nombre: 'Bella Vita Estética',
    subdominio: 'bellavita',
    plan: 'enterprise',
    activo: true,
    fecha_creacion: '2024-02-15T00:00:00Z',
    fecha_expiracion: null,
    configuracion: null,
    limite_usuarios: 50,
    limite_pacientes: 10000,
    logo_url: null,
    direccion: 'Carrera 7 #32-16, Bogotá, Colombia',
    telefono: '+57 601 555 0300',
    email: 'admin@bellavita.com',
    timezone: 'America/Bogota',
    moneda: 'COP',
  },
];

// Contraseña hasheada simulada (en producción sería bcrypt)
const DEMO_PASSWORD = 'Admin123!';

// Simular delay de red
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// ============================================================
// API Client - Simula las llamadas al backend FastAPI
// ============================================================

export const api = {
  // Autenticación
  async login(email: string, password: string): Promise<TokenResponse> {
    await delay(800);
    
    const user = DEMO_USERS.find(u => u.email === email);
    if (!user) {
      throw new Error('Credenciales inválidas. Verifica tu correo electrónico.');
    }
    if (password !== DEMO_PASSWORD) {
      throw new Error('Contraseña incorrecta. Intenta de nuevo.');
    }
    if (!user.activo) {
      throw new Error('Tu cuenta ha sido desactivada. Contacta al administrador.');
    }

    const tenant = user.tenant_id 
      ? DEMO_TENANTS.find(t => t.id === user.tenant_id) || null 
      : null;

    const token: TokenResponse = {
      access_token: `demo_access_${uuidv4()}`,
      refresh_token: `demo_refresh_${uuidv4()}`,
      token_type: 'bearer',
      user,
      tenant,
    };

    // Guardar en localStorage
    localStorage.setItem('spa_access_token', token.access_token);
    localStorage.setItem('spa_refresh_token', token.refresh_token);
    localStorage.setItem('spa_user', JSON.stringify(user));
    if (tenant) {
      localStorage.setItem('spa_tenant', JSON.stringify(tenant));
    }

    return token;
  },

  async logout(): Promise<void> {
    await delay(200);
    localStorage.removeItem('spa_access_token');
    localStorage.removeItem('spa_refresh_token');
    localStorage.removeItem('spa_user');
    localStorage.removeItem('spa_tenant');
  },

  async getCurrentUser(): Promise<{ user: User; tenant: Tenant | null } | null> {
    const userStr = localStorage.getItem('spa_user');
    const tenantStr = localStorage.getItem('spa_tenant');
    const token = localStorage.getItem('spa_access_token');
    
    if (!userStr || !token) return null;
    
    const user = JSON.parse(userStr) as User;
    const tenant = tenantStr ? JSON.parse(tenantStr) as Tenant : null;
    return { user, tenant };
  },

  // Tenants
  async getTenants(): Promise<Tenant[]> {
    await delay(500);
    return DEMO_TENANTS.map(t => ({
      ...t,
      estadisticas: generateStats(t.id),
    }));
  },

  async getTenantById(id: string): Promise<Tenant | null> {
    await delay(300);
    const tenant = DEMO_TENANTS.find(t => t.id === id);
    return tenant ? { ...tenant, estadisticas: generateStats(tenant.id) } : null;
  },

  async createTenant(data: Partial<Tenant>): Promise<Tenant> {
    await delay(1000);
    const newTenant: Tenant = {
      id: uuidv4(),
      nombre: data.nombre || 'Nuevo SPA',
      subdominio: data.subdominio || 'nuevo-spa',
      plan: data.plan || 'basic',
      activo: true,
      fecha_creacion: new Date().toISOString(),
      fecha_expiracion: null,
      configuracion: data.configuracion || null,
      limite_usuarios: data.limite_usuarios || 10,
      limite_pacientes: data.limite_pacientes || 1000,
      logo_url: null,
      direccion: data.direccion || null,
      telefono: data.telefono || null,
      email: data.email || null,
      timezone: data.timezone || 'America/Bogota',
      moneda: data.moneda || 'USD',
    };
    DEMO_TENANTS.push(newTenant);
    return newTenant;
  },

  async updateTenant(id: string, data: Partial<Tenant>): Promise<Tenant> {
    await delay(600);
    const index = DEMO_TENANTS.findIndex(t => t.id === id);
    if (index === -1) throw new Error('Tenant no encontrado');
    DEMO_TENANTS[index] = { ...DEMO_TENANTS[index], ...data };
    return DEMO_TENANTS[index];
  },

  async deleteTenant(id: string): Promise<boolean> {
    await delay(500);
    const index = DEMO_TENANTS.findIndex(t => t.id === id);
    if (index === -1) throw new Error('Tenant no encontrado');
    DEMO_TENANTS[index].activo = false;
    return true;
  },

  async checkSubdomain(subdomain: string): Promise<boolean> {
    await delay(300);
    return !DEMO_TENANTS.some(t => t.subdominio === subdomain);
  },

  // Users
  async getUsers(tenantId?: string): Promise<User[]> {
    await delay(500);
    if (tenantId) {
      return DEMO_USERS.filter(u => u.tenant_id === tenantId);
    }
    return [...DEMO_USERS];
  },

  async createUser(data: UserCreate): Promise<User> {
    await delay(800);
    const newUser: User = {
      id: uuidv4(),
      tenant_id: data.tenant_id || '',
      username: data.username,
      email: data.email,
      nombre: data.nombre,
      apellido: data.apellido,
      rol: data.rol,
      activo: true,
      ultimo_acceso: null,
      telefono: null,
      avatar_url: null,
      email_verificado: false,
      created_at: new Date().toISOString(),
    };
    DEMO_USERS.push(newUser);
    return newUser;
  },

  async updateUser(id: string, data: Partial<User>): Promise<User> {
    await delay(600);
    const index = DEMO_USERS.findIndex(u => u.id === id);
    if (index === -1) throw new Error('Usuario no encontrado');
    DEMO_USERS[index] = { ...DEMO_USERS[index], ...data };
    return DEMO_USERS[index];
  },

  async deleteUser(id: string): Promise<boolean> {
    await delay(500);
    const index = DEMO_USERS.findIndex(u => u.id === id);
    if (index === -1) throw new Error('Usuario no encontrado');
    DEMO_USERS[index].activo = false;
    return true;
  },

  // Dashboard stats
  async getDashboardStats(tenantId?: string): Promise<TenantStats> {
    await delay(400);
    return generateStats(tenantId || 'all');
  },

  // Registro de nuevo SPA
  async registerSpa(spaName: string, subdomain: string, adminEmail: string, adminPassword: string): Promise<{ tenant: Tenant; user: User }> {
    await delay(1500);
    
    const tenant = await this.createTenant({
      nombre: spaName,
      subdominio: subdomain,
      email: adminEmail,
    });

    const user = await this.createUser({
      username: adminEmail.split('@')[0],
      email: adminEmail,
      password: adminPassword,
      nombre: 'Administrador',
      apellido: 'Principal',
      rol: 'admin',
      tenant_id: tenant.id,
    });

    return { tenant, user };
  },
};

// Generador de estadísticas simuladas
function generateStats(tenantId: string): TenantStats {
  const seed = tenantId.charCodeAt(0) || 42;
  return {
    total_usuarios: 3 + (seed % 5),
    total_pacientes: 45 + (seed % 100),
    total_citas_hoy: 5 + (seed % 12),
    total_ingresos_mes: 2500 + (seed % 5000),
    citas_semana: [8, 12, 10, 15, 9, 7, 3].map(v => v + (seed % 5)),
    ingresos_mes: [3200, 4100, 3800, 4500, 5200, 4800, 5100, 4900, 5500, 5800, 6200, 5900].map(v => v + (seed % 500)),
  };
}
