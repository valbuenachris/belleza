// ============================================================
// PublicWalletPage - Página pública de la tarjeta de fidelidad
// Ruta /tarjeta/{token} (SIN autenticación). El token es la única
// credencial; solo se muestran datos de marca y progreso.
// ============================================================

import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, Apple, Loader2, RefreshCw, Smartphone, Star } from 'lucide-react';
import { api, ApiError } from '../services/api';
import { PublicWalletInfo } from '../types';

interface PublicWalletPageProps {
  token: string;
}

export default function PublicWalletPage({ token }: PublicWalletPageProps) {
  const [info, setInfo] = useState<PublicWalletInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState<'apple' | 'google' | null>(null);
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setInfo(await api.getPublicWalletInfo(token));
    } catch (err) {
      const expired = err instanceof ApiError && err.status === 404;
      setError(
        expired
          ? 'Este enlace expiró o no es válido. Pide a tu SPA que te comparta uno nuevo.'
          : 'No se pudo cargar la tarjeta. Revisa tu conexión e inténtalo de nuevo.',
      );
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const handleApple = async () => {
    setBusy('apple');
    setMessage('');
    try {
      await api.downloadPublicPkpass(token);
      setMessage('Pase descargado. Ábrelo para añadirlo a tu Apple Wallet.');
    } catch {
      setMessage('No se pudo descargar el pase de Apple Wallet. Inténtalo de nuevo.');
    } finally {
      setBusy(null);
    }
  };

  const handleGoogle = async () => {
    setBusy('google');
    setMessage('');
    try {
      const res = await api.getPublicGoogleWalletLink(token);
      if (res.enabled && res.save_url) {
        window.open(res.save_url, '_blank', 'noopener,noreferrer');
      } else {
        setMessage(
          'La integración con Google Wallet aún no está configurada por el administrador.',
        );
      }
    } catch {
      setMessage('No se pudo generar el enlace de Google Wallet. Inténtalo de nuevo.');
    } finally {
      setBusy(null);
    }
  };

  const color = info?.tarjeta_color_hex || '#0D9488';
  const pct =
    info && info.puntos_meta > 0
      ? Math.min(100, Math.round((info.puntos_actuales / info.puntos_meta) * 100))
      : 0;

  return (
    <div className="min-h-screen bg-stone-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl overflow-hidden">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 text-stone-400">
            <Loader2 size={28} className="animate-spin mb-3" />
            <p className="text-sm">Cargando tu tarjeta...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
            <AlertCircle size={32} className="text-amber-500 mb-3" />
            <p className="text-stone-700 text-sm mb-5">{error}</p>
            <button
              onClick={load}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-stone-800 text-white text-sm font-medium hover:bg-stone-900 transition-colors"
            >
              <RefreshCw size={15} /> Reintentar
            </button>
          </div>
        ) : info ? (
          <>
            {/* Cabecera con el color de la tarjeta del SPA */}
            <div
              className="px-6 pt-8 pb-6 text-center text-white"
              style={{ backgroundColor: color }}
            >
              {info.tenant_logo_url ? (
                <img
                  src={info.tenant_logo_url}
                  alt={info.tenant_name}
                  className="w-16 h-16 rounded-2xl object-cover mx-auto mb-3 bg-white/20"
                />
              ) : (
                <div className="w-16 h-16 rounded-2xl bg-white/20 flex items-center justify-center mx-auto mb-3">
                  <Star size={30} className="fill-white text-white" />
                </div>
              )}
              <h1 className="text-xl font-bold">{info.tenant_name}</h1>
              <p className="text-sm text-white/80 mt-1">Tarjeta de fidelidad</p>
            </div>

            <div className="px-6 py-6">
              {/* Progreso */}
              <div className="text-center mb-2">
                <p className="text-3xl font-bold text-stone-800">
                  {info.puntos_actuales}{' '}
                  <span className="text-lg font-medium text-stone-400">
                    de {info.puntos_meta}
                  </span>
                </p>
                <p className="text-sm text-stone-500 mt-1">estrellas acumuladas</p>
              </div>

              <div className="h-2.5 bg-stone-100 rounded-full overflow-hidden mb-4">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${pct}%`, backgroundColor: color }}
                />
              </div>

              <p className="text-center text-sm text-stone-600 mb-6">
                Premio: <span className="font-semibold text-stone-800">{info.premio_fidelidad}</span>
              </p>

              {/* Botones de wallet */}
              <div className="space-y-3">
                <button
                  onClick={handleApple}
                  disabled={busy !== null}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-3.5 rounded-2xl bg-black text-white font-semibold hover:bg-stone-900 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                >
                  {busy === 'apple' ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <Apple size={18} />
                  )}
                  Añadir a Apple Wallet
                </button>
                <button
                  onClick={handleGoogle}
                  disabled={busy !== null}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-3.5 rounded-2xl bg-white border-2 text-stone-800 font-semibold hover:bg-stone-50 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                  style={{ borderColor: color }}
                >
                  {busy === 'google' ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <Smartphone size={18} />
                  )}
                  Añadir a Google Wallet
                </button>
              </div>

              {message && (
                <p className="mt-4 text-center text-xs text-stone-500">{message}</p>
              )}

              <p className="mt-6 text-center text-[11px] text-stone-400">
                Este enlace es personal y caduca. Si necesitas uno nuevo, pídelo en tu SPA.
              </p>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
