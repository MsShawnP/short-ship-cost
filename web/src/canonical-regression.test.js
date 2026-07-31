/**
 * TestCinderhavenCanonicalRegression
 *
 * Canonical regression test for the short-ship-cost baked data artifacts.
 * Pattern: mirrors TestCinderhavenValidatedRegression from cost-of-saying-yes.
 *
 * Loads the baked JSON files from web/public/data/ and asserts that key
 * figures match the Cinderhaven canonical values. If any upstream data
 * generation script changes these numbers, the test fails immediately.
 */

import { describe, test, expect } from 'vitest';
import { readFileSync, statSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = resolve(__dirname, '..', 'public', 'data');

/** Helper: load and parse a JSON file from the data directory. */
function loadData(filename) {
  const path = resolve(DATA_DIR, filename);
  const raw = readFileSync(path, 'utf-8');
  return JSON.parse(raw);
}

// -- Canonical values (from CINDERHAVEN_CANONICAL / validation.json) ----------

const CANONICAL = {
  shipped_revenue: 75_543_979.99,
  total_skus: 50,
  total_cost: 894_173.83,
  expected_dimensions: [
    'forgone_revenue',
    'compliance_fines',
    'chargebacks',
    'deductions',
  ],
};

const TOLERANCE = 0.01; // 1 % relative tolerance

// ---------------------------------------------------------------------------
// Smoke tests — files exist and are parseable
// ---------------------------------------------------------------------------

describe('TestCinderhavenCanonicalRegression — smoke', () => {
  const requiredFiles = [
    'meta.json',
    'cost_summary.json',
    'validation.json',
  ];

  test.each(requiredFiles)('%s exists and is non-empty', (filename) => {
    const path = resolve(DATA_DIR, filename);
    expect(existsSync(path)).toBe(true);
    const stat = statSync(path);
    expect(stat.size).toBeGreaterThan(0);
  });

  test.each(requiredFiles)('%s is valid JSON', (filename) => {
    // loadData will throw if the file is not valid JSON
    const data = loadData(filename);
    expect(data).toBeDefined();
    expect(data).not.toBeNull();
  });

  test('no Python script or data generation needed to read baked data', () => {
    // This test proves the JSON artifacts are self-contained static files.
    // If we got this far, we loaded them with pure Node fs — no subprocess.
    const meta = loadData('meta.json');
    const costSummary = loadData('cost_summary.json');
    const validation = loadData('validation.json');
    expect(meta).toBeDefined();
    expect(costSummary).toBeDefined();
    expect(validation).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// meta.json assertions
// ---------------------------------------------------------------------------

describe('TestCinderhavenCanonicalRegression — meta.json', () => {
  const meta = loadData('meta.json');

  test('total_skus equals 50', () => {
    expect(meta.total_skus).toBe(CANONICAL.total_skus);
  });

  test('shipped_revenue is within 1% of canonical value', () => {
    const delta = Math.abs(meta.shipped_revenue - CANONICAL.shipped_revenue);
    const relError = delta / CANONICAL.shipped_revenue;
    expect(relError).toBeLessThan(TOLERANCE);
  });

  test('shipped_revenue matches canonical exactly', () => {
    expect(meta.shipped_revenue).toBe(CANONICAL.shipped_revenue);
  });

  test('meta structural fields exist (dimension list is asserted from cost_summary.json)', () => {
    // meta.json carries cost_parameters — verify the count of top-level
    // scalar fields is reasonable, but the authoritative dimension list
    // comes from cost_summary.json. Here we just verify meta has the
    // structural fields we depend on.
    expect(meta).toHaveProperty('shipped_revenue');
    expect(meta).toHaveProperty('total_skus');
    expect(meta).toHaveProperty('total_orders');
    expect(meta).toHaveProperty('overall_fill_rate');
    expect(meta).toHaveProperty('cost_parameters');
  });
});

// ---------------------------------------------------------------------------
// cost_summary.json assertions
// ---------------------------------------------------------------------------

describe('TestCinderhavenCanonicalRegression — cost_summary.json', () => {
  const costSummary = loadData('cost_summary.json');

  test('contains exactly 4 cost dimensions', () => {
    expect(costSummary).toHaveLength(4);
  });

  test('all 4 expected dimensions are present', () => {
    const dimensionNames = costSummary.map((d) => d.dimension);
    for (const expected of CANONICAL.expected_dimensions) {
      expect(dimensionNames).toContain(expected);
    }
  });

  test('no unexpected dimensions are present', () => {
    const dimensionNames = costSummary.map((d) => d.dimension);
    for (const name of dimensionNames) {
      expect(CANONICAL.expected_dimensions).toContain(name);
    }
  });

  test('sum of total_cost across all dimensions is within 1% of canonical total', () => {
    const sum = costSummary.reduce((acc, d) => acc + d.total_cost, 0);
    const delta = Math.abs(sum - CANONICAL.total_cost);
    const relError = delta / CANONICAL.total_cost;
    expect(relError).toBeLessThan(TOLERANCE);
  });

  test('sum of total_cost matches canonical total exactly', () => {
    // Floating-point sum may drift by a few cents — use toBeCloseTo with
    // 2 decimal places (pennies).
    const sum = costSummary.reduce((acc, d) => acc + d.total_cost, 0);
    expect(sum).toBeCloseTo(CANONICAL.total_cost, 2);
  });

  test('every dimension has total_cost > 0', () => {
    for (const d of costSummary) {
      expect(d.total_cost).toBeGreaterThan(0);
    }
  });

  test('every dimension has a pct_of_shipped field', () => {
    for (const d of costSummary) {
      expect(d).toHaveProperty('pct_of_shipped');
      expect(typeof d.pct_of_shipped).toBe('number');
    }
  });
});

// ---------------------------------------------------------------------------
// validation.json cross-check
// ---------------------------------------------------------------------------

describe('TestCinderhavenCanonicalRegression — validation.json', () => {
  const validation = loadData('validation.json');

  test('baseline_totals.total matches canonical total cost', () => {
    expect(validation.baseline_totals.total).toBeCloseTo(CANONICAL.total_cost, 2);
  });

  test('shipped_revenue matches canonical', () => {
    expect(validation.shipped_revenue).toBe(CANONICAL.shipped_revenue);
  });

  test('baseline_totals contains all 4 dimensions', () => {
    for (const dim of CANONICAL.expected_dimensions) {
      expect(validation.baseline_totals).toHaveProperty(dim);
      expect(typeof validation.baseline_totals[dim]).toBe('number');
    }
  });

  test('validation.json total equals sum of its own dimension breakdown', () => {
    const dims = CANONICAL.expected_dimensions;
    const sum = dims.reduce((acc, dim) => acc + validation.baseline_totals[dim], 0);
    expect(sum).toBeCloseTo(validation.baseline_totals.total, 2);
  });

  test('cost_summary.json and validation.json agree on each dimension', () => {
    const costSummary = loadData('cost_summary.json');
    for (const dim of CANONICAL.expected_dimensions) {
      const fromSummary = costSummary.find((d) => d.dimension === dim);
      expect(fromSummary).toBeDefined();
      expect(fromSummary.total_cost).toBeCloseTo(
        validation.baseline_totals[dim],
        2
      );
    }
  });
});
