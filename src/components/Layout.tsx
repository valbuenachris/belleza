// ============================================================
// Layout Principal - Sidebar + Header + Content
// ============================================================

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Page } from '../types';
import {
  LayoutDashboard, Building2, Users, Calendar, UserCheck,
  Settings, LogOut, Menu, X, Sparkles, ChevronRight, Bell, Search, BookOpen
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
  currentPage: Page;
  onNavigate: (page: Page) => void;
}

const navItems: { id: Page; label: string; icon: React.ReactNode; roles: string[] }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} />, roles: ['superadmin', 'admin', 'manager', 'receptionist', 'therapist'] },
  { id: 'tenants', label: 'SPAs / Tenants', icon: <Building2 size={20} />, roles: ['superadmin'] },
  { id: 'users', label: 'Usuarios', icon: <Users size={20} />, roles: ['superadmin', 'admin', 'manager'] },
  { id: 'appointments', label: 'Citas', icon: <Calendar size={20} />, roles: ['superadmin', 'admin', 'manager', 'receptionist', 'therapist'] },
  { id: 'patients', label: 'Pacientes', icon: <UserCheck size={20} />, roles: ['superadmin', 'admin', 'manager', 'receptionist', 'therapist'] },
  { id: 'settings', label: 'Configuración', icon: <Settings size={20} />, roles: ['superadmin', 'admin', 'manager', 'receptionist', 'therapist'] },
  { id: 'docs', label: 'Documentación', icon: <BookOpen size={20} />, roles: ['superadmin', 'admin', 'manager', 'receptionist', 'therapist'] },
];

export default function Layout({ children, currentPage, onNavigate }: LayoutProps) {
  const { user, tenant, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const filteredNav = navItems.filter(item => 
    user && item.roles.includes(user.rol)
  );

  const handleLogout = async () => {
    await logout();
  };

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
            <div className="hidden sm:flex items-center gap-2 bg-stone-50 rounded-xl px-4 py-2 border border-stone-200 max-w-md flex-1">
              <Search size={18} className="text-stone-400" />
              <input
                type="text"
                placeholder="Buscar..."
                className="bg-transparent border-none outline-none text-sm text-stone-600 placeholder:text-stone-400 w-full"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button className="relative p-2.5 rounded-xl hover:bg-stone-50 transition-colors">
              <Bell size={20} className="text-stone-500" />
              <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>
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
