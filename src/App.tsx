// ============================================================
// App.tsx - Componente Principal del SPA Management System
// Sistema de gestión integral para centros de estética y relajación
// Arquitectura multitenant SaaS
// ============================================================

import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Page } from './types';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import TenantsPage from './pages/TenantsPage';
import UsersPage from './pages/UsersPage';
import SettingsPage from './pages/SettingsPage';
import AppointmentsPage from './pages/AppointmentsPage';
import PatientsPage from './pages/PatientsPage';
import ServicesPage from './pages/ServicesPage';
import ReportsPage from './pages/ReportsPage';
import DocumentationPage from './pages/DocumentationPage';
import AssistantPage from './pages/AssistantPage';
import WhatsAppPage from './pages/WhatsAppPage';
import PaymentsPage from './pages/PaymentsPage';
import PublicWalletPage from './pages/PublicWalletPage';

// ============================================================
// Router interno de la aplicación
// ============================================================
function AppRouter() {
  const { isAuthenticated, isLoading, user } = useAuth();
  const [currentPage, setCurrentPage] = useState<Page>('dashboard');
  const [showRegister, setShowRegister] = useState(false);

  // Pantalla de carga inicial
  if (isLoading) {
    return (
      <div className="min-h-screen bg-stone-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-emerald-200 border-t-emerald-600 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-stone-500 text-sm">Cargando...</p>
        </div>
      </div>
    );
  }

  // Página de registro
  if (showRegister) {
    return <RegisterPage onBack={() => setShowRegister(false)} />;
  }

  // Si no está autenticado, mostrar login
  if (!isAuthenticated) {
    return <LoginPage onNavigateRegister={() => setShowRegister(true)} />;
  }

  // Renderizar la página actual
  const renderPage = () => {
    // Guard de acceso: páginas restringidas redirigen al dashboard
    if (currentPage === 'docs' && user?.rol !== 'superadmin') {
      return <DashboardPage onNavigate={setCurrentPage} />;
    }
    if (currentPage === 'reports' && !['admin', 'manager'].includes(user?.rol ?? '')) {
      return <DashboardPage onNavigate={setCurrentPage} />;
    }
    if (currentPage === 'settings' && !['admin', 'manager'].includes(user?.rol ?? '')) {
      return <DashboardPage onNavigate={setCurrentPage} />;
    }
    if (currentPage === 'assistant' && !['admin', 'manager'].includes(user?.rol ?? '')) {
      return <DashboardPage onNavigate={setCurrentPage} />;
    }
    if (currentPage === 'whatsapp' && !['admin', 'manager'].includes(user?.rol ?? '')) {
      return <DashboardPage onNavigate={setCurrentPage} />;
    }
    if (currentPage === 'payments' && !['admin', 'manager', 'receptionist'].includes(user?.rol ?? '')) {
      return <DashboardPage onNavigate={setCurrentPage} />;
    }

    switch (currentPage) {
      case 'dashboard':
        return <DashboardPage onNavigate={setCurrentPage} />;
      case 'tenants':
        return <TenantsPage />;
      case 'users':
        return <UsersPage />;
      case 'appointments':
        return <AppointmentsPage />;
      case 'services':
        return <ServicesPage />;
      case 'patients':
        return <PatientsPage onNavigate={setCurrentPage} />;
      case 'reports':
        return <ReportsPage />;
      case 'settings':
        return <SettingsPage />;
      case 'assistant':
        return <AssistantPage />;
      case 'whatsapp':
        return <WhatsAppPage />;
      case 'payments':
        return <PaymentsPage />;
      case 'docs':
        return <DocumentationPage />;
      default:
        return <DashboardPage />;
    }
  };

  return (
    <Layout currentPage={currentPage} onNavigate={setCurrentPage}>
      {renderPage()}
    </Layout>
  );
}

// ============================================================
// Componente App principal con providers
// ============================================================
export default function App() {
  // Ruta pública de la tarjeta de fidelidad (/tarjeta/{token}): se
  // renderiza FUERA del AuthProvider y del layout autenticado.
  const match = window.location.pathname.match(/^\/tarjeta\/([^/]+)\/?$/);
  if (match) {
    return <PublicWalletPage token={decodeURIComponent(match[1])} />;
  }

  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  );
}
