// ============================================================
// Página de Tenants - Gestión de SPAs (Solo Superadmin)
// ============================================================

import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Tenant } from '../types';
import {
  Building2, Plus, Search, MoreVertical, Edit, Trash2,
  CheckCircle, XCircle, Globe, Users, Calendar, ArrowUpDown
} from 'lucide-react';

export default function TenantsPage() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);

  useEffect(() => {
    loadTenants();
  }, []);

  const loadTenants = async () => {
    try {
      const data = await api.getTenants();
      setTenants(data);
    } catch {
      // Error
    } finally {
      setLoading(false);
    }
  };

  const filteredTenants = tenants.filter(t =>
    t.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
    t.subdominio.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const planColors: Record<string, string> = {
    basic: 'bg-stone-100 text-stone-700',
    professional: 'bg-emerald-50 text-emerald-700',
    enterprise: 'bg-violet-50 text-violet-700',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-stone-800">SPAs / Tenants</h1>
          <p className="text-stone-500 mt-1">Gestiona todos los centros de estética registrados</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl
            hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-200/50 transition-all"
        >
          <Plus size={18} />
          Nuevo SPA
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex items-center gap-2 bg-white rounded-xl px-4 py-2.5 border border-stone-200 flex-1 max-w-md">
          <Search size={18} className="text-stone-400" />
          <input
            type="text"
            placeholder="Buscar por nombre o subdominio..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-none outline-none text-sm text-stone-700 placeholder:text-stone-400 w-full"
          />
        </div>
        <button className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border border-stone-200 rounded-xl text-sm text-stone-600 hover:bg-stone-50">
          <ArrowUpDown size={16} />
          Ordenar
        </button>
      </div>

      {/* Stats summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl p-4 border border-stone-100">
          <p className="text-sm text-stone-500">Total Tenants</p>
          <p className="text-2xl font-bold text-stone-800">{tenants.length}</p>
        </div>
        <div className="bg-white rounded-xl p-4 border border-stone-100">
          <p className="text-sm text-stone-500">Activos</p>
          <p className="text-2xl font-bold text-emerald-600">{tenants.filter(t => t.activo).length}</p>
        </div>
        <div className="bg-white rounded-xl p-4 border border-stone-100">
          <p className="text-sm text-stone-500">Plan Enterprise</p>
          <p className="text-2xl font-bold text-violet-600">{tenants.filter(t => t.plan === 'enterprise').length}</p>
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="bg-white rounded-2xl border border-stone-100 p-8 animate-pulse">
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-16 bg-stone-50 rounded-xl" />
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-stone-100 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-stone-100">
                  <th className="text-left px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider">SPA</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider hidden md:table-cell">Subdominio</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider">Plan</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider hidden lg:table-cell">Usuarios</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider">Estado</th>
                  <th className="text-right px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-50">
                {filteredTenants.map((tenant) => (
                  <tr key={tenant.id} className="hover:bg-stone-50/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-100 to-teal-100 flex items-center justify-center">
                          <Building2 size={18} className="text-emerald-600" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-stone-800">{tenant.nombre}</p>
                          <p className="text-xs text-stone-500">{tenant.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 hidden md:table-cell">
                      <div className="flex items-center gap-1.5 text-sm text-stone-600">
                        <Globe size={14} className="text-stone-400" />
                        {tenant.subdominio}.spasystem.com
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2.5 py-1 text-xs font-medium rounded-full capitalize ${planColors[tenant.plan]}`}>
                        {tenant.plan}
                      </span>
                    </td>
                    <td className="px-6 py-4 hidden lg:table-cell">
                      <div className="flex items-center gap-1.5 text-sm text-stone-600">
                        <Users size={14} className="text-stone-400" />
                        {tenant.estadisticas?.total_usuarios || 0} / {tenant.limite_usuarios}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {tenant.activo ? (
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600">
                          <CheckCircle size={14} /> Activo
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-red-500">
                          <XCircle size={14} /> Inactivo
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => setSelectedTenant(tenant)}
                          className="p-2 rounded-lg hover:bg-stone-100 text-stone-400 hover:text-stone-600 transition-colors"
                          title="Ver detalles"
                        >
                          <MoreVertical size={16} />
                        </button>
                        <button
                          className="p-2 rounded-lg hover:bg-emerald-50 text-stone-400 hover:text-emerald-600 transition-colors"
                          title="Editar"
                        >
                          <Edit size={16} />
                        </button>
                        <button
                          className="p-2 rounded-lg hover:bg-red-50 text-stone-400 hover:text-red-500 transition-colors"
                          title="Eliminar"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filteredTenants.length === 0 && (
            <div className="text-center py-12">
              <Building2 size={48} className="mx-auto text-stone-300 mb-3" />
              <p className="text-stone-500">No se encontraron SPAs</p>
            </div>
          )}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreateTenantModal
          onClose={() => setShowCreateModal(false)}
          onCreated={() => { setShowCreateModal(false); loadTenants(); }}
        />
      )}

      {/* Detail Modal */}
      {selectedTenant && (
        <TenantDetailModal
          tenant={selectedTenant}
          onClose={() => setSelectedTenant(null)}
        />
      )}
    </div>
  );
}

// ============================================================
// Modal de Crear Tenant
// ============================================================
function CreateTenantModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [formData, setFormData] = useState({
    nombre: '',
    subdominio: '',
    plan: 'basic' as const,
    email: '',
    telefono: '',
    direccion: '',
  });
  const [loading, setLoading] = useState(false);
  const [subdomainAvailable, setSubdomainAvailable] = useState<boolean | null>(null);

  const checkSubdomain = async (value: string) => {
    if (value.length < 3) { setSubdomainAvailable(null); return; }
    const available = await api.checkSubdomain(value);
    setSubdomainAvailable(available);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.createTenant(formData);
      onCreated();
    } catch {
      // Error
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-stone-100">
          <h2 className="text-xl font-semibold text-stone-800">Registrar Nuevo SPA</h2>
          <p className="text-sm text-stone-500 mt-1">Completa los datos para crear un nuevo tenant</p>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Nombre del SPA *</label>
            <input
              type="text"
              required
              value={formData.nombre}
              onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
              className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
              placeholder="Ej: Serenity Spa & Wellness"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Subdominio *</label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                required
                value={formData.subdominio}
                onChange={(e) => {
                  const val = e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '');
                  setFormData({ ...formData, subdominio: val });
                  checkSubdomain(val);
                }}
                className="flex-1 px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                placeholder="mi-spa"
              />
              <span className="text-sm text-stone-400">.spasystem.com</span>
            </div>
            {subdomainAvailable !== null && (
              <p className={`text-xs mt-1 ${subdomainAvailable ? 'text-emerald-600' : 'text-red-500'}`}>
                {subdomainAvailable ? '✓ Subdominio disponible' : '✗ Subdominio no disponible'}
              </p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Plan</label>
            <select
              value={formData.plan}
              onChange={(e) => setFormData({ ...formData, plan: e.target.value as any })}
              className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
            >
              <option value="basic">Basic - $29/mes</option>
              <option value="professional">Professional - $79/mes</option>
              <option value="enterprise">Enterprise - $199/mes</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Email de contacto</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
              placeholder="contacto@spa.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Teléfono</label>
            <input
              type="tel"
              value={formData.telefono}
              onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
              className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
              placeholder="+57 300 123 4567"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Dirección</label>
            <input
              type="text"
              value={formData.direccion}
              onChange={(e) => setFormData({ ...formData, direccion: e.target.value })}
              className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
              placeholder="Calle 100 #15-20, Ciudad"
            />
          </div>
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 border border-stone-200 rounded-xl text-sm font-medium text-stone-600 hover:bg-stone-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || subdomainAvailable === false}
              className="flex-1 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 transition-all"
            >
              {loading ? 'Creando...' : 'Crear SPA'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ============================================================
// Modal de Detalle de Tenant
// ============================================================
function TenantDetailModal({ tenant, onClose }: { tenant: Tenant; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg">
        <div className="p-6 border-b border-stone-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-100 to-teal-100 flex items-center justify-center">
              <Building2 size={22} className="text-emerald-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-stone-800">{tenant.nombre}</h2>
              <p className="text-sm text-stone-500">{tenant.subdominio}.spasystem.com</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-stone-100 text-stone-400">✕</button>
        </div>
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-stone-500 uppercase tracking-wider">Plan</p>
              <p className="text-sm font-medium text-stone-800 capitalize mt-0.5">{tenant.plan}</p>
            </div>
            <div>
              <p className="text-xs text-stone-500 uppercase tracking-wider">Estado</p>
              <p className={`text-sm font-medium mt-0.5 ${tenant.activo ? 'text-emerald-600' : 'text-red-500'}`}>
                {tenant.activo ? 'Activo' : 'Inactivo'}
              </p>
            </div>
            <div>
              <p className="text-xs text-stone-500 uppercase tracking-wider">Usuarios</p>
              <p className="text-sm font-medium text-stone-800 mt-0.5">
                {tenant.estadisticas?.total_usuarios || 0} / {tenant.limite_usuarios}
              </p>
            </div>
            <div>
              <p className="text-xs text-stone-500 uppercase tracking-wider">Pacientes</p>
              <p className="text-sm font-medium text-stone-800 mt-0.5">
                {tenant.estadisticas?.total_pacientes || 0} / {tenant.limite_pacientes}
              </p>
            </div>
            <div>
              <p className="text-xs text-stone-500 uppercase tracking-wider">Zona Horaria</p>
              <p className="text-sm font-medium text-stone-800 mt-0.5">{tenant.timezone}</p>
            </div>
            <div>
              <p className="text-xs text-stone-500 uppercase tracking-wider">Moneda</p>
              <p className="text-sm font-medium text-stone-800 mt-0.5">{tenant.moneda}</p>
            </div>
          </div>
          {tenant.direccion && (
            <div>
              <p className="text-xs text-stone-500 uppercase tracking-wider">Dirección</p>
              <p className="text-sm text-stone-700 mt-0.5">{tenant.direccion}</p>
            </div>
          )}
          <div>
            <p className="text-xs text-stone-500 uppercase tracking-wider">Fecha de Creación</p>
            <p className="text-sm text-stone-700 mt-0.5">
              {new Date(tenant.fecha_creacion).toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' })}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
