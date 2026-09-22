// ============================================================
// Página de Citas - Agenda con anti-doble reserva (backend)
// ============================================================

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { api, ApiError } from '../services/api';
import { Appointment, Patient, Service, User } from '../types';
import {
  Calendar, Plus, Trash2, Clock, DollarSign,
  User as UserIcon, Scissors, AlertCircle
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

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterDate, setFilterDate] = useState(todayStr());
  const [filterStatus, setFilterStatus] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [error, setError] = useState('');

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

  useEffect(() => {
    loadAppointments();
  }, [loadAppointments]);

  const handleCancel = async (id: string) => {
    if (!confirm('¿Deseas cancelar esta cita? Se liberará el horario del terapeuta.')) return;
    setError('');
    try {
      await api.cancelAppointment(id);
      loadAppointments();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cancelar cita');
    }
  };

  const currency = (v: number | null | undefined) =>
    v == null ? '—' : `$${v.toLocaleString('es-CO', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;

  return (
    <div className="space-y-6">
      {error && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600 flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-stone-800">Citas</h1>
          <p className="text-stone-500 mt-1">Agenda, confirma y cancela citas de tus pacientes</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl
            hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-200/50 transition-all"
        >
          <Plus size={18} />
          Nueva Cita
        </button>
      </div>

      {/* Filters */}
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
                          {apt.hora_inicio || apt.time || (apt.date_time ? apt.date_time.slice(11, 16) : '—')} h
                        </span>
                        <span className="text-xs text-stone-400">{apt.duracion} min</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2.5 py-1 text-xs font-medium rounded-full capitalize ${statusColors[apt.estado] || 'bg-stone-50 text-stone-600'}`}>
                        {statusLabels[apt.estado] || apt.estado}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right hidden sm:table-cell">
                      <span className="text-sm font-medium text-stone-700">{currency(apt.precio)}</span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      {apt.estado !== 'cancelled' && (
                        <button
                          onClick={() => handleCancel(apt.id)}
                          className="p-2 rounded-lg hover:bg-red-50 text-stone-400 hover:text-red-500 transition-colors"
                          title="Cancelar cita"
                        >
                          <Trash2 size={16} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showCreateModal && (
        <CreateAppointmentModal
          onClose={() => setShowCreateModal(false)}
          onCreated={() => { setShowCreateModal(false); loadAppointments(); }}
        />
      )}
    </div>
  );
}

// ============================================================
// Modal de Nueva Cita
// ============================================================
function CreateAppointmentModal({ onClose, onCreated }: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [therapists, setTherapists] = useState<User[]>([]);
  const [metaLoading, setMetaLoading] = useState(true);

  const [formData, setFormData] = useState({
    patientId: '',
    serviceId: '',
    therapistId: '',
    fecha: todayStr(),
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