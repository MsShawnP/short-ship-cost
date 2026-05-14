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

### 2026-05-07 — Build the interactive tool in React or polished HTML/JS, hosted on Netlify or GitHub Pages
- **Why:** The portfolio already has Streamlit (velocity tool), R/Shiny (health audit), Python CLI tools, and SQL. The gap is a product-quality interactive web tool that a non-technical executive would open in a browser. This fills that gap and demonstrates front-end data storytelling.
- **Scope:** Interactive tool deliverable
- **Do not:** Use Streamlit, Power BI, or Shiny for this project's interactive piece.

### 2026-05-07 — Use React for the interactive tool framework
- **Why:** Better fit for the kind of multi-control parameter-driven UI this project needs (channel filters, parameter overrides, scenario sliders). Component model gives cleaner state management than vanilla HTML/JS for the level of interactivity planned. Refines the earlier "React or polished HTML/JS" decision into a firm choice.
- **Scope:** Interactive tool framework
- **Do not:** Reach for vanilla HTML/JS or jQuery for this app.

### 2026-05-07 — Deliver data to the browser as pre-extracted JSON, not by loading the SQLite files via sql.js
- **Why:** The cost-engine output (`short_ship_cost.db`) is small enough to extract to JSON at build time. Avoiding `sql.js` keeps the bundle smaller, removes WASM loading overhead, and means the tool starts faster on first paint. The orders DB (22 MB) doesn't need to ship to the browser at all — only its summarized cost output does.
- **Scope:** Data delivery to the interactive tool
- **Do not:** Load `short_ship_orders.db` or `cinderhaven_extract.db` directly in the browser via `sql.js`. Pre-extract whatever the tool needs at build time.

### 2026-05-07 — Use the same 18–24 month time window as existing Cinderhaven scan data
- **Why:** Keeps the door open for future projects to JOIN the order data with scan data. Consistency across the Cinderhaven dataset.
- **Scope:** Synthetic order data generation
- **Do not:** Create a different time window that would make cross-referencing impossible.

### 2026-05-08 — Use React (Vite) for the interactive tool
- **Why:** React's component model and state management fit the parameter adjustment panel and drill-down interactions. Vite for fast dev/build. Portfolio gap is a product-quality web tool — React fills it.
- **Scope:** Interactive tool
- **Do not:** Use vanilla HTML/JS, Streamlit, or any other framework.

### 2026-05-08 — Pre-computed JSON for data delivery, not client-side SQLite
- **Why:** React's ecosystem is built around JS objects. JSON is native — no translation layer, no wasm dependency (sql.js), no async queries fighting React's rendering model. Data is small enough to bundle. Pre-aggregate in a Python export script so the app gets summary-level data, not 125K raw order lines.
- **Scope:** Data pipeline from cost engine to interactive tool
- **Do not:** Load SQLite files in the browser or build a backend API.

### 2026-05-08 — Browser-side parameter overrides operate by ratio scaling on pre-aggregated JSON, not by re-running the cost engine
- **Why:** The Python cost engine reads from `short_ship_orders.db` (22 MB) — too big for the browser. To make the parameter sliders responsive, `web/src/utils/costEngine.js` derives per-(dimension, retailer) ratios from `params / baseline_params` and multiplies the pre-aggregated JSON aggregates. Deauthorization is the exception: it filters `deauthorization_events.json` by the user's threshold settings. Buffer scenarios use ratio scaling for the scenario-by-dimension breakdowns.
- **Scope:** `ParameterPanel` recompute path
- **Do not:** Ship the orders DB to the browser. Do not attempt to re-run the cost engine in JS over raw order lines. When a new parameter is added, decide upfront whether it's ratio-scalable; if not (e.g., a velocity threshold being *raised*), document the limitation rather than bolt on a new data shape.

### ~~2026-05-08 — Host on Netlify~~ (reversed 2026-05-09)
- **Why:** Zero-config for React apps, auto-detects build command, instant deploys from GitHub, free tier generous. Less friction than GitHub Pages for a Vite + React project.
- **Scope:** Deployment
- **Do not:** Use GitHub Pages unless Netlify proves problematic.
- **Reversed:** See 2026-05-09 — Host on Cloudflare Workers.

### 2026-05-09 — Host on Cloudflare Workers (static assets)
- **Why:** The 2026-05-08 Netlify deploy worked, but Cloudflare's autoconfig PR (`#1`) wired up Wrangler + `@cloudflare/vite-plugin` with single-page-application asset handling and an observability hook. Cloudflare's edge network and zero-config Vite integration matched what Netlify gave us; staying on the platform that already had the working PR was the lower-friction path. The deployment is technically Workers Static Assets (`wrangler.jsonc` with `assets.not_found_handling = "single-page-application"`), not Cloudflare Pages — the URL is `*.workers.dev`.
- **Scope:** Deployment
- **Do not:** Refer to the deployment as "Cloudflare Pages" — it's Workers serving static assets. Do not revert to Netlify or GitHub Pages without a new decision.

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

### 2026-05-08 — Recharts for charting, validated for print compatibility
- **Why:** SVG-based (critical for print CSS — renders as vectors, not rasterized canvas). React-native component API. Print compatibility spike in task 1 confirms it works before building all sections.
- **Scope:** All charts in the interactive tool
- **Do not:** Use Chart.js or other canvas-based charting libraries.

### 2026-05-08 — Click-to-pin (no hover tooltips) is the canonical chart interaction
- **Why:** Hover tooltips disappear when the mouse leaves; users want to read the breakdown at length, talk about it, hand the screen off. Click-to-pin keeps the detail visible. Dark `PinnedCallout` card above each chart unifies the pattern; dimming on non-selected items reinforces the focus.
- **Scope:** All charts across all sections
- **Do not:** Add hover tooltips. Do not put pinned details inline below the chart (they get lost). Do not vary the callout style per section.

### 2026-05-08 — Sequential teal palette by magnitude rank for cost dimensions
- **Why:** A categorical palette assigns colors by *type* (lost-revenue=navy, deauth=red), but eight categorical hues compete for attention. Sequential teal (`#0A3D3D` darkest → `#BDEEE8` lightest) sorted by dimension magnitude communicates the hierarchy at a glance and lets the same dimension read identically across every section. Documented in `docs/design-spec.md` and centralized in `web/src/lib/dimensions.js`.
- **Scope:** All charts and tables in the interactive tool
- **Do not:** Reintroduce the categorical navy/red/gray palette. Do not assign a brand color (e.g., red) to a single dimension — palette ordering is by magnitude, not by meaning.

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

---

## Reversed / Superseded

- **2026-05-08 — Host on Netlify** → reversed 2026-05-09 by "Host on Cloudflare Workers (static assets)" (in the Architecture & Pipeline section above).
