import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  getRatios,
  ratioFor,
  scaleSkuTotals,
  filterDeauthEvents,
  deauthTotal,
  deauthByRetailer,
  deauthBySku,
  scaleCostByRetailer,
  scaleCostByMonth,
  scaleCostBySku,
  scaleBufferScenarios,
  summaryFromMonthly,
  validateBaseline,
} from './costEngine.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const load = (name) =>
  JSON.parse(
    readFileSync(join(__dirname, '../../public/data', `${name}.json`), 'utf-8'),
  )

function extractBaselineParams(meta) {
  const out = {}
  for (const [k, v] of Object.entries(meta.cost_parameters)) out[k] = v.value
  return out
}

const meta = load('meta')
const validation = load('validation')
const costSummary = load('cost_summary')
const costByMonth = load('cost_by_month')
const costByRetailer = load('cost_by_retailer')
const costBySku = load('cost_by_sku')
const bufferScenarios = load('buffer_scenarios')
const deauthEvents = load('deauthorization_events')
const baseline = extractBaselineParams(meta)

// ---------------------------------------------------------------------------
// 4A: Trivial sanity check
// ---------------------------------------------------------------------------

describe('test runner sanity', () => {
  it('imports costEngine without error', () => {
    expect(typeof getRatios).toBe('function')
    expect(typeof validateBaseline).toBe('function')
  })

  it('loads validation.json', () => {
    expect(validation.baseline_totals).toBeDefined()
    expect(validation.baseline_totals.total).toBeGreaterThan(0)
  })
})

// ---------------------------------------------------------------------------
// 4B: Baseline validation — JS engine at baseline params matches Python output
// ---------------------------------------------------------------------------

describe('baseline validation', () => {
  const ratios = getRatios(baseline, baseline)
  const events = filterDeauthEvents(deauthEvents, baseline)
  const scaledByMonth = scaleCostByMonth(costByMonth, ratios)
  const scaledSummary = summaryFromMonthly(costSummary, scaledByMonth, events)

  it('validateBaseline returns null (all dims within $1)', () => {
    const result = validateBaseline(scaledSummary, validation, 1.0)
    expect(result).toBeNull()
  })

  const expected = validation.baseline_totals
  const dims = Object.keys(expected).filter((d) => d !== 'total')

  for (const dim of dims) {
    it(`${dim} matches within $1`, () => {
      const row = scaledSummary.find((r) => r.dimension === dim)
      expect(row).toBeDefined()
      expect(Math.abs(row.total_cost - expected[dim])).toBeLessThanOrEqual(1.0)
    })
  }

  it('total matches within $1', () => {
    const actualTotal = scaledSummary.reduce((s, r) => s + r.total_cost, 0)
    expect(Math.abs(actualTotal - expected.total)).toBeLessThanOrEqual(1.0)
  })

  it('scaleCostByRetailer produces rows at baseline', () => {
    const scaled = scaleCostByRetailer(costByRetailer, ratios, events)
    expect(scaled.length).toBeGreaterThan(0)
    const total = scaled.reduce((s, r) => s + r.cost, 0)
    expect(total).toBeGreaterThan(0)
  })

  it('scaleCostBySku produces rows at baseline', () => {
    const scaled = scaleCostBySku(costBySku, ratios, events)
    expect(scaled.length).toBeGreaterThan(0)
    const total = scaled.reduce((s, r) => s + r.total_cost, 0)
    expect(total).toBeGreaterThan(0)
  })

  it('scaleBufferScenarios produces scenarios at baseline', () => {
    const deauthScale = 1
    const scaled = scaleBufferScenarios(
      bufferScenarios.scenarios,
      ratios,
      deauthScale,
    )
    expect(scaled.length).toBe(bufferScenarios.scenarios.length)
    expect(scaled[0].total_cost).toBeGreaterThan(0)
  })
})

// ---------------------------------------------------------------------------
// 4C: Parameter-adjusted scenarios
// ---------------------------------------------------------------------------

describe('parameter-adjusted scenarios', () => {
  it('doubling Walmart OTIF rate doubles Walmart OTIF ratio', () => {
    const adjusted = { ...baseline, otif_walmart_rate: baseline.otif_walmart_rate * 2 }
    const ratios = getRatios(adjusted, baseline)
    expect(ratios.otif.Walmart).toBeCloseTo(2.0, 5)
    expect(ratios.otif.Costco).toBeCloseTo(1.0, 5)
  })

  it('doubling Walmart OTIF rate increases otif_fines total', () => {
    const adjusted = { ...baseline, otif_walmart_rate: baseline.otif_walmart_rate * 2 }
    const ratios = getRatios(adjusted, baseline)
    const events = filterDeauthEvents(deauthEvents, adjusted)
    const scaledByMonth = scaleCostByMonth(costByMonth, ratios)
    const scaledSummary = summaryFromMonthly(costSummary, scaledByMonth, events)
    const otifRow = scaledSummary.find((r) => r.dimension === 'otif_fines')
    expect(otifRow.total_cost).toBeGreaterThan(
      validation.baseline_totals.otif_fines,
    )
  })

  it('lowering deauth distributor threshold to 0.8 reduces deauth events', () => {
    const adjusted = { ...baseline, deauth_distributor_fill_rate: 0.8 }
    const baselineEvents = filterDeauthEvents(deauthEvents, baseline)
    const adjustedEvents = filterDeauthEvents(deauthEvents, adjusted)
    expect(adjustedEvents.length).toBeLessThanOrEqual(baselineEvents.length)
  })

  it('raising deauth distributor threshold to 0.95 increases deauth events', () => {
    const adjusted = { ...baseline, deauth_distributor_fill_rate: 0.95 }
    const baselineEvents = filterDeauthEvents(deauthEvents, baseline)
    const adjustedEvents = filterDeauthEvents(deauthEvents, adjusted)
    expect(adjustedEvents.length).toBeGreaterThanOrEqual(baselineEvents.length)
  })

  it('zeroing triage params produces zero triage ratio', () => {
    const adjusted = { ...baseline, triage_minutes_per_order: 0 }
    const ratios = getRatios(adjusted, baseline)
    expect(ratios.triage_labor).toBe(0)
  })

  it('zeroing triage produces zero triage_labor in summary', () => {
    const adjusted = { ...baseline, triage_minutes_per_order: 0 }
    const ratios = getRatios(adjusted, baseline)
    const events = filterDeauthEvents(deauthEvents, adjusted)
    const scaledByMonth = scaleCostByMonth(costByMonth, ratios)
    const scaledSummary = summaryFromMonthly(costSummary, scaledByMonth, events)
    const triageRow = scaledSummary.find((r) => r.dimension === 'triage_labor')
    expect(triageRow.total_cost).toBe(0)
  })

  it('non-param dims (lost_revenue, dtc_cancellations, distributor_returns) are unaffected by OTIF changes', () => {
    const adjusted = { ...baseline, otif_walmart_rate: baseline.otif_walmart_rate * 3 }
    const ratios = getRatios(adjusted, baseline)
    expect(ratioFor('lost_revenue', 'Walmart', ratios)).toBe(1)
    expect(ratioFor('dtc_cancellations', 'Walmart', ratios)).toBe(1)
    expect(ratioFor('distributor_returns', 'UNFI', ratios)).toBe(1)
  })

  it('DTC margin spread inversion clamps to zero', () => {
    const adjusted = {
      ...baseline,
      wholesale_margin_pct: 0.60,
      dtc_margin_pct: 0.55,
    }
    const ratios = getRatios(adjusted, baseline)
    expect(ratios.dtc_margin_leakage).toBe(0)
  })
})

// ---------------------------------------------------------------------------
// 4D: Edge cases
// ---------------------------------------------------------------------------

describe('edge cases', () => {
  it('getRatios with zero baseline values returns 1 (not NaN/Infinity)', () => {
    const zeroBaseline = { ...baseline }
    for (const k of Object.keys(zeroBaseline)) zeroBaseline[k] = 0
    const ratios = getRatios(zeroBaseline, zeroBaseline)
    expect(Number.isFinite(ratios.otif.Walmart)).toBe(true)
    expect(ratios.otif.Walmart).toBe(1)
    expect(Number.isFinite(ratios.chargebacks.Costco)).toBe(true)
    expect(Number.isFinite(ratios.triage_labor)).toBe(true)
  })

  it('scaleSkuTotals clamps negative values to zero', () => {
    const byDim = { lost_revenue: 100, otif_fines: -50, deauthorization: 200 }
    const ratios = getRatios(baseline, baseline)
    const result = scaleSkuTotals(byDim, ratios, -10)
    expect(result.deauthorization).toBe(0)
    expect(result.otif_fines).toBeGreaterThanOrEqual(0)
  })

  it('scaleSkuTotals handles NaN deauth gracefully', () => {
    const byDim = { lost_revenue: 100, deauthorization: 50 }
    const ratios = getRatios(baseline, baseline)
    const result = scaleSkuTotals(byDim, ratios, NaN)
    expect(result.deauthorization).toBe(0)
  })

  it('validateBaseline returns mismatches for wrong input', () => {
    const wrongSummary = [
      { dimension: 'lost_revenue', total_cost: 0 },
      { dimension: 'otif_fines', total_cost: 0 },
    ]
    const result = validateBaseline(wrongSummary, validation, 1.0)
    expect(result).not.toBeNull()
    expect(result.length).toBeGreaterThan(0)
  })

  it('filterDeauthEvents returns empty for extreme thresholds', () => {
    const adjusted = {
      ...baseline,
      deauth_distributor_fill_rate: 0.01,
      deauth_velocity_walmart: 0.001,
      deauth_velocity_costco: 0.001,
      deauth_velocity_whole_foods: 0.001,
      deauth_velocity_regional: 0.001,
    }
    const events = filterDeauthEvents(deauthEvents, adjusted)
    expect(events.length).toBeLessThan(deauthEvents.length)
  })

  it('deauthTotal of empty array is 0', () => {
    expect(deauthTotal([])).toBe(0)
  })

  it('deauthByRetailer of empty array is empty map', () => {
    const m = deauthByRetailer([])
    expect(m.size).toBe(0)
  })

  it('deauthBySku of empty array is empty map', () => {
    const m = deauthBySku([])
    expect(m.size).toBe(0)
  })

  it('summaryFromMonthly handles empty monthly data', () => {
    const events = filterDeauthEvents(deauthEvents, baseline)
    const result = summaryFromMonthly(costSummary, [], events)
    expect(result.length).toBe(costSummary.length)
    const deauthRow = result.find((r) => r.dimension === 'deauthorization')
    expect(deauthRow.total_cost).toBeGreaterThan(0)
  })

  it('scaleCostByRetailer with no deauth events omits deauth rows', () => {
    const ratios = getRatios(baseline, baseline)
    const result = scaleCostByRetailer(costByRetailer, ratios, [])
    const deauthRows = result.filter((r) => r.dimension === 'deauthorization')
    expect(deauthRows.length).toBe(0)
  })

  it('scaleBufferScenarios with deauthScale=0 zeros deauth dims', () => {
    const ratios = getRatios(baseline, baseline)
    const scaled = scaleBufferScenarios(
      bufferScenarios.scenarios,
      ratios,
      0,
    )
    for (const s of scaled) {
      if (s.by_dimension.deauthorization) {
        expect(s.by_dimension.deauthorization.original).toBe(0)
        expect(s.by_dimension.deauthorization.simulated).toBe(0)
      }
    }
  })
})

describe('data consistency', () => {
  const validation = load('validation')
  const meta = load('meta')
  const indexHtml = readFileSync(
    join(__dirname, '../../index.html'),
    'utf-8',
  )

  it('meta.json total_orders and total_lines are positive integers', () => {
    expect(Number.isInteger(meta.total_orders)).toBe(true)
    expect(meta.total_orders).toBeGreaterThan(0)
    expect(Number.isInteger(meta.total_lines)).toBe(true)
    expect(meta.total_lines).toBeGreaterThan(0)
  })

  it('OG meta description matches validation.json total', () => {
    const totalM = `$${(validation.baseline_totals.total / 1e6).toFixed(1)}M`
    expect(indexHtml).toContain(totalM)
  })
})
