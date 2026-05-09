/**
 * JS implementation of the parameter-sensitive parts of the Python cost
 * engine. Most cost dimensions scale linearly with their parameter, so we
 * apply ratio multipliers to the pre-computed JSON aggregates rather than
 * re-running the engine over raw order data (which would require shipping
 * the 22 MB orders DB to the browser).
 *
 * Deauthorization is the exception: events are filtered against the user's
 * threshold settings, which can shift which (sku, retailer) pairs trigger.
 */

function safeRatio(a, b) {
  if (!Number.isFinite(a) || !Number.isFinite(b) || b === 0) return 1
  const r = a / b
  if (!Number.isFinite(r) || r < 0) return 0
  return r
}

// Final clamp before a cost value reaches the UI: kill non-finite values
// and prevent negatives. Costs are inherently non-negative; if a parameter
// combination would push one negative, the floor is zero.
function clampCost(v) {
  if (!Number.isFinite(v) || v < 0) return 0
  return v
}

/** Build a lookup of per-(dimension, retailer) ratios. */
export function getRatios(params, baseline) {
  const otif = {
    Walmart: safeRatio(params.otif_walmart_rate, baseline.otif_walmart_rate),
    Costco: safeRatio(
      params.otif_costco_flat_fee,
      baseline.otif_costco_flat_fee,
    ),
    'Whole Foods': safeRatio(
      params.otif_whole_foods_rate,
      baseline.otif_whole_foods_rate,
    ),
    UNFI: safeRatio(params.otif_unfi_rate, baseline.otif_unfi_rate),
    KeHE: safeRatio(params.otif_kehe_rate, baseline.otif_kehe_rate),
    Regional: safeRatio(
      params.otif_regional_rate,
      baseline.otif_regional_rate,
    ),
  }
  const cb_wc = safeRatio(
    params.chargeback_rate_walmart_costco,
    baseline.chargeback_rate_walmart_costco,
  )
  const cb_other = safeRatio(
    params.chargeback_rate_other,
    baseline.chargeback_rate_other,
  )
  const chargebacks = {
    Walmart: cb_wc,
    Costco: cb_wc,
    'Whole Foods': cb_other,
    UNFI: cb_other,
    KeHE: cb_other,
    Regional: cb_other,
  }
  // DTC margin leakage is the spread between DTC and wholesale margin.
  // If the user pulls wholesale above DTC, the spread inverts; we clamp at
  // zero so the displayed cost can't go negative or NaN.
  const dtcNumerator = params.dtc_margin_pct - params.wholesale_margin_pct
  const dtcDenominator =
    baseline.dtc_margin_pct - baseline.wholesale_margin_pct
  const dtcSpread =
    dtcNumerator <= 0 || dtcDenominator <= 0
      ? 0
      : safeRatio(dtcNumerator, dtcDenominator)
  const triage = safeRatio(
    params.triage_minutes_per_order *
      params.triage_hourly_rate *
      params.triage_share_of_orders,
    baseline.triage_minutes_per_order *
      baseline.triage_hourly_rate *
      baseline.triage_share_of_orders,
  )
  return {
    otif,
    chargebacks,
    dtc_margin_leakage: dtcSpread,
    triage_labor: triage,
  }
}

/** Per-(dim, retailer) scaling factor for non-deauth dims. */
export function ratioFor(dim, retailer, ratios) {
  if (dim === 'otif_fines') return ratios.otif[retailer] ?? 1
  if (dim === 'chargebacks') return ratios.chargebacks[retailer] ?? 1
  if (dim === 'dtc_margin_leakage') return ratios.dtc_margin_leakage
  if (dim === 'triage_labor') return ratios.triage_labor
  // lost_revenue, dtc_cancellations, distributor_returns: no params
  return 1
}

/** Scale parameter-sensitive aggregate dims; deauth rows are recomputed
 * from filtered events, so callers must pass the new deauth value. */
export function scaleSkuTotals(byDimension, ratios, newDeauth) {
  const out = {}
  for (const [dim, value] of Object.entries(byDimension)) {
    if (dim === 'deauthorization') {
      out[dim] = clampCost(newDeauth)
    } else {
      // SKU-level dims have no retailer breakdown — for OTIF and chargebacks
      // we approximate with a flat dim-level ratio (Walmart vs other averages
      // out at the SKU rollup level).
      out[dim] = clampCost(value * dimAverageRatio(dim, ratios))
    }
  }
  return out
}

function dimAverageRatio(dim, ratios) {
  if (dim === 'otif_fines') {
    const vs = Object.values(ratios.otif)
    return vs.reduce((s, v) => s + v, 0) / vs.length
  }
  if (dim === 'chargebacks') {
    const vs = Object.values(ratios.chargebacks)
    return vs.reduce((s, v) => s + v, 0) / vs.length
  }
  if (dim === 'dtc_margin_leakage') return ratios.dtc_margin_leakage
  if (dim === 'triage_labor') return ratios.triage_labor
  return 1
}

/** Filter deauthorization events against the active thresholds. */
export function filterDeauthEvents(events, params) {
  const distThreshold = params.deauth_distributor_fill_rate
  const velThresholds = {
    Walmart: params.deauth_velocity_walmart,
    Costco: params.deauth_velocity_costco,
    'Whole Foods': params.deauth_velocity_whole_foods,
  }
  const regionalThreshold = params.deauth_velocity_regional

  return events.filter((e) => {
    if (e.trigger_type === 'distributor_consecutive_months') {
      return (
        e.fill_rate !== null &&
        e.fill_rate !== undefined &&
        e.fill_rate < distThreshold
      )
    }
    if (e.trigger_type === 'velocity_below_threshold') {
      const t = velThresholds[e.retailer] ?? regionalThreshold
      return (
        e.velocity_without_shorts >= t && e.velocity_with_shorts < t
      )
    }
    return false
  })
}

export function deauthTotal(events) {
  return events.reduce((s, e) => s + e.annualized_revenue_lost, 0)
}

export function deauthByRetailer(events) {
  const map = new Map()
  for (const e of events) {
    map.set(e.retailer, (map.get(e.retailer) || 0) + e.annualized_revenue_lost)
  }
  return map
}

export function deauthBySku(events) {
  const map = new Map()
  for (const e of events) {
    map.set(e.sku, (map.get(e.sku) || 0) + e.annualized_revenue_lost)
  }
  return map
}

/** Re-derive cost_by_retailer with parameter scaling applied. Deauth rows
 * are replaced with per-retailer totals from the filtered event list. */
export function scaleCostByRetailer(rawRows, ratios, deauthEvents) {
  const deauthMap = deauthByRetailer(deauthEvents)
  const result = []
  for (const r of rawRows) {
    if (r.dimension === 'deauthorization') continue // replace below
    result.push({
      ...r,
      cost: clampCost(r.cost * ratioFor(r.dimension, r.retailer, ratios)),
    })
  }
  for (const [retailer, cost] of deauthMap.entries()) {
    result.push({
      retailer,
      dimension: 'deauthorization',
      month: null,
      cost: clampCost(cost),
    })
  }
  return result
}

/** Re-derive cost_by_month with parameter scaling. Deauth has no monthly
 * attribution and is not present in cost_by_month. */
export function scaleCostByMonth(rawRows, ratios) {
  return rawRows.map((r) => ({
    ...r,
    cost: clampCost(r.cost * dimAverageRatio(r.dimension, ratios)),
  }))
}

/** Re-derive cost_by_sku with parameter scaling on by_dimension and
 * by_month, plus deauth recomputed from filtered events (replacing the
 * baseline deauth value on each SKU entry).
 *
 * The "Other" row's deauth = total_filtered_deauth − sum(top-20 deauth). */
export function scaleCostBySku(rawRows, ratios, deauthEvents) {
  const deauthMap = deauthBySku(deauthEvents)
  const totalDeauth = deauthTotal(deauthEvents)

  const top = rawRows.filter((r) => r.sku !== 'Other')
  const otherRow = rawRows.find((r) => r.sku === 'Other')

  let topDeauth = 0
  const scaledTop = top.map((r) => {
    const newDeauth = deauthMap.get(r.sku) || 0
    topDeauth += newDeauth
    return scaleOneSkuRow(r, ratios, newDeauth)
  })

  let result = scaledTop
  if (otherRow) {
    const otherDeauth = Math.max(0, totalDeauth - topDeauth)
    result = [...scaledTop, scaleOneSkuRow(otherRow, ratios, otherDeauth)]
  }
  return result
}

function scaleOneSkuRow(row, ratios, newDeauth) {
  const newByDim = scaleSkuTotals(row.by_dimension, ratios, newDeauth)
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
}

/** Buffer scenarios — approximate scaling. For non-deauth dims, multiply
 * original/simulated by the dim-average ratio. For deauth, scale by the
 * filtered/baseline deauth ratio so the cliff still expresses itself. */
export function scaleBufferScenarios(rawScenarios, ratios, deauthScale) {
  return rawScenarios.map((s) => {
    const newByDim = {}
    for (const [dim, v] of Object.entries(s.by_dimension)) {
      const factor =
        dim === 'deauthorization' ? deauthScale : dimAverageRatio(dim, ratios)
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

/** Re-derive cost_summary totals from the scaled aggregates. */
export function summaryFromMonthly(rawSummary, scaledByMonth, deauthEvents) {
  const totals = new Map()
  for (const r of scaledByMonth) {
    totals.set(r.dimension, (totals.get(r.dimension) || 0) + r.cost)
  }
  totals.set('deauthorization', clampCost(deauthTotal(deauthEvents)))
  return rawSummary.map((r) => ({
    ...r,
    total_cost: clampCost(totals.get(r.dimension) ?? r.total_cost),
  }))
}

/** Validate JS scaled output against validation.json. Returns null when
 * within tolerance, or an object describing first mismatch. */
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
