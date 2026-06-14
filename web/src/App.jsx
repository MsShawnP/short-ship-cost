import { Component, lazy, Suspense, useEffect, useMemo, useState } from 'react'

import Header from './components/Header.jsx'
import DimensionToggle from './components/DimensionToggle.jsx'
import CostStack from './components/CostStack.jsx'
import ParameterPanel, {
  ParameterToggleButton,
} from './components/ParameterPanel.jsx'
import { TimeRangeProvider, useTimeRange } from './lib/timeRange.jsx'
import {
  getRatios,
  scaleCostByRetailer,
  scaleCostByMonth,
  scaleCostBySku,
  scaleBufferScenarios,
  summaryFromMonthly,
  validateBaseline,
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
  'validation',
]

function SectionFallback() {
  return <div className="section-fallback" aria-hidden="true" />
}

class SectionErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="section-error">
          <p className="section-error-title">This section could not render</p>
          <p className="section-error-body">{this.state.error.message}</p>
        </div>
      )
    }
    return this.props.children
  }
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
      <main className="page" role="alert">
        <div className="statusBlock">
          <p className="statusTitle">Could not load analysis data</p>
          <p className="statusBody">{error.message}</p>
          <button
            type="button"
            className="statusRetry"
            onClick={() => window.location.reload()}
          >
            Reload
          </button>
        </div>
      </main>
    )
  }

  if (!data) {
    return (
      <main className="page" aria-busy="true" aria-live="polite">
        <div className="statusBlock">
          <div className="statusSkeleton" aria-hidden="true">
            <div className="skelLineLg" />
            <div className="skelLineMd" />
            <div className="skelChart" />
          </div>
          <p className="statusBody">Loading analysis&hellip;</p>
        </div>
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
    const cost_by_retailer = scaleCostByRetailer(data.cost_by_retailer, ratios)
    const cost_by_month = scaleCostByMonth(data.cost_by_month, ratios)
    const cost_by_sku = scaleCostBySku(data.cost_by_sku, ratios)
    const cost_summary = summaryFromMonthly(data.cost_summary, cost_by_month)
    const buffer_scenarios = {
      scenarios: scaleBufferScenarios(
        data.buffer_scenarios.scenarios,
        ratios,
      ),
    }
    return {
      cost_summary,
      cost_by_retailer,
      cost_by_month,
      cost_by_sku,
      buffer_scenarios,
    }
  }, [data, params, baselineParams])

  const validation = useMemo(() => {
    if (!scaled || paramsModified) return null
    const result = validateBaseline(scaled.cost_summary, data.validation)
    if (result) {
      console.warn('JS cost engine baseline mismatch:', result)
    }
    return result
  }, [scaled, paramsModified, data.validation])

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

  if (!scaled) return null

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
        <SectionErrorBoundary>
          <Suspense fallback={<SectionFallback />}>
            <RetailerDrilldown
              costByRetailer={scaled.cost_by_retailer}
              costBySku={scaled.cost_by_sku}
            />
          </Suspense>
        </SectionErrorBoundary>
        <SectionErrorBoundary>
          <Suspense fallback={<SectionFallback />}>
            <TimeSeries costByMonth={scaled.cost_by_month} />
          </Suspense>
        </SectionErrorBoundary>
        <SectionErrorBoundary>
          <Suspense fallback={<SectionFallback />}>
            <BufferSimulation bufferScenarios={scaled.buffer_scenarios} />
          </Suspense>
        </SectionErrorBoundary>
      </main>
      <section className="methodology" id="methodology">
        <details>
          <summary className="methodology-summary">
            About this analysis
          </summary>
          <div className="methodology-body">
            <p>
              This analysis uses order and shipment data from the Cinderhaven
              Provisions data platform, covering a ~$25M annual revenue
              specialty food brand operating across retail channels (Walmart,
              Costco, Whole Foods, Kroger, Sprouts, and regional grocers) and
              distributors (UNFI, KeHE, DPI Northwest). The dataset covers{' '}
              {data.meta.total_orders.toLocaleString()} orders and{' '}
              {data.meta.total_lines.toLocaleString()} shipment lines over a{' '}
              {Math.round((new Date(data.meta.time_window.end) - new Date(data.meta.time_window.start)) / (365.25 * 86400000))}-year window.
            </p>
            <p>
              Four cost dimensions are computed from the gap between ordered
              and shipped quantities: forgone revenue, compliance fines,
              chargebacks, and deductions. Compliance fines use
              retailer-specific schedules (rate, basis, threshold) that can be
              adjusted via the parameter panel. Chargebacks and deductions are
              actual platform events attributed to short-ship causes.
            </p>
            <p>
              The buffer simulation models structural improvements to fill rate
              by lifting every shipment line to a target percentage, then
              recomputing all four dimensions. It does not prescribe how to
              build the buffer &mdash; only what even a modest improvement would
              recover in quantifiable costs.
            </p>
            <p>
              Compliance fine parameters are tunable. The baseline values
              reflect the fine schedules embedded in the platform data.
              Adjusting any parameter recalculates all downstream totals in
              real time.
            </p>
          </div>
        </details>
      </section>
      <footer className="footer">
        <span>
          Data window: {data.meta.time_window.start} to{' '}
          {data.meta.time_window.end}. Platform order data &mdash;{' '}
          <a href="#methodology" className="footer-link">methodology</a>.
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
