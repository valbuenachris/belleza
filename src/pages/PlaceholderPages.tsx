// ============================================================
// Páginas Placeholder - Módulos en desarrollo
// ============================================================

import React from 'react';
import { Calendar, UserCheck, ClipboardList, BarChart3, Construction } from 'lucide-react';

interface PlaceholderPageProps {
  title: string;
  description: string;
  icon: React.ReactNode;
}

function PlaceholderPage({ title, description, icon }: PlaceholderPageProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="w-20 h-20 bg-emerald-50 rounded-2xl flex items-center justify-center mb-6">
        <Construction size={36} className="text-emerald-500" />
      </div>
      <h1 className="text-2xl font-bold text-stone-800 mb-2">{title}</h1>
      <p className="text-stone-500 max-w-md mb-8">{description}</p>
      <div className="bg-white rounded-2xl border border-stone-100 p-8 max-w-lg w-full">
        <h3 className="text-sm font-semibold text-stone-700 mb-4">Próximamente en este módulo:</h3>
        <ul className="space-y-3 text-left">
          <li className="flex items-center gap-3 text-sm text-stone-600">
            <div className="w-6 h-6 bg-emerald-100 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-emerald-600 text-xs">✓</span>
            </div>
            Gestión completa con interfaz intuitiva
          </li>
          <li className="flex items-center gap-3 text-sm text-stone-600">
            <div className="w-6 h-6 bg-emerald-100 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-emerald-600 text-xs">✓</span>
            </div>
            Integración con el sistema multitenant
          </li>
          <li className="flex items-center gap-3 text-sm text-stone-600">
            <div className="w-6 h-6 bg-emerald-100 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-emerald-600 text-xs">✓</span>
            </div>
            Reportes y estadísticas en tiempo real
          </li>
          <li className="flex items-center gap-3 text-sm text-stone-600">
            <div className="w-6 h-6 bg-emerald-100 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-emerald-600 text-xs">✓</span>
            </div>
            API REST completa con FastAPI
          </li>
        </ul>
      </div>
    </div>
  );
}

export function AppointmentsPage() {
  return (
    <PlaceholderPage
      title="Gestión de Citas"
      description="Calendario interactivo para agendar, modificar y cancelar citas de tus pacientes con recordatorios automáticos."
      icon={<Calendar size={36} />}
    />
  );
}

export function PatientsPage() {
  return (
    <PlaceholderPage
      title="Gestión de Pacientes"
      description="Historial clínico, fichas de pacientes, alergias, preferencias y seguimiento de tratamientos."
      icon={<UserCheck size={36} />}
    />
  );
}

export function ServicesPage() {
  return (
    <PlaceholderPage
      title="Catálogo de Servicios"
      description="Define tus servicios, precios, duración, categorías y asignación de terapeutas especializados."
      icon={<ClipboardList size={36} />}
    />
  );
}

export function ReportsPage() {
  return (
    <PlaceholderPage
      title="Reportes y Analíticas"
      description="Dashboards avanzados con métricas de rendimiento, ingresos, ocupación y satisfacción del cliente."
      icon={<BarChart3 size={36} />}
    />
  );
}
