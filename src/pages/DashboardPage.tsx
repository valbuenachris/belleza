// ============================================================
// Dashboard - Vista principal con estadísticas
// ============================================================

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { TenantStats } from '../types';
import {
  Users, Calendar, DollarSign, UserCheck, TrendingUp,
  Clock, ArrowUpRight, ArrowDownRight, Activity
} from 'lucide-react';

export default function DashboardPage() {
  const { user, tenant } = useAuth();
  const [stats, setStats] = useState<TenantStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const data = await api.getDashboardStats(tenant?.id);
        setStats(data);
      } catch {
        // Error handling
      } finally {
        setLoading(false);
      }
    };
    loadStats();
  }, [tenant]);

  const statCards = stats ? [
    {
      label: 'Usuarios Activos',
      value: stats.total_usuarios,
      icon: <Users size={22} />,
      change: '+12%',
      positive: true,
      color: 'emerald',
    },
    {
      label: 'Pacientes Registrados',
      value: stats.total_pacientes,
      icon: <UserCheck size={22} />,
      change: '+8%',
      positive: true,
      color: 'blue',
    },
    {
      label: 'Citas Hoy',
      value: stats.total_citas_hoy,
      icon: <Calendar size={22} />,
      change: '+23%',
      positive: true,
      color: 'violet',
    },
    {
      label: 'Ingresos del Mes',
      value: `$${stats.total_ingresos_mes.toLocaleString()}`,
      icon: <DollarSign size={22} />,
      change: '-3%',
      positive: false,
      color: 'amber',
    },
  ] : [];

  const days = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-stone-800">
            ¡Hola, {user?.nombre}! 👋
          </h1>
          <p className="text-stone-500 mt-1">
            {tenant ? `Panel de ${tenant.nombre}` : 'Panel de Administración Global'}
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-stone-500 bg-white px-4 py-2 rounded-xl border border-stone-200">
          <Clock size={16} />
          <span>{new Date().toLocaleDateString('es-ES', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</span>
        </div>
      </div>

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
              <div className={`flex items-center gap-1 mt-2 text-xs font-medium ${
                card.positive ? 'text-emerald-600' : 'text-red-500'
              }`}>
                {card.positive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                {card.change} vs. mes anterior
              </div>
            </div>
          ))}
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
              +15%
            </div>
          </div>
          {stats && (
            <div className="flex items-end gap-3 h-48">
              {stats.citas_semana.map((value, i) => {
                const max = Math.max(...stats.citas_semana);
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
                {/* Area */}
                <path
                  d={`M 0 ${150 - (stats.ingresos_mes[0] / Math.max(...stats.ingresos_mes)) * 130} ${stats.ingresos_mes
                    .map((v, i) => `L ${(i / 11) * 400} ${150 - (v / Math.max(...stats.ingresos_mes)) * 130}`)
                    .join(' ')} L 400 150 L 0 150 Z`}
                  fill="url(#revenueGradient)"
                />
                {/* Line */}
                <path
                  d={`M 0 ${150 - (stats.ingresos_mes[0] / Math.max(...stats.ingresos_mes)) * 130} ${stats.ingresos_mes
                    .map((v, i) => `L ${(i / 11) * 400} ${150 - (v / Math.max(...stats.ingresos_mes)) * 130}`)
                    .join(' ')}`}
                  fill="none"
                  stroke="rgb(16, 185, 129)"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
                {/* Points */}
                {stats.ingresos_mes.map((v, i) => (
                  <circle
                    key={i}
                    cx={(i / 11) * 400}
                    cy={150 - (v / Math.max(...stats.ingresos_mes)) * 130}
                    r="3"
                    fill="white"
                    stroke="rgb(16, 185, 129)"
                    strokeWidth="2"
                  />
                ))}
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

      {/* Recent activity */}
      <div className="bg-white rounded-2xl p-6 border border-stone-100">
        <h3 className="text-lg font-semibold text-stone-800 mb-4">Actividad Reciente</h3>
        <div className="space-y-3">
          {[
            { action: 'Nueva cita agendada', detail: 'Masaje relajante - 60 min', time: 'Hace 5 min', color: 'emerald' },
            { action: 'Paciente registrado', detail: 'Carolina Méndez', time: 'Hace 15 min', color: 'blue' },
            { action: 'Pago procesado', detail: '$120.00 - Facial premium', time: 'Hace 32 min', color: 'amber' },
            { action: 'Cita completada', detail: 'Terapia de piedras calientes', time: 'Hace 1 hora', color: 'violet' },
            { action: 'Usuario actualizado', detail: 'Laura Martínez - Rol cambiado', time: 'Hace 2 horas', color: 'stone' },
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-4 p-3 rounded-xl hover:bg-stone-50 transition-colors">
              <div className={`w-2.5 h-2.5 rounded-full ${
                item.color === 'emerald' ? 'bg-emerald-500' :
                item.color === 'blue' ? 'bg-blue-500' :
                item.color === 'amber' ? 'bg-amber-500' :
                item.color === 'violet' ? 'bg-violet-500' :
                'bg-stone-400'
              }`} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-stone-700">{item.action}</p>
                <p className="text-xs text-stone-500 truncate">{item.detail}</p>
              </div>
              <span className="text-xs text-stone-400 whitespace-nowrap">{item.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
