// ============================================================
// Página del Asistente IA (FreeLLMAPI)
// Chat interactivo con la IA + panel de administración del
// historial de consultas (filtros, estadísticas y eliminación).
// Acceso restringido a roles admin/manager (ver App.tsx).
// ============================================================

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api, ApiError } from '../services/api';
import {
  AssistantChatTurn,
  AssistantQuery,
  AssistantStatusResponse,
  AssistantStatsResponse,
} from '../types';
import {
  Send, Bot, ThumbsUp, ThumbsDown, Trash2, Search, Loader2,
  History as HistoryIcon, MessageCircle, Sparkles, ChevronLeft,
  ChevronRight, CheckCircle2, XCircle, HelpCircle,
} from 'lucide-react';

// ============================================================
// Tipos locales
// ============================================================

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  queryId?: string;
  is_understood?: boolean | null;
  created_at?: string;
  pending?: boolean;
  error?: boolean;
}

type Tab = 'chat' | 'history';

// ============================================================
// Utilidades de formato (mismo estilo que el resto de páginas)
// ============================================================

const fmtTime = (iso?: string | null) => {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
};

const fmtDate = (iso?: string | null) => {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' });
};

const inputClass =
  "w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400";

// Sugerencias rápidas para comenzar la conversación
const SUGGESTIONS = [
  '¿Qué servicios recomiendan para una sesión de relajación?',
  '¿Cómo funciona el programa de fidelidad?',
  '¿Cuántas estrellas se necesitan para una sesión gratis?',
];

// Salvaguarda de tokens: máximo de turnos que se envían como contexto a
// la IA (el backend además recorta a los últimos 10 mensajes válidos).
const MAX_HISTORY_SENT = 15;
// Tope de turnos retenidos en memoria para el contexto de la conversación.
const MAX_HISTORY_STATE = 50;

// ============================================================
// Componente principal
// ============================================================

export default function AssistantPage() {
  const [tab, setTab] = useState<Tab>('chat');

  // ----------------------------------------------------------
  // Estado de la integración (backend)
  // ----------------------------------------------------------
  const [status, setStatus] = useState<AssistantStatusResponse | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);

  // ----------------------------------------------------------
  // Estado del Chat
  // ----------------------------------------------------------
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  // Contexto de la conversación (turnos user/assistant) que se envía a la
  // IA junto con la nueva pregunta para resolver preguntas de seguimiento.
  const [history, setHistory] = useState<AssistantChatTurn[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState('');
  const chatBodyRef = useRef<HTMLDivElement>(null);

  // ----------------------------------------------------------
  // Estado del panel de administración (Historial)
  // ----------------------------------------------------------
  const [queries, setQueries] = useState<AssistantQuery[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyOffset, setHistoryOffset] = useState(0);
  const [historySearch, setHistorySearch] = useState('');
  const [historyFilter, setHistoryFilter] = useState('all');
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [stats, setStats] = useState<AssistantStatsResponse | null>(null);
  // Disparador de recarga del panel (evita dobles llamadas y re-renders
  // por tecla con la búsqueda: solo recarga al pulsar Filtrar/paginación).
  const [reloadKey, setReloadKey] = useState(0);

  const PAGE_SIZE = 20;

  // ----------------------------------------------------------
  // Carga del estado de la integración
  // ----------------------------------------------------------
  useEffect(() => {
    api.getAssistantStatus()
      .then(setStatus)
      .catch((err) => {
        // Si el backend aún no responde, se muestra la advertencia genérica
        setChatError(err instanceof ApiError ? err.message : 'No se pudo verificar el estado del asistente');
      })
      .finally(() => setStatusLoading(false));
  }, []);

  // Auto-scroll del chat al final
  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  }, [messages, sending]);

  // ----------------------------------------------------------
  // Historial del chat (consultas previas del usuario)
  // ----------------------------------------------------------
  const loadChatHistory = useCallback(async () => {
    try {
      const data = await api.getAssistantHistory({ limit: 50 });
      const ordered = (data.queries || []).slice().reverse();
      const prev = ordered
        .map<ChatMessage[]>((q) => [
          { id: `hq-${q.id}-q`, role: 'user' as const, content: q.question, created_at: q.created_at },
          {
            id: `hq-${q.id}-a`,
            role: 'assistant' as const,
            content: q.response || '—',
            queryId: q.id,
            is_understood: q.is_understood,
            created_at: q.created_at,
          },
        ])
        .flat();
      setMessages((current) => (current.length ? current : prev));

      // Sembrar también el contexto que se enviará a la IA, omitiendo las
      // consultas sin respuesta para no inyectar ruido en la conversación.
      const prevHistory: AssistantChatTurn[] = [];
      ordered.forEach((q) => {
        prevHistory.push({ role: 'user', content: q.question });
        if (q.response && q.response.trim()) {
          prevHistory.push({ role: 'assistant', content: q.response });
        }
      });
      setHistory((current) =>
        current.length ? current : prevHistory.slice(-MAX_HISTORY_STATE),
      );
    } catch (err) {
      // Error no bloqueante: el chat sigue funcionando sin historial
      setChatError(err instanceof ApiError ? err.message : 'No se pudo cargar el historial del chat');
    }
  }, []);

  // ----------------------------------------------------------
  // Consultas del tenant (panel de administración)
  // ----------------------------------------------------------
  const loadQueries = useCallback(async (offset: number) => {
    setHistoryLoading(true);
    setHistoryError('');
    try {
      const data = await api.getAssistantQueries({
        search: historySearch || undefined,
        is_understood: historyFilter === 'all' ? undefined : historyFilter,
        limit: PAGE_SIZE,
        offset,
      });
      setQueries(data.queries || []);
      setHistoryTotal(data.total ?? 0);
      setHistoryOffset(offset);
    } catch (err) {
      setHistoryError(err instanceof ApiError ? err.message : 'Error al cargar el historial');
    } finally {
      setHistoryLoading(false);
    }
  }, [historySearch, historyFilter]);

  const loadStats = useCallback(async () => {
    try {
      setStats(await api.getAssistantStats());
    } catch {
      // Las estadísticas son informativas: si fallan, no bloquean la página
    }
  }, []);

  // Carga según la pestaña activa. En 'history' se usa reloadKey como
  // disparador explícito (paginación, filtros) para leer siempre los
  // valores de búsqueda/filtro más recientes del render.
  useEffect(() => {
    if (tab === 'chat') {
      if (!messages.length) loadChatHistory();
    } else {
      loadQueries(historyOffset);
      loadStats();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, reloadKey]);

  // ----------------------------------------------------------
  // Acciones del Chat
  // ----------------------------------------------------------

  const sendQuestion = async () => {
    const question = input.trim();
    if (!question || sending || !status?.active) return;

    setInput('');
    setChatError('');

    const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: 'user', content: question };
    const pendingId = `a-${Date.now()}`;
    const pendingMsg: ChatMessage = { id: pendingId, role: 'assistant', content: '', pending: true };

    setMessages((prev) => [...prev, userMsg, pendingMsg]);

    // Contexto para esta petición: solo los turnos PREVIOS, recortados
    // como salvaguarda de tokens. El backend añade la pregunta actual como
    // último mensaje del prompt, por lo que incluirla aquí la duplicaría.
    const contextHistory = history.slice(-MAX_HISTORY_SENT);

    // El estado sí incorpora ya el turno del usuario para los siguientes
    // mensajes de la conversación.
    const nextHistory: AssistantChatTurn[] = [
      ...history,
      { role: 'user', content: question },
    ];
    setHistory(nextHistory.slice(-MAX_HISTORY_STATE));

    setSending(true);

    try {
      const res = await api.assistantAsk(question, contextHistory);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingId
            ? {
                ...m,
                content: res.response,
                queryId: res.id,
                is_understood: res.is_understood,
                created_at: res.created_at,
                pending: false,
              }
            : m,
        ),
      );
      // La respuesta pasa a formar parte del contexto para seguimientos.
      setHistory((prev) =>
        [...prev, { role: 'assistant' as const, content: res.response }].slice(-MAX_HISTORY_STATE),
      );
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Error al conectar con el asistente';
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingId ? { ...m, content: msg, pending: false, error: true } : m,
        ),
      );
      setChatError(msg);
    } finally {
      setSending(false);
    }
  };

  const sendFeedback = async (msg: ChatMessage, value: boolean) => {
    if (!msg.queryId) return;
    try {
      await api.sendAssistantFeedback(msg.queryId, value);
      setMessages((prev) =>
        prev.map((m) => (m.id === msg.id ? { ...m, is_understood: value } : m)),
      );
      setChatError('');
    } catch (err) {
      setChatError(err instanceof ApiError ? err.message : 'No se pudo guardar el feedback');
    }
  };

  // ----------------------------------------------------------
  // Acciones del panel de administración
  // ----------------------------------------------------------

  const handleSearch = () => {
    setHistoryOffset(0);
    setReloadKey((k) => k + 1);
  };

  const handleFilter = (value: string) => {
    setHistoryFilter(value);
    setHistoryOffset(0);
    setReloadKey((k) => k + 1);
  };

  const goToPage = (offset: number) => {
    setHistoryOffset(offset);
    setReloadKey((k) => k + 1);
  };

  const deleteQuery = async (query: AssistantQuery) => {
    if (!window.confirm('¿Eliminar esta consulta del historial?')) return;
    try {
      await api.deleteAssistantQuery(query.id);
      setQueries((prev) => prev.filter((q) => q.id !== query.id));
      setHistoryTotal((t) => Math.max(0, t - 1));
      loadStats();
    } catch (err) {
      setHistoryError(err instanceof ApiError ? err.message : 'Error al eliminar la consulta');
    }
  };

  const active = Boolean(status?.active);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-stone-800">Asistente IA</h1>
          <p className="text-stone-500 mt-1">
            Consultas de clientes, recomendaciones y programa de fidelidad
          </p>
        </div>
        {statusLoading ? (
          <span className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-stone-100 text-sm text-stone-500">
            <Loader2 size={16} className="animate-spin" /> Verificando...
          </span>
        ) : (
          <span
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium ${
              active
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                : 'bg-amber-50 text-amber-700 border border-amber-100'
            }`}
          >
            <Bot size={18} />
            {active ? 'Asistente activo' : 'Asistente no configurado'}
          </span>
        )}
      </div>

      {/* Aviso si el asistente no está operativo */}
      {!statusLoading && !active && (
        <div className="p-4 bg-amber-50 border border-amber-100 rounded-xl text-sm text-amber-700">
          <strong>El asistente IA no está activo.</strong> Solicita al administrador que active{' '}
          <code className="bg-amber-100/60 px-1 rounded">FREELLMAPI_ENABLED</code> y configure la{' '}
          <code className="bg-amber-100/60 px-1 rounded">FREELLMAPI_API_KEY</code> en el backend
          (usa status.missing para diagnosticar). El resto del sistema funciona con normalidad.
        </div>
      )}

      {chatError && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">
          {chatError}
        </div>
      )}
      {historyError && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">
          {historyError}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-stone-200">
        <button
          onClick={() => setTab('chat')}
          className={`inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
            tab === 'chat'
              ? 'border-emerald-500 text-emerald-700'
              : 'border-transparent text-stone-500 hover:text-stone-700'
          }`}
        >
          <MessageCircle size={16} /> Chat
        </button>
        <button
          onClick={() => setTab('history')}
          className={`inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
            tab === 'history'
              ? 'border-emerald-500 text-emerald-700'
              : 'border-transparent text-stone-500 hover:text-stone-700'
          }`}
        >
          <HistoryIcon size={16} /> Historial y gestión
        </button>
      </div>

      {/* ==================================================
          PESTAÑA: CHAT
      ================================================== */}
      {tab === 'chat' && (
        <div className="bg-white rounded-2xl border border-stone-100 shadow-sm overflow-hidden flex flex-col h-[560px]">
          {/* Zona de mensajes */}
          <div ref={chatBodyRef} className="flex-1 overflow-y-auto p-4 space-y-4 bg-stone-50/50">
            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center px-6">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white shadow-lg shadow-emerald-200/50 mb-4">
                  <Bot size={32} />
                </div>
                <h3 className="text-lg font-semibold text-stone-800">Hola, soy tu asistente del SPA</h3>
                <p className="text-stone-500 text-sm mt-2 max-w-md">
                  Pregúntame sobre servicios, recomendaciones de tratamiento o el programa de
                  fidelidad (estrellas y sesiones gratuitas).
                </p>
                <div className="flex flex-col gap-2 mt-6 w-full max-w-md">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => { setInput(s); }}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm bg-white border border-stone-200 rounded-xl text-stone-600 hover:border-emerald-300 hover:text-emerald-700 transition-colors text-left"
                    >
                      <Sparkles size={15} className="text-emerald-500 shrink-0" />
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-br-md'
                    : msg.error
                      ? 'bg-red-50 border border-red-100 text-red-700 rounded-bl-md'
                      : 'bg-white border border-stone-200 text-stone-700 rounded-bl-md'
                }`}>
                  {msg.pending ? (
                    <span className="inline-flex items-center gap-2 text-stone-400">
                      <Loader2 size={15} className="animate-spin" /> El asistente está pensando...
                    </span>
                  ) : (
                    <>
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                      <div className="mt-1.5 flex items-center justify-between gap-3">
                        <span className="text-[11px] opacity-60">{fmtTime(msg.created_at)}</span>
                        {msg.role === 'assistant' && !msg.error && msg.queryId && (
                          <span className="flex items-center gap-1">
                            <button
                              title="Respuesta útil"
                              onClick={() => sendFeedback(msg, true)}
                              className={`p-1 rounded-md transition-colors ${
                                msg.is_understood === true
                                  ? 'bg-emerald-100 text-emerald-600'
                                  : 'text-stone-400 hover:text-emerald-600'
                              }`}
                            >
                              <ThumbsUp size={13} />
                            </button>
                            <button
                              title="No fue útil"
                              onClick={() => sendFeedback(msg, false)}
                              className={`p-1 rounded-md transition-colors ${
                                msg.is_understood === false
                                  ? 'bg-red-100 text-red-500'
                                  : 'text-stone-400 hover:text-red-500'
                              }`}
                            >
                              <ThumbsDown size={13} />
                            </button>
                          </span>
                        )}
                      </div>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Barra de entrada */}
          <div className="border-t border-stone-200 p-3 bg-white flex gap-2">
            <input
              type="text"
              placeholder={active ? 'Escribe tu consulta...' : 'Asistente desactivado'}
              value={input}
              disabled={!active}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') sendQuestion(); }}
              className={inputClass}
            />
            <button
              onClick={sendQuestion}
              disabled={!active || sending || !input.trim()}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-200/50 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {sending ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
              Enviar
            </button>
          </div>
        </div>
      )}

      {/* ==================================================
          PESTAÑA: HISTORIAL Y GESTIÓN (admin/manager)
      ================================================== */}
      {tab === 'history' && (
        <div className="space-y-6">
          {/* Tarjetas de estadísticas */}
          {stats && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                icon={<MessageCircle size={18} />}
                label="Consultas totales"
                value={stats.total_queries}
                color="text-emerald-600 bg-emerald-50"
              />
              <StatCard
                icon={<CheckCircle2 size={18} />}
                label="Respuestas útiles"
                value={stats.understood}
                color="text-teal-600 bg-teal-50"
              />
              <StatCard
                icon={<XCircle size={18} />}
                label="No útiles"
                value={stats.not_understood}
                color="text-red-500 bg-red-50"
              />
              <StatCard
                icon={<HelpCircle size={18} />}
                label="Sin valorar"
                value={stats.pending_feedback}
                color="text-amber-600 bg-amber-50"
              />
            </div>
          )}

          {/* Filtros de búsqueda */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex items-center gap-2 bg-white rounded-xl px-4 py-2.5 border border-stone-200 flex-1 max-w-md">
              <Search size={18} className="text-stone-400" />
              <input
                type="text"
                placeholder="Buscar por pregunta o respuesta..."
                value={historySearch}
                onChange={(e) => setHistorySearch(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(); }}
                className="bg-transparent border-none outline-none text-sm text-stone-700 placeholder:text-stone-400 w-full"
              />
            </div>
            <select
              value={historyFilter}
              onChange={(e) => handleFilter(e.target.value)}
              className="bg-white border border-stone-200 rounded-xl px-4 py-2.5 text-sm text-stone-700 focus:outline-none"
            >
              <option value="all">Todos los feedback</option>
              <option value="true">Solo útiles</option>
              <option value="false">Solo no útiles</option>
            </select>
            <button
              onClick={handleSearch}
              className="inline-flex items-center gap-2 px-4 py-2.5 border border-stone-200 rounded-xl text-sm font-medium text-stone-600 hover:bg-stone-50 transition-colors"
            >
              <Search size={16} /> Filtrar
            </button>
          </div>

          {/* Tabla de consultas */}
          {historyLoading ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="bg-white rounded-2xl p-5 border border-stone-100 animate-pulse">
                  <div className="h-3 bg-stone-100 rounded w-1/3 mb-3" />
                  <div className="h-3 bg-stone-100 rounded w-2/3 mb-2" />
                  <div className="h-3 bg-stone-100 rounded w-1/4" />
                </div>
              ))}
            </div>
          ) : queries.length === 0 ? (
            <div className="bg-white rounded-2xl p-10 border border-stone-100 text-center">
              <MessageCircle size={32} className="mx-auto text-stone-300 mb-2" />
              <p className="text-stone-500 text-sm">
                No hay consultas que coincidan con los filtros.
              </p>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-stone-100 shadow-sm overflow-hidden">
              <div className="divide-y divide-stone-100">
                {queries.map((q) => (
                  <div key={q.id} className="p-4 flex flex-col lg:flex-row lg:items-center gap-3 lg:gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-stone-800">
                        {q.question}
                      </p>
                      <p className="text-sm text-stone-500 line-clamp-3 mt-0.5">
                        {q.response || '—'}
                      </p>
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 text-xs text-stone-400">
                        <span>{q.user_name || 'Usuario eliminado'}</span>
                        <span>{fmtDate(q.created_at)} {fmtTime(q.created_at)}</span>
                        {q.is_understood === true && (
                          <span className="inline-flex items-center gap-1 text-teal-600">
                            <ThumbsUp size={12} /> Útil
                          </span>
                        )}
                        {q.is_understood === false && (
                          <span className="inline-flex items-center gap-1 text-red-500">
                            <ThumbsDown size={12} /> No útil
                          </span>
                        )}
                        {q.is_understood === null && (
                          <span className="inline-flex items-center gap-1 text-stone-400">
                            <HelpCircle size={12} /> Sin valorar
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => deleteQuery(q)}
                      className="inline-flex items-center gap-2 px-3 py-2 border border-red-100 text-red-500 rounded-lg text-sm hover:bg-red-50 transition-colors shrink-0"
                    >
                      <Trash2 size={15} /> Eliminar
                    </button>
                  </div>
                ))}
              </div>

              {/* Paginación */}
              <div className="flex items-center justify-between px-4 py-3 border-t border-stone-100 bg-stone-50/50">
                <span className="text-xs text-stone-500">
                  {historyTotal} consulta(s) — mostrando {historyOffset + 1}-
                  {Math.min(historyOffset + PAGE_SIZE, historyTotal)}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => goToPage(Math.max(0, historyOffset - PAGE_SIZE))}
                    disabled={historyOffset === 0}
                    className="inline-flex items-center gap-1 px-3 py-1.5 border border-stone-200 rounded-lg text-sm text-stone-600 hover:bg-stone-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft size={16} /> Anterior
                  </button>
                  <button
                    onClick={() => goToPage(historyOffset + PAGE_SIZE)}
                    disabled={historyOffset + PAGE_SIZE >= historyTotal}
                    className="inline-flex items-center gap-1 px-3 py-1.5 border border-stone-200 rounded-lg text-sm text-stone-600 hover:bg-stone-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    Siguiente <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Nota de privacidad (muestra información mínima del usuario) */}
          <p className="text-xs text-stone-400">
            El historial es exclusivo de tu SPA (aislado por tenant). Las preguntas se registran
            con el usuario que las realizó para control de calidad de las respuestas de la IA.
          </p>
        </div>
      )}
    </div>
  );
}

// ============================================================
// Tarjeta de estadística reutilizable
// ============================================================

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="bg-white rounded-2xl p-5 border border-stone-100 shadow-sm">
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${color} mb-3`}>
        {icon}
      </div>
      <p className="text-2xl font-bold text-stone-800">{value}</p>
      <p className="text-sm text-stone-500 mt-0.5">{label}</p>
    </div>
  );
}