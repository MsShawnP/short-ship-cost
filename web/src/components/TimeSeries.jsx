import { useMemo, useState } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
} from 'recharts'

import { DIMENSION_LABEL, DIMENSION_COLOR } from '../lib/dimensions.js'
import { fmtCompact, fmtPct } from '../lib/format.js'
import { useTimeRange, formatMonthLabel } from '../lib/timeRange.jsx'
import PinnedCallout from './PinnedCallout.jsx'
import styles from './TimeSeries.module.css'

// cost_by_month covers 7 dimensions — deauthorization is event-level only
// (no monthly attribution), per docs/cost-engine-docs.md.
const ALL_MONTHLY_DIMS = [
  'lost_revenue',
  'otif_fines',
  'chargebacks',
  'dtc_cancellations',
  'triage_labor',
  'distributor_returns',
  'dtc_margin_leakage',
]

function fmtShortMonth(ym) {
  if (!ym) return ''
  const [y, m] = ym.split('-').map(Number)
  const d = new Date(Date.UTC(y, m - 1, 1))
  const monthName = d.toLocaleString('en-US', {
    month: 'short',
    timeZone: 'UTC',
  })
  return `${monthName} '${String(y).slice(-2)}`
}

// Each padded-key prefix gives Recharts a separate dataKey carrying an
// inflated value so thin dimensions render with a minimum visual height.
// The original `row[d]` value is preserved for the tooltip.
const PAD_KEY = (d) => `_p_${d}`

// Approximate ratio of plot area covered by a 12px layer at typical
// chart height (~290px after margins/axis). One pass of padding inflates
// the total stack roughly 25–30%, which is acceptable for a chart whose
// purpose is showing the *trend*, not exact monthly totals.
const MIN_LAYER_FRACTION = 0.04

function buildMonthlyData(costByMonth, range, dims) {
  const dimSet = new Set(dims)
  const map = new Map()
  for (const r of costByMonth) {
    if (range.isFiltered) {
      if (r.month < range.startMonth || r.month > range.endMonth) continue
    }
    if (!dimSet.has(r.dimension)) continue
    if (!map.has(r.month)) {
      const init = { month: r.month, label: fmtShortMonth(r.month), total: 0 }
      for (const d of dims) init[d] = 0
      map.set(r.month, init)
    }
    const row = map.get(r.month)
    if (Object.prototype.hasOwnProperty.call(row, r.dimension)) {
      row[r.dimension] += r.cost
      row.total += r.cost
    }
  }
  const rows = Array.from(map.values()).sort((a, b) =>
    a.month.localeCompare(b.month),
  )

  // Apply minimum visual height so thin dimensions are visible.
  const peakTotal = rows.reduce((max, r) => (r.total > max ? r.total : max), 0)
  const minDollar = peakTotal * MIN_LAYER_FRACTION
  for (const row of rows) {
    for (const d of dims) {
      const real = row[d]
      row[PAD_KEY(d)] = real > 0 ? Math.max(real, minDollar) : 0
    }
  }

  return rows
}

function buildTitle(rows, range) {
  if (rows.length === 0) {
    return 'No monthly data for the selected range'
  }
  if (rows.length < 4) {
    return `Monthly cost of shorts, ${fmtShortMonth(rows[0].month)}–${fmtShortMonth(rows[rows.length - 1].month)}`
  }
  const half = Math.floor(rows.length / 2)
  const firstAvg = rows.slice(0, half).reduce((s, r) => s + r.total, 0) / half
  const secondAvg =
    rows.slice(half).reduce((s, r) => s + r.total, 0) / (rows.length - half)
  if (firstAvg === 0) {
    return 'Monthly cost of shorts'
  }
  const change = secondAvg / firstAvg - 1

  const periodLabel = range.isFiltered
    ? `${fmtShortMonth(rows[0].month)}–${fmtShortMonth(rows[rows.length - 1].month)}`
    : 'the analysis window'

  if (change > 0.10) {
    return `Short-shipping costs climbed through ${periodLabel}`
  }
  if (change < -0.10) {
    return `Short-shipping costs eased through ${periodLabel}`
  }
  return 'The cost of shorts held steady — the business never saw it'
}

export default function TimeSeries({ costByMonth }) {
  const range = useTimeRange()
  const { activeDims } = range
  const [pinned, setPinned] = useState(null) // 'YYYY-MM' or null

  const dims = useMemo(
    () => ALL_MONTHLY_DIMS.filter((d) => activeDims.has(d)),
    [activeDims],
  )

  const data = useMemo(
    () => buildMonthlyData(costByMonth, range, dims),
    [costByMonth, range, dims],
  )

  const stats = useMemo(() => {
    if (data.length === 0) return null
    const total = data.reduce((s, r) => s + r.total, 0)
    const avg = total / data.length
    let peak = data[0]
    let low = data[0]
    for (const r of data) {
      if (r.total > peak.total) peak = r
      if (r.total < low.total) low = r
    }
    return { avg, peak, low, count: data.length }
  }, [data])

  const title = useMemo(() => buildTitle(data, range), [data, range])

  // Tick interval: keep the X-axis readable with up to ~12 labels.
  const tickInterval =
    data.length <= 12
      ? 0
      : data.length <= 18
        ? 1
        : Math.max(1, Math.ceil(data.length / 12))

  return (
    <section className={styles.section}>
      <div className={styles.sectionHead}>
        <h2 className={styles.sectionTitle}>The trend</h2>
        <p className={styles.sectionSubtitle}>
          Monthly cost of shorts over time
        </p>
      </div>

      <div className={styles.chartBlock}>
        <h3 className={styles.chartTitle}>{title}</h3>
        <p className={styles.chartSubtitle}>
          Stacked monthly cost across {dims.length} dimensions. Click any
          month to pin its breakdown.
        </p>

        {pinned && (() => {
          const row = data.find((r) => r.month === pinned)
          if (!row) return null
          const breakdown = dims
            .map((d) => ({
              color: DIMENSION_COLOR[d],
              label: DIMENSION_LABEL[d],
              value: fmtCompact(row[d] || 0),
              pct: fmtPct((row[d] || 0) / Math.max(row.total, 1)),
              raw: row[d] || 0,
            }))
            .filter((e) => e.raw > 0)
            .sort((a, b) => b.raw - a.raw)
          return (
            <PinnedCallout
              title={formatMonthLabel(row.month)}
              subtitle={`Total ${fmtCompact(row.total)}`}
              breakdown={breakdown}
              onUnpin={() => setPinned(null)}
            />
          )
        })()}

        {data.length === 0 || dims.length === 0 ? (
          <p className={styles.chartEmpty}>
            {dims.length === 0
              ? 'All monthly dimensions are excluded. Re-enable a dimension chip above to see the trend.'
              : 'No monthly data for the selected range.'}
          </p>
        ) : (
          <div
            className={styles.chartContainer}
            role="img"
            aria-label={`Stacked monthly cost of shorts across ${dims.length} dimensions over ${data.length} months. Peak month: ${stats ? stats.peak.month : ''}.`}
          >
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={data}
                margin={{ top: 16, right: 24, bottom: 16, left: 8 }}
                onClick={(state) => {
                  if (state?.activePayload?.length) {
                    const m = state.activePayload[0].payload.month
                    setPinned((prev) => (prev === m ? null : m))
                  }
                }}
                style={{ cursor: 'pointer' }}
              >
                <CartesianGrid
                  stroke="var(--color-gridline)"
                  vertical={false}
                />
                <XAxis
                  dataKey="label"
                  interval={tickInterval}
                  tick={{
                    fill: 'var(--color-text-secondary)',
                    fontFamily: 'var(--font-sans)',
                    fontSize: 12,
                  }}
                  tickLine={false}
                  axisLine={{ stroke: 'var(--color-border)' }}
                />
                <YAxis
                  tickFormatter={(v) => fmtCompact(v)}
                  tick={{
                    fill: 'var(--color-text-secondary)',
                    fontFamily: 'var(--font-sans)',
                    fontSize: 12,
                  }}
                  tickLine={false}
                  axisLine={false}
                  width={56}
                />
                {dims.map((dim) => (
                  <Area
                    key={dim}
                    type="monotone"
                    dataKey={PAD_KEY(dim)}
                    stackId="cost"
                    stroke={DIMENSION_COLOR[dim]}
                    strokeWidth={0}
                    fill={DIMENSION_COLOR[dim]}
                    fillOpacity={1}
                    isAnimationActive={false}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        <p className={styles.chartFootnote}>
          Source: Cinderhaven Provisions synthetic order data. Deauthorization
          is omitted because the underlying events are SKU- and
          retailer-level, not monthly. Layer heights have a minimum display
          size; click any month for exact values.
        </p>
      </div>

      {stats && (
        <div className={styles.stats}>
          <div className={styles.stat}>
            <div className={styles.statValue}>{fmtCompact(stats.avg)}</div>
            <div className={styles.statLabel}>per month, average</div>
            <div className={styles.statSub}>
              over {stats.count} month{stats.count === 1 ? '' : 's'}
            </div>
          </div>
          <div className={styles.stat}>
            <div className={styles.statValue}>{fmtCompact(stats.peak.total)}</div>
            <div className={styles.statLabel}>peak month</div>
            <div className={styles.statSub}>
              {formatMonthLabel(stats.peak.month)}
            </div>
          </div>
          <div className={styles.stat}>
            <div className={styles.statValue}>{fmtCompact(stats.low.total)}</div>
            <div className={styles.statLabel}>low month</div>
            <div className={styles.statSub}>
              {formatMonthLabel(stats.low.month)}
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
