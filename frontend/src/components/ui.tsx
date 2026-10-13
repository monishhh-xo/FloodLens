import type { ReactNode } from 'react'
import type { RiskLevel } from '../api/types'
import { RISK_BADGE } from '../lib/format'

export function Card({
  title,
  subtitle,
  children,
  actions,
  className = '',
}: {
  title?: string
  subtitle?: string
  children: ReactNode
  actions?: ReactNode
  className?: string
}) {
  return (
    <section className={`bg-white rounded-lg border border-slate-200 shadow-sm ${className}`}>
      {(title || actions) && (
        <header className="flex items-start justify-between gap-2 px-5 pt-4 pb-2 border-b border-slate-100">
          <div>
            {title && <h2 className="text-sm font-semibold text-slate-800">{title}</h2>}
            {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  )
}

export function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${RISK_BADGE[level]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {level}
    </span>
  )
}

export function Badge({
  children,
  tone = 'slate',
}: {
  children: ReactNode
  tone?: 'slate' | 'blue' | 'amber' | 'red' | 'green'
}) {
  const tones: Record<string, string> = {
    slate: 'bg-slate-100 text-slate-700 border-slate-300',
    blue: 'bg-sky-50 text-sky-800 border-sky-300',
    amber: 'bg-amber-50 text-amber-800 border-amber-300',
    red: 'bg-red-50 text-red-800 border-red-300',
    green: 'bg-emerald-50 text-emerald-800 border-emerald-300',
  }
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-medium border ${tones[tone]}`}>
      {children}
    </span>
  )
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-6 justify-center text-slate-500">
      <span className="h-5 w-5 rounded-full border-2 border-slate-300 border-t-sky-600 animate-spin" />
      {label && <span className="text-sm">{label}</span>}
    </div>
  )
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-3 py-2">
      {Array.from({ length: lines }).map((_, index) => (
        <div key={index} className="h-4 rounded bg-slate-200 animate-pulse" style={{ width: `${100 - index * 15}%` }} />
      ))}
    </div>
  )
}

export function EmptyState({ title, message }: { title: string; message?: string }) {
  return (
    <div className="text-center py-8 px-4">
      <div className="mx-auto h-10 w-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 text-xl">
        ∅
      </div>
      <p className="mt-3 text-sm font-medium text-slate-600">{title}</p>
      {message && <p className="mt-1 text-xs text-slate-500 max-w-md mx-auto">{message}</p>}
    </div>
  )
}

export function ErrorState({
  title,
  message,
  onRetry,
}: {
  title: string
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-4">
      <p className="text-sm font-semibold text-red-800">{title}</p>
      <p className="mt-1 text-xs text-red-700 break-words">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 px-3 py-1.5 text-xs font-medium rounded bg-red-700 text-white hover:bg-red-800"
        >
          Retry
        </button>
      )}
    </div>
  )
}

export function ScoreBar({ score, color }: { score: number; color: string }) {
  const percent = Math.max(0, Math.min(100, score))
  return (
    <div className="h-2 w-full rounded-full bg-slate-200 overflow-hidden" role="progressbar" aria-valuenow={score} aria-valuemin={0} aria-valuemax={100}>
      <div className="h-full rounded-full transition-all" style={{ width: `${percent}%`, backgroundColor: color }} />
    </div>
  )
}

export function PrimaryButton({
  children,
  onClick,
  disabled,
  loading,
}: {
  children: ReactNode
  onClick?: () => void
  disabled?: boolean
  loading?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-sky-700 text-white text-sm font-semibold hover:bg-sky-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
    >
      {loading && <span className="h-3.5 w-3.5 rounded-full border-2 border-white/40 border-t-white animate-spin" />}
      {children}
    </button>
  )
}