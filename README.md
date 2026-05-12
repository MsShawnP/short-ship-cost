# The Cost of Shorts

An interactive analysis of what it costs a specialty food business
when it cannot fulfill retail partner orders as submitted — and why
the true cost is invisible when the original order is overwritten.

**[View the live tool →](https://short-ship-cost.msshawnp.workers.dev)**

## What this is

Cinderhaven Provisions is a ~$25M specialty food brand selling
through Walmart, Costco, Whole Foods, UNFI, KeHE, regional chains,
and direct-to-consumer. Like many manufacturers its size, it
produces mostly to order and cannot keep up with demand. Every week
an EDI/sales admin manually edits orders down to match available
inventory, prioritising by retailer importance and due date. The
legacy system overwrites the original order with the edited version.

The original order — the thing the retailer actually asked for — is
gone. And with it, any ability to measure the cost of not fulfilling
it.

This tool reconstructs that cost. It generates synthetic order data
(43,110 orders, $51.9M shipped over two years), models the triage
process, and calculates the full cost of every short across eight
dimensions:

| Dimension | Description |
|---|---|
| Lost revenue | Units ordered but never shipped |
| Deauthorization | Shelf placement lost from chronic underfill |
| OTIF fines | Walmart, Costco, Whole Foods, UNFI, KeHE penalties |
| Chargebacks | Retailer compliance charges on shorted POs |
| DTC cancellations | Customer cancellations from hold-for-complete delays |
| DTC margin leakage | Cancelled DTC customers who buy in-store at lower margin |
| Distributor returns | Unsold promo product returned or written off |
| Triage labour | Human time spent editing every order |

The headline: **$25.6M in total short-shipping costs on $51.9M
shipped revenue** — 49.4% of the topline. The business thinks it
ships $52M. The demand it cannot see is $70M+.

## What the tool does

- **Headline cost stack** — flow-split chart showing total cost
  allocated across eight dimensions, with contextual benchmarks
  (% of revenue, % of estimated margin, unshipped demand gap)
- **Retailer and SKU drill-down** — stacked bars by retailer,
  sortable heatmap table of the 20 costliest SKUs
- **Time series** — monthly stacked area chart with trend detection
  (rising, steady, eased) and summary statistics
- **Buffer simulation** — staircase chart showing cost recovery at
  80/85/90/95% fill rates, with a deauthorization cliff at 90%
- **Parameter adjustment** — sliders for OTIF rates, deauthorization
  thresholds, margins, triage costs, and chargebacks; costs
  recalculate in the browser with a reset-to-baseline button
- **Time-range filter** — narrow any section to a custom month range
- **Dimension toggles** — exclude/include individual cost dimensions
- **Print export** — `Ctrl+P` produces a paginated, Economist-style
  PDF with clean typography and sharp SVG charts

## Tech stack

- **Frontend** — React (Vite), custom SVG charts, Recharts for area
  and bar charts, CSS Modules, code-split via React.lazy
- **Data pipeline** — Python scripts generating synthetic orders and
  running a modular cost engine across eight dimensions
- **Data delivery** — pre-aggregated JSON (81 KB total); no backend,
  no API
- **Cost engine (browser)** — JS implementation scaling aggregates
  by parameter ratios, validated against Python output
- **Hosting** — Cloudflare Pages (static site)
- **Typography** — Playfair Display + Source Sans 3

## Repository structure

```
data/               SQLite databases (extract, orders, costs)
docs/               Schema, cost-engine docs, design spec
scripts/            Python pipeline: order generation, cost engine,
                    validation, JSON export
web/                React app (Vite)
  public/data/      Pre-aggregated JSON consumed by the app
  src/components/   Section components, parameter panel, header
  src/lib/          Shared utilities (time range, dimensions, format)
  src/utils/        Browser-side cost engine
```

## Run locally

```
cd web
npm install
npm run dev
```

Opens at `http://localhost:5173`. The app loads JSON from
`web/public/data/`; no backend or database connection required.

To regenerate JSON from the SQLite databases:

```
python scripts/export_json.py
```

## Methodology

The synthetic order data, triage model, and cost engine are
documented in [`docs/cost-engine-docs.md`](docs/cost-engine-docs.md).
All cost parameters are tunable via the interactive panel and
documented in [`docs/cost-engine-benchmarks.md`](docs/cost-engine-benchmarks.md).

---

A [Lailara LLC](https://github.com/MsShawnP) portfolio piece.

## License

MIT — see [LICENSE](LICENSE).
