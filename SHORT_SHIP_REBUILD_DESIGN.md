# Short-Ship Cost Rebuild — Design Document

> **OUTCOME NOTE (2026-07-30).** The rebuild shipped. Measured results came in
> well below this document's expected ranges: forgone revenue $523K/3yr, total
> cost $894K/3yr (~$298K/yr), fill rates 99.2% retailer / 99.5% distributor
> (this doc's 92.0%/94.2% "confirmed" pair predates the platform reseed).
> The expected-value table below is design history — do NOT propagate it to
> CINDERHAVEN_CANONICAL.md; the shipped figures are canonical.

**Status:** DRAFT — awaiting Shawn's approval before any code
**Date:** 2026-06-14
**Supersedes:** The entire existing cost engine (`scripts/cost_engine/*`),
the synthetic order pipeline (`scripts/generate_orders.py`,
`scripts/run_triage.py`, etc.), and all three SQLite databases.

---

## What is changing and why

The current project generates its own synthetic orders at 69% fill
rate, producing a $33.1M cost figure across 8 dimensions on $53M of
shipped revenue. The plausibility audit
(`cinderhaven-plausibility-audit.md`) dismantled this:

- The platform ships 100% of ordered units and collects $76M cash —
  a company cannot collect $76M on $53M of shipped goods
- 90% of the $33.1M comes from two dimensions (lost revenue +
  deauthorization) that are revenue-framed, not P&L costs
- OTIF fines are 5× the canonical OTIF figure ($690K/yr vs $136K/yr)
- Three contradictory fulfillment realities (100%, 95/86%, 69%)
  coexist in the canonical table

The platform now has **causal fulfillment data** — shipment lines
with actual shortages at 92% retailer / 94% distributor fill rates,
plus event-driven chargebacks and deductions triggered by those
shortages. The rebuild replaces the synthetic order pipeline with
direct reads from platform tables.

---

## 1. Dimension verdicts

Standard applied: **if the platform can't produce the number from
recorded events, it doesn't belong.** Modeled fine schedules applied
to real shortfall events are acceptable (the events are real; the
rates are industry-standard contractual terms). Forward projections,
assumed admin costs, and synthetic DTC outcomes are not.

### Verdict summary

| # | Old dimension | Old $ (3yr) | Old % | Verdict | Rationale |
|---|---|---|---|---|---|
| 1 | lost_revenue | $23.4M | 71.5% | **KEEP** | Directly from shipment lines |
| 2 | deauthorization | $6.2M | 18.9% | **DROP** | Forward projection, not a recorded event |
| 3 | otif_fines | $2.1M | 6.3% | **RELABEL** | Becomes "compliance fines" — same logic, platform events |
| 4 | triage_labor | $502K | 1.5% | **DROP** | Admin time estimate, not observable |
| 5 | distributor_returns | $464K | 1.4% | **DROP** | Promo-driven, not short-caused |
| 6 | chargebacks | $78K | 0.24% | **KEEP** | Platform now has actual event-driven amounts |
| 7 | dtc_cancellations | $9.4K | 0.03% | **DROP** | No DTC shipment data in platform |
| 8 | dtc_margin_leakage | $1.0K | 0.003% | **DROP** | No DTC shipment data in platform |

Five of eight dimensions are dropped. The surviving analysis is
smaller in dollar terms but every number traces to a platform event.

---

### Dimension-by-dimension reasoning

#### 1. lost_revenue → KEEP

**What it was:** `(qty_ordered - qty_shipped) × case_pack × unit_price`
for every retail and distributor line. Valued at full wholesale
invoice price.

**What it becomes:** `SUM(units_short × unit_price)` from
`fct_retailer_shipment_lines` and `fct_distributor_shipment_lines`,
joined to order-line pricing.

**Platform source:**
```sql
-- retailer channel
SELECT l.sku, o.retailer_id, s.ship_date,
       l.units_ordered, l.units_shipped,
       l.units_ordered - l.units_shipped AS units_short,
       ol.unit_price
FROM fct_retailer_shipment_lines l
JOIN stg_retailer_shipments s ON l.shipment_id = s.shipment_id
JOIN stg_retailer_orders o ON s.order_id = o.order_id
JOIN stg_retailer_order_lines ol ON o.order_id = ol.order_id AND l.sku = ol.sku
WHERE l.is_short = TRUE
```
Distributor channel: identical pattern against
`fct_distributor_shipment_lines`.

**What changes at 92/94% fill:**
At 69% fill the old model produced $23.4M of forgone revenue over
3 years (~$7.8M/yr). At 92% retailer fill on ~$52M of retailer
invoiced revenue (3yr), forgone revenue ≈ 8% × $52M ≈ **$4.2M
over 3yr** (~$1.4M/yr). Distributor at 94% on ~$24M ≈ **$1.4M
over 3yr**. Combined estimate: **~$5.6M over 3yr ($1.9M/yr)**.

**Framing decision:** The old model valued shorted units at full
wholesale price. The plausibility audit noted the economic loss is
forgone contribution margin (price − COGS ≈ 46–54% of price), not
forgone revenue. The rebuild should present **both**:
- Primary headline: forgone revenue (what the business didn't bill —
  this is how operators think)
- Secondary line: forgone contribution (~50% of the revenue figure —
  the actual profit impact)

Both are computable from platform data (shipment lines + sku_costs).

---

#### 2. deauthorization → DROP

**What it was:** For each (SKU, retailer) pair, compare velocity
with shorts vs. without shorts against IRI/Nielsen delist
thresholds. If shorts pushed velocity below the threshold, count
12 months of annualized revenue as "revenue at risk." Produced
$6.2M (18.9% of total) from 127 modeled events.

**Why it's dropped:**
1. **Not a recorded event.** The platform has no deauthorization
   table. The "cost" was a 12-month forward revenue projection per
   modeled trigger — a forecast, not a fact.
2. **Thresholds are external assumptions.** The delist thresholds
   (Walmart 2.5 u/store/wk, Costco 10.0, etc.) come from
   IRI/Nielsen category review norms, not from any retailer
   contract or platform record.
3. **At 92% fill, the signal collapses.** The gap between
   "velocity if everything shipped" and "velocity as shipped" is
   8%, not 31%. Far fewer SKU/retailer pairs would cross any
   threshold. The dimension was already strained at 69% fill
   ($6.2M of revenue-at-risk at a $25M company that kept all
   retailers); at 92% fill it likely produces a handful of
   marginal events worth <$200K combined.
4. **Double-counts with lost revenue.** Deauthorization valued
   shorted demand as both lost revenue (dim 1) and lost future
   shelf space (dim 2). The forward projection partially
   re-counts the same units.

**What we lose:** The narrative that "shorts don't just cost you
this order — they can cost you the shelf." This is true but it's
an argument, not a data finding. The rebuild presents it as
explanatory context in the narrative, not as a dollar dimension.

---

#### 3. otif_fines → RELABEL as "compliance_fines"

**What it was:** Retailer-specific fine schedules (Walmart 3% of
line COGS below 98% fill, Costco $250 flat per shorted PO, etc.)
applied to every PO in the synthetic order data. Produced $2.1M
(6.3% of total) — $690K/yr. The canonical OTIF figure says
$136K/yr fines — a 5× contradiction the plausibility audit flagged.

**What it becomes:** Same contractual fine logic, but applied to
**real shortfall events from platform shipment lines** instead of
synthetic orders at 69% fill.

**Why RELABEL not KEEP:** The fine rates are assumed (from
`cost-engine-benchmarks.md`), not recorded in the platform. The
events are real; the dollars per event are modeled. That's honest
and standard — real OTIF programs work exactly this way (fill
falls below threshold → contractual penalty fires). But the
dimension name should reflect that: "compliance fines (modeled
from contractual schedules)" not "OTIF fines."

**Platform source:** Same query as lost_revenue (shipment lines
with units_short > 0), but aggregated per PO and tested against
per-retailer fill thresholds. The fine schedule from
`parameters.py` is preserved — those rates are defensible
industry norms.

**What changes at 92% fill:**
At 92% average fill, individual POs cluster around 92% with
variance. Walmart's 98% line-level threshold still catches many
lines. Whole Foods / UNFI / KeHE at 95% catch some POs. Regional
at 90% catches fewer. Rough estimate: **$200K–400K over 3yr**
($70–130K/yr), which is much closer to the canonical's $136K/yr
OTIF figure than the old $690K/yr. The 5× contradiction resolves.

---

#### 4. triage_labor → DROP

**What it was:** `order_count × 90% × 20 min × $30/hr` = ~$9 per
order. Produced $502K (1.5% of total).

**Why it's dropped:**
1. **Not observable from platform data.** The platform records
   orders, shipments, chargebacks, deductions. It does not record
   how long an admin spent editing a PO.
2. **Semi-fixed cost.** The plausibility audit noted this stays
   flat across buffer scenarios — it's not a variable cost of
   shorts, it's an operating cost that exists whether fill is 69%
   or 95%.
3. **The "20 min at $30/hr" is an assumption stack.** Not
   benchmarked against any Cinderhaven record.

**What we lose:** The "hidden tax" narrative — every order costs
$9 in human review time. Can be mentioned in the narrative as
qualitative context, not as a dollar dimension.

---

#### 5. distributor_returns → DROP

**What it was:** Credit amounts from `distributor_returns` table
(promo unsold at 12% + claims at 5% of shipped promo cases).
Produced $464K (1.4% of total).

**Why it's dropped:**
1. **Promo-driven, not short-caused.** The plausibility audit
   classified this as "Hard, but promo-driven (12% unsold + 5%
   claims), not short-caused." Distributors return unsold promo
   product whether or not the brand short-shipped other orders.
2. **The platform has no distributor returns table in the
   fulfillment pipeline.** Distributor deductions exist (and
   short_ship deductions are event-driven), but returns are a
   separate commercial process not tied to fulfillment events.
3. **Causal link is weak.** The old model generated these returns
   from its synthetic promo orders, not from the shortage gap.
   Including them inflated the "cost of shorts" with a cost that
   would exist at any fill rate.

---

#### 6. chargebacks → KEEP (actual event-driven amounts)

**What it was:** Estimated chargeback rates (0.5% Walmart/Costco,
0.3% other) applied to shorted goods value. Produced $78K (0.24%).
The old model explicitly noted it was a "fallback rate" because
the historical chargebacks table wasn't generated from its
synthetic shorts.

**What it becomes:** Actual chargebacks from
`raw.retailer_chargebacks` and `raw.distributor_chargebacks`
where `reason = 'short_ship'`. These are event-driven — the
platform's seed scripts trigger a chargeback when a shipment has
shorted lines, with retailer-specific assessment probabilities
and amounts proportional to shorted value.

**Platform source:**
```sql
-- actual short-ship chargebacks
SELECT rc.retailer_id, rc.sku, rc.month, rc.amount
FROM raw.retailer_chargebacks rc
WHERE rc.reason = 'short_ship'
UNION ALL
SELECT dc.distributor_id, dc.sku, dc.month, dc.amount
FROM raw.distributor_chargebacks dc
WHERE dc.reason = 'short_ship'
```

**Why this replaces the fallback-rate model:** The platform's
chargebacks are generated with actual assessment probabilities
per retailer (not every short triggers a chargeback — Walmart's
auto-deduct rate differs from Sprouts'). The amounts are
proportional to shorted value with retailer-specific rates and
clamps. This is more realistic than a flat 0.3–0.5% applied to
every shorted dollar.

**Note on scope:** `late_delivery` and `receiving_discrepancy`
chargebacks also exist in the platform. These are fulfillment
costs but not short-ship costs. The rebuild keeps scope tight to
quantity shortages. Late delivery chargebacks could be added as a
future extension under a broader "fulfillment failure cost" frame.

---

#### 7. dtc_cancellations → DROP

**What it was:** Revenue lost from DTC orders where hold-for-
complete delays caused customer cancellation. Produced $9.4K (0.03%).

**Why it's dropped:**
1. **No DTC shipment data in the platform.** The Shopify pipeline
   has orders, transactions, refunds, and chargebacks — financial
   data only. No `shopify_shipment_lines` table, no fill rates,
   no shortage events.
2. **The old model generated synthetic DTC outcomes** (a hold-
   duration cancellation curve). None of that exists in the
   platform.
3. **Trivially small.** Even in the old model at 69% fill, DTC
   cancellations were 0.03% of total cost. The old model's DTC
   fill rate was ~96% because DTC is held until complete.

---

#### 8. dtc_margin_leakage → DROP

**What it was:** Margin difference when DTC customers gave up
waiting and bought in-store instead (order_value × 20% margin
spread). Produced $1.0K (0.003%).

**Why it's dropped:** Same reasons as dtc_cancellations — no DTC
fulfillment data in the platform, and the amount was negligible.

---

## 2. The new dimension structure

Three dimensions survive. All are directly computable from
platform tables.

| # | Dimension | Source | What it measures |
|---|---|---|---|
| 1 | **Forgone revenue** | `fct_retailer_shipment_lines` + `fct_distributor_shipment_lines` | Units not shipped × wholesale price |
| 2 | **Compliance fines** | Modeled: fine schedules applied to shortfall events from shipment lines | Contractual penalties for non-compliant POs |
| 3 | **Short-ship chargebacks** | `raw.retailer_chargebacks` + `raw.distributor_chargebacks` WHERE reason = 'short_ship' | Actual penalty charges triggered by short events |

### Why compliance fines and chargebacks are separate

In CPG operations these are distinct financial instruments:
- **Compliance fines** are contractual OTIF penalties — the
  retailer's compliance program levies a fine when fill falls below
  a threshold. Rates are per the retailer's published program
  (Walmart 3% of COGS, Costco $250 flat, etc.).
- **Chargebacks** are per-event penalty charges — the retailer's
  AP team debits the supplier for each shorted shipment at the
  retailer's chargeback rate. Assessment is probabilistic (not
  every short triggers one) and amounts vary.

Both flow through different P&L lines and require different
remediation strategies. Separating them tells the operator a
richer story about where the money goes.

### What about short-ship deductions?

The platform also has event-driven `short_ship` deductions in
`raw.retailer_deductions` and `raw.distributor_deductions` — money
withheld from remittance payments when a shipment is short. These
are a third financial consequence of shorts: you get paid less.

**Decision needed:** Include deductions as a 4th dimension, or keep
scope to 3? The argument for including:
- Deductions are the largest financial hit from shorts for most
  brands (retailers just pay you less — no invoice, no dispute
  window, the money is gone)
- The platform has actual amounts with causal linkage to shipment
  events
- It would make the total cost picture more complete

The argument for excluding:
- Deductions partially overlap with forgone revenue (if you didn't
  ship it, you didn't bill it, and the retailer may also deduct
  for what you did ship short)
- Need to verify there's no double-count between "revenue not
  billed" (dim 1) and "revenue billed but deducted" (dim 4)

**Recommendation:** Include as a 4th dimension after verifying
the deduction amounts are incremental to forgone revenue (i.e.,
the deduction is a penalty on top of not getting paid for the
shorted units, not a restatement of the same loss). The platform's
deduction generation logic (`SHORT_SHIP_DED_RATE * shorted_value`,
clamped) suggests the deduction is a penalty rate applied to
shorted value — separate from the forgone revenue, not a
restatement of it.

---

## 3. Expected magnitudes

Rough estimates based on 92% retailer / 94% distributor fill
rates and the platform's revenue base (~$52M retailer + ~$24M
distributor invoiced over 36 months).

| Dimension | Estimated 3yr | Estimated annual | % of revenue |
|---|---|---|---|
| Forgone revenue | ~$5.0–6.0M | ~$1.7–2.0M | 6.5–7.8% |
| Compliance fines | ~$200–400K | ~$70–130K | 0.3–0.5% |
| Short-ship chargebacks | ~$100–300K | ~$35–100K | 0.1–0.4% |
| (Short-ship deductions) | ~$200–500K | ~$70–170K | 0.3–0.7% |
| **Total (3 dims)** | **~$5.3–6.7M** | **~$1.8–2.2M** | **~7–9%** |
| **Total (4 dims)** | **~$5.5–7.2M** | **~$1.9–2.4M** | **~7–10%** |

**Compare to old model:** $33.1M (3yr) / $11M/yr / 44% of shipped.
The rebuild produces ~$2M/yr / ~8% of invoiced — roughly 5× smaller.
Every dollar traces to a platform event.

**Is ~$2M/yr a compelling story?** Yes. For a $25M brand, losing
$2M/yr to fulfillment failures — money that would have been billed,
fines that didn't need to happen, chargebacks that hit the P&L — is
a board-level problem. The old model's $11M/yr was dramatic but
indefensible. $2M/yr is the kind of number an operator nods at
because it matches their experience.

---

## 4. Formal source queries (per dimension)

Each surviving dimension has one authoritative query against the
platform. These are the exact data paths the rebuild will implement.

### Dimension 1: Forgone revenue

```sql
-- Retailer forgone revenue
SELECT
    s.ship_date,
    o.retailer_id,
    l.sku,
    l.units_ordered,
    l.units_shipped,
    l.units_ordered - l.units_shipped AS units_short,
    ol.unit_price,
    (l.units_ordered - l.units_shipped) * ol.unit_price AS forgone_revenue,
    (l.units_ordered - l.units_shipped) * sc.cogs_per_unit AS forgone_cogs,
    (l.units_ordered - l.units_shipped) * (ol.unit_price - sc.cogs_per_unit) AS forgone_contribution
FROM fct_retailer_shipment_lines l
JOIN stg_retailer_shipments s ON l.shipment_id = s.shipment_id
JOIN stg_retailer_orders o ON s.order_id = o.order_id
JOIN stg_retailer_order_lines ol ON o.order_id = ol.order_id AND l.sku = ol.sku
JOIN raw.sku_costs sc ON l.sku = sc.sku
WHERE l.is_short = TRUE

-- Distributor forgone revenue: same pattern against
-- fct_distributor_shipment_lines, stg_distributor_shipments,
-- stg_distributor_orders, stg_distributor_order_lines
```

Output: per-line forgone revenue AND forgone contribution margin.
The tool displays both (revenue as headline, contribution as
secondary).

### Dimension 2: Compliance fines (modeled from contractual schedules)

```sql
-- PO-level fill rates for fine threshold testing
SELECT
    o.order_id,
    o.retailer_id,
    SUM(l.units_shipped)::FLOAT / NULLIF(SUM(l.units_ordered), 0) AS po_fill_rate,
    SUM(l.units_ordered) AS po_units_ordered,
    SUM(l.units_shipped) AS po_units_shipped,
    SUM(ol.unit_price * l.units_ordered) AS po_value,
    SUM(sc.cogs_per_unit * l.units_ordered) AS po_cogs
FROM fct_retailer_shipment_lines l
JOIN stg_retailer_shipments s ON l.shipment_id = s.shipment_id
JOIN stg_retailer_orders o ON s.order_id = o.order_id
JOIN stg_retailer_order_lines ol ON o.order_id = ol.order_id AND l.sku = ol.sku
JOIN raw.sku_costs sc ON l.sku = sc.sku
GROUP BY o.order_id, o.retailer_id
```

Fine logic applied in Python (not in SQL — the schedules are
configuration, not data):
- Walmart: 3% of line COGS where line fill < 98%
- Costco: $250 flat per PO where PO fill < 95%
- Whole Foods: 2% of PO COGS where PO fill < 95%
- UNFI: 3% of shorted value where PO fill < 95%
- KeHE: 2% of PO COGS where PO fill < 95%
- Regional: 1% of PO COGS where PO fill < 90%

These rates are from `cost-engine-benchmarks.md` (industry-standard
contractual terms). The rebuild preserves them from `parameters.py`.

### Dimension 3: Short-ship chargebacks

```sql
-- Actual event-driven chargebacks from platform
SELECT
    rc.retailer_id,
    rc.sku,
    rc.month,
    rc.amount
FROM raw.retailer_chargebacks rc
WHERE rc.reason = 'short_ship'

UNION ALL

SELECT
    dc.distributor_id,
    dc.sku,
    dc.month,
    dc.amount
FROM raw.distributor_chargebacks dc
WHERE dc.reason = 'short_ship'
```

No modeling required — these are actual amounts from the platform's
event-driven chargeback generation. The platform seeds chargebacks
with retailer-specific assessment probabilities and amounts
proportional to shorted value.

### Dimension 4 (if approved): Short-ship deductions

```sql
-- Actual event-driven deductions from platform
SELECT
    rd.retailer_id,
    rd.order_id,
    rd.amount,
    rd.deduction_date
FROM raw.retailer_deductions rd
WHERE rd.deduction_type = 'short_ship'

UNION ALL

SELECT
    dd.distributor_id,
    dd.order_id,
    dd.amount,
    dd.deduction_date
FROM raw.distributor_deductions dd
WHERE dd.deduction_type = 'short_ship'
```

Same as chargebacks — actual amounts, no modeling. The platform
generates short_ship deductions at 90% assessment rate on shorted
shipments, with amounts = `SHORT_SHIP_DED_RATE * shorted_value`.

---

## 5. Source tables and data contracts (read-only)

### Platform tables consumed (read-only)

| Table | Schema | What we use |
|---|---|---|
| `fct_retailer_shipment_lines` | mart | units_ordered, units_shipped, units_short, is_short, sku, retailer_id, ship_date |
| `fct_distributor_shipment_lines` | mart | Same columns, distributor_id instead of retailer_id |
| `fct_retailer_receipt_lines` | mart | units_received, units_discrepant (informational — not in core dims) |
| `raw.retailer_chargebacks` | raw | reason='short_ship' rows: retailer_id, sku, month, amount |
| `raw.distributor_chargebacks` | raw | reason='short_ship' rows: distributor_id, sku, month, amount |
| `raw.retailer_deductions` | raw | deduction_type='short_ship' rows: retailer_id, order_id, amount, date |
| `raw.distributor_deductions` | raw | deduction_type='short_ship' rows: distributor_id, order_id, amount, date |
| `raw.retailer_orders` | raw | order_id, retailer_id, po_date, total_value (for PO-level fill) |
| `raw.retailer_order_lines` | raw | unit_price (for revenue valuation) |
| `raw.distributor_order_lines` | raw | unit_price |
| `raw.product_master` | raw | sku, product_line (for grouping) |
| `raw.sku_costs` | raw | cogs_per_unit (for contribution margin calc) |
| `raw.retailers` | raw | name, store_doors (for display) |
| `raw.distributors` | raw | name, type |

### What the rebuild does NOT consume

- `raw.shopify_*` — no DTC fulfillment data
- `raw.retailer_requirements` / `raw.retailer_rules` — no fine
  schedules in the platform (we use our own from benchmarks doc)
- `raw.retailer_disputes` / `raw.distributor_disputes` — disputes
  are the recovery side, not the cost side
- `raw.distributor_returns` — does not exist; returns are not in
  the platform's fulfillment pipeline
- Any synthetic order tables from the old pipeline (`orders`,
  `order_lines_original`, `order_lines_shipped`, `dtc_outcomes`,
  `distributor_returns`, `order_shorts`)

---

## 6. What the interactive tool needs to change

### Structural changes

- **8 dimensions → 3 (or 4).** The flow-split chart, dimension
  toggle chips, and teal palette all resize. Fewer dimensions
  means each one is larger and more readable.
- **Headline number drops from $33.1M to ~$6M.** The framing
  statement ("every dollar in this tool traces to a platform
  event") changes the tone from dramatic to authoritative.
- **Fill rate framing.** The old model framed around a 69% fill
  catastrophe. The rebuild frames around "92% sounds fine until
  you see what the 8% gap actually costs." That's a stronger
  argument for a prospect who thinks their fill rate is acceptable.
- **Source data format.** The old pipeline exported to JSON from
  3 SQLite databases. The rebuild needs a new export path — either
  query the platform's Postgres directly or build a new extract
  script that reads from the platform and writes JSON.

### What survives from the current tool

- The React app structure, Vite build, Cloudflare deployment
- The flow-split chart (resized for 3–4 dimensions)
- The retailer/SKU drill-down section (same structure, new data)
- The time series section (fewer stacked layers)
- The parameter panel concept (but with different parameters —
  fine rates are still tunable, deauth thresholds are gone)
- The print CSS export
- All the mobile work (bottom sheet, breakpoints, touch targets)
- The animation system (useAnimatedValue hook, chart transitions)
- The methodology appendix (rewritten for the new approach)

### Buffer simulation

The old buffer simulation showed "what if fill moved from 69% to
80/85/90/95%?" At 92% fill, the scenarios become "what if fill
moved from 92% to 95/97/98/99%?" This is actually a better story
— the incremental cost of moving from 92% to 95% is real and
achievable, whereas "what if you went from 69% to 95%" is fantasy.

The simulation logic stays the same (lift units_shipped toward
target, recompute costs) but operates on a much smaller gap. The
deauth cliff at 90% is gone (dimension dropped). The buffer
staircase chart becomes a smoother curve showing diminishing
returns as fill approaches 100%.

---

## 7. Open questions for Shawn

1. **Include short-ship deductions as a 4th dimension?** The
   platform has the data and the amounts are incremental. Adds
   ~$200–500K/3yr to the total. Recommendation: yes.

2. **Include late-delivery costs?** The platform has late_delivery
   chargebacks and deductions — real money lost to a different
   type of fulfillment failure. Including them broadens the tool
   from "short-ship cost" to "fulfillment failure cost." Could
   rename the tool or add as a toggle. Recommendation: not in
   this rebuild — keep scope tight, revisit after.

3. **Data access path.** Options:
   - (a) Query the Fly.io Postgres directly from a new extract
     script (`flyctl proxy` → psycopg2 queries → JSON export)
   - (b) Build against the certified local replica (Docker
     Compose, same as the plausibility audit used)
   - (c) Pre-extract a SQLite snapshot from the platform and
     consume that

   Recommendation: (b) — the local replica is already certified
   equivalent to prod and doesn't require Fly.io credentials in
   the build pipeline.

4. **Contribution margin display.** Show forgone contribution
   alongside forgone revenue? Recommendation: yes, as a secondary
   line — operators think in revenue but the profit impact is the
   sharper number.

---

## 8. What this does NOT change

- The brand (Cinderhaven Provisions) and its context
- The portfolio positioning (this is a demonstration of what
  fulfillment visibility reveals, not a client tool)
- The design system (DS v2, Lailara tokens)
- The hosting (Cloudflare Workers at shortships.lailarallc.com)
- The Economist voice and chart standards
- The business question ("What does it cost when you can't
  fulfill orders as submitted?")

What changes is the answer: from "$33M, trust me" to "$6M, and
here's the receipt."

---

## 9. Canonical impact

### What enters CINDERHAVEN_CANONICAL.md

After the rebuild produces final numbers, these rows replace the
retired short-ship entries in the engagement-level headline table:

| Figure | Expected value | Engagement | Status after rebuild |
|--------|---------------|------------|---------------------|
| Short-ship forgone revenue (3yr) | ~$5.0–6.0M | short-ship-cost | New — replaces $32.8M |
| Short-ship compliance fines (3yr) | ~$200–400K | short-ship-cost | New |
| Short-ship chargebacks (3yr) | ~$100–300K | short-ship-cost | New |
| Short-ship deductions (3yr) | ~$200–500K | short-ship-cost | New (if 4th dim approved) |
| Short-ship total cost (3yr) | ~$5.3–7.2M | short-ship-cost | New — replaces $32.8M |
| Short-ship total cost (annual) | ~$1.8–2.4M/yr | short-ship-cost | New — replaces $11M/yr |
| Short-ship dimension count | 3 (or 4) | short-ship-cost | Down from 8 |

Fill rate figures already confirmed in canonical and do not change:
- Fulfillment fill rate (retailer): 92.0% ✅
- Fulfillment fill rate (distributor): 94.2% ✅

### What moves to SUPERSEDED

These entries are already in SUPERSEDED but the rebuild confirms
their permanent retirement:

| Dead value | Already in SUPERSEDED? | Note |
|------------|----------------------|------|
| $32.8M short-ship total cost (3yr, 8 dimensions) | Yes | Rebuild replaces with ~$5.3–7.2M |
| $53.0M short-ship shipped revenue | Yes | Platform invoiced revenue replaces this figure |
| $33.1M short-ship (pre-date-shift) | Yes | Same lineage, same retirement |
| 69% fill rate | Not as a standalone entry | Add: "69.3% synthetic fill rate — short-ship-cost project's order generator. Superseded by platform causal fill rates (92%/94%)" |
| 8-dimension cost model | Not as a standalone entry | Add: "8-dimension short-ship cost model (lost_revenue, deauthorization, otif_fines, triage_labor, distributor_returns, chargebacks, dtc_cancellations, dtc_margin_leakage) — superseded by 3-dimension model grounded in platform events" |

### Thesis range impact

The canonical thesis range ($1.4M–$3.1M/yr, status ⚠️ Awaiting
regen) aggregates across all ten decisions. The short-ship rebuild
changes the short-ship component:

- **Old contribution:** Derived from the $33.1M/3yr figure and its
  8 dimensions. The exact annual figure used in the thesis range
  was ~$1.07M/yr (manifesto.qmd line 97: "$1,066,480 in
  short-shipping cost exposure").
- **New contribution:** The rebuild total (~$1.8–2.4M/yr) is
  larger than the old thesis contribution, but the composition is
  different — forgone revenue is not a P&L hit in the same way
  fines and chargebacks are. The thesis range entry for this
  decision needs reframing, not just a number swap.

The thesis range cannot be recomputed from this project alone — it
requires all ten decision figures, several of which have their own
pending regens ($461K → ~$50–95K for PDHA, deductions restated,
channel story inverted). The short-ship rebuild produces its number;
the thesis range recomputation is a the-ten-decisions concern.

### APPROVED PHRASINGS (proposed — Shawn approves)

These would be added to the APPROVED PHRASINGS table in
CINDERHAVEN_CANONICAL.md after the rebuild produces final numbers:

| Context | Proposed phrasing |
|---------|-------------------|
| Short-ship cost (annual) | "~$[X]M/yr in fulfillment shortfall costs across [3\|4] dimensions" |
| Short-ship cost (3yr) | "$[X]M in total fulfillment shortfall costs over 36 months" |
| Short-ship framing | "92% fill rate costs ~$[X]M/yr — every dollar traces to a platform event" |

Exact figures and final wording deferred to Shawn after the rebuild
produces actuals.

---

## 10. Cascade to blocked NARRATIVE_REWRITE entries

These are the text surfaces in other projects that cite short-ship
figures retired by this rebuild. Cataloged in
`PHASE5_CHANGE_REPORT.md` (sections 1 and 3). Listed here so the
rebuild's downstream blast radius is visible before code starts.

### short-ship-cost (this project)

| File | Line | Current text | What changes | Class |
|------|------|-------------|-------------|-------|
| README.md | 29 | "74,306 orders, $53M shipped over three years" | Order count, revenue, and time window all change — figures come from platform queries | NARRATIVE_REWRITE |
| README.md | 45 | "dimensions on $53M shipped revenue" | $53M replaced by platform invoiced revenue; "8 cost dimensions" becomes 3 (or 4) | NARRATIVE_REWRITE |

### the-ten-decisions — manifesto.qmd

Short-ship-dependent entries only. Other entries in the change
report (chargebacks $461K, deductions, channel story, lifecycle)
are owned by their respective projects, not by this rebuild.

| Line | Current text | What the rebuild affects | Class |
|------|-------------|------------------------|-------|
| 43 | "Total across all ten decisions \| **$1.4M–$3.1M**" | Thesis range includes short-ship component; cannot recompute until all ten figures are final | NARRATIVE_REWRITE |
| 97 | "$1,066,480 in short-shipping cost exposure" | Old figure from $33.1M model; replaced by rebuild output | FIGURE_SWAP |
| 195 | "a roughly 69% fill rate" | Platform causal fill: 92% retailer, 94% distributor | NARRATIVE_REWRITE |
| 202 | "69.19% overall fill rate. $33,128,550 in total short-shipping costs over three years" | Both figures retired. Fill 92%/94%; total ~$5.3–7.2M | NARRATIVE_REWRITE |

### the-ten-decisions — research/cinderhaven-findings.md

| Line | Current text | What the rebuild affects | Class |
|------|-------------|------------------------|-------|
| 11 | "$1,066,480 — highest-cost single SKU" | Depends on rebuild — highest-cost SKU changes at 92% fill | FIGURE_SWAP |
| 35 | "$33,128,550 in total short-shipping costs...69.19% overall fill rate; $2,055,467 in OTIF fines; $6,422,619 in deauthorization risk" | All figures retired. OTIF fines → compliance fines; deauthorization dropped entirely | NARRATIVE_REWRITE |
| 36–37 | "69% fill rate" / "90% fill rate scenario recovers $20.6M of the $33.1M" | Entire fulfillment narrative needs rewrite — buffer scenario operates on 92→95/97/98/99% range, not 69→90% | NARRATIVE_REWRITE |

### What this rebuild does NOT unblock

These entries in the change report cite short-ship figures but
also depend on other projects' regens. They are not unblocked by
the short-ship rebuild alone:

- **manifesto.qmd line 43 (thesis range):** Requires all ten
  decision figures — PDHA, deductions, channel, lifecycle regens
  are separate.
- **manifesto.qmd lines 288, 290 (channel story):** Owned by
  where-the-money-comes-from COGS fix, not short-ship.
- **manifesto.qmd line 131 ($461K chargebacks):** Owned by PDHA
  regen, not short-ship.
- **manifesto.qmd line 165 (deductions):** Owned by
  retailer-deduction-recovery, not short-ship.
- **manifesto.qmd line 326 (86.5¢):** Owned by contract-to-cash;
  87¢ per canonical (live post-06-20-tuning mart; was 86¢ pre-tuning).
- **research/cinderhaven-findings.md lines 19, 27, 29, 51, 59:**
  Owned by their respective projects (PDHA, deductions, channel,
  lifecycle).

### Prose rule reminder

Per working rules: Shawn approves all narrative text. The entries
above identify WHAT needs changing and WHERE. The rebuild produces
the numbers; Shawn writes (or approves) the replacement prose.
Do not draft replacement text.
