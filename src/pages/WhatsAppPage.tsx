import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api, ApiError } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  WhatsAppSettings,
  WhatsAppStatusResponse,
  WhatsAppConversation,
  WhatsAppMessage,
} from '../types';
import { fmtTime, fmtDate, fmtDateTime, getTenantTimezone } from '../utils/dateTime';
import {
  Smartphone, RefreshCw, Loader2, CheckCircle2, XCircle,
  Settings, MessageCircle, Wifi, WifiOff, ChevronDown,
  ChevronUp, Phone, User, Clock,
} from 'lucide-react';

type Tab = 'instance' | 'agent' | 'conversations';

const inputClass =
  "w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400";

export default function WhatsAppPage() {
  const { tenant } = useAuth();
  const tz = getTenantTimezone(tenant);
  const [tab, setTab] = useState<Tab>('instance');

  // ----------------------------------------------------------
  // Settings
  // ----------------------------------------------------------
  const [settings, setSettings] = useState<WhatsAppSettings | null>(null);
  const [settingsLoading, setSettingsLoading] = useState(true);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsError, setSettingsError] = useState('');

  // ----------------------------------------------------------
  // Instance
  // ----------------------------------------------------------
  const [status, setStatus] = useState<WhatsAppStatusResponse | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [qrLoading, setQrLoading] = useState(false);

  // ----------------------------------------------------------
  // Agent
  // ----------------------------------------------------------
  const [agentEnabled, setAgentEnabled] = useState(false);
  const [agentName, setAgentName] = useState('Asistente del SPA');
  const [agentTone, setAgentTone] = useState('amable');
  const [notifEnabled, setNotifEnabled] = useState(false);

  // ----------------------------------------------------------
  // Conversations
  // ----------------------------------------------------------
  const [conversations, setConversations] = useState<WhatsAppConversation[]>([]);
  const [convTotal, setConvTotal] = useState(0);
  const [convLoading, setConvLoading] = useState(false);
  const [selectedConv, setSelectedConv] = useState<string | null>(null);
  const [messages, setMessages] = useState<WhatsAppMessage[]>([]);
  const [msgLoading, setMsgLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const threadRef = useRef<HTMLDivElement | null>(null);
  const nearBottomRef = useRef(true);

  // QR / status / conversation polling
  const qrPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const statusPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const convPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const msgPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ----------------------------------------------------------
  // Cargar settings
  // ----------------------------------------------------------
  useEffect(() => {
    loadSettings();
    loadStatus();
    startStatusPolling();
    return () => {
      if (statusPollRef.current) clearInterval(statusPollRef.current);
      if (qrPollRef.current) clearInterval(qrPollRef.current);
      if (convPollRef.current) clearInterval(convPollRef.current);
      if (msgPollRef.current) clearInterval(msgPollRef.current);
    };
  }, []);

  const loadSettings = async () => {
    setSettingsLoading(true);
    try {
      const s = await api.getWhatsAppSettings();
      setSettings(s);
      setAgentEnabled(s.agent_enabled);
      setAgentName(s.agent_name);
      setAgentTone(s.agent_tone);
      setNotifEnabled(s.notifications_enabled);
      if (s.qr_code && s.status !== 'open') {
        setQrCode(s.qr_code);
        startQrPolling();
      }
    } catch (e) {
      setSettingsError('Error al cargar configuración');
    } finally {
      setSettingsLoading(false);
    }
  };

  const loadStatus = async () => {
    setStatusLoading(true);
    try {
      const s = await api.getWhatsAppStatus();
      setStatus(s);
    } catch {
      // noop
    } finally {
      setStatusLoading(false);
    }
  };

  // ----------------------------------------------------------
  // Instance management
  // ----------------------------------------------------------
  const handleCreateInstance = async () => {
    setQrLoading(true);
    setQrCode(null);
    try {
      const result = await api.createWhatsAppInstance();
      if (result.qr) {
        setQrCode(result.qr);
        startQrPolling();
      }
      await loadSettings();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : 'Error al crear instancia';
      setSettingsError(msg);
    } finally {
      setQrLoading(false);
    }
  };

  const handleConnect = async () => {
    setQrLoading(true);
    setQrCode(null);
    try {
      const result = await api.connectWhatsApp();
      if (result.qr) {
        setQrCode(result.qr);
        startQrPolling();
      }
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : 'Error al conectar';
      setSettingsError(msg);
    } finally {
      setQrLoading(false);
    }
  };

  const startQrPolling = () => {
    if (qrPollRef.current) clearInterval(qrPollRef.current);
    qrPollRef.current = setInterval(async () => {
      try {
        const s = await api.getWhatsAppStatus();
        setStatus(s);
        if (s.connected) {
          setQrCode(null);
          if (qrPollRef.current) clearInterval(qrPollRef.current);
        } else {
          const settings = await api.getWhatsAppSettings();
          if (settings.qr_code) setQrCode(settings.qr_code);
        }
      } catch {
        // noop
      }
    }, 5000);

    setTimeout(() => {
      if (qrPollRef.current) clearInterval(qrPollRef.current);
    }, 120000);
  };

  const startStatusPolling = () => {
    if (statusPollRef.current) clearInterval(statusPollRef.current);
    statusPollRef.current = setInterval(async () => {
      try {
        const s = await api.getWhatsAppStatus();
        setStatus(s);
      } catch {
        // noop
      }
    }, 15000);
  };

  const handleDisconnect = async () => {
    if (!confirm('¿Desconectar la instancia de WhatsApp?')) return;
    try {
      await api.disconnectWhatsApp();
      setQrCode(null);
      await loadStatus();
      await loadSettings();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : 'Error al desconectar';
      setSettingsError(msg);
    }
  };

  // ----------------------------------------------------------
  // Agent settings
  // ----------------------------------------------------------
  const handleSaveAgent = async () => {
    setSettingsSaving(true);
    setSettingsError('');
    try {
      const s = await api.updateWhatsAppSettings({
        agent_enabled: agentEnabled,
        agent_name: agentName,
        agent_tone: agentTone,
        notifications_enabled: notifEnabled,
      });
      setSettings(s);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : 'Error al guardar';
      setSettingsError(msg);
    } finally {
      setSettingsSaving(false);
    }
  };

  // ----------------------------------------------------------
  // Conversations
  // ----------------------------------------------------------
  const loadConversations = useCallback(async () => {
    setConvLoading(true);
    try {
      const res = await api.getWhatsAppConversations({ limit: 50 });
      setConversations(res.conversations);
      setConvTotal(res.total);
    } catch {
      // noop
    } finally {
      setConvLoading(false);
    }
  }, []);

  const loadMessages = useCallback(async (convId: string, silent = false) => {
    if (!silent) {
      setMsgLoading(true);
      setSelectedConv(convId);
    }
    try {
      const res = await api.getWhatsAppMessages(convId, { limit: 100 });
      setMessages(res.messages);
    } catch {
      // noop
    } finally {
      if (!silent) setMsgLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tab === 'conversations') {
      loadConversations();
      // Polling: refrescar la lista cada 10s y los mensajes de la conversación
      // seleccionada cada 5s, para que llegue el último mensaje en vivo.
      if (convPollRef.current) clearInterval(convPollRef.current);
      convPollRef.current = setInterval(() => {
        loadConversations();
      }, 10000);

      if (msgPollRef.current) clearInterval(msgPollRef.current);
      msgPollRef.current = setInterval(() => {
        if (selectedConv) {
          loadMessages(selectedConv, true);
        }
      }, 5000);
    }

    return () => {
      if (convPollRef.current) clearInterval(convPollRef.current);
      if (msgPollRef.current) clearInterval(msgPollRef.current);
    };
  }, [tab, loadConversations, loadMessages, selectedConv]);

  // Auto-scroll al fondo al abrir o cambiar de conversación (muestra el
  // último mensaje, como cualquier chat de WhatsApp).
  useEffect(() => {
    if (selectedConv) {
      messagesEndRef.current?.scrollIntoView({ block: 'end' });
    }
  }, [selectedConv]);

  // Cuando llegan mensajes nuevos: ancla al fondo SOLO si el usuario ya está
  // cerca del final (no interrumpe la lectura de mensajes antiguos).
  useEffect(() => {
    const el = threadRef.current;
    if (!el) return;
    if (nearBottomRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages]);

  // ----------------------------------------------------------
  // Render
  // ----------------------------------------------------------
  const isConnected = status?.connected === true;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-stone-800">WhatsApp</h1>
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium ${
            isConnected
              ? 'bg-emerald-50 text-emerald-700'
              : 'bg-stone-100 text-stone-500'
          }`}>
            {isConnected ? <Wifi size={14} /> : <WifiOff size={14} />}
            {isConnected ? 'Conectado' : 'Desconectado'}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-stone-100 rounded-xl p-1">
        {[
          { id: 'instance' as Tab, label: 'Instancia', icon: <Smartphone size={16} /> },
          { id: 'agent' as Tab, label: 'Agente', icon: <Settings size={16} /> },
          { id: 'conversations' as Tab, label: 'Conversaciones', icon: <MessageCircle size={16} /> },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all flex-1 justify-center ${
              tab === t.id
                ? 'bg-white text-emerald-700 shadow-sm'
                : 'text-stone-500 hover:text-stone-700'
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {settingsError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          {settingsError}
        </div>
      )}

      {/* Tab: Instance */}
      {tab === 'instance' && (
        <div className="bg-white rounded-2xl border border-stone-200 p-6">
          <h2 className="text-lg font-semibold text-stone-800 mb-4">Instancia de WhatsApp</h2>
          <p className="text-sm text-stone-500 mb-6">
            Conecta un número de WhatsApp para que los pacientes puedan agendar citas.
          </p>

          {settingsLoading ? (
            <div className="flex items-center gap-2 text-stone-400 py-8 justify-center">
              <Loader2 size={20} className="animate-spin" />
              <span className="text-sm">Cargando...</span>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Estado actual */}
              <div className="bg-stone-50 rounded-xl p-4 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-stone-500">Instancia</span>
                  <span className="text-sm font-medium text-stone-700">
                    {settings?.instance_name || '—'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-stone-500">Estado</span>
                  <span className={`text-sm font-medium capitalize ${
                    isConnected ? 'text-emerald-600' : 'text-stone-500'
                  }`}>
                    {isConnected ? 'Conectado' : status?.state || 'Desconectado'}
                  </span>
                </div>
                {settings?.connected_at && (
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-stone-500">Conectado desde</span>
                    <span className="text-sm text-stone-600">{fmtDate(settings.connected_at, tz)} {fmtTime(settings.connected_at, tz)}</span>
                  </div>
                )}
              </div>

              {/* QR Code */}
              {qrCode && qrCode.length > 50 ? (
                <div className="bg-white border border-stone-200 rounded-xl p-6 text-center space-y-3">
                  <p className="text-sm font-medium text-stone-700">Escanea el código QR con WhatsApp</p>
                  <div className="inline-block bg-white p-4 rounded-xl border border-stone-100 shadow-sm">
                    <img
                      src={`data:image/png;base64,${qrCode}`}
                      alt="QR Code"
                      className="w-48 h-48 mx-auto"
                      onError={(e) => { e.currentTarget.style.display = 'none'; }}
                    />
                  </div>
                  <p className="text-xs text-stone-400">
                    Abre WhatsApp {'>'} Menú {'>'} Dispositivos vinculados {'>'} Vincular un dispositivo
                  </p>
                </div>
              ) : null}

              {/* Actions */}
              <div className="flex gap-3">
                {!settings?.instance_name ? (
                  <button
                    onClick={handleCreateInstance}
                    disabled={qrLoading}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 text-white rounded-xl text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                  >
                    {qrLoading ? <Loader2 size={18} className="animate-spin" /> : <Smartphone size={18} />}
                    {qrLoading ? 'Creando...' : 'Crear instancia'}
                  </button>
                ) : !isConnected ? (
                  <>
                    <button
                      onClick={handleConnect}
                      disabled={qrLoading}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 text-white rounded-xl text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                    >
                      {qrLoading ? <Loader2 size={18} className="animate-spin" /> : <RefreshCw size={18} />}
                      {qrLoading ? 'Conectando...' : 'Conectar'}
                    </button>
                    <button
                      onClick={handleDisconnect}
                      className="px-4 py-2.5 bg-red-50 text-red-600 rounded-xl text-sm font-medium hover:bg-red-100 transition-colors"
                    >
                      Desconectar
                    </button>
                  </>
                ) : (
                  <button
                    onClick={handleDisconnect}
                    className="px-4 py-2.5 bg-red-50 text-red-600 rounded-xl text-sm font-medium hover:bg-red-100 transition-colors"
                  >
                    Desconectar
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab: Agent */}
      {tab === 'agent' && (
        <div className="bg-white rounded-2xl border border-stone-200 p-6">
          <h2 className="text-lg font-semibold text-stone-800 mb-4">Agente de Citas</h2>
          <p className="text-sm text-stone-500 mb-6">
            Configura el asistente virtual que atenderá a los pacientes por WhatsApp.
          </p>

          <div className="space-y-5 max-w-md">
            <label className="flex items-center justify-between p-4 bg-stone-50 rounded-xl cursor-pointer">
              <div>
                <p className="text-sm font-medium text-stone-700">Agente activo</p>
                <p className="text-xs text-stone-400">Los pacientes podrán agendar citas automáticamente</p>
              </div>
              <input
                type="checkbox"
                checked={agentEnabled}
                onChange={(e) => setAgentEnabled(e.target.checked)}
                className="w-5 h-5 rounded border-stone-300 text-emerald-600 focus:ring-emerald-500"
              />
            </label>

            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1.5">Nombre del agente</label>
              <input
                type="text"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                className={inputClass}
                maxLength={100}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1.5">Tono de comunicación</label>
              <select
                value={agentTone}
                onChange={(e) => setAgentTone(e.target.value)}
                className={inputClass}
              >
                <option value="amable">Amable</option>
                <option value="profesional">Profesional</option>
                <option value="vendedor">Vendedor</option>
                <option value="cercano">Cercano</option>
              </select>
            </div>

            <label className="flex items-center justify-between p-4 bg-stone-50 rounded-xl cursor-pointer">
              <div>
                <p className="text-sm font-medium text-stone-700">Notificaciones</p>
                <p className="text-xs text-stone-400">Notificar al personal cuando se agenda una cita por WhatsApp</p>
              </div>
              <input
                type="checkbox"
                checked={notifEnabled}
                onChange={(e) => setNotifEnabled(e.target.checked)}
                className="w-5 h-5 rounded border-stone-300 text-emerald-600 focus:ring-emerald-500"
              />
            </label>

            <button
              onClick={handleSaveAgent}
              disabled={settingsSaving}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 text-white rounded-xl text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors"
            >
              {settingsSaving && <Loader2 size={18} className="animate-spin" />}
              Guardar configuración
            </button>
          </div>
        </div>
      )}

      {/* Tab: Conversations */}
      {tab === 'conversations' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Conversations list */}
          <div className="bg-white rounded-2xl border border-stone-200 p-4">
            <h2 className="text-lg font-semibold text-stone-800 mb-4">Conversaciones</h2>
            {convLoading ? (
              <div className="flex items-center justify-center py-8 text-stone-400">
                <Loader2 size={20} className="animate-spin" />
              </div>
            ) : conversations.length === 0 ? (
              <div className="text-center py-8 text-stone-400 text-sm">
                <MessageCircle size={32} className="mx-auto mb-2 opacity-50" />
                No hay conversaciones aún
              </div>
            ) : (
              <div className="space-y-1 max-h-[600px] overflow-y-auto">
                {conversations.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => loadMessages(c.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-colors ${
                      selectedConv === c.id
                        ? 'bg-emerald-50 border border-emerald-200'
                        : 'hover:bg-stone-50 border border-transparent'
                    }`}
                  >
                    <div className="w-11 h-11 rounded-full bg-gradient-to-br from-emerald-100 to-teal-100 flex items-center justify-center shrink-0">
                      <Phone size={16} className="text-emerald-600" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline gap-2">
                        <p className="min-w-0 flex-1 truncate text-sm font-medium text-stone-800">
                          {c.push_name || c.patient_name || c.phone}
                        </p>
                        <span className="shrink-0 text-[10px] text-stone-400">
                          {c.last_message_at ? fmtTime(c.last_message_at, tz) : ''}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <p className="min-w-0 flex-1 truncate text-xs text-stone-400">
                          {c.last_message_role === 'user' && '👤 '}
                          {c.last_message_role === 'assistant' && '🤖 '}
                          {c.last_message_content || 'Sin mensajes'}
                        </p>
                        <span className={`shrink-0 px-1.5 py-0.5 text-[10px] font-medium rounded-full ${
                          c.status === 'bot' ? 'bg-blue-50 text-blue-600' : 'bg-amber-50 text-amber-600'
                        }`}>
                          {c.status === 'bot' ? 'Bot' : 'Humano'}
                        </span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Messages */}
          <div className="bg-white rounded-2xl border border-stone-200 p-4 flex flex-col">
            <h2 className="text-lg font-semibold text-stone-800 mb-4">
              {selectedConv ? 'Mensajes' : 'Selecciona una conversación'}
            </h2>
            {!selectedConv ? (
              <div className="text-center py-8 text-stone-400 text-sm">
                <MessageCircle size={32} className="mx-auto mb-2 opacity-50" />
                Selecciona una conversación para ver los mensajes
              </div>
            ) : msgLoading && messages.length === 0 ? (
              <div className="flex items-center justify-center py-8 text-stone-400">
                <Loader2 size={20} className="animate-spin" />
              </div>
            ) : (
              <div
                ref={threadRef}
                onScroll={() => {
                  const el = threadRef.current;
                  if (!el) return;
                  nearBottomRef.current =
                    el.scrollHeight - el.scrollTop - el.clientHeight < 120;
                }}
                className="space-y-3 max-h-[600px] overflow-y-auto flex-1"
              >
                {messages.length === 0 ? (
                  <p className="text-center text-stone-400 text-sm py-8">Sin mensajes</p>
                ) : (
                  messages.map((m) => (
                    <div
                      key={m.id}
                      className={`flex ${m.role === 'user' ? 'justify-start' : 'justify-end'}`}
                    >
                      <div className={`max-w-[80%] p-3 rounded-2xl ${
                        m.role === 'user'
                          ? 'bg-stone-100 text-stone-700'
                          : 'bg-emerald-50 text-emerald-800'
                      }`}>
                        <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                        <p className="text-[10px] text-stone-400 mt-1 text-right">
                          {fmtTime(m.created_at, tz)}
                        </p>
                      </div>
                    </div>
                  ))
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}