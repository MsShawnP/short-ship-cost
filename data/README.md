# data/

Self-contained data extract for `short-ship-cost`.

## `cinderhaven_extract.db`

A SQLite database carrying the eight Cinderhaven Provisions tables this
project consumes. Approximately 1.6 MB, ~14,600 rows, safe to commit.

It is a one-way extract from the [`cinderhaven-data`](https://github.com/MsShawnP/cinderhaven-data)
repo's built database (`cinderhaven_product_master.db`, ~172 MB).
Schemas, primary keys, NOT NULL constraints, and indexes are preserved
verbatim. To rebuild, run `scripts/extract_cinderhaven.py` against a
local build of the source database.

### Tables included

| Table | Rows | What it is |
|---|---|---|
| `product_master` | 90 | SKU master: identifiers (sku, gtin14, upc), product line, subcategory, case pack, MSRP, nutrition. Includes deliberate data-quality defects on some rows (missing case dimensions, etc.) |
| `sku_costs` | 90 | COGS, landed cost, retailer-specific wholesale prices (Walmart / Costco / Whole Foods / Regional / UNFI / DTC), and trade-spend rates per channel |
| `stores` | 902 | Retail door list with retailer, chain, region, state, volume tier. UNFI and DTC are represented as single aggregated rows |
| `distribution_log` | 12,507 | SKU × store authorization history (auth and deauth dates). Underpins which SKUs are on shelf where, and over what window |
| `promotions` | 198 | Retailer-specific promotional events: timing, depth, store scope |
| `price_history` | 398 | Time-keyed wholesale prices by SKU × retailer over the 18–24-month window |
| `chargebacks` | 381 | Historical compliance chargebacks by month / retailer / reason / SKU. Includes "Short shipment" and "Late delivery" reasons alongside the data-quality reasons that drive most of them |
| `retailer_requirements` | 29 | Field-level compliance requirements by retailer (e.g., Walmart requires `gtin14` with valid check digit). Drives the `chargebacks` table |

### What is NOT included and why

**`scan_data`** (~1.19 M rows, ~140 MB in the source DB). POS sell-through
is a different data layer from order fulfillment; this project models the
gap between *orders received* and *orders shipped*, which `scan_data` does
not speak to. Excluding it is what keeps the extract small enough to
commit.

## What this project will add (not yet built)

Tables this project will create live alongside the Cinderhaven extract.
Scope is tracked in `PLAN.md`; nothing below exists yet.

1. **`original_orders`** — orders as submitted by retail partners,
   before any human triage or editing.
2. **`shipped_orders`** — orders as actually shipped, after triage. The
   delta between `original_orders` and `shipped_orders` is the entire
   subject of this project.
3. **`otif_fine_schedule`** — per-retailer fine rates (rate per missing
   unit, per missing dollar, per shipment, fixed fees, etc.) used to
   compute fines on shorts. Distinct from the `chargebacks` table, which
   is historical actuals, not a lookup schedule.
4. **DTC cancellation parameters** — share of held-incomplete DTC
   orders that cancel as a function of hold duration, plus the
   downstream wholesale-margin substitution rate.
5. **Triage labor parameters** — minutes per order edit and blended
   labor rate.
6. **Deauthorization risk parameters** — mapping from short-rate
   trajectory to deauthorization probability and forward revenue at risk.
7. **Distributor return / claim parameters** — UNFI / KeHE over-order
   return and write-off rates for promo periods.

These will be added as the relevant `PLAN.md` tasks land. Some may live
as parameter files (CSV / JSON) rather than SQLite tables.
