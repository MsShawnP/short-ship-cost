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

  // Filter by month range.
  const filteredCosts = useMemo(
    () => filterByMonth(costByMonth, range),
    [costByMonth, range],
  )
  const filteredOrders = useMemo(
    () => filterByMonth(ordersByMonth, range),
    [ordersByMonth, range],
  )

  // Sum filtered costs by dimension. Deauthorization is missing from
  // cost_by_month (events are SKU/retailer-level, not monthly), so when
  // filtered we omit it and surface a note. When unfiltered we pull
  // deauth from cost_summary so the headline matches the full-period total.
  // Then narrow further by the user's active-dimension toggles.
  const { dims, costsByDim, deauthFull, deauthSuppressed } = useMemo(() => {
    const byDim = {}
    for (const r of filteredCosts) {
      byDim[r.dimension] = (byDim[r.dimension] || 0) + r.cost
    }
    const deauthRow = summary.find((r) => r.dimension === 'deauthorization')
    const deauthFull = deauthRow ? deauthRow.total_cost : 0
    let availableDims
    if (range.isFiltered) {
      availableDims = ORDER.filter((d) => d !== 'deauthorization')
    } else {
      byDim.deauthorization = deauthFull
      availableDims = ORDER
    }
    const dims = availableDims.filter((d) => activeDims.has(d))
    const deauthSuppressed =
      availableDims.includes('deauthorization') && !activeDims.has('deauthorization')
    return { dims, costsByDim: byDim, deauthFull, deauthSuppressed }
  }, [filteredCosts, summary, range.isFiltered, activeDims])

  const { segs, total } = useMemo(
    () => buildLayout(costsByDim, dims),
    [costsByDim, dims],
  )

  const lostRevenue = costsByDim.lost_revenue || 0
  const cascading = total - lostRevenue

  const shipped = filteredOrders.reduce((s, r) => s + r.shipped_revenue, 0)
  const demand = filteredOrders.reduce((s, r) => s + r.demand, 0)
  const demandGap = demand - shipped

  const wholesaleMargin = meta.cost_parameters.wholesale_margin_pct.value
  const estMargin = shipped * wholesaleMargin
  const pctOfShipped = shipped > 0 ? total / shipped : 0
  const pctOfMargin = estMargin > 0 ? total / estMargin : 0

  const topCascading = segs
    .filter((s) => s.key !== 'lost_revenue' && s.value > 0)
    .sort((a, b) => b.value - a.value)[0]

  const fmtC = useCallback((v) => fmtCompact(v), [])
  const fmtP = useCallback((v) => fmtPct(v), [])
  const animTotal = useAnimatedValue(total, fmtC)
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
      <p className={styles.framing}>
        When a business cannot ship an order in full, standard practice is to
        edit it down and ship what inventory allows. Most systems then overwrite
        the original&mdash;and with it, any record of what was actually demanded
        and any visibility into what that shortfall costs.
      </p>

      <div className={styles.callout}>
        <div className={styles.calloutNumber}>{animTotal}</div>
        <p className={styles.calloutPrimary}>
          in {range.isFiltered ? 'short-shipping costs over the selected period' : 'total short-shipping costs'} &mdash;{' '}
          {fmtPct(pctOfShipped)} of shipped revenue.
        </p>
        <p className={styles.calloutSecondary}>
          Cinderhaven received {fmtCompact(demand)} in orders from retail and
          distributor partners. It shipped {fmtCompact(shipped)}. The{' '}
          {fmtCompact(demandGap)} gap &mdash; and the {fmtCompact(cascading)}{' '}
          in cascading costs it triggers &mdash; are invisible because the
          original orders are overwritten.
        </p>
      </div>

      {topCascading && (
        <p className={styles.insightLine}>
          Lost revenue is {fmtPct(lostRevenue / total)} of the total. The
          other {fmtPct(cascading / total)}&mdash;led
          by {topCascading.label.toLowerCase()} at {fmtCompact(topCascading.value)}&mdash;are
          costs no one can measure when the original order is overwritten.
        </p>
      )}

      <div className={styles.chart}>
        <h2 className={styles.chartTitle}>
          Beyond the revenue gap: {fmtCompact(cascading)} in cascading costs
          the business cannot see
        </h2>
        <p className={styles.chartSubtitle}>
          The {fmtCompact(total)} {range.isFiltered ? 'period' : 'total'}{' '}
          flows into {dims.length} cost dimensions. Click any block to pin
          its details.
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
            fill={DIMENSION_COLOR.lost_revenue}
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
            Total
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
          Source: Cinderhaven Provisions synthetic order data, {periodLabel}.
          The smallest dimensions are drawn at a {RIGHT_MIN_H}-pixel minimum
          block height for readability; the connecting flows preserve true
          proportional width on the left.
          {range.isFiltered && (
            <>
              {' '}
              Deauthorization ({fmtCompact(deauthFull)} full-period) is
              omitted when a time filter is active because the underlying
              events are SKU- and retailer-level, not monthly. Buffer
              simulation is also full-period only.
            </>
          )}
          {deauthSuppressed && !range.isFiltered && (
            <>
              {' '}
              Deauthorization ({fmtCompact(deauthFull)}) is excluded by the
              dimension toggle.
            </>
          )}
        </p>

      </div>

      <div className={styles.benchmarks}>
        <div className={styles.benchmark}>
          <div className={styles.benchmarkValue}>{animPctShipped}</div>
          <div className={styles.benchmarkLabel}>of shipped revenue</div>
        </div>
        <div className={styles.benchmark}>
          <div className={styles.benchmarkValue}>{animPctMargin}</div>
          <div className={styles.benchmarkLabel}>of estimated gross margin</div>
          <div className={styles.benchmarkNote}>
            assumes {fmtPct(wholesaleMargin)} wholesale margin
          </div>
        </div>
        <div className={styles.benchmark}>
          <div className={styles.benchmarkValue}>{animDemandGap}</div>
          <div className={styles.benchmarkLabel}>in unshipped demand</div>
        </div>
      </div>
    </section>
  )
}
