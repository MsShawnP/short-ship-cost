# Short-Ship Cost Analysis — traces every dollar of fulfillment shortfall to a recorded platform event

What does it cost when you can't fulfill orders as submitted? This
tool answers that for Cinderhaven Provisions, a fictional ~$25M
specialty food brand: it reads shipment lines where units ordered
exceeded units shipped, prices the gap across four cost dimensions,
and presents the result in an interactive dashboard.

The dataset is synthetic. The methodology is real. Every figure
regenerates from a single pipeline against the Cinderhaven Data
Platform (Postgres).

**Live:** https://shortships.lailarallc.com

## What it does

- Computes shortfall cost across four dimensions — forgone revenue,
  compliance fines, chargebacks, and deductions — directly from
  platform shipment, chargeback, and deduction records
- Models compliance fines from published retailer schedules
  (Walmart 3% of COGS, Costco $250 flat fee per any-short PO, etc.)
  applied to real shortfall events
- Simulates line-level fill-floor buffers (95–99%) and recomputes
  all four dimensions to show what a fill-rate lift recovers
- Exports the results as JSON consumed by a React dashboard with
  retailer drilldowns, SKU breakdowns, and monthly time series

## Why it matters

At a 99.3% portfolio fill rate (99.2% retailer / 99.5% distributor),
Cinderhaven still loses $894K over three years ($298K/yr):

| Dimension | 3-Year | Annual | % of Shipped |
|---|---|---|---|
| Forgone revenue | $523K | $174K | 0.69% |
| Compliance fines | $165K | $55K | 0.22% |
| Chargebacks | $119K | $40K | 0.16% |
| Deductions | $87K | $29K | 0.12% |

No modeled soft costs, no forward projections, no assumed admin
time. Forgone contribution margin — the actual profit impact — runs
$91K/yr, roughly 52% of the forgone revenue figure.

Two findings a fill-rate KPI alone would miss:

- **Fine structure beats fill rate.** Costco generates 85% of all
  compliance fines ($140K of $165K) because its $250 flat fee fires
  on any shorted line, even at 99%+ fill. Costco is also the largest
  single-retailer cost contributor at $212K (24% of total).
- **The floor matters more than the average.** At 99.3% average
  fill, individual lines still fall short. Lifting the line-level
  floor to 99% recovers $523K — 58.5% of total shortfall cost:

| Floor | Total Cost | Recovery | Recovery % |
|---|---|---|---|
| Baseline (99.3% avg) | $894K | — | — |
| 95% floor | $587K | $307K | 34.3% |
| 97% floor | $490K | $405K | 45.3% |
| 98% floor | $436K | $458K | 51.2% |
| 99% floor | $371K | $523K | 58.5% |

Chargebacks and deductions are unaffected by the fill-rate lift
because they are actual platform events, not modeled from the gap.

## Quick start

Run the dashboard against the JSON checked into the repo:

```bash
cd web
npm install
npm run dev
```

Other commands (from `web/`): `npm test` runs the canonical
regression suite that pins the published figures; `npm run build`
produces the production bundle; `npm run deploy` builds and ships
via Wrangler.

To regenerate the data from the platform (requires `psycopg2` and
the Cinderhaven Postgres replica reachable at `localhost:5432`):

```bash
python scripts/rebuild_from_platform.py
```

This rebuilds `data/short_ship_cost.db`, re-exports the JSON under
`web/public/data/`, and prints the figure summary.

## Tech stack

- **Frontend:** React 19, Vite, Recharts plus custom SVG components
- **Data pipeline:** Python 3.11+ with psycopg2, Postgres to SQLite
  to JSON
- **Testing:** Vitest canonical-figure regression test
- **Deployment:** Cloudflare Workers via Wrangler

## Project structure

- `scripts/rebuild_from_platform.py` — the entire pipeline: queries
  platform tables (`fct_*_shipment_lines`, `raw.*_chargebacks`,
  `raw.*_deductions`, `raw.sku_costs`), computes all four dimensions
  and buffer scenarios
- `data/short_ship_cost.db` — SQLite output of the pipeline
- `web/` — React dashboard; reads static JSON from `web/public/data/`
- `SHORT_SHIP_REBUILD_DESIGN.md` — design document with the
  dimension-by-dimension audit verdicts
- `docs/cost-engine-benchmarks.md` — cost engine benchmarks

The dataset covers 50 SKUs, 5 product lines, 6 retailers, and 3
distributors, defined canonically in the companion
cinderhaven-data-platform project.

## Provenance

This tool has been rebuilt twice. The original synthetic engine
generated orders at a 69% fill rate, producing $33.1M across 8
dimensions. A plausibility audit found that figure indefensible —
three incompatible fulfillment realities coexisted in the portfolio.
The first rebuild replaced the synthetic engine with platform
queries and landed at $6.6M / 92.7% fill across 4 dimensions. A
subsequent cinderhaven-data-platform reseed recalibrated fill rates
upward to 99.3%, producing the current $894K figure. Eight
dimensions became four. Every dollar now has a receipt.

---

Built by [Lailara LLC](https://lailarallc.com) — data hygiene and
analytics consulting for specialty food brands scaling into national
retail.

## License

MIT — see [LICENSE](LICENSE).
