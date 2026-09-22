// ============================================================
// Dashboard - Vista principal con estadísticas reales
// ============================================================

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api, ApiError } from '../services/api';
import { TenantStats, Appointment, Page } from '../types';
import {
  Users, Calendar, DollarSign, UserCheck, TrendingUp,
  Clock, Activity, Building2, CheckCircle2, Circle,
  ChevronRight, Settings, Tag, HelpCircle, UserPlus, CalendarPlus,
  AlertCircle
} from 'lucide-react';

interface DashboardPageProps {
  onNavigate?: (page: Page) => void;
}

export default function DashboardPage({ onNavigate }: DashboardPageProps) {
  const { user, tenant } = useAuth();
  const [stats, setStats] = useState<TenantStats | null>(null);
  const [recentAppointments, setRecentAppointments] = useState<Appointment[]>([]);
  const [servicesCount, setServicesCount] = useState(0);
  const [therapistsCount, setTherapistsCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const isSuperadmin = user?.rol === 'superadmin';

  const currencyFormatter = new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: tenant?.moneda || 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
  const fmtMoney = (v: number) => currencyFormatter.format(v);

  useEffect(() => {
    if (isSuperadmin) {
      setLoading(false);
      return;
    }
    const loadStats = async () => {
      setLoading(true);
      setError('');
      try {
        const [statsData, apts, servicesRes, usersRes] = await Promise.all([
          api.getDashboardStats(),
          api.getAppointments({}),
          api.getServices(),
          api.getUsers(),
        ]);
        setStats(statsData);
        setRecentAppointments((apts.appointments || []).slice(0, 5));
        setServicesCount(servicesRes.services?.length ?? 0);
        setTherapistsCount((usersRes ?? []).filter((u) => u.rol === 'therapist' && u.activo).length);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Error al cargar el dashboard');
      } finally {
        setLoading(false);
      }
    };
    loadStats();
  }, [isSuperadmin]);

  const statCards = stats ? [
    {
      label: 'Usuarios Activos',
      value: stats.total_usuarios,
      icon: <Users size={22} />,
      color: 'emerald',
    },
    {
      label: 'Pacientes Registrados',
      value: stats.total_pacientes,
      icon: <UserCheck size={22} />,
      color: 'blue',
    },
    {
      label: 'Citas Hoy',
      value: stats.total_citas_hoy,
      icon: <Calendar size={22} />,
      color: 'violet',
    },
    {
      label: 'Ingresos de Hoy',
      value: fmtMoney(stats.total_ingresos_hoy),
      icon: <DollarSign size={22} />,
      color: 'amber',
    },
  ] : [];

  const checklist = stats
    ? [
        {
          label: 'Configura los horarios de tu SPA',
          page: 'settings' as Page,
          icon: <Settings size={16} />,
          done: Boolean(
            tenant?.configuracion &&
            tenant.configuracion.horario_apertura &&
            tenant.configuracion.horario_cierre
          ),
        },
        {
          label: 'Crea tu primer servicio',
          page: 'services' as Page,
          icon: <Tag size={16} />,
          done: servicesCount > 0,
        },
        {
          label: 'Agrega al menos un terapeuta',
          page: 'users' as Page,
          icon: <HelpCircle size={16} />,
          done: therapistsCount > 0,
        },
        {
          label: 'Registra tu primer paciente',
          page: 'patients' as Page,
          icon: <UserPlus size={16} />,
          done: stats.total_pacientes > 0,
        },
        {
          label: 'Agenda tu primera cita',
          page: 'appointments' as Page,
          icon: <CalendarPlus size={16} />,
          done: recentAppointments.length > 0,
        },
      ]
    : [];

  const doneCount = checklist.filter((c) => c.done).length;
  const progress = checklist.length ? Math.round((doneCount / checklist.length) * 100) : 0;

  const quotaBars = stats && tenant
    ? [
        {
          label: 'Usuarios',
          used: stats.total_usuarios,
          limit: tenant.limite_usuarios,
          color: 'bg-emerald-500',
        },
        {
          label: 'Pacientes',
          used: stats.total_pacientes,
          limit: tenant.limite_pacientes,
          color: 'bg-blue-500',
        },
      ]
    : [];

  const days = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

  // Estado de la prueba gratuita / suscripción del tenant
  const expInfo = React.useMemo(() => {
    if (isSuperadmin || !tenant || !tenant.fecha_expiracion) return null;
    const exp = new Date(tenant.fecha_expiracion);
    if (isNaN(exp.getTime())) return null;
    const remaining = Math.ceil((exp.getTime() - Date.now()) / 86400000);
    return { remaining, exp };
  }, [tenant, isSuperadmin]);

  const navigate = (page: Page) => {
    if (onNavigate) onNavigate(page);
  };

  if (isSuperadmin) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-stone-800">¡Hola, {user?.nombre} {user?.apellido}! 👋</h1>
          <p className="text-stone-500 mt-1">Panel de Administración Global</p>
        </div>
        <div className="bg-white rounded-2xl border border-stone-100 p-12 text-center">
          <div className="w-16 h-16 bg-emerald-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Building2 size={32} className="text-emerald-600" />
          </div>
          <h2 className="text-xl font-semibold text-stone-800 mb-2">Gestión de Tenants</h2>
          <p className="text-stone-500 max-w-md mx-auto">
            Como superadministrador puedes crear, gestionar y visualizar los SPAs registrados en la plataforma desde el módulo de Tenants.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-stone-800">
            ¡Hola, {user?.nombre} {user?.apellido}! 👋
          </h1>
          <p className="text-stone-500 mt-1">
            {tenant ? `Panel de ${tenant.nombre}` : 'Panel de Administración'}
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-stone-500 bg-white px-4 py-2 rounded-xl border border-stone-200">
          <Clock size={16} />
          <span>{new Date().toLocaleDateString('es-ES', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</span>
        </div>
      </div>

      {/* Aviso de prueba gratuita / suscripción */}
      {expInfo && (
        expInfo.remaining < 0 ? (
          <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-100 rounded-2xl text-sm text-red-700">
            <AlertCircle size={18} className="shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Tu suscripción ha expirado</p>
              <p className="text-red-600/80 mt-0.5">
                Tu periodo de prueba o suscripción finalizó el{' '}
                {expInfo.exp.toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' })}.
                Contacta al administrador para renovar tu servicio.
              </p>
            </div>
          </div>
        ) : expInfo.remaining <= 14 ? (
          <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-100 rounded-2xl text-sm text-amber-800">
            <AlertCircle size={18} className="shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">
                ⏰ Tu periodo de prueba gratuito finaliza en{' '}
                {expInfo.remaining === 0 ? 'hoy' : `${expInfo.remaining} día${expInfo.remaining === 1 ? '' : 's'}`}.
              </p>
              <p className="text-amber-700/80 mt-0.5">
                Contacta al administrador para activar tu suscripción mensual.
              </p>
            </div>
          </div>
        ) : null
      )}

      {error && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">{error}</div>
      )}

      {/* Stats cards */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white rounded-2xl p-6 border border-stone-100 animate-pulse">
              <div className="h-4 bg-stone-100 rounded w-24 mb-3" />
              <div className="h-8 bg-stone-100 rounded w-16 mb-2" />
              <div className="h-3 bg-stone-100 rounded w-20" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((card, i) => (
            <div
              key={i}
              className="bg-white rounded-2xl p-6 border border-stone-100 hover:shadow-lg hover:shadow-stone-100 transition-all duration-300"
            >
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-medium text-stone-500">{card.label}</span>
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                  card.color === 'emerald' ? 'bg-emerald-50 text-emerald-600' :
                  card.color === 'blue' ? 'bg-blue-50 text-blue-600' :
                  card.color === 'violet' ? 'bg-violet-50 text-violet-600' :
                  'bg-amber-50 text-amber-600'
                }`}>
                  {card.icon}
                </div>
              </div>
              <p className="text-2xl font-bold text-stone-800">{card.value}</p>
              <div className="flex items-center gap-1 mt-2 text-xs font-medium text-stone-400">
                <Activity size={14} />
                En tiempo real
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Onboarding checklist + Plan usage */}
      {!loading && stats && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Onboarding checklist */}
          <div className="bg-white rounded-2xl p-6 border border-stone-100">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-stone-800">Configuración Inicial</h3>
                <p className="text-sm text-stone-500">Completa estos pasos para activar tu SPA</p>
              </div>
              <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full">
                {doneCount}/{checklist.length}
              </span>
            </div>
            <div className="h-2 bg-stone-100 rounded-full overflow-hidden mb-4">
              <div className="h-full bg-emerald-500 rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
            </div>
            <div className="space-y-1">
              {checklist.map((item, i) => (
                <button
                  key={i}
                  onClick={() => navigate(item.page)}
                  className="w-full flex items-center gap-3 p-2.5 rounded-xl hover:bg-stone-50 transition-colors text-left"
                >
                  <span className={`shrink-0 ${item.done ? 'text-emerald-500' : 'text-stone-300'}`}>
                    {item.done ? <CheckCircle2 size={20} /> : <Circle size={20} />}
                  </span>
                  <span className={`text-sm flex-1 ${item.done ? 'text-stone-400 line-through' : 'text-stone-700 font-medium'}`}>
                    {item.label}
                  </span>
                  <span className={`shrink-0 w-7 h-7 rounded-lg flex items-center justify-center ${
                    item.done ? 'bg-emerald-50 text-emerald-600' : 'bg-stone-100 text-stone-400'
                  }`}>
                    {item.icon}
                  </span>
                  <ChevronRight size={16} className="shrink-0 text-stone-300" />
                </button>
              ))}
            </div>
          </div>

          {/* Plan usage */}
          <div className="bg-white rounded-2xl p-6 border border-stone-100">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-stone-800">Uso del Plan</h3>
                <p className="text-sm text-stone-500">
                  {tenant ? `Límites del plan ${tenant.plan}` : 'Límites del plan'}
                </p>
              </div>
              <span className="text-xs font-semibold text-stone-600 bg-stone-100 px-2.5 py-1 rounded-full capitalize">
                {tenant?.plan || '—'}
              </span>
            </div>
            <div className="space-y-5">
              {quotaBars.map((bar, i) => {
                const pct = bar.limit > 0 ? Math.min(100, Math.round((bar.used / bar.limit) * 100)) : 0;
                return (
                  <div key={i}>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-sm font-medium text-stone-600">{bar.label}</span>
                      <span className="text-sm text-stone-500">
                        <span className="font-semibold text-stone-800">{bar.used}</span> de {bar.limit}
                      </span>
                    </div>
                    <div className="h-2.5 bg-stone-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${bar.color} rounded-full transition-all duration-500 ${
                          pct >= 100 ? 'bg-red-500' : ''
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <p className="text-xs text-stone-400 mt-1">{pct}% utilizado</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Charts section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Weekly appointments chart */}
        <div className="bg-white rounded-2xl p-6 border border-stone-100">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-stone-800">Citas de la Semana</h3>
              <p className="text-sm text-stone-500">Distribución diaria</p>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full">
              <TrendingUp size={14} />
              Semana actual
            </div>
          </div>
          {stats && (
            <div className="flex items-end gap-3 h-48">
              {stats.citas_semana.map((value, i) => {
                const max = Math.max(...stats.citas_semana, 1);
                const height = (value / max) * 100;
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-2">
                    <div className="w-full relative group">
                      <div
                        className="w-full bg-gradient-to-t from-emerald-500 to-teal-400 rounded-lg transition-all duration-500 hover:from-emerald-400 hover:to-teal-300"
                        style={{ height: `${height}%`, minHeight: '8px' }}
                      />
                      <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-stone-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                        {value} citas
                      </div>
                    </div>
                    <span className="text-xs text-stone-500 font-medium">{days[i]}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Monthly revenue chart */}
        <div className="bg-white rounded-2xl p-6 border border-stone-100">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-stone-800">Ingresos Mensuales</h3>
              <p className="text-sm text-stone-500">Últimos 12 meses</p>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full">
              <Activity size={14} />
              Tendencia
            </div>
          </div>
          {stats && (
            <div className="relative h-48">
              <svg className="w-full h-full" viewBox="0 0 400 150" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="revenueGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="rgb(16, 185, 129)" stopOpacity="0.3" />
                    <stop offset="100%" stopColor="rgb(16, 185, 129)" stopOpacity="0" />
                  </linearGradient>
                </defs>
                {(() => {
                  const values = stats.ingresos_mes;
                  const max = Math.max(...values, 1);
                  const y = (v: number) => 150 - (v / max) * 130;
                  return (
                    <>
                      <path
                        d={`M 0 ${y(values[0])} ${values.map((v, i) => `L ${(i / 11) * 400} ${y(v)}`).join(' ')} L 400 150 L 0 150 Z`}
                        fill="url(#revenueGradient)"
                      />
                      <path
                        d={`M 0 ${y(values[0])} ${values.map((v, i) => `L ${(i / 11) * 400} ${y(v)}`).join(' ')}`}
                        fill="none"
                        stroke="rgb(16, 185, 129)"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                      />
                      {values.map((v, i) => (
                        <circle
                          key={i}
                          cx={(i / 11) * 400}
                          cy={y(v)}
                          r="3"
                          fill="white"
                          stroke="rgb(16, 185, 129)"
                          strokeWidth="2"
                        />
                      ))}
                    </>
                  );
                })()}
              </svg>
              <div className="absolute bottom-0 left-0 right-0 flex justify-between text-xs text-stone-400 -mb-5">
                <span>Ene</span>
                <span>Mar</span>
                <span>May</span>
                <span>Jul</span>
                <span>Sep</span>
                <span>Nov</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Recent appointments */}
      <div className="bg-white rounded-2xl p-6 border border-stone-100">
        <h3 className="text-lg font-semibold text-stone-800 mb-4">Próximas Citas</h3>
        {recentAppointments.length === 0 ? (
          <p className="text-sm text-stone-500">No hay citas próximas registradas.</p>
        ) : (
          <div className="space-y-3">
            {recentAppointments.map(apt => (
              <div key={apt.id} className="flex items-center gap-4 p-3 rounded-xl hover:bg-stone-50 transition-colors">
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-stone-700">{apt.patient} — {apt.service}</p>
                  <p className="text-xs text-stone-500 truncate">{apt.hora_inicio || apt.time || '—'} h · {apt.therapist}</p>
                </div>
                <span className="text-xs text-stone-400 whitespace-nowrap capitalize">{apt.estado}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}