// ============================================================
// Página de Pacientes - CRUD real contra el backend FastAPI
// ============================================================

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api, ApiError } from '../services/api';
import { Patient, Appointment, Page, ClinicalRecord, ClinicalRecordCreateInput } from '../types';
import { useAuth } from '../context/AuthContext';
import { requestScheduleAppointment } from '../services/scheduleRequest';
import { setPatientFichaListener } from '../services/patientActions';
import {
  UserPlus, Search, Trash2, Mail, Phone, MapPin,
  Calendar, Stethoscope, Users as UsersIcon, Pencil, FileText,
  X, CalendarPlus, Clock, Printer, Plus, ClipboardList, History, Edit3,
  Star, Wallet, Gift, Smartphone
} from 'lucide-react';

export default function PatientsPage({ onNavigate }: { onNavigate?: (page: Page) => void }) {
  const { tenant } = useAuth();
  const puntosMeta = tenant?.puntos_meta ?? 10;
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
                {(patient.puntos ?? 0) > 0 || (patient.sesiones_gratis ?? 0) > 0 ? (
                  <div className="flex items-center gap-2">
                    <Star size={13} className="text-amber-400 flex-shrink-0" />
                    <span className="flex items-center gap-1.5">
                      {patient.puntos ?? 0} / {puntosMeta} estrellas
                      {(patient.sesiones_gratis ?? 0) > 0 && (
                        <span className="inline-flex px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-emerald-50 text-emerald-700">
                          {patient.sesiones_gratis} gratis
                        </span>
                      )}
                    </span>
                  </div>
                ) : null}
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
          onRefresh={loadPatients}
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

function PatientClinicalModal({ patient, onClose, onSchedule, onRefresh }: {
  patient: Patient;
  onClose: () => void;
  onSchedule: (patientId: string) => void;
  onRefresh?: () => void;
}) {
  const { tenant } = useAuth();
  const puntosMeta = tenant?.puntos_meta ?? 10;
  const premioFidelidad = tenant?.premio_fidelidad || 'Sesión de Spa gratis';
  const [activeTab, setActiveTab] = useState<'appointments' | 'clinical'>('appointments');
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [records, setRecords] = useState<ClinicalRecord[]>([]);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [recordsError, setRecordsError] = useState('');
  const [showRecordForm, setShowRecordForm] = useState(false);
  const [editingRecord, setEditingRecord] = useState<ClinicalRecord | null>(null);
  const [savingRecord, setSavingRecord] = useState(false);

  // Programa de fidelidad (estrellas / sesiones gratis / pase digital)
  const [loyalty, setLoyalty] = useState({ puntos: patient.puntos ?? 0, sesiones_gratis: patient.sesiones_gratis ?? 0 });
  const [loyaltyBusy, setLoyaltyBusy] = useState(false);
  const [loyaltyMsg, setLoyaltyMsg] = useState('');
  const [loyaltyErr, setLoyaltyErr] = useState('');

  const handleDownloadPass = async () => {
    setLoyaltyBusy(true);
    setLoyaltyMsg('');
    setLoyaltyErr('');
    try {
      await api.downloadWalletPass(patient.id);
      setLoyaltyMsg('Pase descargado. Compártelo o ábrelo para añadirlo a Apple/Google Wallet.');
    } catch (err) {
      setLoyaltyErr(err instanceof ApiError ? err.message : 'Error al generar el pase');
    } finally {
      setLoyaltyBusy(false);
    }
  };

  const handleGoogleWallet = async () => {
    setLoyaltyBusy(true);
    setLoyaltyMsg('');
    setLoyaltyErr('');
    try {
      const res = await api.getGoogleWalletSaveLink(patient.id);
      if (res.enabled && res.save_url) {
        window.open(res.save_url, '_blank', 'noopener,noreferrer');
        setLoyaltyMsg(res.message || 'Abriendo Google Wallet… Añade la tarjeta a tu cartera.');
      } else {
        setLoyaltyErr(res.message || 'Google Wallet no está habilitado en este sistema.');
      }
    } catch (err) {
      setLoyaltyErr(err instanceof ApiError ? err.message : 'Error al generar el enlace de Google Wallet');
    } finally {
      setLoyaltyBusy(false);
    }
  };

  const handleRedeem = async () => {
    if (loyalty.sesiones_gratis <= 0) return;
    setLoyaltyBusy(true);
    setLoyaltyMsg('');
    setLoyaltyErr('');
    try {
      const res = await api.redeemSession(patient.id);
      setLoyalty({ puntos: res.puntos, sesiones_gratis: res.sesiones_gratis });
      setLoyaltyMsg(res.message);
      onRefresh?.();
    } catch (err) {
      setLoyaltyErr(err instanceof ApiError ? err.message : 'Error al canjear la sesión gratuita');
    } finally {
      setLoyaltyBusy(false);
    }
  };

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

  const loadRecords = async () => {
    setRecordsLoading(true);
    setRecordsError('');
    try {
      const data = await api.getPatientRecords(patient.id);
      setRecords(data.records || []);
    } catch (err) {
      setRecordsError(err instanceof ApiError ? err.message : 'Error al cargar la historia clínica');
    } finally {
      setRecordsLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
    loadRecords();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  // Formato compacto SOLO para el total invertido (evita desbordes en móvil).
  // Miles: "$30k", "$45k", "$45.9k". Importes < 1000 conservan fmtMoney.
  const fmtMoneyCompact = (v: number) => {
    if (Math.abs(v) < 1000) return fmtMoney(v);
    const compact = Math.round((v / 1000) * 10) / 10;
    return `$${Number.isInteger(compact) ? compact : compact.toFixed(1)}k`;
  };

  const submitRecord = async (payload: ClinicalRecordCreateInput) => {
    setSavingRecord(true);
    setRecordsError('');
    try {
      if (editingRecord) {
        await api.updateClinicalRecord(editingRecord.id, payload);
      } else {
        await api.createClinicalRecord(patient.id, payload);
      }
      setShowRecordForm(false);
      setEditingRecord(null);
      await loadRecords();
    } catch (err) {
      setRecordsError(err instanceof ApiError ? err.message : 'Error al guardar la evolución');
    } finally {
      setSavingRecord(false);
    }
  };

  const handleDeleteRecord = async (r: ClinicalRecord) => {
    if (!confirm('¿Eliminar esta evolución de la historia clínica?')) return;
    try {
      await api.deleteClinicalRecord(r.id);
      await loadRecords();
    } catch (err) {
      setRecordsError(err instanceof ApiError ? err.message : 'Error al eliminar la evolución');
    }
  };

  const esc = (s?: string | null) =>
    (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  const handlePrint = () => {
    const w = window.open('', '_blank', 'width=900,height=760');
    if (!w) return;
    const rows = records
      .map((r) => {
        const chip = (label: string, value?: string | null) =>
          value ? `<tr><th>${esc(label)}</th><td>${esc(value)}</td></tr>` : '';
        return `
        <div class="evo">
          <div class="evo-head">
            <span class="fecha">${esc(fmtDate(r.fecha))}</span>
            <span class="terapeuta">Terapeuta: ${r.therapist_name ? esc(r.therapist_name) : '—'}</span>
          </div>
          <table class="datos">
            ${chip('Zona tratada', r.zona_tratada)}
            ${chip('Tratamiento / Servicio', r.tratamiento_servicio)}
            ${chip('Productos / Parámetros', r.productos_parametros)}
            ${chip('Diagnóstico', r.diagnostico)}
          </table>
          <p class="obs-title">Observaciones / Evolución</p>
          <p class="obs">${r.observaciones ? esc(r.observaciones) : '—'}</p>
        </div>`;
      })
      .join('') || '<p class="vacio">Sin evoluciones registradas.</p>';

    const html = `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Historia Clínica — ${esc(patient.nombre)} ${esc(patient.apellido)}</title>
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; color:#1c1917; margin:0; padding:40px; }
  .brand { display:flex; justify-content:space-between; align-items:flex-end; border-bottom:3px solid #0f766e; padding-bottom:12px; }
  .brand h1 { font-size:22px; margin:0; color:#0f766e; }
  .brand p { margin:2px 0 0; font-size:12px; color:#78716c; }
  .titulo { font-size:14px; margin:22px 0 8px; text-transform:uppercase; letter-spacing:1px; color:#44403c; font-weight:700; }
  .paciente { width:100%; border-collapse:collapse; margin-bottom:4px; }
  .paciente td, .paciente th { padding:6px 8px; font-size:13px; }
  .paciente th { text-align:left; color:#78716c; font-weight:600; width:200px; }
  .paciente td { border-bottom:1px solid #e7e5e4; }
  .alergias { background:#f5f5f4; border-left:4px solid #dc2626; padding:10px 12px; font-size:13px; }
  .evo { border:1px solid #e7e5e4; border-radius:8px; padding:12px 14px; margin-bottom:14px; page-break-inside:avoid; }
  .evo-head { display:flex; justify-content:space-between; border-bottom:1px solid #f0efed; padding-bottom:6px; margin-bottom:8px; }
  .evo-head .fecha { font-weight:700; color:#0f766e; font-size:13px; }
  .evo-head .terapeuta { font-size:12px; color:#78716c; }
  .datos { width:100%; border-collapse:collapse; }
  .datos th, .datos td { text-align:left; padding:4px 8px 4px 0; font-size:13px; vertical-align:top; }
  .datos th { color:#78716c; font-weight:600; width:230px; white-space:nowrap; }
  .obs-title { font-size:12px; font-weight:600; color:#44403c; margin:8px 0 2px; }
  .obs { font-size:13px; white-space:pre-wrap; margin:0; }
  .vacio { color:#a8a29e; font-size:13px; }
  .firma { margin-top:48px; border-top:1px solid #d6d3d1; padding-top:8px; font-size:12px; color:#57534e; }
  @media print { body { padding:0; } }
</style>
</head>
<body>
  <div class="brand">
    <div>
      <h1>Historia Clínica</h1>
      <p>Registro de tratamientos y evolución del paciente</p>
    </div>
    <div>
      <p>Generado: ${esc(new Date().toLocaleString('es-ES'))}</p>
    </div>
  </div>

  <div class="titulo">Datos del Paciente</div>
  <table class="paciente">
    <tr><th>Nombre</th><td>${esc(patient.nombre)} ${esc(patient.apellido)}</td></tr>
    ${patient.telefono ? `<tr><th>Teléfono</th><td>${esc(patient.telefono)}</td></tr>` : ''}
    ${patient.email ? `<tr><th>Email</th><td>${esc(patient.email)}</td></tr>` : ''}
    ${patient.direccion ? `<tr><th>Dirección</th><td>${esc(patient.direccion)}</td></tr>` : ''}
    ${patient.fecha_nacimiento ? `<tr><th>Fecha de nacimiento</th><td>${esc(fmtDate(patient.fecha_nacimiento))}</td></tr>` : ''}
  </table>

  <div class="titulo">Alergias / Notas Médicas</div>
  <div class="alergias">${esc(patient.notas_medicas) || 'Sin alergias ni notas médicas registradas.'}</div>

  <div class="titulo">Evoluciones de Tratamiento (${records.length})</div>
  ${rows}

  <div class="firma">Firma del profesional: ______________________________________</div>
</body>
</html>`;

    w.document.write(html);
    w.document.close();
    setTimeout(() => { w.focus(); w.print(); }, 400);
  };

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

        {/* Tabs */}
        <div className="flex gap-1 border-b border-stone-100 px-6">
          <button
            onClick={() => setActiveTab('appointments')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === 'appointments'
                ? 'text-emerald-600 border-emerald-500'
                : 'text-stone-500 border-transparent hover:text-stone-700'
            }`}
          >
            <History size={15} />
            Historial de Citas
          </button>
          <button
            onClick={() => setActiveTab('clinical')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === 'clinical'
                ? 'text-emerald-600 border-emerald-500'
                : 'text-stone-500 border-transparent hover:text-stone-700'
            }`}
          >
            <ClipboardList size={15} />
            Historia Clínica / Evoluciones
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

          {/* Programa de Fidelidad */}
          <div className="bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-100 rounded-2xl p-4">
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <Star size={16} className="text-amber-500" />
                <h3 className="text-sm font-semibold text-stone-700">Programa de Fidelidad</h3>
              </div>
              <span className="text-xs font-medium text-amber-700">{loyalty.puntos} / {puntosMeta} estrellas</span>
            </div>

            <div className="flex items-center gap-1 mb-3" aria-label="Progreso de estrellas">
              {Array.from({ length: puntosMeta }).map((_, i) => (
                <Star
                  key={i}
                  size={18}
                  className={i < loyalty.puntos ? 'fill-amber-400 text-amber-400' : 'text-stone-300'}
                />
              ))}
            </div>

            <p className="text-xs text-stone-500 mb-3">
              {loyalty.sesiones_gratis > 0
                ? `¡Tienes ${loyalty.sesiones_gratis} ${loyalty.sesiones_gratis === 1 ? 'sesión gratis disponible' : 'sesiones gratis disponibles'}!`
                : `Cada cita completada suma una estrella. ¡${puntosMeta} estrellas = ${premioFidelidad}!`}
            </p>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={handleDownloadPass}
                disabled={loyaltyBusy}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-white border border-amber-200 text-amber-700 hover:bg-amber-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Descargar pase .pkpass para Apple Wallet / Google Wallet"
              >
                <Wallet size={14} />
                Añadir a Wallet
              </button>
              <button
                type="button"
                onClick={handleGoogleWallet}
                disabled={loyaltyBusy}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-white border border-teal-200 text-teal-700 hover:bg-teal-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Añadir la tarjeta de fidelidad a Google Wallet (Android)"
              >
                <Smartphone size={14} />
                Añadir a Google Wallet
              </button>
              <button
                type="button"
                onClick={handleRedeem}
                disabled={loyalty.sesiones_gratis <= 0 || loyaltyBusy}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                title="Usar una sesión gratuita"
              >
                <Gift size={14} />
                Canjear Sesión Gratis
              </button>
            </div>

            {loyaltyMsg && <p className="mt-2 text-xs text-emerald-700">{loyaltyMsg}</p>}
            {loyaltyErr && <p className="mt-2 text-xs text-red-600">{loyaltyErr}</p>}
          </div>

          {activeTab === 'appointments' && (
            <>
              {/* Estadísticas */}
              <div className="grid grid-cols-1 min-[360px]:grid-cols-3 gap-3">
                <div className="p-3 sm:p-4 bg-emerald-50 rounded-xl text-center min-w-0 overflow-hidden">
                  <p className="text-lg sm:text-2xl font-bold text-emerald-700 break-words">{totalCitas}</p>
                  <p className="text-xs text-stone-500 mt-1 break-words">Citas atendidas</p>
                </div>
                <div className="p-3 sm:p-4 bg-blue-50 rounded-xl text-center min-w-0 overflow-hidden">
                  <p className="text-lg sm:text-2xl font-bold text-blue-700 break-words">{fmtMoneyCompact(totalGastos)}</p>
                  <p className="text-xs text-stone-500 mt-1 break-words">Total invertido</p>
                </div>
                <div className="p-3 sm:p-4 bg-violet-50 rounded-xl text-center min-w-0 overflow-hidden">
                  <p className="text-base sm:text-xl font-bold text-violet-700 mt-0.5 break-words">{ultimaVisita ? fmtDate(ultimaVisita.toISOString()) : '—'}</p>
                  <p className="text-xs text-stone-500 mt-1 break-words">Última visita</p>
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
            </>
          )}

          {activeTab === 'clinical' && (
            <div>
              <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                <h3 className="text-sm font-semibold text-stone-700 uppercase tracking-wider">
                  Historia Clínica
                  <span className="ml-2 text-xs font-normal normal-case text-stone-400">
                    ({records.length} evoluciones)
                  </span>
                </h3>
                <div className="flex gap-2">
                  <button
                    onClick={handlePrint}
                    disabled={records.length === 0}
                    className="inline-flex items-center gap-1.5 px-3 py-2 border border-stone-200 rounded-xl text-xs font-medium text-stone-600 hover:bg-stone-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    title="Imprimir historia clínica"
                  >
                    <Printer size={14} />
                    Imprimir
                  </button>
                  <button
                    onClick={() => { setEditingRecord(null); setShowRecordForm(true); }}
                    className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl text-xs font-medium hover:from-emerald-600 hover:to-teal-700 transition-all"
                  >
                    <Plus size={14} />
                    Nueva Evolución
                  </button>
                </div>
              </div>

              {recordsError && (
                <div className="mb-3 p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">{recordsError}</div>
              )}

              {showRecordForm && (
                <ClinicalRecordFormModal
                  patient={patient}
                  record={editingRecord}
                  saving={savingRecord}
                  onSubmit={submitRecord}
                  onCancel={() => { setShowRecordForm(false); setEditingRecord(null); }}
                />
              )}

              {!showRecordForm && recordsLoading ? (
                <div className="space-y-2">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-16 bg-stone-100 rounded-xl animate-pulse" />
                  ))}
                </div>
              ) : !showRecordForm && records.length === 0 ? (
                <div className="text-center py-10 bg-stone-50 rounded-xl">
                  <ClipboardList size={32} className="mx-auto text-stone-300 mb-2" />
                  <p className="text-sm text-stone-400">
                    Aún no hay evoluciones registradas en la historia clínica
                  </p>
                </div>
              ) : (
                !showRecordForm && (
                  <div className="space-y-3">
                    {records.map((r) => (
                      <div key={r.id} className="p-4 bg-stone-50 rounded-xl border border-stone-100">
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
                            <span className="text-sm font-semibold text-stone-800">{fmtDate(r.fecha)}</span>
                            {r.therapist_name && (
                              <span className="inline-flex items-center gap-1 text-xs text-stone-500 truncate">
                                <Stethoscope size={12} className="text-stone-400 shrink-0" />
                                {r.therapist_name}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-1 shrink-0">
                            <button
                              onClick={() => { setEditingRecord(r); setShowRecordForm(true); }}
                              className="p-1.5 rounded-lg hover:bg-stone-200 text-stone-400 hover:text-emerald-600 transition-colors"
                              title="Editar evolución"
                            >
                              <Edit3 size={14} />
                            </button>
                            <button
                              onClick={() => handleDeleteRecord(r)}
                              className="p-1.5 rounded-lg hover:bg-stone-200 text-stone-400 hover:text-red-500 transition-colors"
                              title="Eliminar evolución"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                        {(r.zona_tratada || r.tratamiento_servicio) && (
                          <div className="mt-2.5 flex flex-wrap gap-1.5">
                            {r.zona_tratada && (
                              <span className="inline-flex px-2 py-0.5 text-[10px] font-medium rounded-full bg-emerald-50 text-emerald-700">
                                {r.zona_tratada}
                              </span>
                            )}
                            {r.tratamiento_servicio && (
                              <span className="inline-flex px-2 py-0.5 text-[10px] font-medium rounded-full bg-sky-50 text-sky-700">
                                {r.tratamiento_servicio}
                              </span>
                            )}
                          </div>
                        )}
                        {r.productos_parametros && (
                          <p className="mt-2 text-xs text-stone-500">
                            <span className="font-medium text-stone-600">Productos / Parámetros:</span>{' '}
                            {r.productos_parametros}
                          </p>
                        )}
                        {r.diagnostico && (
                          <p className="mt-1 text-xs text-stone-500">
                            <span className="font-medium text-stone-600">Diagnóstico / Valoración:</span>{' '}
                            {r.diagnostico}
                          </p>
                        )}
                        {r.observaciones && (
                          <p className="mt-2 text-sm text-stone-700 border-t border-stone-200 pt-2 whitespace-pre-wrap">
                            {r.observaciones}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )
              )}
            </div>
          )}
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

function ClinicalRecordFormModal({ patient, record, saving, onSubmit, onCancel }: {
  patient: Patient;
  record: ClinicalRecord | null;
  saving: boolean;
  onSubmit: (payload: ClinicalRecordCreateInput) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    fecha: record?.fecha ? record.fecha.slice(0, 10) : new Date().toISOString().slice(0, 10),
    zona_tratada: record?.zona_tratada || '',
    tratamiento_servicio: record?.tratamiento_servicio || '',
    productos_parametros: record?.productos_parametros || '',
    observaciones: record?.observaciones || '',
    diagnostico: record?.diagnostico || '',
  });
  const [error, setError] = useState('');

  const inputClass =
    'w-full px-3 py-2 border border-stone-200 rounded-xl text-sm focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-400 outline-none bg-white transition';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.tratamiento_servicio.trim() && !form.zona_tratada.trim()) {
      setError('Indica al menos la zona tratada o el tratamiento realizado');
      return;
    }
    setError('');
    onSubmit({
      fecha: form.fecha ? `${form.fecha}T00:00:00` : undefined,
      zona_tratada: form.zona_tratada.trim() || null,
      tratamiento_servicio: form.tratamiento_servicio.trim() || null,
      productos_parametros: form.productos_parametros.trim() || null,
      observaciones: form.observaciones.trim() || null,
      diagnostico: form.diagnostico.trim() || null,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 bg-white border border-stone-200 rounded-2xl shadow-sm mb-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-stone-700">
          {record ? 'Editar Evolución' : 'Nueva Evolución Clínica'}
        </h4>
        <span className="text-xs text-stone-400">{patient.nombre} {patient.apellido}</span>
      </div>

      <p className="text-xs text-stone-500 italic mb-3">
        Escribe la zona tratada, el tratamiento/servicio, los productos/parámetros utilizados y la
        evaluación de la sesión. Quedará registrado como evolución en la historia clínica.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
        <div>
          <label className="block text-xs font-medium text-stone-500 mb-1">Fecha</label>
          <input
            type="date"
            required
            value={form.fecha}
            onChange={(e) => setForm((f) => ({ ...f, fecha: e.target.value }))}
            className={inputClass}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-stone-500 mb-1">Zona tratada</label>
          <input
            type="text"
            value={form.zona_tratada}
            onChange={(e) => setForm((f) => ({ ...f, zona_tratada: e.target.value }))}
            placeholder="Ej: Rostro, Espalda..."
            className={inputClass}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-stone-500 mb-1">Tratamiento / Servicio</label>
          <input
            type="text"
            value={form.tratamiento_servicio}
            onChange={(e) => setForm((f) => ({ ...f, tratamiento_servicio: e.target.value }))}
            placeholder="Ej: Radiofrecuencia, Masaje descontracturante..."
            className={inputClass}
          />
        </div>
      </div>

      <div className="mb-3">
        <label className="block text-xs font-medium text-stone-500 mb-1">Productos / Parámetros aplicados</label>
        <textarea
          rows={2}
          value={form.productos_parametros}
          onChange={(e) => setForm((f) => ({ ...f, productos_parametros: e.target.value }))}
          placeholder="Productos cosmetológicos, intensidad, potencia, tiempo, etc."
          className={`${inputClass} resize-y`}
        />
      </div>

      <div className="mb-3">
        <label className="block text-xs font-medium text-stone-500 mb-1">Diagnóstico / Valoración</label>
        <textarea
          rows={2}
          value={form.diagnostico}
          onChange={(e) => setForm((f) => ({ ...f, diagnostico: e.target.value }))}
          placeholder="Diagnóstico o valoración de la sesión"
          className={`${inputClass} resize-y`}
        />
      </div>

      <div className="mb-3">
        <label className="block text-xs font-medium text-stone-500 mb-1">Observaciones / Evolución del paciente</label>
        <textarea
          rows={3}
          value={form.observaciones}
          onChange={(e) => setForm((f) => ({ ...f, observaciones: e.target.value }))}
          placeholder="Describe la evolución del paciente, reacciones, recomendaciones..."
          className={`${inputClass} resize-y`}
        />
      </div>

      {error && (
        <div className="mb-3 p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">{error}</div>
      )}

      <div className="flex gap-2 justify-end">
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="px-4 py-2 border border-stone-200 rounded-xl text-sm font-medium text-stone-600 hover:bg-stone-50 disabled:opacity-50"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white text-sm font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 transition-all disabled:opacity-50 inline-flex items-center gap-2"
        >
          {saving ? 'Guardando...' : record ? 'Guardar Cambios' : 'Registrar Evolución'}
        </button>
      </div>
    </form>
  );
}