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

At a 92.7% portfolio fill rate, Cinderhaven loses $6.6M over three
years ($2.2M/yr) across four cost dimensions:

| Dimension | 3-Year | Annual | % of Shipped |
|---|---|---|---|
| Forgone revenue | $5.5M | $1.8M | 7.85% |
| Compliance fines | $369K | $123K | 0.52% |
| Chargebacks | $344K | $115K | 0.49% |
| Deductions | $331K | $110K | 0.47% |

Every dollar traces to a platform event. No modeled soft costs, no
forward projections, no assumed admin time.

Forgone contribution margin — the actual profit impact — runs
$958K/yr, roughly 52% of the forgone revenue figure.

## The Costco finding

Costco generates 76% of all compliance fines ($281K of $369K)
because of its $250 flat fee per any-short PO. At 92% fill, 17% of
Costco POs have at least one shorted line. Improving Costco fill
from 92% to 95% is the single highest-return operational fix in the
analysis.

## Buffer simulation

The tool models what happens as fill rate improves:

| Target | Total Cost | Recovery | Recovery % |
|---|---|---|---|
| Baseline (92.7%) | $6.6M | — | — |
| 95% | $1.2M | $5.4M | 81.5% |
| 97% | $835K | $5.7M | 87.3% |
| 98% | $640K | $5.9M | 90.3% |
| 99% | $411K | $6.2M | 93.8% |

Moving from 92% to 95% fill recovers 81% of the total shortfall
cost. Diminishing returns set in above 97%.

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

This tool previously generated its own synthetic orders at a 69%
fill rate, producing a $33.1M cost figure across 8 dimensions. The
plausibility audit found that figure was indefensible — three
incompatible fulfillment realities coexisted in the portfolio. The
rebuild replaced the synthetic engine with direct platform queries.
$33M became $6.6M. Eight dimensions became four. Every dollar now
has a receipt.

---

Built by [Lailara LLC](https://lailarallc.com) — data hygiene and
analytics consulting for specialty food brands scaling into national
retail.

## License

MIT — see [LICENSE](LICENSE).
