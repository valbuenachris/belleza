// ============================================================
// Página de Pacientes - CRUD real contra el backend FastAPI
// ============================================================

import React, { useState, useEffect, useCallback } from 'react';
import { api, ApiError } from '../services/api';
import { Patient } from '../types';
import {
  UserPlus, Search, Trash2, Mail, Phone, MapPin,
  Calendar, Stethoscope, Users as UsersIcon
} from 'lucide-react';

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [error, setError] = useState('');

  const loadPatients = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getPatients();
      setPatients(data.patients || []);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cargar pacientes');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPatients();
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
              className="bg-white rounded-2xl p-6 border border-stone-100 hover:shadow-lg hover:shadow-stone-100 transition-all duration-300"
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
                <button
                  onClick={() => handleDelete(patient.id)}
                  className="p-1.5 rounded-lg hover:bg-red-50 text-stone-400 hover:text-red-500 transition-colors"
                  title="Eliminar paciente"
                >
                  <Trash2 size={14} />
                </button>
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
                <div className="flex items-center gap-1.5 text-xs text-stone-500">
                  <UsersIcon size={13} />
                  {patient.ultima_cita
                    ? new Date(patient.ultima_cita).toLocaleDateString('es-ES')
                    : 'Sin visitas'}
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