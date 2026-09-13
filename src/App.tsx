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
import { AppointmentsPage, PatientsPage } from './pages/PlaceholderPages';
import DocumentationPage from './pages/DocumentationPage';

// ============================================================
// Router interno de la aplicación
// ============================================================
function AppRouter() {
  const { isAuthenticated, isLoading } = useAuth();
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
    switch (currentPage) {
      case 'dashboard':
        return <DashboardPage />;
      case 'tenants':
        return <TenantsPage />;
      case 'users':
        return <UsersPage />;
      case 'appointments':
        return <AppointmentsPage />;
      case 'patients':
        return <PatientsPage />;
      case 'settings':
        return <SettingsPage />;
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
  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  );
}
