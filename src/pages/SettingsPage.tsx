// ============================================================
// Página de Configuración - Ajustes del tenant
// ============================================================

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  Settings as SettingsIcon, Building2, Clock, Globe,
  Save, CheckCircle, Bell, Palette, Shield
} from 'lucide-react';

export default function SettingsPage() {
  const { tenant, user } = useAuth();
  const [activeTab, setActiveTab] = useState('general');
  const [saved, setSaved] = useState(false);
  const [formData, setFormData] = useState({
    nombre: tenant?.nombre || '',
    email: tenant?.email || '',
    telefono: tenant?.telefono || '',
    direccion: tenant?.direccion || '',
    timezone: tenant?.timezone || 'America/Bogota',
    moneda: tenant?.moneda || 'USD',
    horarioApertura: tenant?.configuracion?.horario_apertura || '08:00',
    horarioCierre: tenant?.configuracion?.horario_cierre || '20:00',
    duracionCita: tenant?.configuracion?.duracion_cita_default || 60,
    recordatorioCitas: tenant?.configuracion?.recordatorio_citas ?? true,
    confirmacionCitas: tenant?.configuracion?.confirmacion_citas ?? true,
  });

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const tabs = [
    { id: 'general', label: 'General', icon: <Building2 size={16} /> },
    { id: 'schedule', label: 'Horarios', icon: <Clock size={16} /> },
    { id: 'notifications', label: 'Notificaciones', icon: <Bell size={16} /> },
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
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl
            hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-200/50 transition-all"
        >
          {saved ? <CheckCircle size={18} /> : <Save size={18} />}
          {saved ? 'Guardado' : 'Guardar Cambios'}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white rounded-xl p-1 border border-stone-200 overflow-x-auto">
        {tabs.map(tab => (
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
        {activeTab === 'general' && (
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
        )}

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
                {['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'].map((day, i) => (
                  <button
                    key={i}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      i < 6
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : 'bg-stone-50 text-stone-400 border border-stone-200'
                    }`}
                  >
                    {day}
                  </button>
                ))}
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

        {activeTab === 'security' && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-stone-800 mb-4">Seguridad</h3>
            <div className="space-y-4">
              <div className="p-4 bg-stone-50 rounded-xl">
                <p className="text-sm font-medium text-stone-700">Cambiar Contraseña</p>
                <p className="text-xs text-stone-500 mt-0.5 mb-3">Actualiza tu contraseña de acceso</p>
                <div className="space-y-3 max-w-sm">
                  <input
                    type="password"
                    placeholder="Contraseña actual"
                    className="w-full px-4 py-2.5 bg-white border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  />
                  <input
                    type="password"
                    placeholder="Nueva contraseña"
                    className="w-full px-4 py-2.5 bg-white border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  />
                  <button className="px-4 py-2 bg-stone-800 text-white text-sm font-medium rounded-lg hover:bg-stone-700 transition-colors">
                    Actualizar Contraseña
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
