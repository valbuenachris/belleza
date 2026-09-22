// ============================================================
// Página de Pacientes - CRUD real contra el backend FastAPI
// ============================================================

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api, ApiError } from '../services/api';
import { Patient, Appointment, Page } from '../types';
import { requestScheduleAppointment } from '../services/scheduleRequest';
import { setPatientFichaListener } from '../services/patientActions';
import {
  UserPlus, Search, Trash2, Mail, Phone, MapPin,
  Calendar, Stethoscope, Users as UsersIcon, Pencil, FileText,
  X, CalendarPlus, Clock
} from 'lucide-react';

export default function PatientsPage({ onNavigate }: { onNavigate?: (page: Page) => void }) {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingPatient, setEditingPatient] = useState<Patient | null>(null);
  const [viewingPatient, setViewingPatient] = useState<Patient | null>(null);
  const [error, setError] = useState('');
  const patientsRef = useRef<Patient[]>([]);
  const pendingFichaRef = useRef<string | null>(null);

  const loadPatients = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getPatients();
      const list = data.patients || [];
      patientsRef.current = list;
      setPatients(list);
      if (pendingFichaRef.current) {
        const p = list.find((x) => x.id === pendingFichaRef.current);
        if (p) setViewingPatient(p);
        pendingFichaRef.current = null;
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cargar pacientes');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPatients();
  }, [loadPatients]);

  // Recibir solicitudes de apertura de Ficha desde el buscador global
  useEffect(() => {
    setPatientFichaListener((patientId: string) => {
      const p = patientsRef.current.find((x) => x.id === patientId);
      if (p) {
        setViewingPatient(p);
      } else {
        pendingFichaRef.current = patientId;
        loadPatients();
      }
    });
    return () => setPatientFichaListener(null);
  }, [loadPatients]);

  const filteredPatients = patients.filter(p => {
    const q = searchTerm.toLowerCase();
    return (
      p.nombre.toLowerCase().includes(q) ||
      p.apellido.toLowerCase().includes(q) ||
      (p.email || '').toLowerCase().includes(q) ||
      (p.telefono || '').toLowerCase().includes(q)
    );
  });

  const handleDelete = async (id: string) => {
    if (!confirm('¿Estás seguro de que deseas eliminar este paciente?')) return;
    setError('');
    try {
      await api.deletePatient(id);
      loadPatients();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al eliminar paciente');
    }
  };

  const handleSchedule = (patientId: string) => {
    setViewingPatient(null);
    requestScheduleAppointment(patientId);
    onNavigate?.('appointments');
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-stone-800">Pacientes</h1>
          <p className="text-stone-500 mt-1">Gestión de pacientes de tu SPA</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl
            hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-200/50 transition-all"
        >
          <UserPlus size={18} />
          Nuevo Paciente
        </button>
      </div>

      {/* Search */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex items-center gap-2 bg-white rounded-xl px-4 py-2.5 border border-stone-200 flex-1 max-w-md">
          <Search size={18} className="text-stone-400" />
          <input
            type="text"
            placeholder="Buscar por nombre, email o teléfono..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-none outline-none text-sm text-stone-700 placeholder:text-stone-400 w-full"
          />
        </div>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-white rounded-2xl p-6 border border-stone-100 animate-pulse">
              <div className="h-4 bg-stone-100 rounded w-24 mb-3" />
              <div className="h-3 bg-stone-100 rounded w-32 mb-2" />
              <div className="h-3 bg-stone-100 rounded w-20" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredPatients.map((patient) => (
            <div
              key={patient.id}
              onClick={() => setViewingPatient(patient)}
              className="bg-white rounded-2xl p-6 border border-stone-100 hover:shadow-lg hover:shadow-stone-100 transition-all duration-300 cursor-pointer"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-emerald-100 to-teal-100 flex items-center justify-center">
                    <span className="text-sm font-bold text-emerald-700">
                      {patient.nombre[0]}{patient.apellido[0]}
                    </span>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-stone-800">{patient.nombre} {patient.apellido}</p>
                    {patient.genero && (
                      <p className="text-xs text-stone-500">{patient.genero}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={(e) => { e.stopPropagation(); setEditingPatient(patient); }}
                    className="p-1.5 rounded-lg hover:bg-emerald-50 text-stone-400 hover:text-emerald-600 transition-colors"
                    title="Editar paciente"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(patient.id); }}
                    className="p-1.5 rounded-lg hover:bg-red-50 text-stone-400 hover:text-red-500 transition-colors"
                    title="Eliminar paciente"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              <div className="space-y-2 text-xs text-stone-500">
                {patient.email && (
                  <div className="flex items-center gap-2">
                    <Mail size={13} />
                    <span className="truncate">{patient.email}</span>
                  </div>
                )}
                {patient.telefono && (
                  <div className="flex items-center gap-2">
                    <Phone size={13} />
                    <span>{patient.telefono}</span>
                  </div>
                )}
                {patient.direccion && (
                  <div className="flex items-center gap-2">
                    <MapPin size={13} />
                    <span className="truncate">{patient.direccion}</span>
                  </div>
                )}
                {patient.notas_medicas && (
                  <div className="flex items-start gap-2">
                    <Stethoscope size={13} className="mt-0.5 flex-shrink-0" />
                    <span className="truncate">{patient.notas_medicas}</span>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between mt-4 pt-4 border-t border-stone-100">
                <div className="flex items-center gap-1.5 text-xs text-stone-500">
                  <Calendar size={13} />
                  {patient.total_citas ?? 0} citas
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5 text-xs text-stone-500">
                    <UsersIcon size={13} />
                    {patient.ultima_cita
                      ? new Date(patient.ultima_cita).toLocaleDateString('es-ES')
                      : 'Sin visitas'}
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); setViewingPatient(patient); }}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-emerald-600 bg-emerald-50 hover:bg-emerald-100 transition-colors"
                  >
                    <FileText size={13} />
                    Ver Ficha
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {filteredPatients.length === 0 && !loading && (
        <div className="text-center py-12 bg-white rounded-2xl border border-stone-100">
          <Stethoscope size={48} className="mx-auto text-stone-300 mb-3" />
          <p className="text-stone-500">No se encontraron pacientes</p>
        </div>
      )}

      {showCreateModal && (
        <CreatePatientModal
          onClose={() => setShowCreateModal(false)}
          onCreated={() => { setShowCreateModal(false); loadPatients(); }}
        />
      )}

      {editingPatient && (
        <EditPatientModal
          patient={editingPatient}
          onClose={() => setEditingPatient(null)}
          onUpdated={() => { setEditingPatient(null); loadPatients(); }}
        />
      )}

      {viewingPatient && (
        <PatientClinicalModal
          patient={viewingPatient}
          onClose={() => setViewingPatient(null)}
          onSchedule={handleSchedule}
        />
      )}
    </div>
  );
}

// ============================================================
// Modal de Crear Paciente
// ============================================================
function CreatePatientModal({ onClose, onCreated }: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [formData, setFormData] = useState({
    nombre: '',
    apellido: '',
    email: '',
    telefono: '',
    direccion: '',
    notas_medicas: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.createPatient({
        nombre: formData.nombre,
        apellido: formData.apellido,
        email: formData.email || null,
        telefono: formData.telefono || null,
        direccion: formData.direccion || null,
        notas_medicas: formData.notas_medicas || null,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al crear paciente');
      setLoading(false);
    }
  };

  const inputClass = "w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-stone-100">
          <h2 className="text-xl font-semibold text-stone-800">Nuevo Paciente</h2>
          <p className="text-sm text-stone-500 mt-1">Registra un nuevo paciente en tu SPA</p>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">{error}</div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Nombre *</label>
              <input
                type="text" required value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                className={inputClass} placeholder="María"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Apellido *</label>
              <input
                type="text" required value={formData.apellido}
                onChange={(e) => setFormData({ ...formData, apellido: e.target.value })}
                className={inputClass} placeholder="González"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Email</label>
              <input
                type="email" value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className={inputClass} placeholder="maria@email.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Teléfono</label>
              <input
                type="tel" value={formData.telefono}
                onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                className={inputClass} placeholder="+57 300 123 4567"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Dirección</label>
            <input
              type="text" value={formData.direccion}
              onChange={(e) => setFormData({ ...formData, direccion: e.target.value })}
              className={inputClass} placeholder="Calle 100 #15-20, Ciudad"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Notas médicas / Alergias</label>
            <textarea
              value={formData.notas_medicas}
              onChange={(e) => setFormData({ ...formData, notas_medicas: e.target.value })}
              className={`${inputClass} resize-none`} rows={3}
              placeholder="Alergias, condiciones o preferencias"
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
              type="submit" disabled={loading}
              className="flex-1 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 transition-all"
            >
              {loading ? 'Creando...' : 'Crear Paciente'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ============================================================
// Modal de Editar Paciente
// ============================================================
function EditPatientModal({ patient, onClose, onUpdated }: {
  patient: Patient;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [formData, setFormData] = useState({
    nombre: patient.nombre,
    apellido: patient.apellido,
    email: patient.email || '',
    telefono: patient.telefono || '',
    direccion: patient.direccion || '',
    notas_medicas: patient.notas_medicas || '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!formData.nombre.trim() || !formData.apellido.trim()) {
      setError('El nombre y el apellido son obligatorios');
      return;
    }
    if (formData.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email.trim())) {
      setError('Formato de email inválido');
      return;
    }
    setLoading(true);
    try {
      await api.updatePatient(patient.id, {
        nombre: formData.nombre.trim(),
        apellido: formData.apellido.trim(),
        email: formData.email.trim() || null,
        telefono: formData.telefono.trim() || null,
        direccion: formData.direccion.trim() || null,
        notas_medicas: formData.notas_medicas.trim() || null,
      });
      onUpdated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al actualizar paciente');
      setLoading(false);
    }
  };

  const inputClass = "w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-stone-100">
          <h2 className="text-xl font-semibold text-stone-800">Editar Paciente</h2>
          <p className="text-sm text-stone-500 mt-1">Actualiza los datos de {patient.nombre} {patient.apellido}</p>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">{error}</div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Nombre *</label>
              <input
                type="text" required value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                className={inputClass} placeholder="María"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Apellido *</label>
              <input
                type="text" required value={formData.apellido}
                onChange={(e) => setFormData({ ...formData, apellido: e.target.value })}
                className={inputClass} placeholder="González"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Email</label>
              <input
                type="email" value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className={inputClass} placeholder="maria@email.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Teléfono</label>
              <input
                type="tel" value={formData.telefono}
                onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                className={inputClass} placeholder="+57 300 123 4567"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Dirección</label>
            <input
              type="text" value={formData.direccion}
              onChange={(e) => setFormData({ ...formData, direccion: e.target.value })}
              className={inputClass} placeholder="Calle 100 #15-20, Ciudad"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Notas médicas / Alergias</label>
            <textarea
              value={formData.notas_medicas}
              onChange={(e) => setFormData({ ...formData, notas_medicas: e.target.value })}
              className={`${inputClass} resize-none`} rows={3}
              placeholder="Alergias, condiciones o preferencias"
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
              type="submit" disabled={loading}
              className="flex-1 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 transition-all"
            >
              {loading ? 'Guardando...' : 'Guardar Cambios'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ============================================================
// Ficha del Paciente - Detalle + Historial clínico
// ============================================================
const fichaStatusLabels: Record<string, string> = {
  pending: 'Pendiente',
  confirmed: 'Confirmada',
  completed: 'Completada',
  cancelled: 'Cancelada',
};

const fichaStatusColors: Record<string, string> = {
  pending: 'bg-amber-50 text-amber-700',
  confirmed: 'bg-emerald-50 text-emerald-700',
  completed: 'bg-blue-50 text-blue-700',
  cancelled: 'bg-red-50 text-red-500',
};

function PatientClinicalModal({ patient, onClose, onSchedule }: {
  patient: Patient;
  onClose: () => void;
  onSchedule: (patientId: string) => void;
}) {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadHistory = async () => {
      setLoading(true);
      setError('');
      try {
        const data = await api.getAppointments({ patient_id: patient.id, limit: 100 });
        setAppointments(data.appointments || []);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Error al cargar el historial');
      } finally {
        setLoading(false);
      }
    };
    loadHistory();
  }, [patient.id]);

  // Estadísticas del paciente (excluye citas canceladas)
  const active = appointments.filter((a) => a.estado !== 'cancelled');
  const totalCitas = active.length;
  const totalGastos = active.reduce((sum, a) => sum + (a.precio ?? 0), 0);
  const ultimaVisita = active.reduce<Date | null>((max, a) => {
    const d = a.date_time ? new Date(a.date_time) : null;
    if (!d || isNaN(d.getTime())) return max;
    return max === null || d > max ? d : max;
  }, null);

  const fmtDate = (iso: string | null | undefined) => {
    if (!iso) return '—';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '—';
    return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const fmtTime = (a: Appointment) =>
    a.hora_inicio || a.time || (a.date_time ? a.date_time.slice(11, 16) : '--:--');

  const fmtMoney = (v: number) =>
    `$${v.toLocaleString('es-CO', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-5 border-b border-stone-100 flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-emerald-100 to-teal-100 flex items-center justify-center">
              <span className="text-sm font-bold text-emerald-700">
                {patient.nombre[0]}{patient.apellido[0]}
              </span>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-stone-800">Ficha del Paciente</h2>
              <p className="text-sm text-stone-500">{patient.nombre} {patient.apellido}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-stone-100 text-stone-400 hover:text-stone-600 transition-colors"
            title="Cerrar"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Datos de contacto */}
          <div>
            <h3 className="text-sm font-semibold text-stone-700 uppercase tracking-wider mb-3">Datos del Paciente</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {patient.telefono && (
                <div className="flex items-center gap-2 text-sm text-stone-600">
                  <Phone size={14} className="text-stone-400 shrink-0" />
                  <span>{patient.telefono}</span>
                </div>
              )}
              {patient.email && (
                <div className="flex items-center gap-2 text-sm text-stone-600">
                  <Mail size={14} className="text-stone-400 shrink-0" />
                  <span className="truncate">{patient.email}</span>
                </div>
              )}
              {patient.direccion && (
                <div className="flex items-center gap-2 text-sm text-stone-600">
                  <MapPin size={14} className="text-stone-400 shrink-0" />
                  <span className="truncate">{patient.direccion}</span>
                </div>
              )}
              {patient.fecha_nacimiento && (
                <div className="flex items-center gap-2 text-sm text-stone-600">
                  <Calendar size={14} className="text-stone-400 shrink-0" />
                  <span>{fmtDate(patient.fecha_nacimiento)}</span>
                </div>
              )}
            </div>
            <div className="mt-3 p-3 bg-stone-50 rounded-xl">
              <div className="flex items-start gap-2 text-sm">
                <Stethoscope size={14} className="mt-0.5 text-stone-400 shrink-0" />
                <div>
                  <p className="text-xs font-medium text-stone-500">Notas médicas / Alergias</p>
                  <p className="text-sm text-stone-700 mt-0.5">
                    {patient.notas_medicas || 'Sin notas médicas registradas'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Estadísticas */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-4 bg-emerald-50 rounded-xl text-center">
              <p className="text-2xl font-bold text-emerald-700">{totalCitas}</p>
              <p className="text-xs text-stone-500 mt-1">Citas atendidas</p>
            </div>
            <div className="p-4 bg-blue-50 rounded-xl text-center">
              <p className="text-2xl font-bold text-blue-700">{fmtMoney(totalGastos)}</p>
              <p className="text-xs text-stone-500 mt-1">Total invertido</p>
            </div>
            <div className="p-4 bg-violet-50 rounded-xl text-center">
              <p className="text-xl font-bold text-violet-700 mt-0.5">{ultimaVisita ? fmtDate(ultimaVisita.toISOString()) : '—'}</p>
              <p className="text-xs text-stone-500 mt-1">Última visita</p>
            </div>
          </div>

          {/* Historial de citas */}
          <div>
            <h3 className="text-sm font-semibold text-stone-700 uppercase tracking-wider mb-3">Historial de Citas</h3>
            {error && (
              <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">{error}</div>
            )}
            {loading ? (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="h-16 bg-stone-100 rounded-xl animate-pulse" />
                ))}
              </div>
            ) : appointments.length === 0 ? (
              <div className="text-center py-8 bg-stone-50 rounded-xl">
                <Calendar size={32} className="mx-auto text-stone-300 mb-2" />
                <p className="text-sm text-stone-400">Este paciente aún no tiene citas registradas</p>
              </div>
            ) : (
              <div className="space-y-2">
                {appointments.map((a) => (
                  <div key={a.id} className="p-3 bg-stone-50 rounded-xl">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <Clock size={14} className="text-stone-400 shrink-0" />
                        <span className="text-sm font-semibold text-stone-800">
                          {fmtDate(a.date_time)} · {fmtTime(a)}h
                        </span>
                        <span className={`inline-flex px-2 py-0.5 text-[10px] font-medium rounded-full capitalize shrink-0 ${
                          fichaStatusColors[a.estado] || 'bg-stone-100 text-stone-600'
                        }`}>
                          {fichaStatusLabels[a.estado] || a.estado}
                        </span>
                      </div>
                      <span className="text-sm font-semibold text-stone-700 shrink-0">{fmtMoney(a.precio ?? 0)}</span>
                    </div>
                    <div className="mt-1.5 grid grid-cols-1 sm:grid-cols-3 gap-1 text-xs text-stone-500">
                      <span className="truncate">Servicio: {a.service || '—'}</span>
                      <span className="truncate">Terapeuta: {a.therapist || '—'}</span>
                      <span>{a.duracion} min</span>
                    </div>
                    {a.notas && (
                      <p className="mt-1 text-xs text-stone-500 line-clamp-2">{a.notas}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-stone-100 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 border border-stone-200 rounded-xl text-sm font-medium text-stone-600 hover:bg-stone-50"
          >
            Cerrar
          </button>
          <button
            onClick={() => onSchedule(patient.id)}
            className="flex-1 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 transition-all inline-flex items-center justify-center gap-2"
          >
            <CalendarPlus size={16} />
            Agendar Cita
          </button>
        </div>
      </div>
    </div>
  );
}