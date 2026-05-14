# short-ship-cost — Current Work Plan

The current arc of work. Updated when the arc changes, not every
session. For session-by-session state, see HANDOFF.md.

---

## No active arc

Arc 2 closed on 2026-05-09 (see Arc history). The next arc is not
yet defined.

---

## Arc history

### Arc 2 — Interactive tool (completed 2026-05-09)

Built the single-page React app (Vite) that presents the full
cost-of-shorts analysis: four sections (headline cost stack,
retailer/SKU drill-down, time series, buffer simulation), parameter
adjustment panel with browser-side cost engine, time-range filter,
dimension toggles, click-to-pin callouts, print CSS export, and
deployed live. Initial deployment targeted Netlify (task 11);
migrated to Cloudflare Workers (static assets) on 2026-05-09 — see
DECISIONS.md.

Goal: a single-page React app that presents the full cost-of-shorts
analysis, lets users explore by retailer/SKU/time period, adjust
parameters, run buffer simulations, and export an Economist-style
PDF via print CSS. Hosted on Cloudflare Workers.

Business question: same as the project.

Tasks:

- [x] Set up React project scaffolding — Vite + React, basic folder
      structure, host config, deploy an empty shell to confirm the
      pipeline works end-to-end (local → GitHub → live URL).
      Include a print compatibility spike: render one SVG chart
      (Recharts), print to PDF, confirm it doesn't break before
      building all sections.
- [x] Build the JSON export script — Python script that reads all
      three DBs and outputs the JSON files the React app consumes.
      Pre-aggregate data: the React app gets summary-level data for
      rendering, not raw order lines. Include a `meta` object carrying
      last-updated date and the cost_parameters used. Output a
      `validation.json` with known totals per dimension so the JS
      math can be tested against the Python output.
- [x] Design the page structure and visual language — wireframe the
      single scrollable page: what sections exist, what order, what
      charts go where. Establish typography, color palette, and chart
      style (Economist-inspired). This is a design task, not a code
      task — output is a documented spec the build tasks reference.
- [x] Build Section 1: Headline cost stack — the $25.6M total,
      eight-dimension breakdown, "your business thinks it shipped $X
      but the true cost of shorts is $Y" framing. Include contextual
      benchmark: total cost as % of shipped revenue, as % of estimated
      gross margin. Key chart: stacked bar or waterfall showing base
      lost revenue + cascading costs.
- [x] Build Section 2: Retailer and SKU drill-down — filterable
      views by retailer and SKU. Show which retailers bear the most
      cost, which SKUs are most shorted, where deauthorization events
      cluster. Use pre-grouped data (top contributors, not all 90
      SKUs). Key charts: heatmap or bar charts by retailer × dimension,
      top-N SKU table.
- [x] Build Section 3: Time series — monthly cost trends across the
      18–24 month window. Show whether the problem is getting worse.
      Key chart: line or area chart by dimension over time.
- [x] Build Section 4: Buffer simulation — the staircase chart. Show
      cost recovery at 80/85/90/95% fill rates. Highlight the
      deauthorization cliff at 90%. Let users see what they'd save.
- [x] Build parameter adjustment panel — let users modify fine rates,
      thresholds (including deauthorization thresholds — both retailer
      velocity thresholds and distributor fill rate threshold, so users
      can drag the 90% distributor threshold and watch the deauth cliff
      shift), margins, triage cost, and see the cost stack recalculate.
      Cost engine math runs in JS against in-memory JSON data, validated
      against validation.json to confirm JS reproduces Python output.
      Include a "Reset to Baseline" button that restores validated
      defaults. Use React Context + hooks for state management, with
      useMemo on cost calculations to avoid UI stutter during slider
      interaction.
- [x] Build print CSS export — @media print stylesheet that reformats
      the page into an Economist-style document. Clean typography,
      sharp SVG charts, proper page breaks between sections. Triggered
      by a button that calls window.print(). Include a print mode that
      disables chart animations before rendering.
- [x] Polish pass — responsive behavior, loading states, edge cases,
      accessibility basics, final visual tuning. Review each section
      as its own vertical slice. Desktop is the primary target;
      responsive but not mobile-first.
- [x] Deploy to production — final deploy, confirm everything works
      at the live URL, update README with the link. Initially shipped
      to Netlify; migrated to Cloudflare Workers (static assets) the
      same day.

Out of scope for this arc:

- Backend/API layer — this is a static site with bundled JSON
- User authentication or saved sessions
- Connecting to actual client data
- Mobile-first optimization (responsive but desktop is primary)
- Moving order data to a separate repo
- State management libraries (Zustand, Redux) — React Context +
  hooks unless complexity demands otherwise

Definition of done — met:

- [x] React app is live at a public URL
      (https://short-ship-cost.msshawnp.workers.dev)
- [x] All four sections render correctly with real data from the cost
      engine
- [x] JS cost math matches Python output (validated against
      validation.json)
- [x] Parameter adjustments recalculate costs in the browser with a
      reset-to-baseline option
- [x] Buffer simulation staircase chart shows the deauthorization
      cliff at 90%
- [x] Print CSS export produces a clean, readable PDF with proper
      page breaks and sharp SVG charts
- [x] The app looks like a product, not a prototype
- [x] README links to the live tool

### Arc 1 — Synthetic order data + cost engine (completed 2026-05-07)

Generated synthetic order dataset (43,110 orders, 125,748 lines,
$51.9M shipped over 18-24 months) and built modular cost engine
calculating all eight cost dimensions. Total cost of shorts: $25.6M
= 49.4% of shipped revenue. Buffer simulation shows 86% recovery at
95% fill rate with deauthorization cliff at 90%. 35/35 validation
checks pass. Three databases (cinderhaven_extract.db, short_ship_orders.db,
short_ship_cost.db) documented in docs/cost-engine-docs.md.
