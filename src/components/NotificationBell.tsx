// ============================================================
// NotificationBell - Campana de notificaciones del header
// Badge con el contador de no leídas + dropdown con las notificaciones
// recientes. Polling cada 45s (solo contador si está cerrado; lista +
// contador si está abierto) y refresco inmediato al volver a la
// pestaña/ventana (los timers se estrangulan en segundo plano).
// ============================================================

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Bell, CheckCheck, Inbox, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api, ApiError } from '../services/api';
import { AppNotification } from '../types';

// Auto-refresco del contador (dentro del rango 30-60s recomendado).
const POLL_MS = 45000;
const LIST_LIMIT = 12;

const TYPE_DOT: Record<string, string> = {
  appointment: 'bg-emerald-500',
  appointment_reminder: 'bg-amber-500',
  loyalty: 'bg-violet-500',
  system: 'bg-sky-500',
};

function timeAgo(iso: string): string {
  const date = new Date(iso);
  if (isNaN(date.getTime())) return '';
  const mins = Math.floor((Date.now() - date.getTime()) / 60000);
  if (mins < 1) return 'ahora';
  if (mins < 60) return `hace ${mins} min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `hace ${hours} h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `hace ${days} d`;
  return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
}

export default function NotificationBell() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<AppNotification[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const [markingAll, setMarkingAll] = useState(false);
  const [error, setError] = useState('');
  const wrapRef = useRef<HTMLDivElement>(null);
  // Evita peticiones de polling solapadas.
  const requestBusyRef = useRef(false);
  // Versión de mutaciones locales (marcar leídas): permite descartar
  // respuestas de polling que salieron antes de la mutación y llegan tarde.
  const mutationVersionRef = useRef(0);

  // El superadmin no tiene tenant: no hay notificaciones que mostrar.
  const hasTenant = Boolean(user?.tenant_id);

  const refreshCount = useCallback(async () => {
    if (!hasTenant || requestBusyRef.current) return;
    requestBusyRef.current = true;
    const version = mutationVersionRef.current;
    try {
      const res = await api.getUnreadNotificationsCount();
      // Solo aplicar si no hubo una mutación local mientras tanto.
      if (version === mutationVersionRef.current) setUnread(res.unread_count);
    } catch {
      // Silencioso: el contador se reintenta en el siguiente ciclo.
    } finally {
      requestBusyRef.current = false;
    }
  }, [hasTenant]);

  const loadList = useCallback(async (silent = false) => {
    if (!hasTenant) return;
    if (silent && requestBusyRef.current) return;
    requestBusyRef.current = true;
    const version = mutationVersionRef.current;
    if (!silent) {
      setLoading(true);
      setError('');
    }
    try {
      const res = await api.getNotifications({ limit: LIST_LIMIT });
      if (version === mutationVersionRef.current) {
        setItems(res.notifications);
        setUnread(res.unread_count);
      }
      setError('');
    } catch (err) {
      if (!silent) {
        setError(
          err instanceof ApiError ? err.message : 'No se pudieron cargar las notificaciones',
        );
      }
    } finally {
      requestBusyRef.current = false;
      if (!silent) setLoading(false);
    }
  }, [hasTenant]);

  // Lógica del tick de polling. Se guarda en un ref para que el interval
  // use SIEMPRE la versión más reciente (sin stale closures) y no tenga
  // que reiniciarse cada vez que cambia `open` u otro estado.
  const tick = useCallback(() => {
    if (open) {
      // Dropdown abierto: una sola llamada trae lista + contador.
      loadList(true);
    } else {
      refreshCount();
    }
  }, [open, loadList, refreshCount]);

  const tickRef = useRef(tick);
  useEffect(() => {
    tickRef.current = tick;
  }, [tick]);

  // Polling estable: un único interval por sesión de tenant.
  useEffect(() => {
    if (!hasTenant) return;
    tickRef.current(); // refresco inmediato al montar
    const id = window.setInterval(() => tickRef.current(), POLL_MS);
    return () => window.clearInterval(id);
  }, [hasTenant]);

  // Los timers se estrangulan en pestañas en segundo plano; al volver a la
  // pestaña/ventana se refresca al instante para que se sienta en vivo.
  useEffect(() => {
    if (!hasTenant) return;
    const wake = () => {
      if (document.visibilityState === 'visible') tickRef.current();
    };
    window.addEventListener('focus', wake);
    document.addEventListener('visibilitychange', wake);
    return () => {
      window.removeEventListener('focus', wake);
      document.removeEventListener('visibilitychange', wake);
    };
  }, [hasTenant]);

  // Cerrar al hacer clic fuera
  useEffect(() => {
    if (!open) return;
    const handler = (event: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next) loadList();
  };

  const handleItemClick = async (notification: AppNotification) => {
    if (notification.is_read) return;
    // Invalida respuestas de polling en vuelo (evita que pisen el cambio)
    // y bloquea nuevos polls hasta que termine la mutación.
    mutationVersionRef.current += 1;
    requestBusyRef.current = true;
    // Actualización optimista
    setItems((prev) =>
      prev.map((n) =>
        n.id === notification.id
          ? { ...n, is_read: true, read_at: new Date().toISOString() }
          : n,
      ),
    );
    setUnread((prev) => Math.max(0, prev - 1));
    try {
      await api.markNotificationRead(notification.id);
    } catch {
      // Revertir si el backend rechaza la operación
      setItems((prev) =>
        prev.map((n) =>
          n.id === notification.id ? { ...n, is_read: false, read_at: null } : n,
        ),
      );
      setUnread((prev) => prev + 1);
    } finally {
      requestBusyRef.current = false;
    }
  };

  const handleMarkAll = async () => {
    if (markingAll || unread === 0) return;
    setMarkingAll(true);
    // Invalida respuestas de polling en vuelo (evita que pisen el cambio)
    // y bloquea nuevos polls hasta que termine la mutación.
    mutationVersionRef.current += 1;
    requestBusyRef.current = true;
    try {
      await api.markAllNotificationsRead();
      const now = new Date().toISOString();
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true, read_at: n.read_at ?? now })));
      setUnread(0);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudieron marcar como leídas');
    } finally {
      requestBusyRef.current = false;
      setMarkingAll(false);
    }
  };

  if (!hasTenant) return null;

  return (
    <div className="relative" ref={wrapRef}>
      <button
        onClick={toggle}
        aria-label="Notificaciones"
        aria-expanded={open}
        className="relative p-2.5 rounded-xl hover:bg-stone-50 transition-colors"
      >
        <Bell size={20} className="text-stone-500" />
        {unread > 0 && (
          <span className="absolute top-1.5 right-1.5 min-w-[18px] h-[18px] px-1 flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full border-2 border-white">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 max-w-[calc(100vw-2rem)] bg-white rounded-2xl border border-stone-100 shadow-xl z-50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-stone-100">
            <p className="font-semibold text-sm text-stone-800">Notificaciones</p>
            <button
              onClick={handleMarkAll}
              disabled={markingAll || unread === 0}
              className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 hover:text-emerald-700 disabled:text-stone-300 disabled:cursor-not-allowed transition-colors"
            >
              {markingAll ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <CheckCheck size={13} />
              )}
              Marcar todas
            </button>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center gap-2 py-10 text-stone-400 text-sm">
                <Loader2 size={16} className="animate-spin" /> Cargando...
              </div>
            ) : error ? (
              <div className="px-4 py-8 text-center text-sm text-red-600">{error}</div>
            ) : items.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-stone-400">
                <Inbox size={28} className="mb-2" />
                <p className="text-sm">No tienes notificaciones</p>
              </div>
            ) : (
              items.map((notification) => (
                <button
                  key={notification.id}
                  onClick={() => handleItemClick(notification)}
                  className={`w-full flex gap-3 px-4 py-3 text-left border-b border-stone-50 last:border-0 transition-colors ${
                    notification.is_read
                      ? 'bg-white hover:bg-stone-50'
                      : 'bg-emerald-50/40 hover:bg-emerald-50/70'
                  }`}
                >
                  <span
                    className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${
                      TYPE_DOT[notification.type] ?? 'bg-stone-400'
                    }`}
                  />
                  <span className="min-w-0 flex-1">
                    <span
                      className={`block text-sm ${
                        notification.is_read
                          ? 'font-medium text-stone-700'
                          : 'font-semibold text-stone-900'
                      }`}
                    >
                      {notification.title}
                    </span>
                    {notification.message && (
                      <span className="block text-xs text-stone-500 mt-0.5 break-words">
                        {notification.message}
                      </span>
                    )}
                    <span className="block text-[11px] text-stone-400 mt-1">
                      {timeAgo(notification.created_at)}
                    </span>
                  </span>
                  {!notification.is_read && (
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
