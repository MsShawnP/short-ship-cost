# Short-Ship Cost Analysis — Cinderhaven Provisions

What does it cost when you can't fulfill orders as submitted? This
tool traces every dollar of fulfillment shortfall cost to a specific
platform event — a shipment line where units ordered exceeded units
shipped.

Cinderhaven Provisions is a fictional ~$25M specialty food brand.
The dataset is synthetic. The methodology is real. Every figure
regenerates from a single pipeline against the Cinderhaven Data
Platform (Postgres).

**Live:** https://shortships.lailarallc.com

## What it finds

At a 99.3% portfolio fill rate (99.2% retailer / 99.5% distributor),
Cinderhaven loses $894K over three years ($298K/yr) across four cost
dimensions:

| Dimension | 3-Year | Annual | % of Shipped |
|---|---|---|---|
| Forgone revenue | $523K | $174K | 0.69% |
| Compliance fines | $165K | $55K | 0.22% |
| Chargebacks | $119K | $40K | 0.16% |
| Deductions | $87K | $29K | 0.12% |

Every dollar traces to a platform event. No modeled soft costs, no
forward projections, no assumed admin time.

Forgone contribution margin — the actual profit impact — runs
$91K/yr, roughly 52% of the forgone revenue figure.

## The Costco finding

Costco generates 85% of all compliance fines ($140K of $165K)
because of its $250 flat fee per any-short PO. Even at 99%+ fill,
the flat-fee structure means any shorted line on a Costco PO
triggers the full penalty. Costco is also the largest single-
retailer cost contributor at $212K (24% of total).

## Buffer simulation

The tool models what a line-level fill floor recovers. At 99.3%
average fill, individual lines still fall below target — the buffer
simulation lifts the floor and recomputes all four dimensions:

| Floor | Total Cost | Recovery | Recovery % |
|---|---|---|---|
| Baseline (99.3% avg) | $894K | — | — |
| 95% floor | $587K | $307K | 34.3% |
| 97% floor | $490K | $405K | 45.3% |
| 98% floor | $436K | $458K | 51.2% |
| 99% floor | $371K | $523K | 58.5% |

Lifting the floor to 99% recovers 59% of total shortfall cost.
Chargebacks and deductions are unaffected by the fill-rate lift
because they are actual platform events, not modeled from the gap.

## Data contract

Consumes the Cinderhaven Data Platform directly:

- `fct_retailer_shipment_lines` / `fct_distributor_shipment_lines`
  — units ordered vs shipped per line
- `raw.retailer_chargebacks` / `raw.distributor_chargebacks` where
  reason = 'short_ship'
- `raw.retailer_deductions` / `raw.distributor_deductions` where
  deduction_type = 'short_ship'
- `raw.sku_costs` — COGS for contribution margin calculation
- Compliance fines modeled from published retailer schedules
  (Walmart 3% of COGS, Costco $250 flat, etc.)

50 SKUs, 5 product lines, 6 retailers, 3 distributors. Canonical
reference: `CINDERHAVEN_CANONICAL.md`.

## Stack

- **Frontend:** React 19, Vite
- **Charts:** D3 / custom SVG
- **Data pipeline:** Python → JSON from platform Postgres
- **Deployment:** Cloudflare Workers

## Run locally

```bash
npm install
npm run dev
```

To regenerate data from the platform:

```bash
python scripts/rebuild_from_platform.py
```

Requires a flyctl proxy to the Cinderhaven database.

## What this replaced

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
