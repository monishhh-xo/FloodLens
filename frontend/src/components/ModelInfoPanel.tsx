import { api } from '../api/client'
import type { ModelInfoResponse } from '../api/types'
import { useApi } from '../hooks/useApi'
import { formatNumber, formatPct } from '../lib/format'
import { Badge, EmptyState, ErrorState, Spinner } from './ui'

function MetricCell({ value, bold }: { value: number; bold?: boolean }) {
  return (
    <td className={`py-1.5 pr-4 text-right tabular-nums ${bold ? 'font-bold text-slate-900' : 'text-slate-600'}`}>
      {formatNumber(value, 4)}
    </td>
  )
}

export default function ModelInfoPanel() {
  const { data, loading, error, reload } = useApi<ModelInfoResponse>(() => api.modelInfo())

  if (loading) return <Spinner label="Loading model information…" />
  if (error) return <ErrorState title="Model information unavailable" message={error} onRetry={reload} />
  if (!data) return <EmptyState title="No model information" />

  const logreg = data.metrics.logistic_regression
  const forest = data.metrics.random_forest_comparison
  const baseline = data.metrics.majority_class_baseline
  const control = data.metrics.shuffled_label_control
  const verdict = data.metrics.verdict
  const confusion = logreg.test.confusion_matrix

  return (
    <div className="space-y-6">
      <div className="rounded-md border border-red-300 bg-red-50 p-4">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge tone="red">PROTOTYPE · NOT RELIABLE</Badge>
          <span className="text-sm font-bold text-red-900">{data.algorithm}</span>
          <span className="text-xs text-red-700">v{data.model_version} · trained {new Date(data.trained_at_utc).toLocaleDateString()}</span>
        </div>
        <p className="text-xs text-red-800 mt-2 leading-relaxed">{data.warning}</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {/* Dataset integrity */}
        <div className="rounded-md border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-slate-800 mb-3">Verified at request time</h3>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
            <div>
              <dt className="text-slate-500">Rows × columns</dt>
              <dd className="font-semibold text-slate-800">
                {data.dataset_integrity.rows} × {data.dataset_integrity.columns}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Null / duplicate values</dt>
              <dd className="font-semibold text-slate-800">
                {data.dataset_integrity.null_values} / {data.dataset_integrity.duplicate_rows}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Target balance</dt>
              <dd className="font-semibold text-slate-800">
                0: {formatPct(data.dataset_integrity.target_balance['0'])} · 1: {formatPct(data.dataset_integrity.target_balance['1'])}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">File SHA-256</dt>
              <dd className="font-mono text-[10px] text-slate-600 break-all">
                {data.dataset_integrity.sha256.slice(0, 32)}…
              </dd>
            </div>
          </dl>
          <p className="text-[11px] text-slate-400 mt-3 leading-snug">{data.dataset_integrity.provenance}</p>
        </div>

        {/* Metrics */}
        <div className="rounded-md border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-slate-800 mb-3">Real evaluation (stratified 80/20, no leakage)</h3>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-slate-200">
                <th className="py-1 pr-3 text-left font-medium">Model</th>
                <th className="py-1 pr-3 text-right font-medium">Acc</th>
                <th className="py-1 pr-3 text-right font-medium">Prec</th>
                <th className="py-1 pr-3 text-right font-medium">Rec</th>
                <th className="py-1 pr-3 text-right font-medium">F1</th>
                <th className="py-1 text-right font-medium">AUC</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-slate-100">
                <td className="py-1.5 pr-3 text-slate-800">Logistic — test</td>
                <MetricCell value={logreg.test.accuracy} bold />
                <MetricCell value={logreg.test.precision} />
                <MetricCell value={logreg.test.recall} />
                <MetricCell value={logreg.test.f1} />
                <MetricCell value={logreg.test.roc_auc} bold />
              </tr>
              <tr className="border-b border-slate-100">
                <td className="py-1.5 pr-3 text-slate-800">Random forest — test</td>
                <MetricCell value={forest.test.accuracy} />
                <MetricCell value={forest.test.precision} />
                <MetricCell value={forest.test.recall} />
                <MetricCell value={forest.test.f1} />
                <MetricCell value={forest.test.roc_auc} />
              </tr>
              <tr className="border-b border-slate-100">
                <td className="py-1.5 pr-3 text-slate-800">Majority baseline</td>
                <MetricCell value={baseline.accuracy} />
                <td className="py-1.5 pr-4 text-right text-slate-400">—</td>
                <td className="py-1.5 pr-4 text-right text-slate-400">—</td>
                <td className="py-1.5 pr-4 text-right text-slate-400">—</td>
                <td className="py-1.5 text-right text-slate-400">—</td>
              </tr>
              <tr>
                <td className="py-1.5 pr-3 text-slate-800">Shuffled-label control</td>
                <MetricCell value={control.accuracy_vs_true_labels} />
                <td className="py-1.5 pr-4 text-right text-slate-400">—</td>
                <td className="py-1.5 pr-4 text-right text-slate-400">—</td>
                <td className="py-1.5 pr-4 text-right text-slate-400">—</td>
                <MetricCell value={control.roc_auc_vs_true_labels} bold />
              </tr>
            </tbody>
          </table>
          <p className="text-[11px] text-slate-500 mt-2 leading-snug">{control.note}</p>
        </div>
      </div>

      {/* Verdict */}
      <div className={`rounded-md border p-4 ${verdict.signal_detected ? 'border-amber-300 bg-amber-50' : 'border-rose-300 bg-rose-50'}`}>
        <div className="flex items-center gap-2">
          <Badge tone={verdict.signal_detected ? 'amber' : 'red'}>
            {verdict.signal_detected ? 'SIGNAL DETECTED' : 'NO SIGNAL DETECTED'}
          </Badge>
          <span className="text-xs text-slate-600">
            test AUC {formatNumber(verdict.test_auc, 3)} vs control AUC {formatNumber(verdict.control_auc, 3)} · baseline improvement{' '}
            {verdict.accuracy_improvement_over_baseline > 0 ? '+' : ''}
            {formatNumber(verdict.accuracy_improvement_over_baseline, 4)}
          </span>
        </div>
        <p className="text-sm text-slate-800 mt-2 leading-relaxed">{verdict.summary}</p>
      </div>

      {/* Confusion matrix */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="rounded-md border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-slate-800 mb-2">Confusion matrix (logistic, test)</h3>
          <table className="text-xs w-full">
            <tbody>
              <tr>
                <td className="p-1 w-24 text-slate-500">Predicted ↓ / actual →</td>
                <td className="p-1 text-center text-slate-600">0 (no flood)</td>
                <td className="p-1 text-center text-slate-600">1 (flooded)</td>
              </tr>
              <tr>
                <td className="p-1 text-slate-600">0 (no flood)</td>
                <td className="p-1 text-center font-bold bg-emerald-50 text-slate-800">{confusion.true_negative}</td>
                <td className="p-1 text-center font-bold bg-red-50 text-slate-800">{confusion.false_negative}</td>
              </tr>
              <tr>
                <td className="p-1 text-slate-600">1 (flooded)</td>
                <td className="p-1 text-center font-bold bg-red-50 text-slate-800">{confusion.false_positive}</td>
                <td className="p-1 text-center font-bold bg-emerald-50 text-slate-800">{confusion.true_positive}</td>
              </tr>
            </tbody>
          </table>
          <p className="text-[11px] text-slate-400 mt-2">
            Nearly every cell ≈ {formatNumber(logreg.test.n / 4, 0)} — the model assigns both classes at random.
          </p>
        </div>

        {/* Feature relevance */}
        <div className="rounded-md border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-slate-800 mb-2">Per-feature relevance (univariate AUC)</h3>
          <div className="space-y-1.5">
            {data.metrics.univariate_feature_signal.numeric.slice(0, 8).map((feature) => {
              const distance = feature.distance_from_chance
              return (
                <div key={feature.feature} className="flex items-center gap-2 text-xs">
                  <span className="w-40 truncate text-slate-600">{feature.feature.replaceAll('_', ' ')}</span>
                  <div className="flex-1 h-2 rounded bg-slate-100 relative">
                    <div
                      className="absolute top-0 left-0 h-full rounded bg-sky-500"
                      style={{ width: `${Math.max(2, Math.min(100, distance * 200))}%` }}
                    />
                  </div>
                  <span className="w-16 text-right tabular-nums text-slate-500">{formatNumber(feature.auc, 3)}</span>
                </div>
              )
            })}
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Bars show distance from 0.5 (random). The strongest feature barely moves — this is the
            measurable proof that the dataset carries no signal.
          </p>
        </div>
      </div>

      {/* Artifact check */}
      {data.artifact_check.available && (
        <div className="rounded-md border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-slate-800 mb-2">Artifact runs end to end — held-out synthetic rows</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-slate-500 border-b border-slate-200">
                  <th className="py-1 pr-3 text-left font-medium">Latitude</th>
                  <th className="py-1 pr-3 text-left font-medium">Longitude</th>
                  <th className="py-1 pr-3 text-right font-medium">Rain (mm)</th>
                  <th className="py-1 pr-3 text-right font-medium">Actual</th>
                  <th className="py-1 text-right font-medium">P(flood) from artifact</th>
                </tr>
              </thead>
              <tbody>
                {data.artifact_check.sampled_rows.map((row, index) => (
                  <tr key={index} className="border-b border-slate-100">
                    <td className="py-1.5 pr-3 tabular-nums text-slate-600">{row.latitude}</td>
                    <td className="py-1.5 pr-3 tabular-nums text-slate-600">{row.longitude}</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums text-slate-600">{formatNumber(row.rainfall_mm)}</td>
                    <td className="py-1.5 pr-3 text-right text-slate-600">{row.actual_label}</td>
                    <td className="py-1.5 text-right tabular-nums text-slate-600">
                      {row.predicted_probability !== null ? formatNumber(row.predicted_probability, 3) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-slate-400 mt-2 leading-snug">{data.artifact_check.note}</p>
        </div>
      )}

      {/* Limitations */}
      <div className="rounded-md border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-800 mb-2">Documented limitations</h3>
        <ul className="list-disc pl-5 space-y-1 text-xs text-slate-600">
          {data.limitations.map((limitation, index) => (
            <li key={index}>{limitation}</li>
          ))}
        </ul>
        <p className="text-[11px] text-slate-400 mt-2">{data.note}</p>
      </div>
    </div>
  )
}