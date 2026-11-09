// ============================================================
// ReportsPage.tsx - Reportes Financieros y de Rendimiento
// KPIs del SPA, top servicios y rendimiento por terapeuta
// ============================================================

import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { api, ApiError } from '../services/api';
import { FinancialReport } from '../types';
import { getTenantTimezone, tzParts, pad2 } from '../utils/dateTime';
import {
  Wallet, CalendarCheck, CalendarX2, Receipt, UserPlus,
  FileDown, Printer, TrendingUp, Users, Award
} from 'lucide-react';

// ============================================================
// Rangos de fechas predefinidos
// ============================================================
type RangeKey = 'month' | 'prevMonth' | 'last3' | 'year';

const RANGES: { key: RangeKey; label: string }[] = [
  { key: 'month', label: 'Este Mes' },
  { key: 'prevMonth', label: 'Mes Anterior' },
  { key: 'last3', label: 'Últimos 3 Meses' },
  { key: 'year', label: 'Año Actual' },
];

// Último día de un mes (m = 1..12)
function lastDayOfMonth(y: number, m: number): number {
  return new Date(y, m, 0).getDate();
}

// Rango en la zona horaria del tenant y que cubre el PERIODO COMPLETO
// (no se corta en "hoy"): así "Este Mes" incluye las citas futuras del resto
// del mes, incluidas las canceladas. Las fechas se calculan con la zona del
// tenant (el backend guarda date_time naive en hora local del negocio).
function rangeToDates(key: RangeKey, tz: string): { desde: string; hasta: string } {
  const { y, m } = tzParts(new Date(), tz);
  const m2 = (mm: number) => String(mm).padStart(2, '0');

  switch (key) {
    case 'month':
      return { desde: `${y}-${m2(m)}-01`, hasta: `${y}-${m2(m)}-${m2(lastDayOfMonth(y, m))}` };
    case 'prevMonth': {
      const pm = m - 1 <= 0 ? 12 : m - 1;
      const py = m - 1 <= 0 ? y - 1 : y;
      return { desde: `${py}-${m2(pm)}-01`, hasta: `${py}-${m2(pm)}-${m2(lastDayOfMonth(py, pm))}` };
    }
    case 'last3': {
      const sm = m - 2 <= 0 ? m - 2 + 12 : m - 2;
      const sy = m - 2 <= 0 ? y - 1 : y;
      return { desde: `${sy}-${m2(sm)}-01`, hasta: `${y}-${m2(m)}-${m2(lastDayOfMonth(y, m))}` };
    }
    case 'year':
      return { desde: `${y}-01-01`, hasta: `${y}-12-31` };
  }
}

// ============================================================
// Componente principal
// ============================================================
export default function ReportsPage() {
  const { tenant } = useAuth();
  const tz = getTenantTimezone(tenant);
  const [range, setRange] = useState<RangeKey>('month');
  const [report, setReport] = useState<FinancialReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const currencyFormatter = new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: tenant?.moneda || 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
  const fmtMoney = (v: number) => currencyFormatter.format(v);

  const loadReport = useCallback(async (key: RangeKey, timezone: string) => {
    setLoading(true);
    setError('');
    try {
      const { desde, hasta } = rangeToDates(key, timezone);
      const data = await api.getFinancialReport({ desde, hasta });
      setReport(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cargar el reporte');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReport(range, tz);
  }, [range, tz, loadReport]);

  // ----------------------------------------------------------
  // Exportar CSV
  // ----------------------------------------------------------
  const handleExportCSV = () => {
    if (!report) return;
    const rows: string[][] = [];
    const csv = (cells: string[]) => cells.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',');

    rows.push(['Reporte Financiero', '']);
    rows.push(['Periodo', `${report.desde} a ${report.hasta}`]);
    rows.push([]);
    rows.push(['KPI', 'Valor']);
    rows.push(['Total Ingresos', String(report.total_ingresos)]);
    rows.push(['Total Citas', String(report.total_citas)]);
    rows.push(['Completadas', String(report.completadas)]);
    rows.push(['Canceladas', String(report.canceladas)]);
    rows.push(['Ticket Promedio', String(report.ticket_promedio)]);
    rows.push(['Pacientes Nuevos', String(report.pacientes_nuevos)]);
    rows.push([]);
    rows.push(['Top Servicios']);
    rows.push(['Servicio', 'Cantidad', 'Ingresos']);
    report.top_servicios.forEach((s) => rows.push([s.servicio, String(s.cantidad), String(s.ingresos)]));
    rows.push([]);
    rows.push(['Rendimiento por Terapeuta']);
    rows.push(['Terapeuta', 'Citas Completadas', 'Ingresos']);
    report.rendimiento_terapeutas.forEach((t) => rows.push([t.terapeuta, String(t.completadas), String(t.ingresos)]));

    const blob = new Blob([`\uFEFF${rows.map((r) => csv(r)).join('\n')}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `reporte-financiero-${report.desde}-${report.hasta}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const kpis = report ? [
    {
      label: 'Total Ingresos',
      value: fmtMoney(report.total_ingresos),
      sub: `Citas completadas: ${report.completadas}`,
      icon: <Wallet size={22} />,
      color: 'emerald',
    },
    {
      label: 'Total Citas',
      value: String(report.total_citas),
      sub: `${report.completadas} completadas`, 
      icon: <CalendarCheck size={22} />,
      color: 'blue',
    },
    {
      label: 'Canceladas',
      value: String(report.canceladas),
      sub: `${report.total_citas} citas en total`,
      icon: <CalendarX2 size={22} />,
      color: 'red',
    },
    {
      label: 'Ticket Promedio',
      value: fmtMoney(report.ticket_promedio),
      sub: 'Por cita atendida',
      icon: <Receipt size={22} />,
      color: 'violet',
    },
    {
      label: 'Pacientes Nuevos',
      value: String(report.pacientes_nuevos),
      sub: 'Registrados en el periodo',
      icon: <UserPlus size={22} />,
      color: 'amber',
    },
  ] : [];

  const colorMap: Record<string, { bg: string; text: string }> = {
    emerald: { bg: 'bg-emerald-50', text: 'text-emerald-600' },
    blue: { bg: 'bg-blue-50', text: 'text-blue-600' },
    red: { bg: 'bg-red-50', text: 'text-red-600' },
    violet: { bg: 'bg-violet-50', text: 'text-violet-600' },
    amber: { bg: 'bg-amber-50', text: 'text-amber-600' },
  };

  const maxServicio = report
    ? Math.max(1, ...report.top_servicios.map((s) => s.cantidad))
    : 1;

  return (
    <div className="space-y-6">
      {error && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-stone-800">Reportes Financieros</h1>
          <p className="text-stone-500 mt-1">Rendimiento y finanzas de tu SPA</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCSV}
            disabled={!report}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium rounded-xl hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 transition-all"
          >
            <FileDown size={16} />
            Exportar CSV
          </button>
          <button
            onClick={() => window.print()}
            className="inline-flex items-center gap-2 px-4 py-2.5 border border-stone-200 rounded-xl text-sm font-medium text-stone-600 hover:bg-stone-50 transition-colors"
          >
            <Printer size={16} />
            Imprimir
          </button>
        </div>
      </div>

      {/* Rango de fechas */}
      <div className="flex flex-wrap items-center gap-2 bg-white rounded-2xl p-2 border border-stone-100 shadow-sm">
        {RANGES.map((r) => (
          <button
            key={r.key}
            onClick={() => setRange(r.key)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              range === r.key
                ? 'bg-emerald-50 text-emerald-700 shadow-sm'
                : 'text-stone-500 hover:bg-stone-50 hover:text-stone-700'
            }`}
          >
            {r.label}
          </button>
        ))}
        {report && (
          <span className="ml-auto px-4 text-xs text-stone-400">
            Periodo: {report.desde} al {report.hasta}
          </span>
        )}
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-28 bg-white rounded-2xl border border-stone-100 animate-pulse" />
          ))}
        </div>
      ) : report ? (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
            {kpis.map((kpi) => {
              const c = colorMap[kpi.color];
              return (
                <div key={kpi.label} className="bg-white rounded-2xl p-5 border border-stone-100 shadow-sm">
                  <div className={`w-11 h-11 rounded-xl ${c.bg} ${c.text} flex items-center justify-center mb-3`}>
                    {kpi.icon}
                  </div>
                  <p className="text-xs font-medium text-stone-400 uppercase tracking-wider">{kpi.label}</p>
                  <p className="text-xl font-bold text-stone-800 mt-1 truncate">{kpi.value}</p>
                  <p className="text-xs text-stone-400 mt-1">{kpi.sub}</p>
                </div>
              );
            })}
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {/* Top Servicios */}
            <div className="bg-white rounded-2xl p-6 border border-stone-100 shadow-sm">
              <div className="flex items-center gap-2 mb-5">
                <TrendingUp size={20} className="text-emerald-600" />
                <h2 className="text-lg font-semibold text-stone-800">Top Servicios</h2>
              </div>
              {report.top_servicios.length === 0 ? (
                <div className="text-center py-10 bg-stone-50 rounded-xl">
                  <Award size={32} className="mx-auto text-stone-300 mb-2" />
                  <p className="text-sm text-stone-400">Sin servicios en este periodo</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {report.top_servicios.slice(0, 6).map((s, idx) => (
                    <div key={s.servicio}>
                      <div className="flex items-center justify-between mb-1.5 text-sm">
                        <span className="font-medium text-stone-700 truncate mr-2">
                          <span className="text-stone-400 font-semibold mr-1.5">{idx + 1}.</span>
                          {s.servicio}
                        </span>
                        <span className="flex items-center gap-3 shrink-0">
                          <span className="text-stone-500">{s.cantidad} citas</span>
                          <span className="font-semibold text-stone-700">{fmtMoney(s.ingresos)}</span>
                        </span>
                      </div>
                      <div className="h-2 bg-stone-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-emerald-400 to-teal-500 rounded-full transition-all duration-700"
                          style={{ width: `${Math.round((s.cantidad / maxServicio) * 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Rendimiento por Terapeuta */}
            <div className="bg-white rounded-2xl p-6 border border-stone-100 shadow-sm">
              <div className="flex items-center gap-2 mb-5">
                <Users size={20} className="text-blue-600" />
                <h2 className="text-lg font-semibold text-stone-800">Rendimiento por Terapeuta</h2>
              </div>
              {report.rendimiento_terapeutas.length === 0 ? (
                <div className="text-center py-10 bg-stone-50 rounded-xl">
                  <Users size={32} className="mx-auto text-stone-300 mb-2" />
                  <p className="text-sm text-stone-400">Sin actividad de terapeutas en este periodo</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-stone-400 uppercase tracking-wider border-b border-stone-100">
                        <th className="py-2.5 pr-3 font-medium">Terapeuta</th>
                        <th className="py-2.5 pr-3 font-medium text-right">Completadas</th>
                        <th className="py-2.5 font-medium text-right">Ingresos</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.rendimiento_terapeutas.map((t) => (
                        <tr key={t.terapeuta} className="border-b border-stone-50 hover:bg-stone-50/50 transition-colors">
                          <td className="py-3 pr-3 font-medium text-stone-700">{t.terapeuta}</td>
                          <td className="py-3 pr-3 text-right">
                            <span className="inline-flex items-center gap-1 text-stone-600">
                              {t.completadas}
                              <span className="text-xs text-stone-400">citas</span>
                            </span>
                          </td>
                          <td className="py-3 text-right font-semibold text-stone-800">
                            {fmtMoney(t.ingresos)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Resumen del periodo */}
          <div className="p-4 bg-white rounded-2xl border border-stone-100 shadow-sm flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-stone-500">
            <span className="flex items-center gap-1.5">
              <TrendingUp size={15} className="text-emerald-600" />
              <strong className="text-stone-700">{report.completadas}</strong> citas completadas de{' '}
              <strong className="text-stone-700">{report.total_citas}</strong> agendadas
            </span>
            <span className="flex items-center gap-1.5">
              <CalendarCheck size={15} className="text-blue-600" />
              Tasa de finalización:{' '}
              <strong className="text-stone-700">
                {report.total_citas ? Math.round((report.completadas / report.total_citas) * 100) : 0}%
              </strong>
            </span>
            <span className="flex items-center gap-1.5">
              <Wallet size={15} className="text-emerald-600" />
              Reservas canceladas:{' '}
              <strong className="text-stone-700">{report.canceladas}</strong>
            </span>
          </div>
        </>
      ) : null}
    </div>
  );
}