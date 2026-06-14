/**
 * JS cost engine for the 4-dimension platform model.
 *
 * Only compliance_fines have tunable parameters (per-channel fine rates).
 * forgone_revenue, chargebacks, and deductions are actual platform data —
 * no parameter scaling needed.
 */

function safeRatio(a, b) {
  if (!Number.isFinite(a) || !Number.isFinite(b) || b === 0) return 1
  const r = a / b
  if (!Number.isFinite(r) || r < 0) return 0
  return r
}

function clampCost(v) {
  if (!Number.isFinite(v) || v < 0) return 0
  return v
}

const FINE_KEY_TO_CHANNEL = {
  fine_walmart: 'Walmart',
  fine_costco: 'Costco',
  fine_whole_foods: 'Whole Foods',
  fine_sprouts: 'Sprouts',
  fine_kroger: 'Kroger',
  fine_regional: 'Regional',
  fine_unfi: 'UNFI',
  fine_kehe: 'KeHE',
  fine_dpi_northwest: 'DPI Northwest',
}

/** Build per-channel ratios for compliance_fines. */
export function getRatios(params, baseline) {
  const fines = {}
  for (const key of Object.keys(baseline)) {
    if (!key.startsWith('fine_')) continue
    const channel = FINE_KEY_TO_CHANNEL[key] ?? key
    fines[channel] = safeRatio(params[key], baseline[key])
  }
  return { compliance_fines: fines }
}

/** Per-(dim, retailer) scaling factor. */
export function ratioFor(dim, retailer, ratios) {
  if (dim === 'compliance_fines') return ratios.compliance_fines[retailer] ?? 1
  return 1
}

function dimAverageRatio(dim, ratios) {
  if (dim === 'compliance_fines') {
    const vs = Object.values(ratios.compliance_fines)
    return vs.length > 0 ? vs.reduce((s, v) => s + v, 0) / vs.length : 1
  }
  return 1
}

/** Re-derive cost_by_retailer with parameter scaling applied. */
export function scaleCostByRetailer(rawRows, ratios) {
  return rawRows.map((r) => ({
    ...r,
    cost: clampCost(r.cost * ratioFor(r.dimension, r.retailer, ratios)),
  }))
}

/** Re-derive cost_by_month with parameter scaling. */
export function scaleCostByMonth(rawRows, ratios) {
  return rawRows.map((r) => ({
    ...r,
    cost: clampCost(r.cost * dimAverageRatio(r.dimension, ratios)),
  }))
}

/** Re-derive cost_by_sku with parameter scaling on by_dimension and by_month. */
export function scaleCostBySku(rawRows, ratios) {
  return rawRows.map((row) => {
    const newByDim = {}
    for (const [dim, value] of Object.entries(row.by_dimension)) {
      newByDim[dim] = clampCost(value * dimAverageRatio(dim, ratios))
    }
    const newByMonth = (row.by_month || []).map((m) => {
      const out = { month: m.month }
      for (const [k, v] of Object.entries(m)) {
        if (k === 'month') continue
        out[k] = clampCost(v * dimAverageRatio(k, ratios))
      }
      return out
    })
    const total = Object.values(newByDim).reduce((s, v) => s + v, 0)
    return {
      ...row,
      total_cost: clampCost(total),
      by_dimension: newByDim,
      by_month: newByMonth,
    }
  })
}

/** Buffer scenarios — scale compliance_fines by the fine-rate ratio;
 *  other dimensions pass through unchanged. */
export function scaleBufferScenarios(rawScenarios, ratios) {
  return rawScenarios.map((s) => {
    const newByDim = {}
    for (const [dim, v] of Object.entries(s.by_dimension)) {
      const factor = dimAverageRatio(dim, ratios)
      const safeFactor = Number.isFinite(factor) && factor >= 0 ? factor : 0
      const original = clampCost(v.original * safeFactor)
      const simulated = clampCost(v.simulated * safeFactor)
      const recovery = original - simulated
      newByDim[dim] = {
        original,
        simulated,
        recovery,
        recovery_pct: original > 0 ? recovery / original : 0,
      }
    }
    let totalCost = 0
    let totalRecovery = 0
    for (const v of Object.values(newByDim)) {
      totalCost += v.simulated
      totalRecovery += v.recovery
    }
    return {
      ...s,
      total_cost: clampCost(totalCost),
      total_recovery: totalRecovery,
      recovery_pct:
        totalCost + totalRecovery > 0
          ? totalRecovery / (totalCost + totalRecovery)
          : 0,
      by_dimension: newByDim,
    }
  })
}

/** Re-derive cost_summary totals from the scaled monthly aggregates. */
export function summaryFromMonthly(rawSummary, scaledByMonth) {
  const totals = new Map()
  for (const r of scaledByMonth) {
    totals.set(r.dimension, (totals.get(r.dimension) || 0) + r.cost)
  }
  return rawSummary.map((r) => ({
    ...r,
    total_cost: clampCost(totals.get(r.dimension) ?? r.total_cost),
  }))
}

/** Validate JS scaled output against validation.json. */
export function validateBaseline(scaledSummary, validation, tolerance = 1.0) {
  const expected = validation.baseline_totals || {}
  const actual = {}
  let actualTotal = 0
  for (const r of scaledSummary) {
    actual[r.dimension] = r.total_cost
    actualTotal += r.total_cost
  }
  const mismatches = []
  for (const dim of Object.keys(expected)) {
    if (dim === 'total') continue
    const want = expected[dim]
    const got = actual[dim]
    if (got === undefined) {
      mismatches.push({ dim, want, got: null })
      continue
    }
    if (Math.abs(got - want) > tolerance) {
      mismatches.push({ dim, want, got })
    }
  }
  if (Math.abs(actualTotal - expected.total) > tolerance) {
    mismatches.push({ dim: 'total', want: expected.total, got: actualTotal })
  }
  return mismatches.length === 0 ? null : mismatches
}
