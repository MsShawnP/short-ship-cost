import { useMemo, useState } from 'react'

import { DIMENSION_LABEL, DIMENSION_COLOR } from '../lib/dimensions.js'
import { fmtCompact, fmtPct } from '../lib/format.js'
import { useTimeRange } from '../lib/timeRange.jsx'
import styles from './RetailerDrilldown.module.css'

const ALL_DIMS = [
  'lost_revenue',
  'deauthorization',
  'otif_fines',
  'chargebacks',
  'dtc_cancellations',
  'triage_labor',
  'distributor_returns',
  'dtc_margin_leakage',
]

const FILTERED_DIMS = ALL_DIMS.filter((d) => d !== 'deauthorization')

// ---- Helpers ---------------------------------------------------------------

function withinRange(month, range) {
  if (!month) return !range.isFiltered
  return month >= range.startMonth && month <= range.endMonth
}

function buildRetailerRows(costByRetailer, range, dims) {
  const dimSet = new Set(dims)
  const map = new Map()
  for (const r of costByRetailer) {
    if (!dimSet.has(r.dimension)) continue
    if (!withinRange(r.month, range)) continue
    if (!map.has(r.retailer)) {
      const init = { retailer: r.retailer, total: 0 }
      for (const d of dims) init[d] = 0
      map.set(r.retailer, init)
    }
    const row = map.get(r.retailer)
    row[r.dimension] += r.cost
    row.total += r.cost
  }
  return Array.from(map.values()).sort((a, b) => b.total - a.total)
}

function buildSkuRows(costBySku, range, dims, selectedRetailer) {
  const filterActive = range.isFiltered

  const rows = costBySku.map((sku) => {
    const totals = Object.fromEntries(dims.map((d) => [d, 0]))
    let total = 0

    if (filterActive) {
      for (const m of sku.by_month || []) {
        if (!withinRange(m.month, range)) continue
        for (const d of dims) {
          const v = m[d] || 0
          if (v) {
            totals[d] += v
            total += v
          }
        }
      }
    } else {
      for (const d of dims) {
        const v = sku.by_dimension?.[d] || 0
        totals[d] = v
        total += v
      }
    }

    return {
      sku: sku.sku,
      product_name: sku.product_name,
      product_line: sku.product_line,
      totals,
      total,
      retailerCost: sku.by_retailer?.[selectedRetailer] || 0,
      isOther: sku.sku === 'Other',
    }
  })

  if (selectedRetailer) {
    return rows.filter((r) => r.retailerCost > 0)
  }
  return rows
}

function sortSkuRows(rows, sortBy) {
  const dir = sortBy.dir === 'asc' ? 1 : -1
  const getter = (r) => {
    switch (sortBy.key) {
      case 'sku':
        return r.sku
      case 'product_name':
        return r.product_name
      case 'product_line':
        return r.product_line
      case 'total':
        return r.total
      default:
        return r.totals[sortBy.key] ?? 0
    }
  }
  const isOther = (r) => r.isOther
  const non = rows.filter((r) => !isOther(r))
  const other = rows.filter(isOther)
  non.sort((a, b) => {
    const av = getter(a)
    const bv = getter(b)
    if (av < bv) return -1 * dir
    if (av > bv) return 1 * dir
    return 0
  })
  return [...non, ...other]
}

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

// ---- Retailer chart (custom SVG) ------------------------------------------

const VB_W = 800
const LABEL_X = 110
const BAR_X = 120
const MAX_BAR_W = 560
const BAR_H = 30
const ROW_GAP = 18
const ROW_H = BAR_H + ROW_GAP
const TOP_PAD = 8
const MIN_SEG_W = 12 // px (viewBox units) — exaggerated so thin dims read as distinct slices

function buildSegments(row, dims, scaleW) {
  // Allocate widths: any dim with cost > 0 gets at least MIN_SEG_W.
  // The padding-up of small segments slightly exaggerates the bar's
  // total width — that's intentional so thin colors remain visible.
  const visible = dims.filter((d) => (row[d] || 0) > 0)
  let cursor = 0
  return visible.map((d) => {
    const v = row[d]
    const trueW = scaleW(v)
    const w = trueW < MIN_SEG_W ? MIN_SEG_W : trueW
    const seg = {
      dim: d,
      x: BAR_X + cursor,
      w,
      color: DIMENSION_COLOR[d],
    }
    cursor += w
    return seg
  })
}

function RetailerChart({ rows, dims, selectedRetailer, onSelect }) {
  const [hovered, setHovered] = useState(null)

  if (!rows.length) {
    return (
      <p className={styles.chartFootnote}>
        No retailer data for the selected time range.
      </p>
    )
  }

  const maxTotal = Math.max(...rows.map((r) => r.total), 1)
  const grandTotal = rows.reduce((s, r) => s + r.total, 0)
  const VB_H = TOP_PAD * 2 + rows.length * ROW_H

  const top = rows[0]
  const topDim = dims
    .map((d) => ({ dim: d, cost: top[d] || 0 }))
    .sort((a, b) => b.cost - a.cost)[0]
  const titleParts = [`${top.retailer} bears the largest cost burden`]
  if (topDim && topDim.cost > 0) {
    titleParts.push(
      `${fmtCompact(top.total)}, driven by ${DIMENSION_LABEL[topDim.dim].toLowerCase()}`,
    )
  }
  const title = titleParts.join(' — ')

  const hoveredRow = hovered ? rows.find((r) => r.retailer === hovered) : null
  const hoveredBreakdown = hoveredRow
    ? dims
        .map((d) => ({
          dim: d,
          cost: hoveredRow[d] || 0,
        }))
        .filter((e) => e.cost > 0)
        .sort((a, b) => b.cost - a.cost)
    : null

  return (
    <div className={styles.chartBlock}>
      <h3 className={styles.chartTitle}>{title}</h3>
      <p className={styles.chartSubtitle}>
        {hoveredRow ? (
          <>
            <strong>{hoveredRow.retailer}</strong> &mdash;{' '}
            {fmtCompact(hoveredRow.total)} (
            {fmtPct(hoveredRow.total / grandTotal)} of all retailers). Click
            to filter SKUs below.
          </>
        ) : (
          <>
            Cost composition by retail partner. Click a bar to filter the
            SKU table below; hover for the dimension breakdown.
          </>
        )}
      </p>

      {hoveredBreakdown && (
        <div className={styles.breakdownRow}>
          {hoveredBreakdown.map((e) => (
            <span key={e.dim} className={styles.breakdownChip}>
              <span
                className={styles.breakdownSwatch}
                style={{ background: DIMENSION_COLOR[e.dim] }}
              />
              {DIMENSION_LABEL[e.dim]}{' '}
              <strong>{fmtCompact(e.cost)}</strong>{' '}
              <span className={styles.breakdownPct}>
                ({fmtPct(e.cost / hoveredRow.total)})
              </span>
            </span>
          ))}
        </div>
      )}

      <svg
        className={styles.svg}
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Cost of shorts by retailer, broken down by dimension"
      >
        {rows.map((r, i) => {
          const rowTop = TOP_PAD + i * ROW_H
          const isSelected = selectedRetailer === r.retailer
          const isDimmed = selectedRetailer !== null && !isSelected
          const isHoveredOther = hovered !== null && hovered !== r.retailer
          const opacity = isDimmed ? 0.3 : isHoveredOther ? 0.55 : 1

          const scaleW = (v) => (v / maxTotal) * MAX_BAR_W
          const segs = buildSegments(r, dims, scaleW)
          const totalBarW = segs.reduce((s, x) => s + x.w, 0)

          return (
            <g
              key={r.retailer}
              className={styles.retailerRow}
              onClick={() =>
                onSelect((cur) => (cur === r.retailer ? null : r.retailer))
              }
              onMouseEnter={() => setHovered(r.retailer)}
              onMouseLeave={() => setHovered(null)}
              opacity={opacity}
            >
              <rect
                x={0}
                y={rowTop - 4}
                width={VB_W}
                height={ROW_H}
                fill="transparent"
              />

              <text
                className={styles.retailerLabel}
                x={LABEL_X}
                y={rowTop + BAR_H / 2 + 4}
                textAnchor="end"
              >
                {r.retailer}
              </text>

              {segs.map((s) => (
                <rect
                  key={`m-${s.dim}`}
                  x={s.x}
                  y={rowTop}
                  width={s.w}
                  height={BAR_H}
                  fill={s.color}
                />
              ))}

              <text
                className={styles.totalLabel}
                x={BAR_X + totalBarW + 8}
                y={rowTop + BAR_H / 2 + 4}
              >
                {fmtCompact(r.total)}
              </text>
            </g>
          )
        })}
      </svg>

      <p className={styles.chartFootnote}>
        Each bar is stacked by cost dimension and sized by the retailer&rsquo;s
        total. Segment widths have a minimum display size; hover for exact
        values.
      </p>
    </div>
  )
}

// ---- SKU table -------------------------------------------------------------

function SkuTable({
  rows,
  dims,
  sortBy,
  onSort,
  selectedRetailer,
  onClearRetailer,
}) {
  // Per-dimension max for heatmap shading (excludes "Other" so it doesn't
  // skew the scale).
  const dimMax = useMemo(() => {
    const m = {}
    for (const d of dims) {
      let max = 0
      for (const r of rows) {
        if (r.isOther) continue
        const v = r.totals[d] || 0
        if (v > max) max = v
      }
      m[d] = max
    }
    return m
  }, [rows, dims])

  const handleSort = (key) => {
    if (sortBy.key === key) {
      onSort({ key, dir: sortBy.dir === 'asc' ? 'desc' : 'asc' })
    } else {
      const dir =
        key === 'sku' || key === 'product_name' || key === 'product_line'
          ? 'asc'
          : 'desc'
      onSort({ key, dir })
    }
  }

  const sortIndicator = (key) =>
    sortBy.key === key ? (sortBy.dir === 'asc' ? '▲' : '▼') : ''

  return (
    <div className={styles.tableBlock}>
      <div className={styles.tableHead}>
        <h3 className={styles.tableTitle}>Top products by cost</h3>
      </div>

      {selectedRetailer && (
        <div className={styles.retailerFilterRow}>
          <span>
            Showing SKUs with cost attributed to{' '}
            <strong>{selectedRetailer}</strong>
            {rows.length > 0 &&
              ` (${rows.filter((r) => !r.isOther).length} SKUs)`}
          </span>
          <button
            type="button"
            className={`${styles.clearButton} no-print`}
            onClick={onClearRetailer}
          >
            Clear filter
          </button>
        </div>
      )}

      <div className={styles.tableScroll}>
        <table className={styles.table}>
          <colgroup>
            <col className={styles.colSku} />
            <col className={styles.colProduct} />
            <col className={styles.colLine} />
            <col className={styles.colTotal} />
            {dims.map((d) => (
              <col key={d} className={styles.colDim} />
            ))}
          </colgroup>
          <thead>
            <tr>
              <th onClick={() => handleSort('sku')}>
                SKU{' '}
                <span className={styles.sortIndicator}>
                  {sortIndicator('sku')}
                </span>
              </th>
              <th onClick={() => handleSort('product_name')}>
                Product{' '}
                <span className={styles.sortIndicator}>
                  {sortIndicator('product_name')}
                </span>
              </th>
              <th onClick={() => handleSort('product_line')}>
                Line{' '}
                <span className={styles.sortIndicator}>
                  {sortIndicator('product_line')}
                </span>
              </th>
              <th
                className={styles.numeric}
                onClick={() => handleSort('total')}
              >
                Total{' '}
                <span className={styles.sortIndicator}>
                  {sortIndicator('total')}
                </span>
              </th>
              {dims.map((d) => (
                <th
                  key={d}
                  className={styles.numeric}
                  onClick={() => handleSort(d)}
                  title={DIMENSION_LABEL[d]}
                >
                  {DIMENSION_LABEL[d].split(' ')[0]}{' '}
                  <span className={styles.sortIndicator}>
                    {sortIndicator(d)}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.sku}
                className={r.isOther ? styles.otherRow : undefined}
              >
                <td>
                  <span className={styles.skuCode}>{r.sku}</span>
                </td>
                <td>
                  <span className={styles.productName}>{r.product_name}</span>
                </td>
                <td>
                  <span className={styles.productLine}>{r.product_line}</span>
                </td>
                <td className={`${styles.numeric} ${styles.totalCell}`}>
                  {fmtCompact(r.total)}
                </td>
                {dims.map((d) => {
                  const v = r.totals[d] || 0
                  const max = dimMax[d] || 1
                  const intensity = v > 0 ? Math.min(1, v / max) : 0
                  const alpha = intensity * 0.55
                  const bg = intensity
                    ? hexToRgba(DIMENSION_COLOR[d], alpha)
                    : 'transparent'
                  return (
                    <td
                      key={d}
                      className={`${styles.numeric} ${styles.heatCell}`}
                      style={{ background: bg }}
                    >
                      {v > 0 ? fmtCompact(v) : '—'}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className={styles.tableFootnote}>
        Top 20 SKUs by total cost plus an &ldquo;Other&rdquo; row for the
        remaining SKUs. Triage labor is excluded from per-SKU attribution
        because it is a per-order cost, not per-SKU. Cell shading scales
        with each column&rsquo;s magnitude.
      </p>
    </div>
  )
}

// ---- Main component --------------------------------------------------------

export default function RetailerDrilldown({ costByRetailer, costBySku }) {
  const range = useTimeRange()
  const [selectedRetailer, setSelectedRetailer] = useState(null)
  const [sortBy, setSortBy] = useState({ key: 'total', dir: 'desc' })

  const dims = range.isFiltered ? FILTERED_DIMS : ALL_DIMS

  const retailerRows = useMemo(
    () => buildRetailerRows(costByRetailer, range, dims),
    [costByRetailer, range, dims],
  )

  const skuRowsRaw = useMemo(
    () => buildSkuRows(costBySku, range, dims, selectedRetailer),
    [costBySku, range, dims, selectedRetailer],
  )

  const skuRows = useMemo(
    () => sortSkuRows(skuRowsRaw, sortBy),
    [skuRowsRaw, sortBy],
  )

  return (
    <section className={styles.section}>
      <div className={styles.sectionHead}>
        <h2 className={styles.sectionTitle}>Where the pain lands</h2>
        <p className={styles.sectionSubtitle}>
          Cost of shorts by retail partner and product
        </p>
      </div>

      <RetailerChart
        rows={retailerRows}
        dims={dims}
        selectedRetailer={selectedRetailer}
        onSelect={setSelectedRetailer}
      />

      <SkuTable
        rows={skuRows}
        dims={dims}
        sortBy={sortBy}
        onSort={setSortBy}
        selectedRetailer={selectedRetailer}
        onClearRetailer={() => setSelectedRetailer(null)}
      />
    </section>
  )
}
