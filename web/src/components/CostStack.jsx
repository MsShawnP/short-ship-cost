import { useState } from 'react'

import { DIMENSION_LABEL } from '../lib/dimensions.js'
import { fmtCompact, fmtPct } from '../lib/format.js'
import styles from './CostStack.module.css'

const ORDER = [
  'lost_revenue',
  'deauthorization',
  'otif_fines',
  'chargebacks',
  'dtc_cancellations',
  'triage_labor',
  'distributor_returns',
  'dtc_margin_leakage',
]

const SEQUENTIAL_TEALS = {
  lost_revenue: '#0A3D3D',
  deauthorization: '#14605C',
  otif_fines: '#1F8078',
  chargebacks: '#2A9D93',
  dtc_cancellations: '#45B5AA',
  triage_labor: '#6BCABD',
  distributor_returns: '#93DCD2',
  dtc_margin_leakage: '#BDEEE8',
}

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

function buildLayout(summary) {
  const byDim = Object.fromEntries(summary.map((r) => [r.dimension, r]))
  const total = summary.reduce((s, r) => s + r.total_cost, 0)

  const segs = ORDER.map((dim) => ({
    key: dim,
    label: DIMENSION_LABEL[dim],
    value: byDim[dim].total_cost,
    color: SEQUENTIAL_TEALS[dim],
  }))

  const totalGap = (segs.length - 1) * RIGHT_GAP
  const blockSpace = BAR_H - totalGap

  let lockedTotal = 0
  let remainingValue = 0
  const locked = new Set()
  for (const s of segs) {
    const propH = (s.value / total) * blockSpace
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
      : (s.value / remainingValue) * remainingSpace
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
    const sliceH = (s.value / total) * BAR_H
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

export default function CostStack({ meta, summary }) {
  const { segs, total } = buildLayout(summary)
  const [hovered, setHovered] = useState(null)
  const hoveredSeg = hovered ? segs.find((s) => s.key === hovered) : null

  const lostRevenue = segs[0].value
  const cascading = total - lostRevenue

  const shipped = meta.shipped_revenue
  const fillRate = meta.overall_fill_rate
  const wholesaleMargin = meta.cost_parameters.wholesale_margin_pct.value
  const estMargin = shipped * wholesaleMargin
  const demand = fillRate > 0 ? shipped / fillRate : 0
  const demandGap = demand - shipped

  const pctOfShipped = total / shipped
  const pctOfMargin = total / estMargin

  const totalCenterY = BAR_Y + BAR_H / 2

  const opacityFor = (key, baseActive, baseDimmed, baseDefault) => {
    if (hovered === null) return baseDefault
    return hovered === key ? baseActive : baseDimmed
  }

  return (
    <section className={styles.section}>
      <div className={styles.callout}>
        <div className={styles.calloutNumber}>{fmtCompact(total)}</div>
        <p className={styles.calloutPrimary}>
          in total short-shipping costs &mdash; {fmtPct(pctOfShipped)} of shipped
          revenue.
        </p>
        <p className={styles.calloutSecondary}>
          Cinderhaven received {fmtCompact(demand)} in orders from retail and
          distributor partners. It shipped {fmtCompact(shipped)}. The{' '}
          {fmtCompact(demandGap)} gap &mdash; and the {fmtCompact(cascading)}{' '}
          in cascading costs it triggers &mdash; are invisible because the
          original orders are overwritten.
        </p>
      </div>

      <div className={styles.chart}>
        <h2 className={styles.chartTitle}>
          Beyond the revenue gap: {fmtCompact(cascading)} in cascading costs
          the business cannot see
        </h2>
        <p className={styles.chartSubtitle}>
          {hoveredSeg ? (
            <>
              <strong>{hoveredSeg.label}</strong> &mdash;{' '}
              {fmtCompact(hoveredSeg.value)} ({fmtPct(hoveredSeg.value / total)}{' '}
              of total)
            </>
          ) : (
            <>
              The {fmtCompact(total)} total flows into eight cost dimensions.
              Hover any block for details.
            </>
          )}
        </p>

        <svg
          className={styles.svg}
          viewBox={`0 0 ${VB_W} ${VB_H}`}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="Flow split: total cost of shorts allocated across eight dimensions"
        >
          {/* Left block: total */}
          <rect
            x={LEFT_X}
            y={BAR_Y}
            width={LEFT_W}
            height={BAR_H}
            fill={SEQUENTIAL_TEALS.lost_revenue}
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

          {/* Connector flows */}
          {segs.map((s) => (
            <path
              key={`flow-${s.key}`}
              className={`${styles.flowPath} ${styles.dimmable}`}
              d={flowPath(s)}
              fill={s.color}
              fillOpacity={opacityFor(s.key, 1, 0.2, 1)}
              onMouseEnter={() => setHovered(s.key)}
              onMouseLeave={() => setHovered(null)}
            />
          ))}

          {/* Right side: hover groups (block + connector + labels) */}
          {segs.map((s) => {
            const opacity = opacityFor(s.key, 1, 0.3, 1)
            return (
              <g
                key={`r-${s.key}`}
                className={`${styles.hoverGroup} ${styles.dimmable}`}
                onMouseEnter={() => setHovered(s.key)}
                onMouseLeave={() => setHovered(null)}
                opacity={opacity}
              >
                {/* Hover hit area covering block + label row */}
                <rect
                  x={RIGHT_X - 4}
                  y={s.rightTop - 2}
                  width={VB_W - RIGHT_X + 4}
                  height={s.rightHeight + 4}
                  fill="transparent"
                />
                {/* Right block */}
                <rect
                  x={RIGHT_X}
                  y={s.rightTop}
                  width={RIGHT_W}
                  height={s.rightHeight}
                  fill={s.color}
                />
                {/* Connector line from block to label */}
                <line
                  x1={CONNECTOR_X1}
                  y1={s.rightCenter}
                  x2={CONNECTOR_X2}
                  y2={s.rightCenter}
                  stroke={s.color}
                  className={styles.connector}
                />
                {/* Label */}
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
          Source: Cinderhaven Provisions synthetic order data,{' '}
          {meta.time_window.start} to {meta.time_window.end}. The six smallest
          dimensions are drawn at a {RIGHT_MIN_H}-pixel minimum block height
          for readability; the connecting flows preserve true proportional
          width on the left.
        </p>
      </div>

      <div className={styles.benchmarks}>
        <div className={styles.benchmark}>
          <div className={styles.benchmarkValue}>{fmtPct(pctOfShipped)}</div>
          <div className={styles.benchmarkLabel}>of shipped revenue</div>
        </div>
        <div className={styles.benchmark}>
          <div className={styles.benchmarkValue}>{fmtPct(pctOfMargin)}</div>
          <div className={styles.benchmarkLabel}>of estimated gross margin</div>
          <div className={styles.benchmarkNote}>
            assumes {fmtPct(wholesaleMargin)} wholesale margin
          </div>
        </div>
        <div className={styles.benchmark}>
          <div className={styles.benchmarkValue}>{fmtCompact(demandGap)}</div>
          <div className={styles.benchmarkLabel}>in unshipped demand</div>
        </div>
      </div>
    </section>
  )
}
