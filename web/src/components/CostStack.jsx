import { useCallback, useMemo, useState } from 'react'

import { DIMENSION_COLOR, DIMENSION_LABEL, DIMENSION_ORDER } from '../lib/dimensions.js'
import { fmtCompact, fmtPct } from '../lib/format.js'
import useAnimatedValue from '../lib/useAnimatedValue.js'
import {
  filterByMonth,
  useTimeRange,
} from '../lib/timeRange.jsx'
import PinnedCallout from './PinnedCallout.jsx'
import styles from './CostStack.module.css'

const ORDER = DIMENSION_ORDER

const VB_W = 720
const VB_H = 500
const BAR_Y = 20
const BAR_H = 460

const LEFT_X = 20
const LEFT_W = 80
const LEFT_RIGHT = LEFT_X + LEFT_W

const RIGHT_X = 360
const RIGHT_W = 80
const RIGHT_LEFT = RIGHT_X
const RIGHT_RIGHT = RIGHT_X + RIGHT_W

const LABEL_X = RIGHT_RIGHT + 22
const LABEL_VALUE_X = VB_W - 4
const CONNECTOR_X1 = RIGHT_RIGHT + 2
const CONNECTOR_X2 = LABEL_X - 4

const RIGHT_MIN_H = 20
const RIGHT_GAP = 4

function buildLayout(costsByDim, dims) {
  const total = dims.reduce((s, d) => s + (costsByDim[d] || 0), 0)

  const segs = dims.map((dim) => ({
    key: dim,
    label: DIMENSION_LABEL[dim],
    value: costsByDim[dim] || 0,
    color: DIMENSION_COLOR[dim],
  }))

  const totalGap = (segs.length - 1) * RIGHT_GAP
  const blockSpace = BAR_H - totalGap

  let lockedTotal = 0
  let remainingValue = 0
  const locked = new Set()
  for (const s of segs) {
    const propH = total > 0 ? (s.value / total) * blockSpace : 0
    if (propH < RIGHT_MIN_H) {
      locked.add(s.key)
      lockedTotal += RIGHT_MIN_H
    } else {
      remainingValue += s.value
    }
  }
  const remainingSpace = blockSpace - lockedTotal
  for (const s of segs) {
    s.rightHeight = locked.has(s.key)
      ? RIGHT_MIN_H
      : remainingValue > 0
        ? (s.value / remainingValue) * remainingSpace
        : RIGHT_MIN_H
  }

  let rCursor = BAR_Y
  for (const s of segs) {
    s.rightTop = rCursor
    s.rightBottom = rCursor + s.rightHeight
    s.rightCenter = (s.rightTop + s.rightBottom) / 2
    rCursor = s.rightBottom + RIGHT_GAP
  }

  let lCursor = BAR_Y
  for (const s of segs) {
    const sliceH = total > 0 ? (s.value / total) * BAR_H : 0
    s.leftTop = lCursor
    s.leftHeight = sliceH
    s.leftBottom = lCursor + sliceH
    lCursor = s.leftBottom
  }

  return { segs, total }
}

function flowPath(s) {
  const lx = LEFT_RIGHT
  const rx = RIGHT_LEFT
  const mid = (lx + rx) / 2
  return [
    `M ${lx} ${s.leftTop}`,
    `C ${mid} ${s.leftTop}, ${mid} ${s.rightTop}, ${rx} ${s.rightTop}`,
    `L ${rx} ${s.rightBottom}`,
    `C ${mid} ${s.rightBottom}, ${mid} ${s.leftBottom}, ${lx} ${s.leftBottom}`,
    'Z',
  ].join(' ')
}

export default function CostStack({ meta, summary, costByMonth, ordersByMonth }) {
  const range = useTimeRange()
  const { activeDims } = range
  const [pinned, setPinned] = useState(null)

  const filteredCosts = useMemo(
    () => filterByMonth(costByMonth, range),
    [costByMonth, range],
  )
  const filteredOrders = useMemo(
    () => filterByMonth(ordersByMonth, range),
    [ordersByMonth, range],
  )

  const { dims, costsByDim } = useMemo(() => {
    const byDim = {}
    for (const r of filteredCosts) {
      byDim[r.dimension] = (byDim[r.dimension] || 0) + r.cost
    }
    const dims = ORDER.filter((d) => activeDims.has(d))
    return { dims, costsByDim: byDim }
  }, [filteredCosts, activeDims])

  const { segs, total } = useMemo(
    () => buildLayout(costsByDim, dims),
    [costsByDim, dims],
  )

  const forgoneRevenue = costsByDim.forgone_revenue || 0
  const cascading = total - forgoneRevenue // cash penalties: fines + chargebacks + deductions

  const contributionMargin = meta.contribution_margin_pct || 0.52
  const forgoneMargin = forgoneRevenue * contributionMargin
  const economicLoss = cascading + forgoneMargin // cash penalties + forgone margin

  const shipped = filteredOrders.reduce((s, r) => s + r.shipped_revenue, 0)
  const demand = filteredOrders.reduce((s, r) => s + r.demand, 0)
  const demandGap = demand - shipped

  const estMargin = shipped * contributionMargin
  const pctOfShipped = shipped > 0 ? economicLoss / shipped : 0
  const pctOfMargin = estMargin > 0 ? cascading / estMargin : 0

  // Full-window, all-dimension figures for the deck headline — independent of
  // the time filter and dimension toggles, but still reflect parameter edits.
  const fullTotals = summary.reduce(
    (acc, d) => {
      acc[d.dimension] = d.total_cost
      acc.total += d.total_cost
      return acc
    },
    { total: 0 },
  )
  const fullForgoneRevenue = fullTotals.forgone_revenue || 0
  const fullCash = fullTotals.total - fullForgoneRevenue
  const fullForgoneMargin = fullForgoneRevenue * contributionMargin
  const fullEconomicLoss = fullCash + fullForgoneMargin
  const windowYears = Math.round(
    (new Date(meta.time_window.end) - new Date(meta.time_window.start)) /
      (365.25 * 86400000),
  )

  const topCascading = segs
    .filter((s) => s.key !== 'forgone_revenue' && s.value > 0)
    .sort((a, b) => b.value - a.value)[0]

  const fmtC = useCallback((v) => fmtCompact(v), [])
  const fmtP = useCallback((v) => fmtPct(v), [])
  const animEconomicLoss = useAnimatedValue(economicLoss, fmtC)
  const animPctShipped = useAnimatedValue(pctOfShipped, fmtP)
  const animPctMargin = useAnimatedValue(pctOfMargin, fmtP)
  const animDemandGap = useAnimatedValue(demandGap, fmtC)

  const activeSeg = pinned ? segs.find((s) => s.key === pinned) : null
  const totalCenterY = BAR_Y + BAR_H / 2

  const opacityFor = (key, baseActive, baseDimmed, baseDefault) => {
    if (pinned === null || pinned === undefined) return baseDefault
    return pinned === key ? baseActive : baseDimmed
  }

  const togglePin = (key) =>
    setPinned((prev) => (prev === key ? null : key))

  const periodLabel = range.isFiltered
    ? `${range.startMonth} to ${range.endMonth}`
    : `${meta.time_window.start} to ${meta.time_window.end}`

  if (total === 0 || segs.length === 0) {
    return (
      <section className={styles.section}>
        <div className={styles.emptyState}>
          <p className={styles.emptyTitle}>No cost data to display</p>
          <p className={styles.emptyBody}>
            {dims.length === 0
              ? 'All dimensions are excluded. Re-enable a dimension chip above to see the breakdown.'
              : 'The current time range contains no cost data. Widen the range from the header filter.'}
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className={styles.section}>
      <header className={styles.deck}>
        <h1 className={styles.deckTitle}>What short-shipping actually costs</h1>
        <p className={styles.deckLede}>
          A sub-1% fill shortfall costs Cinderhaven about{' '}
          {fmtCompact(fullEconomicLoss)} over the {windowYears}-year window
          &mdash; {fmtCompact(fullCash)} in cash penalties plus{' '}
          {fmtCompact(fullForgoneMargin)} in forgone margin &mdash; and almost
          none of it is visible, because the original orders are overwritten.
        </p>
      </header>

      <p className={styles.framing}>
        When a business cannot ship an order in full, standard practice is to
        edit it down and ship what inventory allows. Most systems then overwrite
        the original&mdash;and with it, any record of what was actually demanded
        and any visibility into what that shortfall costs.
      </p>

      <div className={styles.callout}>
        <div className={styles.calloutNumber}>{animEconomicLoss}</div>
        <p className={styles.calloutPrimary}>
          in{' '}
          {range.isFiltered
            ? 'economic loss over the selected period'
            : 'economic loss from short-shipping'}{' '}
          &mdash; {fmtCompact(cascading)} in cash penalties (compliance fines,
          chargebacks, and deductions) plus {fmtCompact(forgoneMargin)} in
          forgone contribution margin, at a {fmtPct(meta.overall_fill_rate)}{' '}
          portfolio fill rate ({fmtPct(meta.retailer_fill_rate)} retailer,{' '}
          {fmtPct(meta.distributor_fill_rate)} distributor).
        </p>
        <p className={styles.calloutSecondary}>
          Cinderhaven received {fmtCompact(demand)} in orders from retail and
          distributor partners and shipped {fmtCompact(shipped)}. The{' '}
          {fmtCompact(forgoneRevenue)} it could not ship is forgone revenue at
          full wholesale &mdash; a top-line opportunity carried at{' '}
          {fmtPct(contributionMargin)} margin, not a cash cost, which is why the
          economic loss counts its margin rather than its full price. The cash
          penalties the shortfall triggers are easy to miss because the original
          orders are overwritten, which is exactly how a sub-1% shortfall still
          compounds into real cost.
        </p>
      </div>

      {topCascading && (
        <p className={styles.insightLine}>
          Forgone revenue of {fmtCompact(forgoneRevenue)} is a top-line
          opportunity, not cash out the door; at {fmtPct(contributionMargin)}{' '}
          margin it represents {fmtCompact(forgoneMargin)} in lost contribution.
          The {fmtCompact(cascading)} in cash penalties it triggers &mdash; led
          by {topCascading.label.toLowerCase()} at{' '}
          {fmtCompact(topCascading.value)} &mdash; is the part no one is
          attributing when the original order is overwritten.
        </p>
      )}

      <div className={styles.chart}>
        <h2 className={styles.chartTitle}>
          Beyond the revenue gap: {fmtCompact(cascading)} in cascading costs
          no one is attributing
        </h2>
        <p className={styles.chartSubtitle}>
          Gross composition: {fmtCompact(total)} across {dims.length} cost
          dimensions. Forgone revenue is drawn at full wholesale; only its{' '}
          {fmtPct(contributionMargin)} margin enters the{' '}
          {fmtCompact(economicLoss)} economic loss above. Click any block to
          pin its details.
        </p>

        {pinned && activeSeg && (
          <PinnedCallout
            title={activeSeg.label}
            subtitle={`${fmtCompact(activeSeg.value)} · ${fmtPct(activeSeg.value / total)} of period`}
            onUnpin={() => setPinned(null)}
          />
        )}

        <svg
          className={styles.svg}
          viewBox={`0 0 ${VB_W} ${VB_H}`}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="Flow split: cost of shorts allocated across dimensions"
        >
          <rect
            x={LEFT_X}
            y={BAR_Y}
            width={LEFT_W}
            height={BAR_H}
            fill={DIMENSION_COLOR.forgone_revenue}
          />
          <text
            className={styles.totalLabelLarge}
            x={LEFT_X + LEFT_W / 2}
            y={totalCenterY - 4}
            textAnchor="middle"
          >
            {fmtCompact(total)}
          </text>
          <text
            className={styles.totalLabelSmall}
            x={LEFT_X + LEFT_W / 2}
            y={totalCenterY + 14}
            textAnchor="middle"
          >
            Gross
          </text>

          {segs.map((s) => (
            <path
              key={`flow-${s.key}`}
              className={`${styles.flowPath} ${styles.dimmable}`}
              d={flowPath(s)}
              fill={s.color}
              fillOpacity={opacityFor(s.key, 1, 0.2, 1)}
              onClick={() => togglePin(s.key)}
            />
          ))}

          {segs.map((s) => {
            const opacity = opacityFor(s.key, 1, 0.3, 1)
            return (
              <g
                key={`r-${s.key}`}
                className={`${styles.hoverGroup} ${styles.dimmable}`}
                onClick={() => togglePin(s.key)}
                opacity={opacity}
              >
                <rect
                  x={RIGHT_X - 4}
                  y={s.rightTop - 2}
                  width={VB_W - RIGHT_X + 4}
                  height={s.rightHeight + 4}
                  fill="transparent"
                />
                <rect
                  x={RIGHT_X}
                  y={s.rightTop}
                  width={RIGHT_W}
                  height={s.rightHeight}
                  fill={s.color}
                />
                <line
                  x1={CONNECTOR_X1}
                  y1={s.rightCenter}
                  x2={CONNECTOR_X2}
                  y2={s.rightCenter}
                  stroke={s.color}
                  className={styles.connector}
                />
                <text
                  className={styles.labelName}
                  x={LABEL_X}
                  y={s.rightCenter + 4}
                >
                  {s.label}
                </text>
                <text
                  className={styles.labelValue}
                  x={LABEL_VALUE_X}
                  y={s.rightCenter + 4}
                  textAnchor="end"
                >
                  {fmtCompact(s.value)}
                </text>
              </g>
            )
          })}
        </svg>

        <p className={styles.chartFootnote}>
          Source: Cinderhaven Provisions platform data, {periodLabel}.
          The smallest dimensions are drawn at a {RIGHT_MIN_H}-pixel minimum
          block height for readability; the connecting flows preserve true
          proportional width on the left.
        </p>
        <p className={styles.chartFootnote}>
          Chargebacks and deductions are drawn from separate platform event
          streams and counted once each. A chargeback is sometimes realized as
          a deduction on remittance; where that occurs the two could overlap, so
          they are reported as distinct line items rather than summed into a
          single penalty figure.
        </p>

      </div>

      <div className={styles.benchmarks}>
        <div className={styles.benchmark}>
          <div className={styles.benchmarkValue}>{animPctShipped}</div>
          <div className={styles.benchmarkLabel}>economic loss, as a share of shipped revenue</div>
        </div>
        <div className={styles.benchmark}>
          <div className={styles.benchmarkValue}>{animPctMargin}</div>
          <div className={styles.benchmarkLabel}>of contribution margin, in cash penalties</div>
          <div className={styles.benchmarkNote}>
            assumes {fmtPct(contributionMargin)} contribution margin
          </div>
        </div>
        <div className={styles.benchmark}>
          <div className={styles.benchmarkValue}>{animDemandGap}</div>
          <div className={styles.benchmarkLabel}>in forgone revenue, at full wholesale</div>
        </div>
      </div>
    </section>
  )
}
