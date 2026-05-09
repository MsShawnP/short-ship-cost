import { lazy, Suspense, useEffect, useMemo, useState } from 'react'

import Header from './components/Header.jsx'
import DimensionToggle from './components/DimensionToggle.jsx'
import CostStack from './components/CostStack.jsx'
import ParameterPanel, {
  ParameterToggleButton,
} from './components/ParameterPanel.jsx'
import { TimeRangeProvider, useTimeRange } from './lib/timeRange.jsx'
import {
  getRatios,
  filterDeauthEvents,
  scaleCostByRetailer,
  scaleCostByMonth,
  scaleCostBySku,
  scaleBufferScenarios,
  summaryFromMonthly,
  validateBaseline,
  deauthTotal,
} from './utils/costEngine.js'
import './App.css'

const RetailerDrilldown = lazy(() => import('./components/RetailerDrilldown.jsx'))
const TimeSeries = lazy(() => import('./components/TimeSeries.jsx'))
const BufferSimulation = lazy(() => import('./components/BufferSimulation.jsx'))

const SOURCES = [
  'meta',
  'cost_summary',
  'cost_by_month',
  'orders_by_month',
  'cost_by_retailer',
  'cost_by_sku',
  'buffer_scenarios',
  'deauthorization_events',
  'validation',
]

function SectionFallback() {
  return <div className="section-fallback" aria-hidden="true" />
}

function extractBaselineParams(meta) {
  const out = {}
  for (const [k, v] of Object.entries(meta.cost_parameters || {})) {
    out[k] = v.value
  }
  return out
}

function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all(
      SOURCES.map((name) =>
        fetch(`./data/${name}.json`).then((r) => {
          if (!r.ok) throw new Error(`${name}.json: ${r.status}`)
          return r.json()
        }),
      ),
    )
      .then((results) => {
        setData(Object.fromEntries(SOURCES.map((n, i) => [n, results[i]])))
      })
      .catch(setError)
  }, [])

  const allMonths = useMemo(() => {
    if (!data) return []
    return [...new Set(data.cost_by_month.map((r) => r.month))].sort()
  }, [data])

  const baselineParams = useMemo(
    () => (data ? extractBaselineParams(data.meta) : null),
    [data],
  )

  if (error) {
    return (
      <main className="page">
        <p className="status">Failed to load data: {error.message}</p>
      </main>
    )
  }

  if (!data) {
    return (
      <main className="page">
        <p className="status">Loading&hellip;</p>
      </main>
    )
  }

  return (
    <TimeRangeProvider allMonths={allMonths} baselineParams={baselineParams}>
      <AppShell data={data} />
    </TimeRangeProvider>
  )
}

function AppShell({ data }) {
  const {
    params,
    baselineParams,
    paramsModified,
  } = useTimeRange()
  const [panelOpen, setPanelOpen] = useState(false)

  const scaled = useMemo(() => {
    if (!params || !baselineParams) return null
    const ratios = getRatios(params, baselineParams)
    const events = filterDeauthEvents(data.deauthorization_events, params)
    const cost_by_retailer = scaleCostByRetailer(
      data.cost_by_retailer,
      ratios,
      events,
    )
    const cost_by_month = scaleCostByMonth(data.cost_by_month, ratios)
    const cost_by_sku = scaleCostBySku(data.cost_by_sku, ratios, events)
    const cost_summary = summaryFromMonthly(
      data.cost_summary,
      cost_by_month,
      events,
    )
    const baselineDeauth = data.cost_summary.find(
      (r) => r.dimension === 'deauthorization',
    )?.total_cost || 1
    const filteredDeauth = deauthTotal(events)
    const deauthScale = filteredDeauth / baselineDeauth
    const buffer_scenarios = {
      scenarios: scaleBufferScenarios(
        data.buffer_scenarios.scenarios,
        ratios,
        deauthScale,
      ),
    }
    return {
      cost_summary,
      cost_by_retailer,
      cost_by_month,
      cost_by_sku,
      deauthorization_events: events,
      buffer_scenarios,
    }
  }, [data, params, baselineParams])

  // Validate JS-baseline output against validation.json on first load (and
  // again whenever params equal baseline — the check only matters then).
  const validation = useMemo(() => {
    if (!scaled || paramsModified) return null
    const result = validateBaseline(scaled.cost_summary, data.validation)
    if (result) {
      // eslint-disable-next-line no-console
      console.warn('JS cost engine baseline mismatch:', result)
    }
    return result
  }, [scaled, paramsModified, data.validation])

  if (!scaled) return null

  const printMeta = useMemo(() => {
    const generated = new Date(data.meta.last_updated).toLocaleDateString(
      'en-US',
      { year: 'numeric', month: 'long', day: 'numeric' },
    )
    const modifiedKeys = paramsModified
      ? Object.keys(baselineParams || {}).filter(
          (k) => params[k] !== baselineParams[k],
        )
      : []
    return { generated, modifiedKeys }
  }, [data.meta.last_updated, params, baselineParams, paramsModified])

  return (
    <>
      <Header
        rightSlot={
          <ParameterToggleButton
            open={panelOpen}
            onToggle={() => setPanelOpen((v) => !v)}
            modified={paramsModified}
          />
        }
      />
      <DimensionToggle />
      <div className="print-meta">
        Generated {printMeta.generated} &middot; Data window{' '}
        {data.meta.time_window.start} to {data.meta.time_window.end}.{' '}
        {paramsModified ? (
          <span className="print-meta-modified">
            Parameters modified from baseline:{' '}
            {printMeta.modifiedKeys.join(', ')}.
          </span>
        ) : (
          <span>Baseline parameters.</span>
        )}
      </div>
      <main className="page">
        <CostStack
          meta={data.meta}
          summary={scaled.cost_summary}
          costByMonth={scaled.cost_by_month}
          ordersByMonth={data.orders_by_month}
        />
        <Suspense fallback={<SectionFallback />}>
          <RetailerDrilldown
            costByRetailer={scaled.cost_by_retailer}
            costBySku={scaled.cost_by_sku}
          />
        </Suspense>
        <Suspense fallback={<SectionFallback />}>
          <TimeSeries costByMonth={scaled.cost_by_month} />
        </Suspense>
        <Suspense fallback={<SectionFallback />}>
          <BufferSimulation bufferScenarios={scaled.buffer_scenarios} />
        </Suspense>
      </main>
      <footer className="footer">
        <span>
          Data window: {data.meta.time_window.start} to{' '}
          {data.meta.time_window.end}. Synthetic order data &mdash;
          methodology in <code>docs/cost-engine-docs.md</code>.
          {paramsModified && (
            <span className="footer-mod">
              {' '}
              Parameters modified from baseline.
            </span>
          )}
        </span>
        <span>Lailara LLC portfolio piece</span>
      </footer>
      <ParameterPanel
        open={panelOpen}
        onClose={() => setPanelOpen(false)}
        validation={validation}
      />
    </>
  )
}

export default App
