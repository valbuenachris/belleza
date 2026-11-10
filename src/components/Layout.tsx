// ============================================================
// Layout Principal - Sidebar + Header + Content
// ============================================================

import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { Page, Patient, Appointment, Service } from '../types';
import { api } from '../services/api';
import { requestPatientFicha } from '../services/patientActions';
import NotificationBell from './NotificationBell';
import {
  LayoutDashboard, Building2, Users, Calendar, UserCheck,
  Settings, LogOut, Menu, X, Sparkles, ChevronRight, Search, BookOpen, Tag, BarChart, Bot, MessageCircle
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
  currentPage: Page;
  onNavigate: (page: Page) => void;
}

const navItems: { id: Page; label: string; icon: React.ReactNode; roles: string[] }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} />, roles: ['superadmin', 'admin', 'manager', 'receptionist', 'therapist'] },
  { id: 'tenants', label: 'SPAs / Tenants', icon: <Building2 size={20} />, roles: ['superadmin'] },
  { id: 'users', label: 'Usuarios', icon: <Users size={20} />, roles: ['admin', 'manager'] },
  { id: 'services', label: 'Servicios', icon: <Tag size={20} />, roles: ['admin', 'manager'] },
  { id: 'appointments', label: 'Citas', icon: <Calendar size={20} />, roles: ['admin', 'manager', 'receptionist', 'therapist'] },
  { id: 'reports', label: 'Reportes', icon: <BarChart size={20} />, roles: ['admin', 'manager'] },
  { id: 'assistant', label: 'Asistente IA', icon: <Bot size={20} />, roles: ['admin', 'manager'] },
  { id: 'whatsapp', label: 'WhatsApp', icon: <MessageCircle size={20} />, roles: ['admin', 'manager'] },
  { id: 'patients', label: 'Pacientes', icon: <UserCheck size={20} />, roles: ['admin', 'manager', 'receptionist', 'therapist'] },
  { id: 'settings', label: 'Configuración', icon: <Settings size={20} />, roles: ['admin', 'manager'] },
  { id: 'docs', label: 'Documentación', icon: <BookOpen size={20} />, roles: ['superadmin'] },
];

export default function Layout({ children, currentPage, onNavigate }: LayoutProps) {
  const { user, tenant, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // ----------------------------------------------------------
  // Búsqueda global (debounce 300ms + atajo Ctrl/Cmd+K)
  // ----------------------------------------------------------
  const [searchQuery, setSearchQuery] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<{
    patients: Patient[];
    appointments: Appointment[];
    services: Service[];
  }>({ patients: [], appointments: [], services: [] });
  const searchInputRef = useRef<HTMLInputElement>(null);
  const searchCacheRef = useRef<{ patients: Patient[]; appointments: Appointment[]; services: Service[]; loaded: boolean } | null>(null);

  const filteredNav = navItems.filter(item => 
    user && item.roles.includes(user.rol)
  );

  const handleLogout = async () => {
    await logout();
  };

  const runSearchAction = (action: () => void) => {
    setSearchOpen(false);
    setSearchQuery('');
    action();
  };

  useEffect(() => {
    const q = searchQuery.trim().toLowerCase();
    if (q.length < 2) {
      setSearchOpen(false);
      setSearchResults({ patients: [], appointments: [], services: [] });
      return;
    }
    setSearchOpen(true);
    const t = setTimeout(async () => {
      setSearchLoading(true);
      try {
        if (!searchCacheRef.current?.loaded) {
          const [p, a, s] = await Promise.all([
            api.getPatients(),
            api.getAppointments({ limit: 500 }),
            api.getServices(),
          ]);
          searchCacheRef.current = {
            patients: p.patients || [],
            appointments: a.appointments || [],
            services: s.services || [],
            loaded: true,
          };
        }
        const cache = searchCacheRef.current!;
        setSearchResults({
          patients: cache.patients
            .filter(
              (x) =>
                x.nombre.toLowerCase().includes(q) ||
                x.apellido.toLowerCase().includes(q) ||
                (x.email || '').toLowerCase().includes(q) ||
                (x.telefono || '').toLowerCase().includes(q)
            )
            .slice(0, 5),
          appointments: cache.appointments
            .filter(
              (x) =>
                (x.patient || '').toLowerCase().includes(q) ||
                (x.service || '').toLowerCase().includes(q)
            )
            .slice(0, 5),
          services: cache.services
            .filter((x) => x.nombre.toLowerCase().includes(q))
            .slice(0, 5),
        });
      } catch {
        setSearchResults({ patients: [], appointments: [], services: [] });
      } finally {
        setSearchLoading(false);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [searchQuery]);

  // Atajo de teclado: Ctrl/Cmd+K enfoca la búsqueda, Escape la cierra
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
        if (searchInputRef.current) {
          searchInputRef.current.select();
        }
      }
      if (e.key === 'Escape') {
        setSearchOpen(false);
        searchInputRef.current?.blur();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const hasResults =
    searchResults.patients.length > 0 ||
    searchResults.appointments.length > 0 ||
    searchResults.services.length > 0;

  return (
    <div className="flex h-screen bg-stone-50 overflow-hidden">
      {/* Overlay mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-40 lg:hidden backdrop-blur-sm"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-72 bg-white border-r border-stone-200 
          transform transition-transform duration-300 ease-in-out flex flex-col
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-stone-100">
          <div className="w-10 h-10 bg-gradient-to-br from-emerald-400 to-teal-600 rounded-xl flex items-center justify-center shadow-lg shadow-emerald-200">
            <Sparkles size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-stone-800 tracking-tight">SPA Manager</h1>
            <p className="text-xs text-stone-400 -mt-0.5">Sistema de Gestión</p>
          </div>
          <button
            className="ml-auto lg:hidden p-1 rounded-lg hover:bg-stone-100"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={20} className="text-stone-500" />
          </button>
        </div>

        {/* Tenant info */}
        {tenant && (
          <div className="px-6 py-4 border-b border-stone-100">
            <p className="text-xs font-medium text-stone-400 uppercase tracking-wider">Tenant Activo</p>
            <p className="text-sm font-semibold text-stone-700 mt-1 truncate">{tenant.nombre}</p>
            <span className="inline-block mt-1.5 px-2 py-0.5 text-xs font-medium bg-emerald-50 text-emerald-700 rounded-full capitalize">
              {tenant.plan}
            </span>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
          {filteredNav.map(item => (
            <button
              key={item.id}
              onClick={() => { onNavigate(item.id); setSidebarOpen(false); }}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200
                ${currentPage === item.id
                  ? 'bg-emerald-50 text-emerald-700 shadow-sm'
                  : 'text-stone-500 hover:bg-stone-50 hover:text-stone-700'
                }`}
            >
              <span className={currentPage === item.id ? 'text-emerald-600' : 'text-stone-400'}>
                {item.icon}
              </span>
              {item.label}
              {currentPage === item.id && (
                <ChevronRight size={16} className="ml-auto text-emerald-400" />
              )}
            </button>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t border-stone-100 p-4">
          <div className="flex items-center gap-3 px-2">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-stone-200 to-stone-300 flex items-center justify-center">
              <span className="text-sm font-bold text-stone-600">
                {user?.nombre?.[0]}{user?.apellido?.[0]}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-stone-700 truncate">
                {user?.nombre} {user?.apellido}
              </p>
              <p className="text-xs text-stone-400 capitalize">{user?.rol}</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 rounded-lg hover:bg-red-50 text-stone-400 hover:text-red-500 transition-colors"
              title="Cerrar sesión"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-stone-200 px-4 lg:px-8 py-4 flex items-center gap-4">
          <button
            className="lg:hidden p-2 rounded-lg hover:bg-stone-100"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={22} className="text-stone-600" />
          </button>

          <div className="flex-1 flex items-center gap-4">
            <div className="hidden sm:block relative max-w-md flex-1">
              <div className="flex items-center gap-2 bg-stone-50 rounded-xl px-4 py-2 border border-stone-200">
                <Search size={18} className="text-stone-400 shrink-0" />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onFocus={() => searchQuery.trim().length >= 2 && setSearchOpen(true)}
                  placeholder="Buscar pacientes, citas, servicios..."
                  className="bg-transparent border-none outline-none text-sm text-stone-600 placeholder:text-stone-400 w-full"
                />
                <span className="hidden lg:flex items-center gap-1 text-[10px] text-stone-400 shrink-0">
                  <kbd className="px-1 py-0.5 bg-white border border-stone-200 rounded font-sans">Ctrl</kbd>
                  <kbd className="px-1 py-0.5 bg-white border border-stone-200 rounded font-sans">K</kbd>
                </span>
              </div>

              {/* Dropdown de resultados */}
              {searchOpen && (
                <>
                  <div className="fixed inset-0 z-30" onClick={() => setSearchOpen(false)} />
                  <div className="absolute top-full mt-2 left-0 right-0 z-50 bg-white rounded-2xl shadow-2xl border border-stone-100 overflow-y-auto max-h-[70vh]">
                    {searchLoading && (
                      <div className="px-4 py-3 text-sm text-stone-400">Buscando...</div>
                    )}

                    {!searchLoading && !hasResults && (
                      <div className="px-5 py-10 text-center">
                        <Search size={28} className="mx-auto text-stone-300 mb-2" />
                        <p className="text-sm text-stone-500">No se encontraron resultados</p>
                        <p className="text-xs text-stone-400 mt-1">Prueba con otro término de búsqueda</p>
                      </div>
                    )}

                    {!searchLoading && searchResults.patients.length > 0 && (
                      <div className="py-2">
                        <p className="px-4 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-stone-400 flex items-center gap-1.5">
                          <UserCheck size={12} /> Pacientes
                        </p>
                        {searchResults.patients.map((p) => (
                          <button
                            key={p.id}
                            onClick={() =>
                              runSearchAction(() => {
                                requestPatientFicha(p.id);
                                onNavigate('patients');
                              })
                            }
                            className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-emerald-50/60 text-left transition-colors"
                          >
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-100 to-teal-100 flex items-center justify-center shrink-0">
                              <span className="text-xs font-bold text-emerald-700">
                                {p.nombre[0]}{p.apellido[0]}
                              </span>
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-medium text-stone-800 truncate">
                                {p.nombre} {p.apellido}
                              </p>
                              <p className="text-xs text-stone-400 truncate">
                                {p.telefono || p.email || 'Paciente'}
                              </p>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}

                    {!searchLoading && searchResults.appointments.length > 0 && (
                      <div className="py-2 border-t border-stone-50">
                        <p className="px-4 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-stone-400 flex items-center gap-1.5">
                          <Calendar size={12} /> Citas
                        </p>
                        {searchResults.appointments.map((a) => (
                          <button
                            key={a.id}
                            onClick={() =>
                              runSearchAction(() => onNavigate('appointments'))
                            }
                            className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-emerald-50/60 text-left transition-colors"
                          >
                            <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                              <Calendar size={14} />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-medium text-stone-800 truncate">
                                {a.patient} — {a.service}
                              </p>
                              <p className="text-xs text-stone-400 truncate">
                                {a.date_time || a.fecha || 'Fecha no disponible'}
                              </p>
                            </div>
                            <span className={`shrink-0 px-2 py-0.5 text-[10px] font-medium rounded-full capitalize ${
                              a.estado === 'cancelled'
                                ? 'bg-red-50 text-red-500'
                                : a.estado === 'completed'
                                ? 'bg-blue-50 text-blue-700'
                                : a.estado === 'confirmed'
                                ? 'bg-emerald-50 text-emerald-700'
                                : 'bg-amber-50 text-amber-700'
                            }`}>
                              {a.estado === 'pending' ? 'Pendiente' : a.estado === 'confirmed' ? 'Confirmada' : a.estado === 'completed' ? 'Completada' : a.estado === 'cancelled' ? 'Cancelada' : a.estado}
                            </span>
                          </button>
                        ))}
                      </div>
                    )}

                    {!searchLoading && searchResults.services.length > 0 && (
                      <div className="py-2 border-t border-stone-50">
                        <p className="px-4 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-stone-400 flex items-center gap-1.5">
                          <Tag size={12} /> Servicios
                        </p>
                        {searchResults.services.map((s) => (
                          <button
                            key={s.id}
                            onClick={() => runSearchAction(() => onNavigate('services'))}
                            className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-emerald-50/60 text-left transition-colors"
                          >
                            <div className="w-8 h-8 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center shrink-0">
                              <Tag size={14} />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-medium text-stone-800 truncate">{s.nombre}</p>
                              <p className="text-xs text-stone-400 truncate">
                                {s.duracion} min · {s.descripcion || 'Servicio'}
                              </p>
                            </div>
                            <span className="shrink-0 text-sm font-semibold text-stone-600">
                              ${s.precio.toLocaleString('es-CO')}
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <NotificationBell />
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
