# short-ship-cost — Decisions Log

Permanent record of choices that should survive session turnover.
If a decision is reversed, strike it through and add the replacement
below — don't delete.

---

## Format

Each entry:
- **Date** — when decided
- **Decision** — one sentence, imperative voice
- **Why** — the reasoning, including what was tried and rejected
- **Scope** — what this applies to (file, chunk, deliverable, or "global")
- **Do not** — explicit anti-instructions, if any

---

## Architecture & Pipeline

### 2026-05-07 — Use Cinderhaven Provisions as the fictional brand for all data and narrative
- **Why:** Cinderhaven is the shared synthetic dataset across the portfolio. Using it maintains consistency and allows future cross-referencing between projects. This is a portfolio piece, not a client deliverable.
- **Scope:** Global
- **Do not:** Use the prospective lead's company name, data, or identifiable details anywhere in this project.

### ~~2026-05-07 — Build the interactive tool in React or polished HTML/JS, hosted on Netlify or GitHub Pages~~
- **Superseded by:** 2026-06-28 — React (Vite) on Cloudflare Workers. Netlify/GitHub Pages never used; Cloudflare Workers provides edge-served static assets with SPA fallback.

### 2026-05-07 — Use React for the interactive tool framework
- **Why:** Better fit for the kind of multi-control parameter-driven UI this project needs (channel filters, parameter overrides, scenario sliders). Component model gives cleaner state management than vanilla HTML/JS for the level of interactivity planned. Refines the earlier "React or polished HTML/JS" decision into a firm choice.
- **Scope:** Interactive tool framework
- **Do not:** Reach for vanilla HTML/JS or jQuery for this app.

### ~~2026-05-07 — Deliver data to the browser as pre-extracted JSON, not by loading the SQLite files via sql.js~~
- **Superseded by:** 2026-06-28 — JSON exported from platform Postgres via `rebuild_from_platform.py`. The old pipeline extracted from local SQLite files via a separate `export_json.py`; the rebuild script now queries Postgres directly and writes JSON in the same run. The browser still receives pre-aggregated JSON — the change is the data source, not the delivery mechanism.

### 2026-06-28 — Pre-aggregated JSON from platform Postgres, not SQLite extraction
- **Why:** The 4-dimension causal model queries the cinderhaven-data-platform Postgres directly. `rebuild_from_platform.py` computes all four dimensions, writes `data/short_ship_cost.db` as an archival artifact, and exports 8 JSON files to `web/public/data/`. No intermediate SQLite databases in the pipeline — Postgres is the single source. The old `cinderhaven_extract.db` and `short_ship_orders.db` no longer exist.
- **Scope:** Data pipeline from platform to interactive tool
- **Do not:** Reintroduce SQLite as an intermediate data source. Do not create a separate JSON export script — all export logic lives in `rebuild_from_platform.py`.

### ~~2026-05-07 — Use the same 18–24 month time window as existing Cinderhaven scan data~~
- **Superseded by:** 2026-06-14 — 4-dimension causal model. The platform uses a 36-month window (2023-01-02 to 2026-01-07). The synthetic order generator that needed time-window alignment no longer exists.

### 2026-05-08 — Use React (Vite) for the interactive tool
- **Why:** React's component model and state management fit the parameter adjustment panel and drill-down interactions. Vite for fast dev/build. Portfolio gap is a product-quality web tool — React fills it.
- **Scope:** Interactive tool
- **Do not:** Use vanilla HTML/JS, Streamlit, or any other framework.

### ~~2026-05-08 — Pre-computed JSON for data delivery, not client-side SQLite~~
- **Superseded by:** 2026-06-28 — Pre-aggregated JSON from platform Postgres. The principle (pre-aggregated JSON, not client-side DB) still holds; the source changed from local SQLite to platform Postgres.

### ~~2026-05-08 — Browser-side parameter overrides operate by ratio scaling on pre-aggregated JSON, not by re-running the cost engine~~
- **Superseded by:** 2026-06-28 — Ratio scaling narrowed to compliance fines only. See replacement entry below.

### 2026-06-28 — Browser-side parameter overrides use ratio scaling for compliance fines only
- **Why:** In the 4-dimension model, only compliance_fines have tunable parameters (per-channel fine rates). Forgone revenue, chargebacks, and deductions are actual platform event data — not scalable by user parameters. `web/src/utils/costEngine.js` derives per-channel ratios from `params / baseline_params` for fine rates and multiplies the pre-aggregated compliance_fines data. The old deauthorization event filtering and 8-dimension ratio scaling no longer apply.
- **Scope:** `ParameterPanel` recompute path
- **Do not:** Add ratio scaling to chargebacks or deductions — these are actual platform events and cannot be meaningfully scaled by a parameter slider.

### ~~2026-05-08 — Host on Netlify~~
- **Superseded by:** 2026-06-28 — Cloudflare Workers. Netlify was never actually used; the project deployed to Cloudflare Workers from the start of the deployment arc.

### 2026-06-28 — Host on Cloudflare Workers
- **Why:** Edge-served static assets with SPA fallback via `wrangler deploy`. Build pipeline: `vite build` → `wrangler deploy`. Custom domain at shortships.lailarallc.com. Free tier covers this project's traffic.
- **Scope:** Deployment
- **Do not:** Move to Netlify, Vercel, or GitHub Pages without a specific reason.

### 2026-09-03 — `main` is the only long-lived branch; `master` is deleted
- **Why:** `ci.yml` sat pinned to `branches: [master]` after the default branch moved to `main`. CI had run ~15 times on `master` pushes through 2026-07-22, then went dormant for six weeks -- the frontend build and vitest ran on nothing that shipped to `main`. The trigger looked correct in isolation; only the branch name was stale. `master` was a strict ancestor of `main` (0 unique commits) and was deleted 2026-09-03 along with its remote ref. Keeping a second long-lived branch is what made the misdiagnosis possible -- and it cost a wrong 'CI never ran' claim that survived into a merged commit message.
- **Scope:** Branching, all five files in `.github/workflows/`
- **Do not:** Recreate `master`, or pin any workflow trigger to it. When changing a branch filter in one workflow, check all five -- `ci.yml`, `deploy.yml`, `client-mode.yml`, `golden.yml`, `canonical-drift.yml` -- in the same pass.

---

## Data & Schema

### 2026-05-07 — Generate synthetic order data (original + edited) as a new data layer, not modify existing Cinderhaven tables
- **Why:** The existing Cinderhaven dataset has scan data (POS sell-through), not order transactions. Orders are a different data layer. Keep them separate. Order data lives in this repo for now, may move to a separate repo later.
- **Scope:** Data generation
- **Do not:** Add order tables to the cinderhaven-data repo during this project.

### 2026-05-07 — Model three short behaviors by channel
- **Why:** The real-world pattern: retail partners either accept backorders or lose the sale; DTC orders are held until 100% complete, causing cancellations and margin leakage to retail.
- **Scope:** Order generation logic
- **Do not:** Treat all channels the same way for shorts.

---

## Visualization

### 2026-05-08 — Single scrollable page, not multi-view navigation
- **Why:** The narrative is the structure — the argument builds top to bottom, Economist-style. Headline cost stack → retailer/SKU drill-down → time series → buffer simulation. Drill-downs use expandable sections or modals, not separate routes. Single page also maps cleanly to the print CSS export.
- **Scope:** Interactive tool layout
- **Do not:** Add client-side routing or multi-page navigation unless a section proves too heavy.

### ~~2026-05-08 — Recharts for charting, validated for print compatibility~~
- **Superseded by:** 2026-06-28 — D3 / custom SVG primary, Recharts retained for time series and buffer staircase only.

### 2026-06-28 — D3 / custom SVG for primary charts, Recharts for time series and buffer simulation
- **Why:** The flow-split chart (Section 1) and retailer stacked bar (Section 2) use custom SVG for precise layout control. Recharts is retained for the stacked area time series (Section 3) and bar chart staircase (Section 4) where its `ResponsiveContainer` and animation support justify the dependency. All rendering is SVG-based for print compatibility.
- **Scope:** All charts in the interactive tool
- **Do not:** Use Chart.js or other canvas-based charting libraries. Do not replace the custom SVG charts with Recharts — the custom layouts provide better control over the flow-split and stacked-bar rendering.

### 2026-05-08 — Click-to-pin (no hover tooltips) is the canonical chart interaction
- **Why:** Hover tooltips disappear when the mouse leaves; users want to read the breakdown at length, talk about it, hand the screen off. Click-to-pin keeps the detail visible. Dark `PinnedCallout` card above each chart unifies the pattern; dimming on non-selected items reinforces the focus.
- **Scope:** All charts across all sections
- **Do not:** Add hover tooltips. Do not put pinned details inline below the chart (they get lost). Do not vary the callout style per section.

### ~~2026-05-08 — Sequential teal palette by magnitude rank for cost dimensions~~
- **Superseded by:** 2026-06-28 — Updated to reflect 4 dimensions instead of 8. Same approach, narrower ramp.

### 2026-06-28 — Sequential Hong Kong teal palette for 4 cost dimensions
- **Why:** Same principle as the original 8-dimension palette — sequential teal sorted by magnitude — but with 4 stops instead of 8. Uses Hong Kong ramp steps 5, 25, 45, 70 (`#063d32` → `#0e6e5a` → `#1fa282` → `#6dcdb5`), per Lailara DS v2. Forgone revenue (darkest) through deductions (lightest). Centralized in `web/src/lib/dimensions.js`.
- **Scope:** All charts and tables in the interactive tool
- **Do not:** Reintroduce the categorical palette. Do not assign a brand color to a single dimension.

---

## Output Formats

### 2026-05-07 — The export/takeaway document is generated from the tool, not a separate static deliverable
- **Why:** More useful — user configures their view and exports a snapshot with analysis. Also a stronger portfolio piece (shows the tool produces client-ready output). Economist style: plain English, data-forward, clean graphics.
- **Scope:** Export feature
- **Do not:** Build a separate static PDF or document disconnected from the interactive tool.

### 2026-05-08 — Use print CSS for the export, not jsPDF or html2pdf
- **Why:** Print CSS produces the highest quality output — crisp vector text (searchable, sharp at any zoom), SVG charts render as vectors, small file sizes. jsPDF requires designing the PDF twice; html2pdf rasterizes everything. Tradeoffs (page break control, browser variation) are manageable for a portfolio piece where we control the demo environment.
- **Scope:** Export feature
- **Do not:** Use jsPDF, html2pdf, or any PDF generation library.

---

## Writing & Voice

### 2026-05-07 — Economist style for all written output and export
- **Why:** Plain English that tells the truth as presented by the data. Sharp charts with clear labels. No decorative nonsense. Distinct from typical dashboard/consulting-deck aesthetic. Matches the portfolio's voice.
- **Scope:** Global — interactive tool, export, README, all prose
- **Do not:** Use McKinsey/consulting-deck style, marketing language, or data-science-prototype aesthetics.

### ~~2026-05-15 — Keep the sequential teal palette unchanged after quantitative evaluation~~
- **Superseded by:** 2026-06-28 — Palette reduced from 8 stops to 4 as part of the 4-dimension rebuild. The deltaE analysis of the 8-stop palette is historical; the current 4-stop palette has wider spacing and no contrast concerns.

### 2026-05-15 — Use CSS Grid (not flex-wrap) for dimension toggle chips
- **Why:** Flex-wrap with label text, hint, and chips in one container wraps unpredictably depending on viewport width. CSS Grid with `repeat(4, 1fr)` desktop / `repeat(2, 1fr)` mobile guarantees even rows regardless of chip text length or container width. With 4 dimensions, this produces a single row on desktop and a 2×2 grid on mobile.
- **Scope:** `DimensionToggle.jsx` and `DimensionToggle.module.css`
- **Do not:** Put the label/hint text back inline with the chips. They live in a separate `.labelRow` flex container above the grid.

### 2026-06-14 — Replace 8-dimension synthetic model with 4-dimension causal model from platform
- **Why:** The plausibility audit found the synthetic 69% fill / $33.1M figure was indefensible — three incompatible fulfillment realities coexisted in the portfolio. The cinderhaven-data-platform now generates causal shipment lines with event-driven chargebacks and deductions. Four dimensions have receipts: forgone revenue (actual gap), compliance fines (modeled from retailer schedules), chargebacks (platform events), deductions (platform events). The dropped dimensions (deauthorization, DTC cancellations, DTC margin leakage, distributor returns, triage labor) were synthetic constructs without platform backing.
- **Scope:** Entire project — data pipeline, React app, all documentation
- **Do not:** Re-add synthetic dimensions. Every cost dollar must trace to a platform event or a retailer-published fine schedule.

### 2026-06-14 — Integrate JSON export into rebuild_from_platform.py, not a separate script
- **Why:** The old pipeline had a separate `export_json.py` that re-queried databases. The rebuild script's `results` dict already contains all granular breakdowns (by_retailer_month, by_sku_month, by_sku_retailer) from `_build_result`. Exporting in the same script avoids re-querying Postgres and keeps the pipeline to one command: `python scripts/rebuild_from_platform.py`.
- **Scope:** Data pipeline
- **Do not:** Create a separate JSON export script. If new JSON shapes are needed, add builder functions to `rebuild_from_platform.py`.

### 2026-09-02 — Require a full `DATABASE_URL`; never assemble a DSN from a password variable
- **Why:** Replacing the hardcoded DSN, the obvious alternative was keeping the connection string in code and injecting only `POSTGRES_PASSWORD`. That reintroduces the exact pattern the new gitleaks rule forbids — a literal connection string with a `password=` slot, one edit away from being populated again — and it duplicates connection config that `.env` already owns. contract-to-cash's `scripts/db.py` does assemble this way; it is not a leak, but it is not the pattern to copy.
- **Scope:** Every DB-backed script in this repo.
- **Do not:** Build a connection string by interpolating a credential. Read `DATABASE_URL` whole, fail fast when unset, and put the URL in `.env`.

### 2026-09-02 — The rotated local-default password stays in git history; do not rewrite history to purge it
- **Why:** The value sat in `scripts/rebuild_from_platform.py` from 87c6ebe, in a public repo. Owner rotated the local Postgres password instead of rewriting history, which makes the historical string worthless. A `filter-repo` purge would rewrite 54 commits, break every published SHA, and force-push a public repo — real cost to remove a string that no longer opens anything.
- **Scope:** short-ship-cost git history.
- **Do not:** Propose `git filter-repo`, BFG, or a force-push for this credential again. The decision is made. This applies only to a rotated local-default; a live or shared credential is a different call.

### 2026-09-02 — Every DB-backed tool ships a real `.gitleaks.toml` covering both DSN forms
- **Why:** The keyword form (`host=... password=...`) survived three months here because the rule only matched `postgres://user:pass@`. Worse, gitleaks exits 0 and reports "no leaks found" when `--config` points at a file that does not exist — otif-blind-spot and contract-to-cash both reference `.gitleaks.toml` in pre-commit and neither has one, so both scan on defaults while showing green.
- **Scope:** short-ship-cost, otif-blind-spot, contract-to-cash — every repo whose pre-commit config names a gitleaks config file.
- **Do not:** Point `--config` at a file you have not confirmed exists; a missing config is silent, not loud. Do not add a URL-form rule without the keyword-form rule beside it.

---

## Reversed / Superseded

### ~~2026-05-07 — Generate synthetic order data (original + edited) as a new data layer~~
- **Superseded by:** 2026-06-14 — 4-dimension causal model from platform. Platform generates actual shipment lines; synthetic orders retired.

### ~~2026-05-07 — Model three short behaviors by channel~~
- **Superseded by:** 2026-06-14 — 4-dimension causal model. Channel-specific synthetic behaviors (DTC hold-for-complete, distributor returns) replaced by platform events.

### ~~2026-05-08 — Browser-side parameter overrides operate by ratio scaling on pre-aggregated JSON~~
- **Partially superseded:** Only compliance_fines have tunable parameters now. Chargebacks and deductions are actual platform events (not scalable). Forgone revenue is the actual gap. The ratio-scaling mechanism still applies to the fine schedule rates.

### ~~2026-05-07 — Build the interactive tool in React or polished HTML/JS, hosted on Netlify or GitHub Pages~~
- **Superseded by:** 2026-06-28 — React (Vite) on Cloudflare Workers.

### ~~2026-05-07 — Deliver data to the browser as pre-extracted JSON, not by loading the SQLite files via sql.js~~
- **Superseded by:** 2026-06-28 — JSON exported from platform Postgres via `rebuild_from_platform.py`. Principle (pre-aggregated JSON) still holds; source changed from SQLite to Postgres.

### ~~2026-05-07 — Use the same 18–24 month time window as existing Cinderhaven scan data~~
- **Superseded by:** 2026-06-14 — Platform uses 36-month window. Synthetic order generator retired.

### ~~2026-05-08 — Pre-computed JSON for data delivery, not client-side SQLite~~
- **Superseded by:** 2026-06-28 — Same principle, source changed from SQLite to platform Postgres.

### ~~2026-05-08 — Host on Netlify~~
- **Superseded by:** 2026-06-28 — Cloudflare Workers. Netlify was never used.

### ~~2026-05-08 — Recharts for charting, validated for print compatibility~~
- **Superseded by:** 2026-06-28 — D3 / custom SVG primary, Recharts retained for time series and buffer staircase only.

### ~~2026-05-08 — Sequential teal palette by magnitude rank for cost dimensions~~
- **Superseded by:** 2026-06-28 — Same approach with 4 Hong Kong teal stops instead of 8.

### ~~2026-05-15 — Keep the sequential teal palette unchanged after quantitative evaluation~~
- **Superseded by:** 2026-06-28 — 8-stop deltaE analysis is historical; 4-stop palette has no contrast concerns.
