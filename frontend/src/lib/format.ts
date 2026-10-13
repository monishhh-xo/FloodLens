import type { RiskLevel } from '../api/types'

/** Semantic colours for each risk band. */
export const RISK_HEX: Record<RiskLevel, string> = {
  Low: '#16a34a',
  Moderate: '#d97706',
  High: '#ea580c',
  Severe: '#dc2626',
}

/** Tailwind utility classes for the same risk bands. */
export const RISK_BADGE: Record<RiskLevel, string> = {
  Low: 'bg-green-100 text-green-800 border-green-300',
  Moderate: 'bg-amber-100 text-amber-800 border-amber-300',
  High: 'bg-orange-100 text-orange-800 border-orange-300',
  Severe: 'bg-red-100 text-red-800 border-red-300',
}

export const RISK_BAR: Record<RiskLevel, string> = {
  Low: 'bg-green-500',
  Moderate: 'bg-amber-500',
  High: 'bg-orange-500',
  Severe: 'bg-red-600',
}

export function levelOf(score: number): RiskLevel {
  if (score < 25) return 'Low'
  if (score < 50) return 'Moderate'
  if (score < 75) return 'High'
  return 'Severe'
}

export function formatUtc(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString(undefined, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '—'
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return iso
  const seconds = Math.max(0, Math.round((Date.now() - then) / 1000))
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 48) return `${hours} h ago`
  return formatUtc(iso)
}

export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  })
}

export function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${Math.round(value)}%`
}