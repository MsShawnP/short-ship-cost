import { useMemo, useState } from 'react'
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  LabelList,
} from 'recharts'

import { DIMENSION_COLOR, DIMENSION_LABEL, DIMENSION_ORDER } from '../lib/dimensions.js'
import { fmtCompact, fmtPct, hexToRgba } from '../lib/format.js'
import { REDUCED_MOTION } from '../lib/useAnimatedValue.js'
import { useTimeRange } from '../lib/timeRange.jsx'
import PinnedCallout from './PinnedCallout.jsx'
import styles from './BufferSimulation.module.css'

const ORDER = DIMENSION_ORDER

const PRIMARY_TEAL = '#0A3D3D'
const ACCENT_RED = '#C54B4B'

function buildScenarioBreakdown(scenario, activeDims) {
  return ORDER.filter((d) => activeDims.has(d))
    .map((dim) => {
      const v = scenario.by_dimension[dim]
      if (!v) return null
      return {
        color: DIMENSION_COLOR[dim],
        label: DIMENSION_LABEL[dim],
        value: fmtCompact(v.simulated),
        pct:
          v.recovery > 0
            ? `−${fmtCompact(v.recovery)}`
            : v.recovery < 0
              ? `+${fmtCompact(-v.recovery)}`
              : '—',
        raw: v.simulated,
      }
    })
    .filter(Boolean)
    .sort((a, b) => b.raw - a.raw)
}

function RecoveryTable({ scenarios, activeDims }) {
  const rows = ORDER.filter((d) => activeDims.has(d))
    .map((dim) => {
      const original = scenarios[0].by_dimension[dim]?.original ?? 0
      const cells = scenarios.map(
        (s) => s.by_dimension[dim]?.simulated ?? 0,
      )
      return { dim, original, cells }
    })
    .filter((r) => r.original > 0)

  return (
    <div className={styles.tableBlock}>
      <h3 className={styles.tableTitle}>Per-dimension recovery</h3>
      <div className={styles.tableScroll}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Dimension</th>
              <th className={styles.numeric}>Baseline</th>
              {scenarios.map((s) => (
                <th key={s.target_fill_rate} className={styles.numeric}>
                  {Math.round(s.target_fill_rate * 100)}%
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const max = r.original || 1
              const isDeauth = r.dim === 'deauthorization'
              const baselineBg = hexToRgba(DIMENSION_COLOR[r.dim], 0.55)
              return (
                <tr
                  key={r.dim}
                  className={isDeauth ? styles.deauthRow : undefined}
                >
                  <td>
                    <span className={styles.dimensionLabel}>
                      {DIMENSION_LABEL[r.dim]}
                    </span>
                  </td>
                  <td
                    className={styles.numeric}
                    style={{ background: baselineBg }}
                  >
                    {fmtCompact(r.original)}
                  </td>
                  {r.cells.map((cost, i) => {
                    const intensity = cost > 0 ? Math.min(1, cost / max) : 0
                    const bg =
                      intensity > 0
                        ? hexToRgba(DIMENSION_COLOR[r.dim], intensity * 0.55)
                        : 'transparent'
                    return (
                      <td
                        key={i}
                        className={styles.numeric}
                        style={{ background: bg }}
                      >
                        {fmtCompact(cost)}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className={styles.tableFootnote}>
        Distributor returns and triage labor are unchanged across scenarios
        by design &mdash; returns depend on promo volume, triage reflects
        the process running regardless of outcome.
      </p>
    </div>
  )
}

export default function BufferSimulation({ bufferScenarios }) {
  const range = useTimeRange()
  const { activeDims } = range
  const scenarios = bufferScenarios.scenarios
  const [pinned, setPinned] = useState(null) // target_fill_rate or null

  // Re-derive each scenario's total over only the active dimensions so the
  // staircase, tooltip, and pinned panel all agree under any toggle state.
  const scenariosFiltered = useMemo(
    () =>
      scenarios.map((s) => {
        let total = 0
        for (const [dim, v] of Object.entries(s.by_dimension)) {
          if (activeDims.has(dim)) total += v.simulated
        }
        return { ...s, _filtered_total: total }
      }),
    [scenarios, activeDims],
  )

  const baseline = useMemo(() => {
    let total = 0
    for (const [dim, v] of Object.entries(scenarios[0].by_dimension)) {
      if (activeDims.has(dim)) total += v.original
    }
    return total
  }, [scenarios, activeDims])

  const barData = useMemo(
    () =>
      scenariosFiltered.map((s) => ({
        target_fill_rate: s.target_fill_rate,
        targetLabel: `${Math.round(s.target_fill_rate * 100)}%`,
        total_cost: s._filtered_total,
        recoveryLabel: `${Math.round(((baseline - s._filtered_total) / Math.max(baseline, 1)) * 100)}% recovered`,
        achieved_fill_rate: s.achieved_fill_rate,
        by_dimension: s.by_dimension,
      })),
    [scenariosFiltered, baseline],
  )

  const s90 = barData.find((s) => s.target_fill_rate === 0.9)
  const recoveredAt90 = baseline - (s90?.total_cost ?? baseline)

  const title = activeDims.has('deauthorization')
    ? `At 90% fill rate, ${fmtCompact(recoveredAt90)} in costs disappear — most from deauthorization`
    : `At 90% fill rate, ${fmtCompact(recoveredAt90)} in costs disappear`

  const pinnedScenario =
    pinned !== null ? scenarios.find((s) => s.target_fill_rate === pinned) : null

  const handleChartClick = (state) => {
    if (state && state.activePayload && state.activePayload.length) {
      const target = state.activePayload[0].payload.target_fill_rate
      setPinned((prev) => (prev === target ? null : target))
    }
  }

  return (
    <section className={styles.section}>
      <div className={styles.sectionHead}>
        <h2 className={styles.sectionTitle}>What recovery looks like</h2>
        <p className={styles.sectionSubtitle}>
          Cost savings from improving fill rate
        </p>
      </div>

      {range.isFiltered && (
        <div className={styles.fullPeriodNote}>
          Buffer simulation uses the full data period (not filtered) because
          it models structural changes to fill rate.
        </div>
      )}

      <div className={styles.staircaseBlock}>
      <div className={styles.chartBlock}>
        <h3 className={styles.chartTitle}>{title}</h3>
        <p className={styles.chartSubtitle}>
          Total cost of shorts at four target fill rates compared to the{' '}
          {fmtCompact(baseline)} baseline at 75% fill. Click any bar to pin
          its breakdown.
        </p>

        {pinnedScenario && (
          <PinnedCallout
            title={`Target ${Math.round(pinnedScenario.target_fill_rate * 100)}% fill`}
            subtitle={`${fmtCompact(
              barData.find((b) => b.target_fill_rate === pinnedScenario.target_fill_rate)?.total_cost ?? 0,
            )} · ${fmtPct(pinnedScenario.achieved_fill_rate)} achieved · ${Math.round(pinnedScenario.recovery_pct * 100)}% recovered`}
            breakdown={buildScenarioBreakdown(pinnedScenario, activeDims)}
            onUnpin={() => setPinned(null)}
          />
        )}

        {baseline === 0 ? (
          <p className={styles.chartEmpty}>
            All dimensions are excluded. Re-enable a dimension chip above to
            see the recovery curve.
          </p>
        ) : (
        <div
          className={styles.chartContainer}
          role="img"
          aria-label={`Bar chart: total cost of shorts across four target fill rates (${barData.map((b) => b.targetLabel).join(', ')}). Baseline ${fmtCompact(baseline)}, ${fmtCompact(recoveredAt90)} recovered at 90% fill.`}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={barData}
              margin={{ top: 80, right: 24, bottom: 24, left: 16 }}
              barCategoryGap="22%"
              onClick={handleChartClick}
              style={{ cursor: 'pointer' }}
            >
              <CartesianGrid stroke="var(--color-gridline)" vertical={false} />
              <XAxis
                dataKey="targetLabel"
                tick={{
                  fill: 'var(--color-text)',
                  fontFamily: 'var(--font-sans)',
                  fontSize: 13,
                  fontWeight: 600,
                }}
                tickLine={false}
                axisLine={{ stroke: 'var(--color-border)' }}
                label={{
                  value: 'Target fill rate',
                  position: 'insideBottom',
                  offset: -8,
                  fill: 'var(--color-text-secondary)',
                  fontSize: 12,
                }}
              />
              <YAxis
                tickFormatter={fmtCompact}
                tick={{
                  fill: 'var(--color-text-secondary)',
                  fontFamily: 'var(--font-sans)',
                  fontSize: 12,
                }}
                tickLine={false}
                axisLine={false}
                width={60}
                domain={[0, baseline * 1.08]}
              />
              <ReferenceLine
                y={baseline}
                stroke={ACCENT_RED}
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{
                  value: `Current: ${fmtCompact(baseline)} at 75% fill`,
                  position: 'insideTopRight',
                  fill: ACCENT_RED,
                  fontSize: 12,
                  fontWeight: 600,
                  offset: 6,
                }}
              />
              <Bar
                dataKey="total_cost"
                fill={PRIMARY_TEAL}
                isAnimationActive={!REDUCED_MOTION}
                animationDuration={250}
                animationEasing="ease-out"
              >
                {barData.map((b) => {
                  const dimmed = pinned !== null && b.target_fill_rate !== pinned
                  return (
                    <Cell
                      key={b.target_fill_rate}
                      fill={PRIMARY_TEAL}
                      fillOpacity={dimmed ? 0.3 : 1}
                    />
                  )
                })}
                <LabelList
                  dataKey="total_cost"
                  position="top"
                  offset={8}
                  formatter={(v) => fmtCompact(v)}
                  style={{
                    fill: 'var(--color-text)',
                    fontFamily: 'var(--font-serif)',
                    fontSize: 15,
                    fontWeight: 700,
                  }}
                />
                <LabelList
                  dataKey="recoveryLabel"
                  position="top"
                  offset={28}
                  style={{
                    fill: 'var(--color-text-secondary)',
                    fontFamily: 'var(--font-sans)',
                    fontSize: 11,
                  }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        )}
        <p className={styles.chartFootnote}>
          Source: Cinderhaven Provisions buffer-simulation outputs. Each
          scenario lifts every retail/distributor line to the target fill
          rate and recomputes all eight cost dimensions; achieved fill is
          slightly higher than target due to asymmetric clamping. Click any
          bar for a pinned breakdown.
        </p>
      </div>

      {activeDims.has('deauthorization') && (
        <div className={styles.cliffCallout}>
          <p className={styles.cliffTitle}>The deauthorization cliff</p>
          <p className={styles.cliffBody}>
            Between 85% and 95% fill, deauthorization costs drop from{' '}
            <strong>$6.2M</strong> to near zero &mdash; in two steps. At 90%,
            distributor catalog risk clears as UNFI and KeHE fill rates
            cross their 90% threshold (<strong>$1.8M</strong> recovered).
            At 95%, retailer shelf risk clears as velocity recovers above
            delisting thresholds (<strong>$4.4M</strong> more). The total:{' '}
            <strong>$6.2M</strong> in forward revenue no longer at risk.
          </p>
        </div>
      )}
      </div>

      <RecoveryTable scenarios={scenarios} activeDims={activeDims} />
    </section>
  )
}
