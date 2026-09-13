// ============================================================
// Página de Registro - Crear cuenta de nuevo SPA
// ============================================================

import React, { useState } from 'react';
import { Sparkles, Building2, Globe, Mail, Lock, Loader2, CheckCircle, ArrowLeft } from 'lucide-react';
import { api } from '../services/api';

interface RegisterPageProps {
  onBack: () => void;
}

export default function RegisterPage({ onBack }: RegisterPageProps) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    spaName: '',
    subdomain: '',
    adminEmail: '',
    adminPassword: '',
    confirmPassword: '',
    phone: '',
    address: '',
    plan: 'basic',
  });
  const [subdomainAvailable, setSubdomainAvailable] = useState<boolean | null>(null);

  const checkSubdomain = async (value: string) => {
    if (value.length < 3) { setSubdomainAvailable(null); return; }
    const available = await api.checkSubdomain(value);
    setSubdomainAvailable(available);
  };

  const validateStep1 = () => {
    return formData.spaName.length >= 3 && formData.subdomain.length >= 3 && subdomainAvailable === true;
  };

  const validateStep2 = () => {
    return (
      formData.adminEmail.includes('@') &&
      formData.adminPassword.length >= 8 &&
      formData.adminPassword === formData.confirmPassword
    );
  };

  const handleSubmit = async () => {
    setError('');
    setLoading(true);
    try {
      await api.registerSpa(
        formData.spaName,
        formData.subdomain,
        formData.adminEmail,
        formData.adminPassword
      );
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || 'Error al registrar el SPA');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-stone-50 via-white to-emerald-50/30 flex items-center justify-center p-4">
        <div className="w-full max-w-md text-center">
          <div className="bg-white rounded-2xl shadow-xl border border-stone-100 p-8">
            <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle size={32} className="text-emerald-600" />
            </div>
            <h2 className="text-2xl font-bold text-stone-800 mb-2">¡Registro Exitoso!</h2>
            <p className="text-stone-500 mb-6">
              Tu SPA <strong>{formData.spaName}</strong> ha sido registrado correctamente.
              Ya puedes acceder con tu cuenta de administrador.
            </p>
            <div className="bg-stone-50 rounded-xl p-4 mb-6 text-left">
              <p className="text-xs text-stone-500 mb-1">Tu URL de acceso:</p>
              <p className="text-sm font-medium text-emerald-600">{formData.subdomain}.spasystem.com</p>
            </div>
            <button
              onClick={onBack}
              className="w-full py-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 transition-all"
            >
              Ir al Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-stone-50 via-white to-emerald-50/30 flex items-center justify-center p-4">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-emerald-100/40 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-teal-100/30 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-lg relative">
        {/* Back button */}
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 text-sm text-stone-500 hover:text-stone-700 mb-6 transition-colors"
        >
          <ArrowLeft size={16} />
          Volver al login
        </button>

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-gradient-to-br from-emerald-400 to-teal-600 rounded-2xl shadow-lg shadow-emerald-200/50 mb-3">
            <Sparkles size={24} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-stone-800">Registra tu SPA</h1>
          <p className="text-stone-500 mt-1 text-sm">Configura tu centro de estética en minutos</p>
        </div>

        {/* Progress */}
        <div className="flex items-center justify-center gap-3 mb-8">
          {[1, 2].map(s => (
            <React.Fragment key={s}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all ${
                step >= s ? 'bg-emerald-500 text-white' : 'bg-stone-200 text-stone-500'
              }`}>
                {s}
              </div>
              {s < 2 && <div className={`w-16 h-0.5 ${step > s ? 'bg-emerald-500' : 'bg-stone-200'}`} />}
            </React.Fragment>
          ))}
        </div>

        {/* Form card */}
        <div className="bg-white rounded-2xl shadow-xl border border-stone-100 p-8">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">
              {error}
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-stone-800 mb-4">Datos de tu SPA</h2>
              
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1.5">
                  <Building2 size={14} className="inline mr-1.5" />
                  Nombre del SPA *
                </label>
                <input
                  type="text"
                  required
                  value={formData.spaName}
                  onChange={(e) => setFormData({ ...formData, spaName: e.target.value })}
                  className="w-full px-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  placeholder="Ej: Serenity Spa & Wellness"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1.5">
                  <Globe size={14} className="inline mr-1.5" />
                  Subdominio *
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    required
                    value={formData.subdomain}
                    onChange={(e) => {
                      const val = e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '');
                      setFormData({ ...formData, subdomain: val });
                      checkSubdomain(val);
                    }}
                    className="flex-1 px-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                    placeholder="mi-spa"
                  />
                  <span className="text-sm text-stone-400 whitespace-nowrap">.spasystem.com</span>
                </div>
                {subdomainAvailable !== null && (
                  <p className={`text-xs mt-1.5 ${subdomainAvailable ? 'text-emerald-600' : 'text-red-500'}`}>
                    {subdomainAvailable ? '✓ Subdominio disponible' : '✗ Subdominio no disponible'}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1.5">Plan</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { value: 'basic', label: 'Basic', price: '$29/mes' },
                    { value: 'professional', label: 'Pro', price: '$79/mes' },
                    { value: 'enterprise', label: 'Enterprise', price: '$199/mes' },
                  ].map(plan => (
                    <button
                      key={plan.value}
                      type="button"
                      onClick={() => setFormData({ ...formData, plan: plan.value })}
                      className={`p-3 rounded-xl border text-center transition-all ${
                        formData.plan === plan.value
                          ? 'border-emerald-400 bg-emerald-50 ring-2 ring-emerald-500/20'
                          : 'border-stone-200 hover:border-stone-300'
                      }`}
                    >
                      <p className="text-sm font-medium text-stone-800">{plan.label}</p>
                      <p className="text-xs text-stone-500">{plan.price}</p>
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={() => setStep(2)}
                disabled={!validateStep1()}
                className="w-full py-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all mt-6"
              >
                Continuar
              </button>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-stone-800 mb-4">Cuenta de Administrador</h2>
              
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1.5">
                  <Mail size={14} className="inline mr-1.5" />
                  Email del administrador *
                </label>
                <input
                  type="email"
                  required
                  value={formData.adminEmail}
                  onChange={(e) => setFormData({ ...formData, adminEmail: e.target.value })}
                  className="w-full px-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  placeholder="admin@tu-spa.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1.5">
                  <Lock size={14} className="inline mr-1.5" />
                  Contraseña *
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={formData.adminPassword}
                  onChange={(e) => setFormData({ ...formData, adminPassword: e.target.value })}
                  className="w-full px-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  placeholder="Mínimo 8 caracteres"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1.5">Confirmar contraseña *</label>
                <input
                  type="password"
                  required
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                  className="w-full px-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400"
                  placeholder="Repite la contraseña"
                />
                {formData.confirmPassword && formData.adminPassword !== formData.confirmPassword && (
                  <p className="text-xs text-red-500 mt-1">Las contraseñas no coinciden</p>
                )}
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => setStep(1)}
                  className="flex-1 py-3 border border-stone-200 rounded-xl text-sm font-medium text-stone-600 hover:bg-stone-50"
                >
                  Atrás
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={!validateStep2() || loading}
                  className="flex-1 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      Registrando...
                    </>
                  ) : (
                    'Crear mi SPA'
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
