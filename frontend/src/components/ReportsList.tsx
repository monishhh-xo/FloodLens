import type { Report } from '../api/types'
import { api } from '../api/client'
import { useApi } from '../hooks/useApi'
import { formatRelative } from '../lib/format'
import { Badge, EmptyState, ErrorState, RiskBadge, Spinner } from './ui'

export default function ReportsList({
  onError,
}: {
  onError?: (message: string) => void
}) {
  const { data, loading, error, reload } = useApi(() => api.reports(25))

  if (loading) return <Spinner label="Loading community reports…" />
  if (error)
    return (
      <ErrorState
        title="Could not load reports"
        message={error}
        onRetry={() => {
          onError?.(error)
          reload()
        }}
      />
    )
  if (!data || data.reports.length === 0)
    return (
      <EmptyState
        title="No reports yet"
        message="Be the first to submit a community waterlogging observation; it will appear here marked as user-submitted."
      />
    )

  const reports: Report[] = data.reports

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <Badge tone="blue">{reports.length} recent · {data.source}</Badge>
        <button
          type="button"
          onClick={reload}
          className="text-xs font-medium text-sky-700 hover:text-sky-800"
        >
          ↻ Refresh
        </button>
      </div>

      <ul className="space-y-3">
        {reports.map((report) => (
          <li key={report.id} className="rounded-md border border-slate-200 bg-white px-3 py-2.5">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-2">
                <RiskBadge level={report.severity} />
                <span className="text-sm font-semibold text-slate-800">
                  {report.zone_name ?? 'Unknown zone'}
                </span>
              </div>
              <span className="text-[11px] text-slate-400">{formatRelative(report.created_at_utc)}</span>
            </div>
            <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">{report.description}</p>
            <div className="flex items-center gap-2 mt-2">
              <Badge tone="amber">user-submitted</Badge>
              <Badge tone="slate">unverified</Badge>
              <span className="text-[10px] text-slate-400 ml-auto">
                {report.latitude.toFixed(4)}, {report.longitude.toFixed(4)}
              </span>
            </div>
          </li>
        ))}
      </ul>

      <p className="mt-3 text-[11px] text-slate-400 leading-snug">{data.note}</p>
    </div>
  )
}