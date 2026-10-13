import { useEffect, useRef, useState } from 'react'
import { api } from './api/client'
import type { AssessResponse, Report, Zone } from './api/types'
import { useApi } from './hooks/useApi'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import StatusBanner from './components/StatusBanner'
import RiskSummaryCards, { type RiskLevelFilter } from './components/RiskSummaryCards'
import ZoneMap from './components/ZoneMap'
import ZoneDetail from './components/ZoneDetail'
import AssessmentPanel from './components/AssessmentPanel'
import HotspotTable from './components/HotspotTable'
import ReportForm from './components/ReportForm'
import ReportsList from './components/ReportsList'
import ModelInfoPanel from './components/ModelInfoPanel'
import { Card, ErrorState, Skeleton } from './components/ui'

const CHENNAI = { latitude: 13.0827, longitude: 80.2707 }

const DISCLAIMER =
  'FloodLens AI is a hackathon prototype for demonstration and education. It is NOT an official flood-warning system and must not be used for emergency decisions. Always follow official advisories from your local disaster-management authority.'

export default function App() {
  const [activeView, setActiveView] = useState('overview')
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null)
  const [riskFilter, setRiskFilter] = useState<RiskLevelFilter>(null)
  const [lastAssessment, setLastAssessment] = useState<AssessResponse | null>(null)
  const [newReportCount, setNewReportCount] = useState(0)
  const [modelInfoOpen, setModelInfoOpen] = useState(false)
  const sectionsRef = useRef<Record<string, HTMLElement | null>>({})

  const health = useApi(() => api.health())
  const zones = useApi(() => api.zones())
  const weather = useApi(() => api.weather(CHENNAI.latitude, CHENNAI.longitude))

  const zoneList: Zone[] = zones.data?.zones ?? []
  const selectedZone = zoneList.find((zone) => zone.id === selectedZoneId) ?? null

  useEffect(() => {
    if (!selectedZoneId && zoneList.length > 0) {
      setSelectedZoneId(zoneList[0].id)
    }
  }, [zoneList.length, selectedZoneId])

  function navigate(view: string) {
    setActiveView(view)
    if (view === 'model') setModelInfoOpen(true)
    requestAnimationFrame(() => {
      sectionsRef.current[view]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }

  function useInAssessment(zone: Zone) {
    setSelectedZoneId(zone.id)
    navigate('assess')
  }

  /** Select a zone from the risk-band panel: highlight it on the map and open details. */
  function selectZoneFromBand(zoneId: string) {
    setSelectedZoneId(zoneId)
    // Bring the map + detail panel into view so the user sees the selection.
    sectionsRef.current.overview?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function handleAssessmentComplete(result: AssessResponse) {
    setLastAssessment(result)
    if (result.zone.id !== 'custom') setSelectedZoneId(result.zone.id)
  }

  function handleReportCreated(_report: Report) {
    setNewReportCount((count) => count + 1)
  }

  const backendOnline = !health.error && health.data !== null
  const weatherOnline = weather.data ? weather.data.available : !weather.error

  return (
    <div className="flex min-h-screen bg-slate-100">
      <Sidebar
        active={activeView}
        onNavigate={navigate}
        backendOnline={backendOnline}
        weatherOnline={weatherOnline}
      />

      <main className="flex-1 min-w-0">
        <TopBar
          health={health.data}
          weatherSource={weather.data?.available ? weather.data.source : null}
          weatherRetrievedAt={weather.data?.available ? weather.data.retrieved_at_utc : null}
          weatherAvailable={weather.data ? weather.data.available : null}
        />

        <StatusBanner health={health.data} healthError={health.error} weather={weather.data} />

        <div className="px-4 md:px-6 py-5 space-y-8 max-w-[1440px]">
          {/* 1 · Overview */}
          <section
            ref={(el) => {
              sectionsRef.current.overview = el
            }}
            className="space-y-5 scroll-mt-4"
          >
            {zones.loading ? (
              <Skeleton lines={5} />
            ) : zones.error ? (
              <ErrorState title="Could not load the zone catalogue" message={zones.error} onRetry={zones.reload} />
            ) : (
              <>
                <RiskSummaryCards
                  zones={zoneList}
                  activeFilter={riskFilter}
                  onFilterChange={setRiskFilter}
                  onSelectZone={selectZoneFromBand}
                />
                <div className="grid lg:grid-cols-3 gap-5">
                  <Card
                    title="Chennai risk zones"
                    subtitle="Select a marker for details + live Open-Meteo weather"
                    className="lg:col-span-2"
                  >
                    <ZoneMap
                      zones={zoneList}
                      selectedId={selectedZoneId}
                      riskFilter={riskFilter}
                      onSelect={setSelectedZoneId}
                    />
                  </Card>
                  <Card
                    title="Selected zone"
                    subtitle="Verified OSM coordinates · live weather · illustrative attributes"
                  >
                    <ZoneDetail zone={selectedZone} onUseInAssessment={useInAssessment} />
                  </Card>
                </div>
              </>
            )}
          </section>

          {/* 2 · Assessment */}
          <section
            ref={(el) => {
              sectionsRef.current.assess = el
            }}
            className="scroll-mt-4"
          >
            <Card
              title="Run a flood risk assessment"
              subtitle="Editable rainfall inputs call POST /api/assess; results update live"
            >
              {zones.loading ? (
                <Skeleton lines={6} />
              ) : zones.error ? (
                <ErrorState title="Zones unavailable" message={zones.error} />
              ) : (
                <AssessmentPanel
                  zones={zoneList}
                  selectedZoneId={selectedZoneId}
                  onSelectZone={setSelectedZoneId}
                  onAssessmentComplete={handleAssessmentComplete}
                />
              )}
            </Card>
          </section>

          {/* 3 · Hotspots */}
          <section
            ref={(el) => {
              sectionsRef.current.hotspots = el
            }}
            className="scroll-mt-4"
          >
            <Card
              title="Risk hotspot table"
              subtitle="Sorted by baseline Demo Risk Estimate (assumed rainfall, illustrative attributes)"
            >
              {zones.loading ? (
                <Skeleton lines={8} />
              ) : zones.error ? (
                <ErrorState title="Zones unavailable" message={zones.error} />
              ) : (
                <HotspotTable
                  zones={zoneList}
                  lastAssessment={lastAssessment}
                  onSelectZone={setSelectedZoneId}
                />
              )}
            </Card>
          </section>

          {/* 4 · Reports */}
          <section
            ref={(el) => {
              sectionsRef.current.reports = el
            }}
            className="scroll-mt-4"
          >
            <div className="grid lg:grid-cols-2 gap-5">
              <Card
                title="Community waterlogging report"
                subtitle="Unverified, user-submitted only"
              >
                <ReportForm zones={zoneList} onCreated={handleReportCreated} />
              </Card>
              <Card
                title="Recent reports"
                subtitle={
                  newReportCount > 0
                    ? `${newReportCount} new submission${newReportCount > 1 ? 's' : ''} this session`
                    : 'Stored locally in SQLite'
                }
              >
                <ReportsList key={newReportCount} />
              </Card>
            </div>
          </section>

          {/* 5 · Model information */}
          <section
            ref={(el) => {
              sectionsRef.current.model = el
            }}
            className="scroll-mt-4"
          >
            <Card
              title="Model information"
              subtitle={
                modelInfoOpen
                  ? 'Real evaluation of the synthetic-data prototype — a documented negative result'
                  : 'Hidden by default — expand to view training & evaluation details'
              }
              actions={
                <button
                  type="button"
                  onClick={() => setModelInfoOpen((open) => !open)}
                  className="rounded border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  {modelInfoOpen ? 'Hide' : 'Show model details'}
                </button>
              }
            >
              {modelInfoOpen ? (
                <ModelInfoPanel />
              ) : (
                <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center">
                  <p className="text-sm text-slate-600">
                    Training metrics, confusion matrix and the{' '}
                    <strong>“no signal detected”</strong> verdict for the synthetic dataset are
                    collapsed to keep the dashboard focused.
                  </p>
                  <button
                    type="button"
                    onClick={() => setModelInfoOpen(true)}
                    className="mt-3 rounded bg-slate-800 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-900"
                  >
                    Show model information
                  </button>
                </div>
              )}
            </Card>
          </section>

          <footer className="border-t border-slate-200 pt-4 pb-2">
            <p className="text-[11px] text-slate-500 leading-relaxed max-w-3xl">{DISCLAIMER}</p>
            <p className="text-[11px] text-slate-400 mt-1">
              Data sources: OpenStreetMap (zone coordinates) · Open-Meteo (weather) · synthetic
              training dataset (documented). Not connected to any official warning system.
            </p>
          </footer>
        </div>
      </main>
    </div>
  )
}