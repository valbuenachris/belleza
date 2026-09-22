// ============================================================
// Página de Tenants - Gestión de SPAs (Solo Superadmin)
// ============================================================

import React, { useState, useEffect } from 'react';
import { api, ApiError } from '../services/api';
import { Tenant, GlobalTenantStats } from '../types';
import {
  Building2, Plus, Search, MoreVertical, Edit, Trash2,
  CheckCircle, XCircle, Users, ArrowUpDown, AlertCircle,
  Lock, Mail, User, Check, Copy, Download, KeyRound,
  DollarSign, PauseCircle, PlayCircle, Layers, RefreshCw
} from 'lucide-react';

export default function TenantsPage() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [globalStats, setGlobalStats] = useState<GlobalTenantStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingTenant, setEditingTenant] = useState<Tenant | null>(null);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);

  useEffect(() => {
    loadTenants();
  }, []);

  const loadTenants = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getTenants();
      setTenants(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cargar los tenants');
    } finally {
      setLoading(false);
    }
    try {
      const stats = await api.getTenantGlobalStats();
      setGlobalStats(stats);
    } catch {
      // Métricas globales no disponibles
    }
  };

  const handleDelete = async (tenant: Tenant) => {
    if (!confirm(`¿Eliminar el SPA "${tenant.nombre}"? Esta acción no se puede deshacer.`)) return;
    setError('');
    try {
      await api.deleteTenant(tenant.id);
      loadTenants();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al eliminar el tenant');
    }
  };

  const handleToggleActive = async (tenant: Tenant) => {
    const suspender = tenant.activo;
    const ok = confirm(
      suspender
        ? `¿Suspender el SPA "${tenant.nombre}"? Sus usuarios no podrán iniciar sesión hasta que lo reactives.`
        : `¿Reactivar el SPA "${tenant.nombre}"? Sus usuarios volverán a tener acceso.`
    );
    if (!ok) return;
    setError('');
    try {
      await api.updateTenant(tenant.id, { activo: !tenant.activo });
      setSelectedTenant(null);
      await loadTenants();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al actualizar el estado del SPA');
    }
  };

  const handleRenew = async (tenant: Tenant) => {
    if (!confirm(`¿Renovar la suscripción de "${tenant.nombre}" por 30 días más?`)) return;
    setError('');
    try {
      await api.renewTenant(tenant.id);
      setSelectedTenant(null);
      await loadTenants();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al renovar la suscripción');
    }
  };

  const filteredTenants = tenants.filter(t =>
    t.nombre.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const planColors: Record<string, string> = {
    basic: 'bg-stone-100 text-stone-700',
    professional: 'bg-emerald-50 text-emerald-700',
    enterprise: 'bg-violet-50 text-violet-700',
  };
  const planLabels: Record<string, string> = {
    basic: 'Basic',
    professional: 'Professional',
    enterprise: 'Enterprise',
  };
  const planBarColors: Record<string, string> = {
    basic: 'bg-stone-400',
    professional: 'bg-emerald-500',
    enterprise: 'bg-violet-500',
  };

  const fmtFecha = (iso: string | null | undefined) => {
    if (!iso) return '—';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '—';
    return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const getSuscripcionInfo = (tenant: Tenant) => {
    if (!tenant.fecha_expiracion) {
      return { fecha: 'Sin expiración', chip: 'bg-stone-100 text-stone-500', label: 'Exenta' };
    }
    const d = new Date(tenant.fecha_expiracion);
    const dias = Math.ceil((d.getTime() - Date.now()) / 86400000);
    let chip = 'bg-emerald-50 text-emerald-700';
    let label = `Vence en ${dias} días`;
    if (dias < 0) {
      chip = 'bg-red-50 text-red-600';
      label = `Expirada (${Math.abs(dias)} d)`;
    } else if (dias === 0) {
      chip = 'bg-amber-50 text-amber-700';
      label = 'Vence hoy';
    } else if (dias <= 7) {
      chip = 'bg-amber-50 text-amber-700';
      label = `Vence en ${dias} día${dias === 1 ? '' : 's'}`;
    }
    return { fecha: fmtFecha(tenant.fecha_expiracion), chip, label, dias };
  };

  const mrr = globalStats?.mrr_estimado ?? 0;
  const distribucion = globalStats?.distribucion_planes || {};
  const totalPorPlan = Object.keys(planLabels).reduce((s, p) => s + (distribucion[p] || 0), 0);

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

      {error && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600 flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex items-center gap-2 bg-white rounded-xl px-4 py-2.5 border border-stone-200 flex-1 max-w-md">
          <Search size={18} className="text-stone-400" />
          <input
            type="text"
            placeholder="Buscar por nombre..."
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

      {/* KPIs globales de la plataforma */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="bg-white rounded-2xl p-5 border border-stone-100 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm text-stone-500">Total SPAs</p>
            <div className="w-9 h-9 rounded-xl bg-emerald-50 flex items-center justify-center">
              <Building2 size={18} className="text-emerald-600" />
            </div>
          </div>
          <p className="text-2xl font-bold text-stone-800 mt-2">{globalStats?.total_spas ?? 0}</p>
          <p className="text-xs text-stone-500 mt-1">
            <span className="text-emerald-600 font-medium">{globalStats?.activos ?? 0} activos</span>
            {' · '}
            <span className="text-red-500 font-medium">{globalStats?.inactivos ?? 0} suspendidos</span>
          </p>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-stone-100 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm text-stone-500">Usuarios Globales</p>
            <div className="w-9 h-9 rounded-xl bg-teal-50 flex items-center justify-center">
              <Users size={18} className="text-teal-600" />
            </div>
          </div>
          <p className="text-2xl font-bold text-stone-800 mt-2">{globalStats?.total_usuarios_globales ?? 0}</p>
          <p className="text-xs text-stone-500 mt-1">en toda la plataforma</p>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-stone-100 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm text-stone-500">MRR Estimado</p>
            <div className="w-9 h-9 rounded-xl bg-violet-50 flex items-center justify-center">
              <DollarSign size={18} className="text-violet-600" />
            </div>
          </div>
          <p className="text-2xl font-bold text-stone-800 mt-2">
            ${mrr.toLocaleString('en-US', { maximumFractionDigits: 0 })}
          </p>
          <p className="text-xs text-stone-500 mt-1">ingresos recurrentes / mes (SPAs activos)</p>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-stone-100 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm text-stone-500">Distribución por Planes</p>
            <div className="w-9 h-9 rounded-xl bg-amber-50 flex items-center justify-center">
              <Layers size={18} className="text-amber-600" />
            </div>
          </div>
          <div className="flex h-2.5 rounded-full overflow-hidden bg-stone-100 mt-3">
            {Object.keys(planLabels).map(p => (
              <div
                key={p}
                className={`${planBarColors[p]} transition-all`}
                style={{ width: totalPorPlan ? `${((distribucion[p] || 0) / totalPorPlan) * 100}%` : '0%' }}
              />
            ))}
          </div>
          <div className="flex flex-col gap-1 mt-3">
            {Object.keys(planLabels).map(p => (
              <div key={p} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-stone-600">
                  <span className={`w-2 h-2 rounded-full ${planBarColors[p]}`} />
                  {planLabels[p]}
                </span>
                <span className="font-medium text-stone-800">
                  {distribucion[p] || 0}
                  {totalPorPlan ? ` (${Math.round(((distribucion[p] || 0) / totalPorPlan) * 100)}%)` : ''}
                </span>
              </div>
            ))}
          </div>
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
                  <th className="text-left px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider">Plan</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider hidden lg:table-cell">Usuarios</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider">Estado</th>
                  <th className="text-left px-6 py-4 text-xs font-semibold text-stone-500 uppercase tracking-wider">Suscripción</th>
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
                          <XCircle size={14} /> Suspendido
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-stone-700">{getSuscripcionInfo(tenant).fecha}</div>
                      <div className={`mt-1 inline-flex px-2 py-0.5 text-[10px] font-medium rounded-full ${getSuscripcionInfo(tenant).chip}`}>
                        {getSuscripcionInfo(tenant).label}
                      </div>
                      <button
                        onClick={() => handleRenew(tenant)}
                        className="mt-1.5 inline-flex items-center gap-1 px-2 py-1 rounded-lg border border-teal-200 text-[10px] font-medium text-teal-600 hover:bg-teal-50 transition-colors"
                        title="Extender la suscripción 30 días"
                      >
                        <RefreshCw size={11} />
                        Renovar (+30 días)
                      </button>
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
                          onClick={() => setEditingTenant(tenant)}
                          className="p-2 rounded-lg hover:bg-emerald-50 text-stone-400 hover:text-emerald-600 transition-colors"
                          title="Editar"
                        >
                          <Edit size={16} />
                        </button>
                        <button
                          onClick={() => handleToggleActive(tenant)}
                          className={`p-2 rounded-lg transition-colors ${
                            tenant.activo
                              ? 'hover:bg-amber-50 text-stone-400 hover:text-amber-600'
                              : 'hover:bg-emerald-50 text-stone-400 hover:text-emerald-600'
                          }`}
                          title={tenant.activo ? 'Suspender SPA' : 'Reactivar SPA'}
                        >
                          {tenant.activo ? <PauseCircle size={16} /> : <PlayCircle size={16} />}
                        </button>
                        <button
                          onClick={() => handleDelete(tenant)}
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
          onRenew={handleRenew}
        />
      )}

      {/* Edit Modal */}
      {editingTenant && (
        <EditTenantModal
          tenant={editingTenant}
          onClose={() => setEditingTenant(null)}
          onUpdated={(updated?: Tenant) => {
            setEditingTenant(null);
            if (updated) {
              setTenants(prev => prev.map(t => (t.id === updated.id ? updated : t)));
            }
            loadTenants();
          }}
        />
      )}
    </div>
  );
}

// ============================================================
// Modal de Crear Tenant
// ============================================================
function CreateTenantModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    nombre: '',
    plan: 'basic' as const,
    email: '',
    telefono: '',
    direccion: '',
    adminNombre: '',
    adminApellido: '',
    adminEmail: '',
    adminPassword: '',
    adminConfirm: '',
    adminRol: 'admin' as const,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const passwordChecks = () => {
    const p = formData.adminPassword;
    return [
      { label: 'Mínimo 8 caracteres', ok: p.length >= 8 },
      { label: 'Una letra mayúscula', ok: /[A-Z]/.test(p) },
      { label: 'Una letra minúscula', ok: /[a-z]/.test(p) },
      { label: 'Un número', ok: /[0-9]/.test(p) },
      { label: 'Un carácter especial', ok: /[!@#$%^&*()_+\-=\[\]{}|;:',.<>?\/`~\\"]/.test(p) },
    ];
  };
  const passwordChecksList = passwordChecks();
  const passwordValid = passwordChecksList.every(c => c.ok);

  const validateStep1 = () => {
    return formData.nombre.length >= 2;
  };

  const validateStep2 = () => {
    return (
      formData.adminNombre.trim().length > 0 &&
      formData.adminApellido.trim().length > 0 &&
      formData.adminEmail.includes('@') &&
      passwordValid &&
      formData.adminPassword === formData.adminConfirm
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateStep2()) return;
    setError('');
    setLoading(true);
    try {
      await api.createTenant({
        nombre: formData.nombre,
        plan: formData.plan,
        email: formData.email || null,
        telefono: formData.telefono || null,
        direccion: formData.direccion || null,
        admin: {
          nombre: formData.adminNombre.trim(),
          apellido: formData.adminApellido.trim(),
          email: formData.adminEmail.trim().toLowerCase(),
          password: formData.adminPassword,
          rol: formData.adminRol,
        },
      });
      setStep(3);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al crear el SPA');
    } finally {
      setLoading(false);
    }
  };

  const inputClass = "w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400";

  const copyCredentials = async () => {
    const text = [
      `SPA: ${formData.nombre}`,
      `Usuario (admin): ${formData.adminNombre} ${formData.adminApellido}`,
      `Email: ${formData.adminEmail.trim().toLowerCase()}`,
      `Contraseña: ${formData.adminPassword}`,
    ].join('\n');
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: seleccionar el bloque de texto
    }
  };

  const downloadCredentials = () => {
    const fileBase = (formData.nombre || 'spa').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
    const text = [
      'Credenciales de Acceso — SPA Management System',
      '===============================================',
      `SPA: ${formData.nombre}`,
      '',
      'Cuenta de administrador',
      `Nombre: ${formData.adminNombre} ${formData.adminApellido}`,
      `Rol: ${formData.adminRol}`,
      `Email: ${formData.adminEmail.trim().toLowerCase()}`,
      `Contraseña temporal: ${formData.adminPassword}`,
      '',
      'Importante: cambia la contraseña tras el primer inicio de sesión en Configuración > Seguridad.',
    ].join('\n');
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `credenciales-${fileBase}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Vista de éxito con resumen de credenciales
  if (step === 3) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
        <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
          <div className="p-6 border-b border-stone-100 text-center">
            <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <CheckCircle size={28} className="text-emerald-600" />
            </div>
            <h2 className="text-xl font-semibold text-stone-800">SPA Creado Exitosamente</h2>
            <p className="text-sm text-stone-500 mt-1">{formData.nombre}</p>
          </div>
          <div className="p-6 space-y-4">
            <p className="text-sm text-stone-600">
              Se creó automáticamente la cuenta de administrador con las siguientes credenciales de acceso:
            </p>
            <div className="bg-stone-50 rounded-xl p-4 border border-stone-100 space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
                  <User size={16} className="text-emerald-600" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-stone-500">Administrador</p>
                  <p className="text-sm font-medium text-stone-800">{formData.adminNombre} {formData.adminApellido} <span className="text-stone-400 capitalize">({formData.adminRol})</span></p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
                  <Mail size={16} className="text-emerald-600" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-stone-500">Email de acceso</p>
                  <p className="text-sm font-medium text-stone-800 break-all">{formData.adminEmail.trim().toLowerCase()}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
                  <KeyRound size={16} className="text-emerald-600" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-stone-500">Contraseña temporal</p>
                  <p className="text-sm font-medium text-stone-800 break-all">{formData.adminPassword}</p>
                </div>
              </div>
            </div>
            <p className="text-xs text-stone-500">
              Guarda esta información. El administrador debe cambiar la contraseña en el primer inicio de sesión (Configuración → Seguridad).
            </p>
            <div className="flex gap-3 pt-2">
              <button
                onClick={downloadCredentials}
                className="inline-flex items-center justify-center gap-2 px-4 py-2.5 border border-stone-200 rounded-xl text-sm font-medium text-stone-600 hover:bg-stone-50"
              >
                <Download size={16} />
                Descargar
              </button>
              <button
                onClick={copyCredentials}
                className={`inline-flex items-center justify-center gap-2 px-4 py-2.5 border rounded-xl text-sm font-medium transition-all ${
                  copied
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                    : 'border-stone-200 text-stone-600 hover:bg-stone-50'
                }`}
              >
                {copied ? <CheckCircle size={16} /> : <Copy size={16} />}
                {copied ? 'Copiado' : 'Copiar'}
              </button>
              <button
                onClick={onCreated}
                className="flex-1 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 transition-all"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-stone-100">
          <h2 className="text-xl font-semibold text-stone-800">Registrar Nuevo SPA</h2>
          <p className="text-sm text-stone-500 mt-1">
            {step === 1 ? 'Completa los datos del negocio' : 'Crea la cuenta de administrador del SPA'}
          </p>
          <div className="flex items-center gap-2 mt-4">
            {[1, 2].map(s => (
              <React.Fragment key={s}>
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium transition-all ${
                  step >= s ? 'bg-emerald-500 text-white' : 'bg-stone-200 text-stone-500'
                }`}>
                  {s}
                </div>
                {s < 2 && <div className={`flex-1 h-0.5 ${step > s ? 'bg-emerald-500' : 'bg-stone-200'}`} />}
              </React.Fragment>
            ))}
          </div>
        </div>
        {step === 1 ? (
          <form onSubmit={(e) => { e.preventDefault(); setError(''); setStep(2); }} className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Nombre del SPA *</label>
              <input
                type="text"
                required
                value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                className={inputClass}
                placeholder="Ej: Serenity Spa & Wellness"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Plan</label>
              <select
                value={formData.plan}
                onChange={(e) => setFormData({ ...formData, plan: e.target.value as any })}
                className={inputClass}
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
                className={inputClass}
                placeholder="contacto@spa.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Teléfono</label>
              <input
                type="tel"
                value={formData.telefono}
                onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                className={inputClass}
                placeholder="+57 300 123 4567"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Dirección</label>
              <input
                type="text"
                value={formData.direccion}
                onChange={(e) => setFormData({ ...formData, direccion: e.target.value })}
                className={inputClass}
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
                disabled={!validateStep1()}
                className="flex-1 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 transition-all"
              >
                Continuar
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {error && (
              <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600 flex items-center gap-2">
                <AlertCircle size={15} />
                {error}
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">
                  <User size={13} className="inline mr-1" /> Nombre *
                </label>
                <input
                  type="text"
                  required
                  value={formData.adminNombre}
                  onChange={(e) => setFormData({ ...formData, adminNombre: e.target.value })}
                  className={inputClass}
                  placeholder="María"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">Apellido *</label>
                <input
                  type="text"
                  required
                  value={formData.adminApellido}
                  onChange={(e) => setFormData({ ...formData, adminApellido: e.target.value })}
                  className={inputClass}
                  placeholder="González"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">
                <Mail size={13} className="inline mr-1" /> Email de acceso *
              </label>
              <input
                type="email"
                required
                value={formData.adminEmail}
                onChange={(e) => setFormData({ ...formData, adminEmail: e.target.value })}
                className={inputClass}
                placeholder="admin@tu-spa.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">
                <Lock size={13} className="inline mr-1" /> Contraseña temporal *
              </label>
              <input
                type="password"
                required
                minLength={8}
                value={formData.adminPassword}
                onChange={(e) => setFormData({ ...formData, adminPassword: e.target.value })}
                className={inputClass}
                placeholder="Mínimo 8 caracteres"
              />
              {formData.adminPassword.length > 0 && (
                <div className="mt-2 space-y-1">
                  {passwordChecksList.map(check => (
                    <p key={check.label} className={`flex items-center gap-1.5 text-xs ${check.ok ? 'text-emerald-600' : 'text-stone-400'}`}>
                      {check.ok ? <Check size={12} className="shrink-0" /> : <XCircle size={12} className="shrink-0" />}
                      {check.label}
                    </p>
                  ))}
                </div>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Confirmar contraseña *</label>
              <input
                type="password"
                required
                value={formData.adminConfirm}
                onChange={(e) => setFormData({ ...formData, adminConfirm: e.target.value })}
                className={inputClass}
                placeholder="Repite la contraseña"
              />
              {formData.adminConfirm && formData.adminPassword !== formData.adminConfirm && (
                <p className="text-xs text-red-500 mt-1">Las contraseñas no coinciden</p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Rol inicial</label>
              <select
                value={formData.adminRol}
                onChange={(e) => setFormData({ ...formData, adminRol: e.target.value as any })}
                className={inputClass}
              >
                <option value="admin">Administrador</option>
                <option value="manager">Gerente</option>
              </select>
            </div>
            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={() => { setError(''); setStep(1); }}
                className="flex-1 py-2.5 border border-stone-200 rounded-xl text-sm font-medium text-stone-600 hover:bg-stone-50"
              >
                Atrás
              </button>
              <button
                type="submit"
                disabled={loading || !validateStep2()}
                className="flex-1 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 transition-all"
              >
                {loading ? 'Creando...' : 'Crear SPA'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

// ============================================================
// Modal de Detalle de Tenant
// ============================================================
function TenantDetailModal({ tenant, onClose, onRenew }: {
  tenant: Tenant;
  onClose: () => void;
  onRenew: (tenant: Tenant) => void;
}) {
  const expInfo = (() => {
    if (!tenant.fecha_expiracion) {
      return { fecha: 'Sin expiración', chip: 'bg-stone-100 text-stone-500', label: 'Exenta' };
    }
    const d = new Date(tenant.fecha_expiracion);
    const dias = Math.ceil((d.getTime() - Date.now()) / 86400000);
    let chip = 'bg-emerald-50 text-emerald-700';
    let label = `Vence en ${dias} días`;
    if (dias < 0) {
      chip = 'bg-red-50 text-red-600';
      label = 'Expirada';
    } else if (dias === 0) {
      chip = 'bg-amber-50 text-amber-700';
      label = 'Vence hoy';
    } else if (dias <= 7) {
      chip = 'bg-amber-50 text-amber-700';
      label = `Vence en ${dias} día${dias === 1 ? '' : 's'}`;
    }
    return {
      fecha: new Date(tenant.fecha_expiracion).toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' }),
      chip,
      label,
    };
  })();

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
              <p className="text-sm text-stone-500">{tenant.email || tenant.plan}</p>
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
                {tenant.activo ? 'Activo' : 'Suspendido'}
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
          <div className="border border-stone-100 rounded-xl p-4">
            <p className="text-xs text-stone-500 uppercase tracking-wider">Suscripción</p>
            <div className="flex items-center justify-between gap-3 mt-1.5">
              <div>
                <p className="text-sm font-medium text-stone-800">{expInfo.fecha}</p>
                <span className={`mt-1 inline-flex px-2 py-0.5 text-[10px] font-medium rounded-full ${expInfo.chip}`}>
                  {expInfo.label}
                </span>
              </div>
              <button
                onClick={() => onRenew(tenant)}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-teal-50 border border-teal-200 text-xs font-medium text-teal-700 hover:bg-teal-100 transition-colors"
              >
                <RefreshCw size={14} />
                Renovar (+30 días)
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Modal de Editar Tenant
// ============================================================
function EditTenantModal({ tenant, onClose, onUpdated }: {
  tenant: Tenant;
  onClose: () => void;
  onUpdated: (updated?: Tenant) => void;
}) {
  const [formData, setFormData] = useState({
    nombre: tenant.nombre,
    email: tenant.email || '',
    telefono: tenant.telefono || '',
    direccion: tenant.direccion || '',
    plan: tenant.plan,
    activo: tenant.activo,
    limite_usuarios: tenant.limite_usuarios,
    limite_pacientes: tenant.limite_pacientes,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const updated = await api.updateTenant(tenant.id, {
        ...formData,
        email: formData.email || null,
        telefono: formData.telefono || null,
        direccion: formData.direccion || null,
      });
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al actualizar el tenant');
      setLoading(false);
    }
  };

  const inputClass = "w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-stone-100">
          <h2 className="text-xl font-semibold text-stone-800">Editar SPA</h2>
          <p className="text-sm text-stone-500 mt-1">Configura los datos del SPA</p>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">{error}</div>
          )}
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Nombre del SPA *</label>
            <input
              type="text" required value={formData.nombre}
              onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
              className={inputClass}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Email de contacto</label>
              <input
                type="email" value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Teléfono</label>
              <input
                type="tel" value={formData.telefono}
                onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                className={inputClass}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Dirección</label>
            <input
              type="text" value={formData.direccion}
              onChange={(e) => setFormData({ ...formData, direccion: e.target.value })}
              className={inputClass}
            />
          </div>
          <div className="p-3 bg-stone-50 rounded-xl flex items-center justify-between gap-3">
            <div>
              <p className="text-xs text-stone-500">Suscripción expira el</p>
              <p className="text-sm font-medium text-stone-800">
                {tenant.fecha_expiracion
                  ? new Date(tenant.fecha_expiracion).toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' })
                  : 'Sin expiración (exenta)'}
              </p>
            </div>
            <span className="text-[10px] text-stone-400 text-right max-w-[140px]">
              Para extenderla usa "Renovar (+30 días)"
            </span>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Plan</label>
              <select
                value={formData.plan}
                onChange={(e) => setFormData({ ...formData, plan: e.target.value as Tenant['plan'] })}
                className={inputClass}
              >
                <option value="basic">Basic</option>
                <option value="professional">Professional</option>
                <option value="enterprise">Enterprise</option>
              </select>
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
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Límite de usuarios</label>
              <input
                type="number" min={1} value={formData.limite_usuarios}
                onChange={(e) => setFormData({ ...formData, limite_usuarios: parseInt(e.target.value) })}
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">Límite de pacientes</label>
              <input
                type="number" min={1} value={formData.limite_pacientes}
                onChange={(e) => setFormData({ ...formData, limite_pacientes: parseInt(e.target.value) })}
                className={inputClass}
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
              {loading ? 'Guardando...' : 'Guardar Cambios'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
