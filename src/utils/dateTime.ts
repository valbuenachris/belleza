// ============================================================
// Utilidades de fecha/hora con la zona horaria del tenant
// Todas las horas del sitio deben usar la zona del tenant
// configurada en la información general (tenant.timezone).
// ============================================================

import { Tenant } from '../types';

export const DEFAULT_TZ = 'America/Bogota';

export function getTenantTimezone(tenant: Tenant | null): string {
  return tenant?.timezone || DEFAULT_TZ;
}

/**
 * Parte de fecha (año, mes, día) de un Date en la zona horaria dada.
 * Se usa para periodos de reportes: el "mes actual" debe calcularse
 * en la zona del tenant, no en la del navegador.
 */
export function tzParts(date: Date, timezone: string = DEFAULT_TZ): { y: number; m: number; d: number } {
  try {
    const parts = new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      timeZone: timezone,
    }).formatToParts(date);
    const get = (t: string) => Number(parts.find((p) => p.type === t)?.value ?? 0);
    return { y: get('year'), m: get('month'), d: get('day') };
  } catch {
    return { y: date.getFullYear(), m: date.getMonth() + 1, d: date.getDate() };
  }
}

export function pad2(n: number): string {
  return String(n).padStart(2, '0');
}

/**
 * Convierte un ISO (posiblemente naive, sin Z) a un Date tratándolo como UTC.
 * El backend guarda datetimes con datetime.utcnow() y los serializa SIN zona
 * (ej. "2026-11-09T04:49:00"). Si se hace new Date(iso) directamente, JS lo
 * interpreta como hora local del navegador y la conversión a la zona del
 * tenant queda mal. Aquí se fuerza las cadenas naive como UTC.
 */
export function parseIsoAsUtc(iso?: string | null): Date {
  if (!iso) return new Date(NaN);
  const hasTz = /(Z|[+-]\d{2}:?\d{2})$/.test(iso);
  return new Date(hasTz ? iso : `${iso}Z`);
}

function toCommon(iso?: string | null): Date {
  return parseIsoAsUtc(iso);
}

export function fmtTime(iso?: string | null, timezone: string = DEFAULT_TZ): string {
  if (!iso) return '';
  const d = toCommon(iso);
  if (isNaN(d.getTime())) return '';
  try {
    return d.toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: timezone,
    });
  } catch {
    return d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  }
}

export function fmtDate(iso?: string | null, timezone: string = DEFAULT_TZ): string {
  if (!iso) return '—';
  const d = toCommon(iso);
  if (isNaN(d.getTime())) return '—';
  try {
    return d.toLocaleDateString('es-ES', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      timeZone: timezone,
    });
  } catch {
    return d.toLocaleDateString('es-ES', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  }
}

export function fmtDateTime(iso?: string | null, timezone: string = DEFAULT_TZ): string {
  if (!iso) return '—';
  const d = toCommon(iso);
  if (isNaN(d.getTime())) return '—';
  try {
    return d.toLocaleString('es-ES', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: timezone,
    });
  } catch {
    return d.toLocaleString('es-ES', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}

export function fmtLongDate(date?: Date | string, timezone: string = DEFAULT_TZ): string {
  const d = typeof date === 'string' ? parseIsoAsUtc(date) : date;
  if (!d || isNaN(d.getTime())) return '';
  try {
    return d.toLocaleDateString('es-ES', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      timeZone: timezone,
    });
  } catch {
    return d.toLocaleDateString('es-ES', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  }
}