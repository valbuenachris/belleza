// ============================================================
// Página de Citas - Agenda con anti-doble reserva (backend)
// Vista Tabla + Vista Calendario mensual
// ============================================================

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { api, ApiError } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Appointment, AppointmentPayment, Patient, Service, User } from '../types';
import { setScheduleListener } from '../services/scheduleRequest';
import { getTenantTimezone } from '../utils/dateTime';
import {
  Calendar, CalendarDays, List, Plus, Clock, DollarSign,
  User as UserIcon, Scissors, AlertCircle, ChevronLeft, ChevronRight, X
} from 'lucide-react';

const statusLabels: Record<string, string> = {
  pending: 'Pendiente',
  confirmed: 'Confirmada',
  completed: 'Completada',
  cancelled: 'Cancelada',
};

const statusColors: Record<string, string> = {
  pending: 'bg-amber-50 text-amber-700',
  confirmed: 'bg-emerald-50 text-emerald-700',
  completed: 'bg-blue-50 text-blue-700',
  cancelled: 'bg-red-50 text-red-500',
};

const statusDots: Record<string, string> = {
  pending: 'bg-amber-400',
  confirmed: 'bg-emerald-500',
  completed: 'bg-blue-500',
  cancelled: 'bg-red-400',
};

const pagoLabels: Record<string, string> = {
  unpaid: 'Sin pagar',
  partial: 'Parcial',
  paid: 'Pagado',
};

const pagoColors: Record<string, string> = {
  unpaid: 'bg-red-50 text-red-600',
  partial: 'bg-amber-50 text-amber-700',
  paid: 'bg-emerald-50 text-emerald-700',
};

const MONTHS = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
const WEEKDAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
const WEEKDAYS_LONG = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

function todayStr(): string {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function pad(n: number): string {
  return String(n).padStart(2, '0');
}

function dateKey(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function parseDateKey(key: string): Date {
  const [y, m, d] = key.split('-').map(Number);
  return new Date(y, m - 1, d);
}

function aptTime(a: Appointment, _timezone?: string): string {
  // Las citas se guardan en hora local del SPA (naive, sin Z). NO se convierten
  // a timezone: se muestra la hora cruda guardada (hora_inicio/time).
  return a.hora_inicio || a.time || (a.date_time ? a.date_time.slice(11, 16) : '--:--');
}

function aptDateKey(a: Appointment, _timezone?: string): string | null {
  // Las citas se guardan en hora local del SPA (naive, sin Z). La agrupación
  // del calendario usa la fecha cruda, sin conversión de zona.
  if (a.date_time) {
    const d = new Date(a.date_time);
    if (!isNaN(d.getTime())) return dateKey(d);
  }
  return a.fecha || null;
}

function formatLongDate(key: string): string {
  const d = parseDateKey(key);
  return `${WEEKDAYS_LONG[(d.getDay() + 6) % 7]}, ${d.getDate()} de ${MONTHS[d.getMonth()]} de ${d.getFullYear()}`;
}

// Genera las 42 celdas del mes (6 semanas), iniciando en Lunes
function buildMonthGrid(year: number, month: number): Date[] {
  const first = new Date(year, month, 1);
  const start = new Date(first);
  start.setDate(first.getDate() - ((first.getDay() + 6) % 7));
  const cells: Date[] = [];
  for (let i = 0; i < 42; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    cells.push(d);
  }
  return cells;
}

type ViewMode = 'table' | 'calendar';

// Acciones rápidas de cambio de estado según el estado actual
function getNextActions(estado: string): { key: string; label: string; className: string }[] {
  if (estado === 'pending') {
    return [
      { key: 'confirmed', label: 'Confirmar', className: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100' },
      { key: 'cancelled', label: 'Cancelar', className: 'bg-red-50 text-red-500 hover:bg-red-100' },
    ];
  }
  if (estado === 'confirmed') {
    return [
      { key: 'completed', label: 'Completar', className: 'bg-blue-50 text-blue-700 hover:bg-blue-100' },
      { key: 'cancelled', label: 'Cancelar', className: 'bg-red-50 text-red-500 hover:bg-red-100' },
    ];
  }
  return [];
}

export default function AppointmentsPage() {
  const { tenant } = useAuth();
  const tz = getTenantTimezone(tenant);
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterDate, setFilterDate] = useState(todayStr());
  const [filterStatus, setFilterStatus] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createInitialDate, setCreateInitialDate] = useState<string | null>(null);
  const [error, setError] = useState('');

  // Estado del calendario
  const [calYear, setCalYear] = useState(new Date().getFullYear());
  const [calMonth, setCalMonth] = useState(new Date().getMonth());
  const [monthAppointments, setMonthAppointments] = useState<Appointment[]>([]);
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [calendarError, setCalendarError] = useState('');
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [preselectedPatientId, setPreselectedPatientId] = useState<string | null>(null);
  const [statusSaving, setStatusSaving] = useState<Record<string, boolean>>({});
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentAppointment, setPaymentAppointment] = useState<Appointment | null>(null);

  const loadAppointments = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getAppointments({
        fecha: filterDate || undefined,
        estado: filterStatus === 'all' ? undefined : filterStatus,
      });
      setAppointments(data.appointments || []);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cargar citas');
    } finally {
      setLoading(false);
    }
  }, [filterDate, filterStatus]);

  const loadCalendar = useCallback(async () => {
    setCalendarLoading(true);
    setCalendarError('');
    try {
      const data = await api.getAppointments({ limit: 500 });
      setMonthAppointments(data.appointments || []);
    } catch (err) {
      setCalendarError(err instanceof ApiError ? err.message : 'Error al cargar el calendario');
    } finally {
      setCalendarLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAppointments();
  }, [loadAppointments]);

  // Cargar datos del calendario al entrar a la vista (y refrescar tras cambios)
  useEffect(() => {
    if (viewMode !== 'calendar') return;
    loadCalendar();
  }, [viewMode, loadCalendar]);

  // Escuchar solicitudes de "Agendar Cita" desde la Ficha del Paciente
  useEffect(() => {
    setScheduleListener((patientId) => {
      setPreselectedPatientId(patientId);
      setCreateInitialDate(todayStr());
      setShowCreateModal(true);
    });
    return () => setScheduleListener(null);
  }, []);

  const applyLocalEstado = useCallback((id: string, estado: string) => {
    setAppointments((list) => list.map((a) => (a.id === id ? { ...a, estado } : a)));
    setMonthAppointments((list) => list.map((a) => (a.id === id ? { ...a, estado } : a)));
  }, []);

  // Cambio de estado con actualización optimista de la UI
  const changeStatus = useCallback(async (id: string, estado: string) => {
    if (statusSaving[id]) return;
    const prev =
      monthAppointments.find((a) => a.id === id)?.estado ??
      appointments.find((a) => a.id === id)?.estado;
    setStatusSaving((s) => ({ ...s, [id]: true }));
    setError('');
    setCalendarError('');
    applyLocalEstado(id, estado);
    try {
      await api.updateAppointment(id, { estado });
      loadAppointments();
      loadCalendar();
    } catch (err) {
      if (prev) applyLocalEstado(id, prev);
      const msg = err instanceof ApiError ? err.message : 'Error al actualizar el estado de la cita';
      setError(msg);
      setCalendarError(msg);
    } finally {
      setStatusSaving((s) => ({ ...s, [id]: false }));
    }
  }, [statusSaving, monthAppointments, appointments, applyLocalEstado, loadAppointments, loadCalendar]);

  const openCreateModal = (initialDate?: string | null) => {
    setCreateInitialDate(initialDate ?? null);
    setShowCreateModal(true);
  };

  const openDay = (key: string) => {
    const d = parseDateKey(key);
    if (d.getFullYear() !== calYear || d.getMonth() !== calMonth) {
      setCalYear(d.getFullYear());
      setCalMonth(d.getMonth());
    }
    setSelectedDay(key);
  };

  const navigateMonth = (delta: number) => {
    const d = new Date(calYear, calMonth + delta, 1);
    setCalYear(d.getFullYear());
    setCalMonth(d.getMonth());
  };

  // Citas agrupadas por día (solo para el mes visible)
  const byDay = useMemo(() => {
    const map: Record<string, Appointment[]> = {};
    for (const a of monthAppointments) {
      const k = aptDateKey(a, tz);
      if (k) (map[k] = map[k] || []).push(a);
    }
    for (const k of Object.keys(map)) {
      map[k].sort((x, y) => aptTime(x, tz).localeCompare(aptTime(y, tz)));
    }
    return map;
  }, [monthAppointments, tz]);

  const monthCellDates = useMemo(() => buildMonthGrid(calYear, calMonth), [calYear, calMonth]);

  const monthCount = useMemo(() => {
    let count = 0;
    for (const cell of monthCellDates) {
      const k = dateKey(cell);
      if (k.startsWith(`${calYear}-${pad(calMonth + 1)}`)) count += (byDay[k] || []).length;
    }
    return count;
  }, [monthCellDates, byDay, calYear, calMonth]);

  const currency = (v: number | null | undefined) =>
    v == null ? '—' : `$${v.toLocaleString('es-CO', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;

  const selectedDayApps = selectedDay ? (byDay[selectedDay] || []) : [];

  return (
    <div className="space-y-6">
      {error && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600 flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-stone-800">Citas</h1>
          <p className="text-stone-500 mt-1">Agenda, confirma y cancela citas de tus pacientes</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {/* Toggle Tabla / Calendario */}
          <div className="inline-flex items-center rounded-xl border border-stone-200 bg-white p-1 shadow-sm">
            <button
              onClick={() => setViewMode('table')}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                viewMode === 'table' ? 'bg-emerald-50 text-emerald-700' : 'text-stone-500 hover:text-stone-700'
              }`}
            >
              <List size={16} />
              Tabla
            </button>
            <button
              onClick={() => setViewMode('calendar')}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                viewMode === 'calendar' ? 'bg-emerald-50 text-emerald-700' : 'text-stone-500 hover:text-stone-700'
              }`}
            >
              <CalendarDays size={16} />
              Calendario
            </button>
          </div>
          <button
            onClick={() => openCreateModal(null)}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl
              hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-200/50 transition-all"
          >
            <Plus size={18} />
            Nueva Cita
          </button>
        </div>
      </div>

      {viewMode === 'table' ? (
        <>
          {/* Filters (Tabla) */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex items-center gap-2 bg-white rounded-xl px-4 py-2.5 border border-stone-200">
              <Calendar size={18} className="text-stone-400" />
              <input
                type="date"
                value={filterDate}
                onChange={(e) => setFilterDate(e.target.value)}
                className="bg-transparent border-none outline-none text-sm text-stone-700 w-full"
              />
            </div>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-4 py-2.5 bg-white border border-stone-200 rounded-xl text-sm text-stone-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            >
              <option value="all">Todos los estados</option>
              <option value="pending">Pendiente</option>
              <option value="confirmed">Confirmada</option>
              <option value="completed">Completada</option>
              <option value="cancelled">Cancelada</option>
            </select>
          </div>

          {/* List */}
          {loading ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="bg-white rounded-2xl p-5 border border-stone-100 animate-pulse">
                  <div className="h-4 bg-stone-100 rounded w-40 mb-2" />
                  <div className="h-3 bg-stone-100 rounded w-64" />
                </div>
              ))}
            </div>
          ) : appointments.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-2xl border border-stone-100">
              <Calendar size={48} className="mx-auto text-stone-300 mb-3" />
              <p className="text-stone-500">No hay citas para esta fecha</p>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-stone-100 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-stone-100">
                      <th className="text-left px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider">Paciente</th>
                      <th className="text-left px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider hidden md:table-cell">Servicio</th>
                      <th className="text-left px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider hidden md:table-cell">Terapeuta</th>
                      <th className="text-left px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider">Horario</th>
                      <th className="text-left px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider">Estado</th>
                      <th className="text-right px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider hidden sm:table-cell">Precio</th>
                      <th className="text-right px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider">Acciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-50">
                    {appointments.map((apt) => (
                      <tr key={apt.id} className="hover:bg-stone-50/50 transition-colors">
                        <td className="px-6 py-4">
                          <p className="text-sm font-medium text-stone-800">{apt.patient}</p>
                        </td>
                        <td className="px-6 py-4 hidden md:table-cell">
                          <p className="text-sm text-stone-600">{apt.service}</p>
                        </td>
                        <td className="px-6 py-4 hidden md:table-cell">
                          <p className="text-sm text-stone-600">{apt.therapist}</p>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex flex-col">
                            <span className="text-sm text-stone-700">
                              {aptTime(apt, tz)} h
                            </span>
                            <span className="text-xs text-stone-400">{apt.duracion} min</span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex flex-col gap-1">
                            <span className={`inline-flex px-2.5 py-1 text-xs font-medium rounded-full capitalize ${statusColors[apt.estado] || 'bg-stone-50 text-stone-600'}`}>
                              {statusLabels[apt.estado] || apt.estado}
                            </span>
                            {apt.estado_pago && (
                              <span className={`inline-flex px-2 py-0.5 text-[10px] font-medium rounded-full ${pagoColors[apt.estado_pago] || 'bg-stone-50 text-stone-600'}`}>
                                {pagoLabels[apt.estado_pago] || apt.estado_pago}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-right hidden sm:table-cell">
                          <span className="text-sm font-medium text-stone-700">{currency(apt.precio)}</span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          {statusSaving[apt.id] ? (
                            <span className="text-xs text-stone-400">Guardando...</span>
                          ) : (
                            <div className="flex items-center justify-end gap-1.5">
                              {getNextActions(apt.estado).map((act) => (
                                <button
                                  key={act.key}
                                  onClick={() => changeStatus(apt.id, act.key)}
                                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${act.className}`}
                                >
                                  {act.label}
                                </button>
                              ))}
                              {(apt.estado === 'confirmed' || apt.estado === 'completed') && (
                                <button
                                  onClick={() => { setPaymentAppointment(apt); setShowPaymentModal(true); }}
                                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-stone-50 text-stone-600 hover:bg-stone-100 transition-colors"
                                  title="Registrar pago"
                                >
                                  <DollarSign className="w-3.5 h-3.5 inline-block" />
                                </button>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      ) : (
        <MonthCalendarView
          calYear={calYear}
          calMonth={calMonth}
          byDay={byDay}
          monthCellDates={monthCellDates}
          monthCount={monthCount}
          loading={calendarLoading}
          error={calendarError}
          onNavigate={navigateMonth}
          onGoToday={() => { setCalYear(new Date().getFullYear()); setCalMonth(new Date().getMonth()); }}
          onDayClick={openDay}
          timezone={tz}
        />
      )}

      {showCreateModal && (
        <CreateAppointmentModal
          initialDate={createInitialDate || undefined}
          initialPatientId={preselectedPatientId}
          onClose={() => { setShowCreateModal(false); setPreselectedPatientId(null); }}
          onCreated={() => {
            setShowCreateModal(false);
            setPreselectedPatientId(null);
            loadAppointments();
            loadCalendar();
          }}
        />
      )}

      {selectedDay && (
        <DayModal
          dayKey={selectedDay}
          appointments={selectedDayApps}
          onClose={() => setSelectedDay(null)}
          onNewAppointment={() => {
            const d = selectedDay;
            setSelectedDay(null);
            openCreateModal(d);
          }}
          statusSaving={statusSaving}
          onStatusChange={(id, estado) => changeStatus(id, estado)}
          timezone={tz}
          onPayment={(apt) => { setPaymentAppointment(apt); setShowPaymentModal(true); }}
        />
      )}

      {showPaymentModal && paymentAppointment && (
        <PaymentModal
          appointment={paymentAppointment}
          timezone={tz}
          onClose={() => { setShowPaymentModal(false); setPaymentAppointment(null); }}
          onPaid={() => {
            setShowPaymentModal(false);
            setPaymentAppointment(null);
            loadAppointments();
            loadCalendar();
          }}
        />
      )}
    </div>
  );
}

// ============================================================
// Vista de Calendario Mensual
// ============================================================

function MonthCalendarView({ calYear, calMonth, byDay, monthCellDates, monthCount, loading, error, onNavigate, onGoToday, onDayClick, timezone }: {
  calYear: number;
  calMonth: number;
  byDay: Record<string, Appointment[]>;
  monthCellDates: Date[];
  monthCount: number;
  loading: boolean;
  error: string;
  onNavigate: (delta: number) => void;
  onGoToday: () => void;
  onDayClick: (dayKey: string) => void;
  timezone: string;
}) {
  const today = todayStr();

  return (
    <div className="space-y-4">
      {/* Navegación del mes */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigate(-1)}
            className="p-2 rounded-xl border border-stone-200 bg-white text-stone-500 hover:bg-stone-50 hover:text-stone-700 transition-colors"
            title="Mes anterior"
          >
            <ChevronLeft size={18} />
          </button>
          <h2 className="text-lg font-semibold text-stone-800 min-w-[160px] text-center">
            {MONTHS[calMonth]} {calYear}
          </h2>
          <button
            onClick={() => onNavigate(1)}
            className="p-2 rounded-xl border border-stone-200 bg-white text-stone-500 hover:bg-stone-50 hover:text-stone-700 transition-colors"
            title="Mes siguiente"
          >
            <ChevronRight size={18} />
          </button>
          <button
            onClick={onGoToday}
            className="px-3 py-2 rounded-xl border border-stone-200 bg-white text-sm font-medium text-stone-600 hover:bg-emerald-50 hover:text-emerald-700 transition-colors"
          >
            Hoy
          </button>
        </div>
        <div className="flex items-center gap-4 text-xs text-stone-500">
          <span className="font-medium text-stone-600">{monthCount} citas en el mes</span>
          <span className="hidden sm:flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" /> Confirmada
          </span>
          <span className="hidden sm:flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-400" /> Pendiente
          </span>
          <span className="hidden sm:flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500" /> Completada
          </span>
          <span className="hidden sm:flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-400" /> Cancelada
          </span>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600 flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {loading ? (
        <div className="bg-white rounded-2xl border border-stone-100 p-6 animate-pulse space-y-4">
          <div className="h-4 bg-stone-100 rounded w-40" />
          <div className="grid grid-cols-7 gap-2">
            {Array.from({ length: 42 }).map((_, i) => (
              <div key={i} className="h-24 bg-stone-100 rounded-xl" />
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-stone-100 overflow-hidden">
          {/* Días de la semana */}
          <div className="grid grid-cols-7 border-b border-stone-100">
            {WEEKDAYS.map((d, i) => (
              <div
                key={d}
                className={`px-2 py-2.5 text-center text-xs font-semibold uppercase tracking-wider text-stone-500 ${i < 6 ? 'border-r border-stone-100' : ''}`}
              >
                {d}
              </div>
            ))}
          </div>

          {/* Celdas del mes */}
          <div className="grid grid-cols-7">
            {monthCellDates.map((cell, i) => {
              const key = dateKey(cell);
              const inMonth = cell.getMonth() === calMonth;
              const isToday = key === today;
              const items = byDay[key] || [];

              return (
                <div
                  key={key}
                  onClick={() => onDayClick(key)}
                  className={`min-h-[92px] sm:min-h-[116px] p-2 flex flex-col gap-1 cursor-pointer transition-colors ${
                    i % 7 !== 6 ? 'border-r' : ''
                  } ${i < 35 ? 'border-b' : ''} border-stone-100 ${
                    inMonth ? 'bg-white hover:bg-emerald-50/40' : 'bg-stone-50/60 hover:bg-stone-100/60'
                  }`}
                >
                  <div className="flex items-start justify-between gap-1">
                    <span
                      className={`inline-flex w-7 h-7 items-center justify-center rounded-full text-sm ${
                        isToday
                          ? 'bg-emerald-500 text-white font-bold'
                          : inMonth
                            ? 'text-stone-700 font-medium'
                            : 'text-stone-400'
                      }`}
                    >
                      {cell.getDate()}
                    </span>
                    {items.length > 0 && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 text-[10px] font-semibold leading-none">
                        {items.length} citas
                      </span>
                    )}
                  </div>

                  <div className="flex-1 overflow-hidden space-y-1 min-h-[10px]">
                    {items.slice(0, 2).map((a) => (
                      <div
                        key={a.id}
                        className="flex items-center gap-1.5 px-1.5 py-0.5 rounded-md bg-stone-50 text-stone-700"
                        title={`${aptTime(a, timezone)}h - ${a.patient} - ${a.service}`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${statusDots[a.estado] || 'bg-stone-300'}`} />
                        <span className="truncate text-[10px] leading-tight">
                          <span className="font-semibold">{aptTime(a, timezone)}h</span>&nbsp;{a.patient}
                        </span>
                      </div>
                    ))}
                    {items.length > 2 && (
                      <div className="text-[10px] text-stone-400 px-1">+{items.length - 2} más</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// Modal de resumen del día
// ============================================================

function DayModal({ dayKey, appointments, onClose, onNewAppointment, statusSaving, onStatusChange, timezone, onPayment }: {
  dayKey: string;
  appointments: Appointment[];
  onClose: () => void;
  onNewAppointment: () => void;
  statusSaving: Record<string, boolean>;
  onStatusChange: (id: string, estado: string) => void;
  timezone: string;
  onPayment?: (apt: Appointment) => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-5 border-b border-stone-100 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-stone-800">Citas del día</h2>
            <p className="text-sm text-stone-500 mt-0.5">{formatLongDate(dayKey)}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-stone-100 text-stone-400 hover:text-stone-600 transition-colors"
            title="Cerrar"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-6 space-y-3">
          {appointments.length === 0 ? (
            <div className="text-center py-10 text-stone-400">
              <Calendar size={40} className="mx-auto mb-2 text-stone-300" />
              <p className="text-sm">No hay citas para este día</p>
            </div>
          ) : (
            <>
              <div className="text-sm text-stone-500">
                {appointments.length} {appointments.length === 1 ? 'cita' : 'citas'} programadas
              </div>
              {appointments.map((a) => (
                <div key={a.id} className="flex items-center gap-3 p-3 bg-stone-50 rounded-xl">
                  <div className="flex flex-col items-center justify-center px-2 py-1 bg-white rounded-lg border border-stone-200 min-w-[64px]">
                    <span className="text-sm font-bold text-stone-800">{aptTime(a, timezone)}</span>
                    <span className="text-[10px] text-stone-400">{a.duracion} min</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-stone-800 truncate">{a.patient}</p>
                    <p className="text-xs text-stone-500 truncate">{a.service} · {a.therapist}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1.5">
                    <div className="flex flex-col items-end gap-0.5">
                      <span className={`inline-flex px-2 py-0.5 text-[10px] font-medium rounded-full capitalize ${statusColors[a.estado] || 'bg-stone-100 text-stone-600'}`}>
                        {statusLabels[a.estado] || a.estado}
                      </span>
                      {a.estado_pago && (
                        <span className={`inline-flex px-1.5 py-0.5 text-[9px] font-medium rounded-full ${pagoColors[a.estado_pago] || 'bg-stone-50 text-stone-600'}`}>
                          {pagoLabels[a.estado_pago] || a.estado_pago}
                        </span>
                      )}
                    </div>
                    {statusSaving[a.id] ? (
                      <span className="text-[10px] text-stone-400">Guardando...</span>
                    ) : (
                      <div className="flex items-center gap-1">
                        {(a.estado === 'confirmed' || a.estado === 'completed') && onPayment && (
                          <button
                            onClick={() => onPayment(a)}
                            className="px-1.5 py-1 rounded-md text-[10px] font-medium bg-stone-100 text-stone-500 hover:bg-stone-200 transition-colors"
                            title="Registrar pago"
                          >
                            $
                          </button>
                        )}
                        {getNextActions(a.estado).map((act) => (
                          <button
                            key={act.key}
                            onClick={() => onStatusChange(a.id, act.key)}
                            className={`px-2 py-1 rounded-md text-[10px] font-medium transition-colors ${act.className}`}
                          >
                            {act.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </>
          )}
        </div>

        <div className="px-6 py-4 border-t border-stone-100 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 border border-stone-200 rounded-xl text-sm font-medium text-stone-600 hover:bg-stone-50"
          >
            Cerrar
          </button>
          <button
            onClick={onNewAppointment}
            className="flex-1 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 transition-all inline-flex items-center justify-center gap-2"
          >
            <Plus size={16} />
            Nueva cita este día
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Modal de Nueva Cita
// ============================================================
function CreateAppointmentModal({ initialDate, initialPatientId, onClose, onCreated }: {
  initialDate?: string;
  initialPatientId?: string | null;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [therapists, setTherapists] = useState<User[]>([]);
  const [metaLoading, setMetaLoading] = useState(true);

  const [formData, setFormData] = useState({
    patientId: initialPatientId || '',
    serviceId: '',
    therapistId: '',
    fecha: initialDate || todayStr(),
    hora: '09:00',
    duracion: '',
    notas: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const selectedService = useMemo(
    () => services.find(s => s.id === formData.serviceId),
    [services, formData.serviceId]
  );

  useEffect(() => {
    const loadMeta = async () => {
      setMetaLoading(true);
      setError('');
      try {
        const [p, s, u] = await Promise.all([
          api.getPatients(),
          api.getServices(),
          api.getUsers(),
        ]);
        setPatients(p.patients || []);
        setServices((s.services || []).filter(sv => sv.activo));
        setTherapists((u || []).filter(t => t.rol === 'therapist' && t.activo));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Error al cargar datos para la cita');
      } finally {
        setMetaLoading(false);
      }
    };
    loadMeta();
  }, []);

  const canSubmit =
    formData.patientId && formData.therapistId && formData.serviceId && formData.fecha && formData.hora;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setError('');
    setLoading(true);
    try {
      await api.createAppointment({
        patient_id: formData.patientId,
        service_id: formData.serviceId,
        therapist_id: formData.therapistId,
        date_time: `${formData.fecha}T${formData.hora}:00`,
        duracion: formData.duracion ? parseInt(formData.duracion, 10) : undefined,
        notas: formData.notas || undefined,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al crear la cita');
      setLoading(false);
    }
  };

  const inputClass = "w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-stone-100">
          <h2 className="text-xl font-semibold text-stone-800">Nueva Cita</h2>
          <p className="text-sm text-stone-500 mt-1">El sistema valida la disponibilidad del horario</p>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border-b border-red-100 text-sm text-red-600">{error}</div>
        )}

        {metaLoading ? (
          <div className="p-8 space-y-3">
            <div className="h-4 bg-stone-100 rounded w-40 animate-pulse" />
            <div className="h-4 bg-stone-100 rounded w-56 animate-pulse" />
            <div className="h-4 bg-stone-100 rounded w-48 animate-pulse" />
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">
                <UserIcon size={14} className="inline mr-1.5" />
                Paciente *
              </label>
              <select
                required
                value={formData.patientId}
                onChange={(e) => setFormData({ ...formData, patientId: e.target.value })}
                className={inputClass}
              >
                <option value="">Selecciona un paciente</option>
                {patients.length === 0 && (
                  <option value="" disabled>No hay pacientes — regístralo en Pacientes</option>
                )}
                {patients.map(p => (
                  <option key={p.id} value={p.id}>{p.nombre} {p.apellido}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">
                <Scissors size={14} className="inline mr-1.5" />
                Servicio *
              </label>
              <select
                required
                value={formData.serviceId}
                onChange={(e) => {
                  const svc = services.find(s => s.id === e.target.value);
                  setFormData({
                    ...formData,
                    serviceId: e.target.value,
                    duracion: svc ? String(svc.duracion) : formData.duracion,
                  });
                }}
                className={inputClass}
              >
                <option value="">Selecciona un servicio</option>
                {services.length === 0 && (
                  <option value="" disabled>No hay servicios — créalos en Servicios</option>
                )}
                {services.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.nombre} — {s.duracion} min — ${s.precio}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Terapeuta *</label>
              <select
                required
                value={formData.therapistId}
                onChange={(e) => setFormData({ ...formData, therapistId: e.target.value })}
                className={inputClass}
              >
                <option value="">Selecciona un terapeuta</option>
                {therapists.length === 0 && (
                  <option value="" disabled>No hay terapeutas — crea uno en Usuarios</option>
                )}
                {therapists.map(t => (
                  <option key={t.id} value={t.id}>{t.nombre} {t.apellido}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">
                  <Calendar size={14} className="inline mr-1.5" />
                  Fecha *
                </label>
                <input
                  type="date" required value={formData.fecha}
                  onChange={(e) => setFormData({ ...formData, fecha: e.target.value })}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">
                  <Clock size={14} className="inline mr-1.5" />
                  Hora *
                </label>
                <input
                  type="time" required value={formData.hora}
                  onChange={(e) => setFormData({ ...formData, hora: e.target.value })}
                  className={inputClass}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">Duración (min)</label>
                <input
                  type="number" min={5} value={formData.duracion}
                  onChange={(e) => setFormData({ ...formData, duracion: e.target.value })}
                  placeholder={selectedService ? String(selectedService.duracion) : '60'}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">
                  <DollarSign size={14} className="inline mr-1.5" />
                  Precio
                </label>
                <p className="px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm text-stone-600">
                  {selectedService ? `$${selectedService.precio.toLocaleString('es-CO')}` : 'Del servicio'}
                </p>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Notas</label>
              <textarea
                value={formData.notas}
                onChange={(e) => setFormData({ ...formData, notas: e.target.value })}
                className={`${inputClass} resize-none`} rows={2}
                placeholder="Instrucciones o detalles de la cita"
              />
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="button" onClick={onClose}
                className="flex-1 py-2.5 border border-stone-200 rounded-xl text-sm font-medium text-stone-600 hover:bg-stone-50"
              >
                Cancelar
              </button>
              <button
                type="submit" disabled={loading || !canSubmit}
                className="flex-1 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 transition-all"
              >
                {loading ? 'Agendando...' : 'Agendar Cita'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

// ============================================================
// Modal de Pago (Registrar pago)
// ============================================================
function PaymentModal({ appointment, onClose, onPaid, timezone }: {
  appointment: Appointment;
  onClose: () => void;
  onPaid: () => void;
  timezone: string;
}) {
  const saldoInicial = Math.max(0, (appointment.monto_total ?? appointment.precio ?? 0) - (appointment.total_pagado ?? 0));
  const [monto, setMonto] = useState(saldoInicial);
  const [metodoPago, setMetodoPago] = useState('efectivo');
  const [descuento, setDescuento] = useState(0);
  const [observaciones, setObservaciones] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [payments, setPayments] = useState<AppointmentPayment[]>([]);
  const [paymentsLoading, setPaymentsLoading] = useState(true);

  useEffect(() => {
    setPaymentsLoading(true);
    api.getAppointmentPayments(appointment.id)
      .then((data) => setPayments(data.payments || []))
      .catch(() => {})
      .finally(() => setPaymentsLoading(false));
  }, [appointment.id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (monto <= 0) {
      setError('El monto debe ser mayor a 0');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await api.registerAppointmentPayment(appointment.id, {
        monto,
        metodo_pago: metodoPago,
        descuento: descuento > 0 ? descuento : undefined,
        observaciones: observaciones || undefined,
      });
      onPaid();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al registrar el pago');
    } finally {
      setLoading(false);
    }
  };

  const inputClass = "w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400";
  const total = appointment.monto_total ?? appointment.precio ?? 0;
  const pagadoTotal = payments.reduce((s, p) => s + p.monto, 0);
  const saldoRestante = Math.max(0, total - pagadoTotal - monto);

  const metodoLabel: Record<string, string> = {
    efectivo: 'Efectivo',
    tarjeta: 'Tarjeta',
    transferencia: 'Transferencia',
    nequi: 'Nequi',
    daviplata: 'Daviplata',
    otro: 'Otro',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-stone-100">
          <h2 className="text-xl font-semibold text-stone-800">Registrar Pago</h2>
          <p className="text-sm text-stone-500 mt-1">
            {appointment.patient} — {appointment.service} ({aptTime(appointment)}h)
          </p>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border-b border-red-100 text-sm text-red-600">{error}</div>
        )}

        {/* Resumen financiero */}
        <div className="p-6 space-y-3 bg-stone-50 border-b border-stone-100">
          <div className="flex justify-between text-sm">
            <span className="text-stone-600">Total cita</span>
            <span className="font-semibold text-stone-800">${total.toLocaleString('es-CO')}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-stone-600">Pagado</span>
            <span className="font-semibold text-emerald-700">${pagadoTotal.toLocaleString('es-CO')}</span>
          </div>
          <div className="flex justify-between text-sm border-t border-stone-200 pt-2">
            <span className="font-medium text-stone-700">Saldo pendiente</span>
            <span className="font-bold text-amber-700">${Math.max(0, total - pagadoTotal).toLocaleString('es-CO')}</span>
          </div>
        </div>

        {/* Historial de pagos */}
        {!paymentsLoading && payments.length > 0 && (
          <div className="px-6 py-4 border-b border-stone-100">
            <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-2">Historial de pagos</h3>
            <div className="space-y-2">
              {payments.map((p) => (
                <div key={p.id} className="flex items-center justify-between text-sm bg-white rounded-lg px-3 py-2 border border-stone-100">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-stone-800">${p.monto.toLocaleString('es-CO')}</span>
                    <span className="text-xs text-stone-400">{metodoLabel[p.metodo_pago] || p.metodo_pago}</span>
                    {p.descuento > 0 && (
                      <span className="text-[10px] text-red-500">(-${p.descuento.toLocaleString('es-CO')} dto)</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {p.observaciones && (
                      <span className="text-[10px] text-stone-400 truncate max-w-[100px]">{p.observaciones}</span>
                    )}
                    <span className="text-[10px] text-stone-400">
                      {p.created_at ? new Date(p.created_at + 'Z').toLocaleDateString('es-CO', { timeZone: timezone, day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : ''}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Monto a pagar *</label>
            <input
              type="number" required min={1} step={1}
              value={monto}
              onChange={(e) => setMonto(Number(e.target.value))}
              className={inputClass}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Método de pago</label>
            <select
              value={metodoPago}
              onChange={(e) => setMetodoPago(e.target.value)}
              className={inputClass}
            >
              <option value="efectivo">Efectivo</option>
              <option value="tarjeta">Tarjeta</option>
              <option value="transferencia">Transferencia</option>
              <option value="nequi">Nequi</option>
              <option value="daviplata">Daviplata</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Descuento</label>
            <input
              type="number" min={0} step={1}
              value={descuento}
              onChange={(e) => setDescuento(Number(e.target.value))}
              className={inputClass}
              placeholder="0"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Observaciones</label>
            <input
              type="text"
              value={observaciones}
              onChange={(e) => setObservaciones(e.target.value)}
              className={inputClass}
              placeholder="Opcional"
            />
          </div>

          {monto > 0 && monto < saldoInicial && (
            <div className="p-3 bg-amber-50 rounded-xl text-xs text-amber-700">
              Queda un saldo pendiente de ${(saldoInicial - monto).toLocaleString('es-CO')} después de este pago (crédito).
            </div>
          )}

          {monto > 0 && monto >= saldoInicial && (
            <div className="p-3 bg-emerald-50 rounded-xl text-xs text-emerald-700">
              Con este pago la cita queda saldada. ✓
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button" onClick={onClose}
              className="flex-1 py-2.5 border border-stone-200 rounded-xl text-sm font-medium text-stone-600 hover:bg-stone-50"
            >
              Cancelar
            </button>
            <button
              type="submit" disabled={loading || monto <= 0}
              className="flex-1 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 transition-all"
            >
              {loading ? 'Registrando...' : 'Registrar Pago'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}