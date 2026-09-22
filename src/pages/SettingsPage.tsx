// ============================================================
// Página de Configuración - Ajustes del tenant
// ============================================================

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { api, ApiError } from '../services/api';
import { Tenant } from '../types';
import {
  Settings as SettingsIcon, Building2, Clock, Globe,
  Save, CheckCircle, Bell, Palette, Shield, AlertCircle, Star
} from 'lucide-react';

export default function SettingsPage() {
  const { tenant, updateTenant, user } = useAuth();
  // Solo admin/manager del tenant pueden configurar el programa de lealtad.
  const canManageLoyalty = ['admin', 'manager'].includes(user?.rol ?? '');
  const [activeTab, setActiveTab] = useState('general');
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [saving, setSaving] = useState(false);
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [formData, setFormData] = useState({
    nombre: tenant?.nombre || '',
    email: tenant?.email || '',
    telefono: tenant?.telefono || '',
    direccion: tenant?.direccion || '',
    timezone: tenant?.timezone || 'America/Bogota',
    moneda: tenant?.moneda || 'USD',
    horarioApertura: tenant?.configuracion?.horario_apertura || '08:00',
    horarioCierre: tenant?.configuracion?.horario_cierre || '20:00',
    diasOperacion: tenant?.configuracion?.dias_operacion || [1, 2, 3, 4, 5, 6],
    duracionCita: tenant?.configuracion?.duracion_cita_default ?? 60,
    recordatorioCitas: tenant?.configuracion?.recordatorio_citas ?? true,
    confirmacionCitas: tenant?.configuracion?.confirmacion_citas ?? true,
    puntosMeta: tenant?.puntos_meta ?? 10,
    premioFidelidad: tenant?.premio_fidelidad || 'Sesión de Spa gratis',
    tarjetaColorHex: tenant?.tarjeta_color_hex || '#0D9488',
  });

  // Vuelca el tenant (contexto/auth) sobre el formulario para que los campos
  // siempre muestren la configuración guardada y nunca queden en blanco.
  const applyTenantToForm = useCallback((t: Tenant | null) => {
    if (!t) return;
    const cfg = t.configuracion;
    setFormData((prev) => ({
      nombre: t.nombre || prev.nombre,
      email: t.email || prev.email,
      telefono: t.telefono || prev.telefono,
      direccion: t.direccion || prev.direccion,
      timezone: t.timezone || prev.timezone,
      moneda: t.moneda || prev.moneda,
      horarioApertura: cfg?.horario_apertura || '08:00',
      horarioCierre: cfg?.horario_cierre || '20:00',
      diasOperacion:
        Array.isArray(cfg?.dias_operacion) && cfg!.dias_operacion.length
          ? cfg!.dias_operacion
          : [1, 2, 3, 4, 5, 6],
      duracionCita: cfg?.duracion_cita_default ?? 60,
      recordatorioCitas: cfg?.recordatorio_citas ?? true,
      confirmacionCitas: cfg?.confirmacion_citas ?? true,
      puntosMeta: t.puntos_meta ?? 10,
      premioFidelidad: t.premio_fidelidad || 'Sesión de Spa gratis',
      tarjetaColorHex: t.tarjeta_color_hex || '#0D9488',
    }));
  }, []);

  // Reconcilia el formulario cada vez que llega/actualiza el tenant en el contexto.
  useEffect(() => {
    applyTenantToForm(tenant);
  }, [tenant, applyTenantToForm]);

  // Refresco best-effort una sola vez por tenant: si el usuario (o el contexto)
  // no trae la configuración, se intenta leer GET /tenants/{id}. Es silencioso:
  // los admins normales reciben 403 y se queda la configuración del contexto.
  const fetchedTenantRef = useRef<string | null>(null);
  useEffect(() => {
    if (!tenant) return;
    if (fetchedTenantRef.current === tenant.id) return;
    fetchedTenantRef.current = tenant.id;
    api
      .getTenantById(tenant.id)
      .then((t) => {
        if (t) {
          updateTenant(t);
          applyTenantToForm(t);
        }
      })
      .catch(() => {
        // Sin permisos (403) o errores de red: usar el tenant del contexto.
      });
  }, [tenant, applyTenantToForm, updateTenant]);

  const handleSave = async () => {
    if (!tenant) return;
    setSaveError('');
    setSaving(true);
    try {
      const updated = await api.updateTenant(tenant.id, {
        nombre: formData.nombre,
        email: formData.email || null,
        telefono: formData.telefono || null,
        direccion: formData.direccion || null,
        timezone: formData.timezone,
        moneda: formData.moneda,
        configuracion: {
          horario_apertura: formData.horarioApertura,
          horario_cierre: formData.horarioCierre,
          dias_operacion: formData.diasOperacion,
          duracion_cita_default: formData.duracionCita,
          recordatorio_citas: formData.recordatorioCitas,
          confirmacion_citas: formData.confirmacionCitas,
        },
        puntos_meta: formData.puntosMeta,
        premio_fidelidad: formData.premioFidelidad,
        tarjeta_color_hex: formData.tarjetaColorHex,
      });
      updateTenant(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : 'Error al guardar la configuración');
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    setPasswordMessage('');
    setPasswordError('');
    if (!passwordData.currentPassword || !passwordData.newPassword) {
      setPasswordError('Ingresa tu contraseña actual y la nueva contraseña');
      return;
    }
    if (passwordData.newPassword.length < 8) {
      setPasswordError('La nueva contraseña debe tener al menos 8 caracteres');
      return;
    }
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setPasswordError('La confirmación no coincide con la nueva contraseña');
      return;
    }
    setPasswordLoading(true);
    try {
      const res = await api.changePassword(passwordData.currentPassword, passwordData.newPassword);
      setPasswordMessage(res.message || 'Contraseña actualizada exitosamente');
      setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
    } catch (err) {
      setPasswordError(err instanceof ApiError ? err.message : 'Error al actualizar la contraseña');
    } finally {
      setPasswordLoading(false);
    }
  };

  const tabs = [
    { id: 'general', label: 'General', icon: <Building2 size={16} /> },
    { id: 'schedule', label: 'Horarios', icon: <Clock size={16} /> },
    { id: 'notifications', label: 'Notificaciones', icon: <Bell size={16} /> },
    { id: 'loyalty', label: 'Programa de Lealtad', icon: <Star size={16} /> },
    { id: 'security', label: 'Seguridad', icon: <Shield size={16} /> },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-stone-800">Configuración</h1>
          <p className="text-stone-500 mt-1">Personaliza tu centro de estética</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving || !tenant}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl
            hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-200/50 transition-all disabled:opacity-50"
        >
          {saved ? <CheckCircle size={18} /> : <Save size={18} />}
          {saved ? 'Guardado' : saving ? 'Guardando...' : 'Guardar Cambios'}
        </button>
      </div>

      {saveError && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600 flex items-center gap-2">
          <AlertCircle size={16} />
          {saveError}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-white rounded-xl p-1 border border-stone-200 overflow-x-auto">
        {tabs.filter(tab => tab.id !== 'loyalty' || canManageLoyalty).map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-emerald-50 text-emerald-700'
                : 'text-stone-500 hover:text-stone-700 hover:bg-stone-50'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="bg-white rounded-2xl border border-stone-100 p-6 lg:p-8">
        {activeTab === 'general' || (activeTab === 'loyalty' && !canManageLoyalty) ? (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-stone-800 mb-4">Información General</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-stone-700 mb-1.5">Nombre del SPA</label>
                  <input
                    type="text"
                    value={formData.nombre}
                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                    className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-stone-700 mb-1.5">Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-stone-700 mb-1.5">Teléfono</label>
                  <input
                    type="tel"
                    value={formData.telefono}
                    onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                    className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-stone-700 mb-1.5">Dirección</label>
                  <input
                    type="text"
                    value={formData.direccion}
                    onChange={(e) => setFormData({ ...formData, direccion: e.target.value })}
                    className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-stone-700 mb-1.5">
                    <Globe size={14} className="inline mr-1" /> Zona Horaria
                  </label>
                  <select
                    value={formData.timezone}
                    onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                    className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  >
                    <option value="America/Bogota">America/Bogota (UTC-5)</option>
                    <option value="America/Mexico_City">America/Mexico_City (UTC-6)</option>
                    <option value="America/Lima">America/Lima (UTC-5)</option>
                    <option value="America/Buenos_Aires">America/Buenos_Aires (UTC-3)</option>
                    <option value="America/Santiago">America/Santiago (UTC-4)</option>
                    <option value="Europe/Madrid">Europe/Madrid (UTC+1)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-stone-700 mb-1.5">Moneda</label>
                  <select
                    value={formData.moneda}
                    onChange={(e) => setFormData({ ...formData, moneda: e.target.value })}
                    className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  >
                    <option value="USD">USD - Dólar</option>
                    <option value="COP">COP - Peso Colombiano</option>
                    <option value="MXN">MXN - Peso Mexicano</option>
                    <option value="EUR">EUR - Euro</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {activeTab === 'schedule' && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-stone-800 mb-4">Horarios de Operación</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1.5">Hora de Apertura</label>
                <input
                  type="time"
                  value={formData.horarioApertura}
                  onChange={(e) => setFormData({ ...formData, horarioApertura: e.target.value })}
                  className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1.5">Hora de Cierre</label>
                <input
                  type="time"
                  value={formData.horarioCierre}
                  onChange={(e) => setFormData({ ...formData, horarioCierre: e.target.value })}
                  className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1.5">Duración Default de Cita (min)</label>
                <input
                  type="number"
                  value={formData.duracionCita}
                  onChange={(e) => setFormData({ ...formData, duracionCita: parseInt(e.target.value) })}
                  className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-stone-700 mb-3">Días de Operación</label>
              <div className="flex flex-wrap gap-2">
                {['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'].map((day, i) => {
                  const isActive = formData.diasOperacion.includes(i + 1);
                  return (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setFormData({
                        ...formData,
                        diasOperacion: isActive
                          ? formData.diasOperacion.filter(d => d !== i + 1)
                          : [...formData.diasOperacion, i + 1].sort(),
                      })}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                        isActive
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-stone-50 text-stone-400 border border-stone-200'
                      }`}
                    >
                      {day}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'notifications' && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-stone-800 mb-4">Preferencias de Notificación</h3>
            <div className="space-y-4">
              {[
                { label: 'Recordatorio de citas', desc: 'Enviar recordatorio 24h antes de la cita', key: 'recordatorioCitas' },
                { label: 'Confirmación de citas', desc: 'Solicitar confirmación al paciente', key: 'confirmacionCitas' },
              ].map(item => (
                <div key={item.key} className="flex items-center justify-between p-4 bg-stone-50 rounded-xl">
                  <div>
                    <p className="text-sm font-medium text-stone-700">{item.label}</p>
                    <p className="text-xs text-stone-500 mt-0.5">{item.desc}</p>
                  </div>
                  <button
                    onClick={() => setFormData({ ...formData, [item.key]: !(formData as any)[item.key] })}
                    className={`w-12 h-6 rounded-full transition-all ${
                      (formData as any)[item.key] ? 'bg-emerald-500' : 'bg-stone-300'
                    }`}
                  >
                    <div className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                      (formData as any)[item.key] ? 'translate-x-6' : 'translate-x-0.5'
                    }`} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'loyalty' && canManageLoyalty && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-stone-800 mb-1">Programa de Lealtad</h3>
              <p className="text-sm text-stone-500 mb-5">
                Personaliza las estrellas, el premio y la tarjeta de fidelidad que ven tus pacientes.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-stone-700 mb-1.5">
                    Estrellas meta (puntos_meta)
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={formData.puntosMeta}
                    onChange={(e) => {
                      const v = parseInt(e.target.value);
                      setFormData({ ...formData, puntosMeta: Number.isNaN(v) ? 1 : Math.max(1, v) });
                    }}
                    className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  />
                  <p className="text-xs text-stone-400 mt-1.5">
                    Estrellas necesarias para ganar una sesión gratuita.
                  </p>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-stone-700 mb-1.5">
                    Premio de fidelidad
                  </label>
                  <input
                    type="text"
                    value={formData.premioFidelidad}
                    onChange={(e) => setFormData({ ...formData, premioFidelidad: e.target.value })}
                    className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  />
                  <p className="text-xs text-stone-400 mt-1.5">
                    Se muestra como mensaje al alcanzar la meta y en el pase digital.
                  </p>
                </div>
                <div className="md:col-span-3">
                  <label className="block text-sm font-medium text-stone-700 mb-1.5">
                    <Palette size={14} className="inline mr-1" /> Color de la tarjeta de fidelidad
                  </label>
                  <div className="flex items-center gap-3">
                    <input
                      type="color"
                      value={/^#[0-9A-Fa-f]{6}$/.test(formData.tarjetaColorHex) ? formData.tarjetaColorHex : '#0D9488'}
                      onChange={(e) => setFormData({ ...formData, tarjetaColorHex: e.target.value })}
                      className="w-12 h-12 rounded-xl border border-stone-200 bg-white cursor-pointer p-1"
                    />
                    <input
                      type="text"
                      value={formData.tarjetaColorHex}
                      maxLength={9}
                      onChange={(e) => setFormData({ ...formData, tarjetaColorHex: e.target.value })}
                      className="w-40 px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm uppercase focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                    />
                    <div
                      className="w-24 h-12 rounded-xl border border-stone-200 flex items-center justify-center text-white text-xs font-semibold"
                      style={{ backgroundColor: /^#[0-9A-Fa-f]{6}$/.test(formData.tarjetaColorHex) ? formData.tarjetaColorHex : '#0D9488' }}
                    >
                      <Star size={14} className="mr-1" /> vista previa
                    </div>
                  </div>
                  <p className="text-xs text-stone-400 mt-1.5">
                    Color de fondo del pase digital (.pkpass) de la tarjeta de fidelidad.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'security' && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-stone-800 mb-4">Seguridad</h3>
            <div className="space-y-4">
              <div className="p-4 bg-stone-50 rounded-xl">
                <p className="text-sm font-medium text-stone-700">Cambiar Contraseña</p>
                <p className="text-xs text-stone-500 mt-0.5 mb-3">Actualiza tu contraseña de acceso</p>
                {passwordError && (
                  <div className="p-3 mb-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600 flex items-center gap-2">
                    <AlertCircle size={15} />
                    {passwordError}
                  </div>
                )}
                {passwordMessage && (
                  <div className="p-3 mb-3 bg-emerald-50 border border-emerald-100 rounded-xl text-sm text-emerald-700 flex items-center gap-2">
                    <CheckCircle size={15} />
                    {passwordMessage}
                  </div>
                )}
                <div className="space-y-3 max-w-sm">
                  <input
                    type="password"
                    placeholder="Contraseña actual"
                    value={passwordData.currentPassword}
                    onChange={(e) => setPasswordData({ ...passwordData, currentPassword: e.target.value })}
                    className="w-full px-4 py-2.5 bg-white border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  />
                  <input
                    type="password"
                    placeholder="Nueva contraseña"
                    value={passwordData.newPassword}
                    onChange={(e) => setPasswordData({ ...passwordData, newPassword: e.target.value })}
                    className="w-full px-4 py-2.5 bg-white border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  />
                  <input
                    type="password"
                    placeholder="Confirmar nueva contraseña"
                    value={passwordData.confirmPassword}
                    onChange={(e) => setPasswordData({ ...passwordData, confirmPassword: e.target.value })}
                    className="w-full px-4 py-2.5 bg-white border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  />
                  <button
                    onClick={handleChangePassword}
                    disabled={passwordLoading}
                    className="px-4 py-2 bg-stone-800 text-white text-sm font-medium rounded-lg hover:bg-stone-700 transition-colors disabled:opacity-50"
                  >
                    {passwordLoading ? 'Actualizando...' : 'Actualizar Contraseña'}
                  </button>
                </div>
              </div>
              <div className="p-4 bg-stone-50 rounded-xl">
                <p className="text-sm font-medium text-stone-700">Sesiones Activas</p>
                <p className="text-xs text-stone-500 mt-0.5">
                  Tu sesión actual está activa desde este dispositivo.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
