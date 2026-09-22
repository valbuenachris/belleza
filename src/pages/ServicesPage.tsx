// ============================================================
// Página de Servicios - CRUD real de los servicios del SPA
// ============================================================

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { api, ApiError } from '../services/api';
import { Service, ServiceCreateInput } from '../types';
import {
  Tag, Plus, Search, Edit, Trash2,
  CheckCircle, XCircle, Clock, AlertCircle
} from 'lucide-react';

export default function ServicesPage() {
  const { user: currentUser, tenant } = useAuth();
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingService, setEditingService] = useState<Service | null>(null);
  const [error, setError] = useState('');

  const canManage = currentUser?.rol === 'admin' || currentUser?.rol === 'manager';

  const currencyFormatter = new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: tenant?.moneda || 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
  const fmtMoney = (v: number) => currencyFormatter.format(v);

  const loadServices = useCallback(async () => {
    setError('');
    try {
      const data = await api.getServices();
      setServices(data.services || []);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cargar servicios');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadServices();
  }, [loadServices]);

  const filteredServices = services.filter(s => {
    const matchesSearch = s.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.descripcion || '').toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  const handleDelete = async (id: string) => {
    if (!confirm('¿Estás seguro de que deseas desactivar este servicio?')) return;
    setError('');
    try {
      await api.deleteService(id);
      loadServices();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al desactivar servicio');
    }
  };

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
          <h1 className="text-2xl lg:text-3xl font-bold text-stone-800">Servicios</h1>
          <p className="text-stone-500 mt-1">Catálogo de servicios de {tenant?.nombre || 'tu SPA'}</p>
        </div>
        {canManage && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl
              hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-200/50 transition-all"
          >
            <Plus size={18} />
            Nuevo Servicio
          </button>
        )}
      </div>

      {/* Search */}
      <div className="flex items-center gap-2 bg-white rounded-xl px-4 py-2.5 border border-stone-200 flex-1 max-w-md">
        <Search size={18} className="text-stone-400" />
        <input
          type="text"
          placeholder="Buscar servicio..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="bg-transparent border-none outline-none text-sm text-stone-700 placeholder:text-stone-400 w-full"
        />
      </div>

      {/* Services Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-white rounded-2xl p-6 border border-stone-100 animate-pulse">
              <div className="h-4 bg-stone-100 rounded w-24 mb-3" />
              <div className="h-3 bg-stone-100 rounded w-40 mb-2" />
              <div className="h-8 bg-stone-100 rounded w-20 mb-2" />
              <div className="h-3 bg-stone-100 rounded w-16" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredServices.map((service) => (
            <div
              key={service.id}
              className={`bg-white rounded-2xl p-6 border transition-all duration-300 ${
                service.activo ? 'border-stone-100 hover:shadow-lg hover:shadow-stone-100' : 'border-stone-100 opacity-70'
              }`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-50 to-teal-100 flex items-center justify-center">
                  <Tag size={22} className="text-emerald-600" />
                </div>
                <div className="flex gap-0.5">
                  {canManage && (
                    <>
                      <button
                        onClick={() => setEditingService(service)}
                        className="p-1.5 rounded-lg hover:bg-stone-100 text-stone-400 hover:text-stone-600 transition-colors"
                        title="Editar servicio"
                      >
                        <Edit size={14} />
                      </button>
                      <button
                        onClick={() => handleDelete(service.id)}
                        className="p-1.5 rounded-lg hover:bg-red-50 text-stone-400 hover:text-red-500 transition-colors"
                        title="Desactivar servicio"
                      >
                        <Trash2 size={14} />
                      </button>
                    </>
                  )}
                </div>
              </div>

              <h3 className="text-base font-semibold text-stone-800 mb-1">{service.nombre}</h3>
              <p className="text-sm text-stone-500 min-h-[2.5rem] mb-4">
                {service.descripcion || 'Sin descripción'}
              </p>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs text-stone-500">
                  <Clock size={13} />
                  <span>{service.duracion} min</span>
                </div>
                <span className="text-lg font-bold text-stone-800">{fmtMoney(service.precio)}</span>
              </div>

              <div className="flex items-center justify-between mt-4 pt-4 border-t border-stone-100">
                {service.activo ? (
                  <span className="inline-flex items-center gap-1 text-xs text-emerald-600">
                    <CheckCircle size={12} /> Activo
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs text-red-500">
                    <XCircle size={12} /> Inactivo
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {filteredServices.length === 0 && !loading && (
        <div className="text-center py-12 bg-white rounded-2xl border border-stone-100">
          <Tag size={48} className="mx-auto text-stone-300 mb-3" />
          <p className="text-stone-500">
            {canManage
              ? 'Aún no has creado servicios. Crea tu primer servicio para poder agendar citas.'
              : 'No se encontraron servicios'}
          </p>
        </div>
      )}

      {showCreateModal && (
        <CreateServiceModal
          onClose={() => setShowCreateModal(false)}
          onCreated={() => { setShowCreateModal(false); loadServices(); }}
        />
      )}

      {editingService && (
        <EditServiceModal
          service={editingService}
          onClose={() => setEditingService(null)}
          onUpdated={() => { setEditingService(null); loadServices(); }}
        />
      )}
    </div>
  );
}

// ============================================================
// Modal de Crear Servicio
// ============================================================
function CreateServiceModal({ onClose, onCreated }: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [formData, setFormData] = useState({
    nombre: '',
    descripcion: '',
    precio: '',
    duracion: '60',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const precio = parseFloat(formData.precio);
    const duracion = parseInt(formData.duracion, 10);
    if (isNaN(precio) || precio < 0) {
      setError('Ingresa un precio válido');
      return;
    }
    if (isNaN(duracion) || duracion < 5 || duracion > 1440) {
      setError('La duración debe estar entre 5 y 1440 minutos');
      return;
    }
    setLoading(true);
    try {
      const data: ServiceCreateInput = {
        nombre: formData.nombre,
        descripcion: formData.descripcion || null,
        precio,
        duracion,
      };
      await api.createService(data);
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al crear servicio');
      setLoading(false);
    }
  };

  const inputClass = "w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-stone-100">
          <h2 className="text-xl font-semibold text-stone-800">Nuevo Servicio</h2>
          <p className="text-sm text-stone-500 mt-1">Agrega un nuevo servicio al catálogo</p>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">{error}</div>
          )}
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Nombre *</label>
            <input
              type="text" required value={formData.nombre}
              onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
              className={inputClass} placeholder="Masaje relajante"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Descripción</label>
            <textarea
              rows={3} value={formData.descripcion}
              onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
              className={inputClass} placeholder="Descripción breve del servicio..."
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Precio *</label>
              <input
                type="number" required min={0} step="0.01" value={formData.precio}
                onChange={(e) => setFormData({ ...formData, precio: e.target.value })}
                className={inputClass} placeholder="0.00"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Duración (min) *</label>
              <input
                type="number" required min={5} max={1440} value={formData.duracion}
                onChange={(e) => setFormData({ ...formData, duracion: e.target.value })}
                className={inputClass} placeholder="60"
              />
            </div>
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
              {loading ? 'Creando...' : 'Crear Servicio'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ============================================================
// Modal de Editar Servicio
// ============================================================
function EditServiceModal({ service, onClose, onUpdated }: {
  service: Service;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [formData, setFormData] = useState({
    nombre: service.nombre,
    descripcion: service.descripcion || '',
    precio: String(service.precio),
    duracion: String(service.duracion),
    activo: service.activo,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const precio = parseFloat(formData.precio);
    const duracion = parseInt(formData.duracion, 10);
    if (isNaN(precio) || precio < 0) {
      setError('Ingresa un precio válido');
      return;
    }
    if (isNaN(duracion) || duracion < 5 || duracion > 1440) {
      setError('La duración debe estar entre 5 y 1440 minutos');
      return;
    }
    setLoading(true);
    try {
      const data: Partial<ServiceCreateInput> & { activo?: boolean } = {
        nombre: formData.nombre,
        descripcion: formData.descripcion || null,
        precio,
        duracion,
        activo: formData.activo,
      };
      await api.updateService(service.id, data);
      onUpdated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al actualizar servicio');
      setLoading(false);
    }
  };

  const inputClass = "w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-stone-100">
          <h2 className="text-xl font-semibold text-stone-800">Editar Servicio</h2>
          <p className="text-sm text-stone-500 mt-1">{service.nombre}</p>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">{error}</div>
          )}
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Nombre *</label>
            <input
              type="text" required value={formData.nombre}
              onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Descripción</label>
            <textarea
              rows={3} value={formData.descripcion}
              onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
              className={inputClass}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Precio *</label>
              <input
                type="number" required min={0} step="0.01" value={formData.precio}
                onChange={(e) => setFormData({ ...formData, precio: e.target.value })}
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Duración (min) *</label>
              <input
                type="number" required min={5} max={1440} value={formData.duracion}
                onChange={(e) => setFormData({ ...formData, duracion: e.target.value })}
                className={inputClass}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Estado</label>
            <select
              value={formData.activo ? '1' : '0'}
              onChange={(e) => setFormData({ ...formData, activo: e.target.value === '1' })}
              className={inputClass}
            >
              <option value="1">Activo</option>
              <option value="0">Inactivo</option>
            </select>
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