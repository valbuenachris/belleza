// ============================================================
// Página de Gestión de Pagos - Métricas + Listado + Acciones
// ============================================================

import React, { useState, useEffect, useCallback } from 'react';
import { api, ApiError } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Appointment, AppointmentPayment, AppointmentsResponse } from '../types';
import { getTenantTimezone } from '../utils/dateTime';
import {
  DollarSign, TrendingUp, CreditCard, AlertCircle,
  Clock, ChevronRight, X, Search
} from 'lucide-react';

// ============================================================
// Constantes de estado de pago
// ============================================================
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

const metodoLabel: Record<string, string> = {
  efectivo: 'Efectivo',
  tarjeta: 'Tarjeta',
  transferencia: 'Transferencia',
  nequi: 'Nequi',
  daviplata: 'Daviplata',
  credito: 'Crédito',
  otro: 'Otro',
};

const currency = (v: number | null | undefined) =>
  v == null ? '—' : `$${v.toLocaleString('es-CO', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;

const aptTime = (a: Appointment) => (a.hora_inicio || a.time || '').slice(0, 5);

// ============================================================
// Modal de pago (adaptado de AppointmentsPage)
// ============================================================
function PaymentModal({
  appointment, onClose, onPaid, timezone,
}: {
  appointment: Appointment;
  onClose: () => void;
  onPaid: () => void;
  timezone: string;
}) {
  const total = appointment.monto_total ?? appointment.precio ?? 0;
  const saldoInicial = Math.max(0, total - (appointment.total_pagado ?? 0));
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
    if (monto < 0) {
      setError('El monto no puede ser negativo');
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
  const pagadoTotal = payments.reduce((s, p) => s + p.monto, 0);

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

        <div className="p-6 space-y-3 bg-stone-50 border-b border-stone-100">
          <div className="flex justify-between text-sm">
            <span className="text-stone-600">Total cita</span>
            <span className="font-semibold text-stone-800">{currency(total)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-stone-600">Pagado</span>
            <span className="font-semibold text-emerald-700">{currency(pagadoTotal)}</span>
          </div>
          <div className="flex justify-between text-sm border-t border-stone-200 pt-2">
            <span className="font-medium text-stone-700">Saldo pendiente</span>
            <span className="font-bold text-amber-700">{currency(Math.max(0, total - pagadoTotal))}</span>
          </div>
        </div>

        {!paymentsLoading && payments.length > 0 && (
          <div className="px-6 py-4 border-b border-stone-100">
            <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-2">Historial de pagos</h3>
            <div className="space-y-2">
              {payments.map((p) => (
                <div key={p.id} className="flex items-center justify-between text-sm bg-white rounded-lg px-3 py-2 border border-stone-100">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-stone-800">{currency(p.monto)}</span>
                    <span className="text-xs text-stone-400">{metodoLabel[p.metodo_pago] || p.metodo_pago}</span>
                    {p.descuento > 0 && (
                      <span className="text-[10px] text-red-500">(-{currency(p.descuento)} dto)</span>
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
              type="number" required min={0} step={1}
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
              <option value="credito">Crédito</option>
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

          {monto === 0 && (
            <div className="p-3 bg-amber-50 rounded-xl text-xs text-amber-700">
              Este pago se registrará como crédito ($0). La cita se podrá marcar como completada.
            </div>
          )}

          {monto > 0 && monto < saldoInicial && (
            <div className="p-3 bg-amber-50 rounded-xl text-xs text-amber-700">
              Queda un saldo pendiente de {currency(saldoInicial - monto)} después de este pago (crédito).
            </div>
          )}

          {monto > 0 && monto >= saldoInicial && (
            <div className="p-3 bg-emerald-50 rounded-xl text-xs text-emerald-700">
              Con este pago la cita queda saldada.
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
              type="submit" disabled={loading || monto < 0}
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

// ============================================================
// PaymentsPage
// ============================================================
export default function PaymentsPage() {
  const { tenant } = useAuth();
  const tz = getTenantTimezone(tenant);

  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Filtros
  const [filterPago, setFilterPago] = useState('all');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterSearch, setFilterSearch] = useState('');

  // Modal de pago
  const [paymentAppointment, setPaymentAppointment] = useState<Appointment | null>(null);
  const [showPaymentModal, setShowPaymentModal] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res: AppointmentsResponse = await api.getAppointments({ limit: 1000 });
      setAppointments(res.appointments || []);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cargar citas');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // ---- Cálculo de métricas ----
  const now = new Date();
  const currentMonth = now.getMonth();
  const currentYear = now.getFullYear();

  const thisMonth = appointments.filter((a) => {
    const d = a.fecha ? new Date(a.fecha + 'T00:00:00') : null;
    return d && d.getMonth() === currentMonth && d.getFullYear() === currentYear;
  });

  const facturadoMes = thisMonth.reduce((s, a) => s + (a.monto_total ?? a.precio ?? 0), 0);
  const ingresos = thisMonth.reduce((s, a) => s + (a.total_pagado ?? 0), 0);
  const pendiente = thisMonth.reduce((s, a) =>
    a.estado_pago !== 'paid' ? s + Math.max(0, (a.monto_total ?? a.precio ?? 0) - (a.total_pagado ?? 0)) : s, 0);
  const creditosCount = thisMonth.filter((a) => a.estado_pago === 'partial').length;

  // ---- Filtrado ----
  let filtered = [...appointments];

  if (filterPago !== 'all') {
    filtered = filtered.filter((a) => a.estado_pago === filterPago);
  }

  if (filterDateFrom) {
    const from = new Date(filterDateFrom + 'T00:00:00');
    filtered = filtered.filter((a) => {
      const d = a.fecha ? new Date(a.fecha + 'T00:00:00') : null;
      return d && d >= from;
    });
  }

  if (filterSearch.trim()) {
    const q = filterSearch.trim().toLowerCase();
    filtered = filtered.filter((a) =>
      (a.patient && a.patient.toLowerCase().includes(q)) ||
      (a.service && a.service.toLowerCase().includes(q))
    );
  }

  // Ordenar más recientes primero
  filtered.sort((a, b) => {
    const da = a.fecha ? `${a.fecha} ${a.hora_inicio || ''}` : '';
    const db = b.fecha ? `${b.fecha} ${b.hora_inicio || ''}` : '';
    return db.localeCompare(da);
  });

  const metricCards = [
    {
      label: 'Facturado del mes',
      value: currency(facturadoMes),
      icon: <TrendingUp size={22} />,
      color: 'blue',
      sub: `${thisMonth.length} cita(s)`,
    },
    {
      label: 'Ingresos cobrados',
      value: currency(ingresos),
      icon: <DollarSign size={22} />,
      color: 'emerald',
      sub: `${((facturadoMes > 0) ? Math.round(ingresos / facturadoMes * 100) : 0)}% del facturado`,
    },
    {
      label: 'Pendiente por cobrar',
      value: currency(pendiente),
      icon: <CreditCard size={22} />,
      color: 'amber',
      sub: `${filtered.filter((a) => a.estado_pago !== 'paid').length} cita(s) con saldo`,
    },
    {
      label: 'Citas con crédito',
      value: `${creditosCount}`,
      icon: <Clock size={22} />,
      color: 'violet',
      sub: `${(thisMonth.length > 0) ? Math.round(creditosCount / thisMonth.length * 100) : 0}% del mes`,
    },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-stone-800">Gestión de Pagos</h1>
          <p className="text-stone-500 mt-1">Administra los cobros de las citas agendadas</p>
        </div>
      </div>

      {/* Success banner */}
      {success && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-sm text-emerald-700 flex items-center gap-2">
          {success}
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600 flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-white rounded-2xl p-6 border border-stone-100 animate-pulse">
                <div className="h-4 bg-stone-100 rounded w-24 mb-4" />
                <div className="h-8 bg-stone-100 rounded w-32" />
                <div className="h-3 bg-stone-100 rounded w-48 mt-2" />
              </div>
            ))}
          </div>
          <div className="h-10 bg-stone-100 rounded-xl animate-pulse" />
          <div className="h-64 bg-stone-100 rounded-2xl animate-pulse" />
        </div>
      ) : (
        <>
          {/* Metric cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {metricCards.map((card, i) => (
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
                  {card.sub}
                </div>
              </div>
            ))}
          </div>

          {/* Filters */}
          <div className="bg-white rounded-2xl border border-stone-100 p-4">
            <div className="flex flex-wrap items-center gap-3">
              <label className="text-xs font-medium text-stone-500 uppercase tracking-wider">Estado:</label>
              <select
                value={filterPago}
                onChange={(e) => setFilterPago(e.target.value)}
                className="px-3 py-2 bg-stone-50 border border-stone-200 rounded-lg text-sm"
              >
                <option value="all">Todos</option>
                <option value="unpaid">Sin pagar</option>
                <option value="partial">Parcial / Crédito</option>
                <option value="paid">Pagado</option>
              </select>

              <label className="text-xs font-medium text-stone-500 uppercase tracking-wider">Desde:</label>
              <input
                type="date"
                value={filterDateFrom}
                onChange={(e) => setFilterDateFrom(e.target.value)}
                className="px-3 py-2 bg-stone-50 border border-stone-200 rounded-lg text-sm"
              />

              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" />
                <input
                  type="text"
                  placeholder="Buscar paciente o servicio..."
                  value={filterSearch}
                  onChange={(e) => setFilterSearch(e.target.value)}
                  className="pl-9 pr-3 py-2 bg-stone-50 border border-stone-200 rounded-lg text-sm w-56"
                />
              </div>

              <span className="text-xs text-stone-400 ml-auto">{filtered.length} resultado(s)</span>
            </div>
          </div>

          {/* Table */}
          {filtered.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-2xl border border-stone-100">
              <DollarSign size={48} className="mx-auto text-stone-300 mb-3" />
              <p className="text-stone-500">No hay citas con estos filtros</p>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-stone-100 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-stone-100 bg-stone-50">
                      <th className="text-left px-4 py-3 font-semibold text-stone-600">Paciente</th>
                      <th className="text-left px-4 py-3 font-semibold text-stone-600">Servicio</th>
                      <th className="text-left px-4 py-3 font-semibold text-stone-600">Fecha / Hora</th>
                      <th className="text-right px-4 py-3 font-semibold text-stone-600">Total</th>
                      <th className="text-right px-4 py-3 font-semibold text-stone-600">Pagado</th>
                      <th className="text-right px-4 py-3 font-semibold text-stone-600">Saldo</th>
                      <th className="text-center px-4 py-3 font-semibold text-stone-600">Estado</th>
                      <th className="text-center px-4 py-3 font-semibold text-stone-600">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((apt) => {
                      const total = apt.monto_total ?? apt.precio ?? 0;
                      const pagado = apt.total_pagado ?? 0;
                      const saldo = Math.max(0, total - pagado);
                      return (
                        <tr key={apt.id} className="border-b border-stone-100 hover:bg-stone-50">
                          <td className="px-4 py-3 font-medium text-stone-700">{apt.patient}</td>
                          <td className="px-4 py-3 text-stone-600">{apt.service}</td>
                          <td className="px-4 py-3 text-stone-500 whitespace-nowrap">
                            {apt.fecha ? apt.fecha.slice(0, 10) : ''} {aptTime(apt)}
                          </td>
                          <td className="px-4 py-3 text-right text-stone-700">{currency(total)}</td>
                          <td className="px-4 py-3 text-right text-emerald-700">{currency(pagado)}</td>
                          <td className={`px-4 py-3 text-right ${saldo > 0 ? 'text-red-600 font-semibold' : 'text-stone-500'}`}>
                            {currency(saldo)}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex px-2.5 py-1 text-xs font-medium rounded-full capitalize ${pagoColors[apt.estado_pago || ''] || 'bg-stone-50 text-stone-600'}`}>
                              {pagoLabels[apt.estado_pago || ''] || apt.estado_pago}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <div className="flex items-center justify-center gap-1">
                              {apt.estado_pago !== 'paid' && (
                                <button
                                  onClick={() => { setPaymentAppointment(apt); setShowPaymentModal(true); }}
                                  className="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                                >
                                  <DollarSign size={14} /> Pago
                                </button>
                              )}
                              {apt.estado_pago === 'paid' && (
                                <button
                                  onClick={() => { setPaymentAppointment(apt); setShowPaymentModal(true); }}
                                  className="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors bg-stone-50 text-stone-500 hover:bg-stone-100"
                                >
                                  <DollarSign size={14} /> Ver
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Payment Modal */}
      {showPaymentModal && paymentAppointment && (
        <PaymentModal
          appointment={paymentAppointment}
          onClose={() => { setShowPaymentModal(false); setPaymentAppointment(null); }}
          onPaid={() => {
            setShowPaymentModal(false);
            setPaymentAppointment(null);
            setSuccess('Pago registrado correctamente');
            fetchAll();
            setTimeout(() => setSuccess(''), 3000);
          }}
          timezone={tz}
        />
      )}
    </div>
  );
}