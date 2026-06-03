# short-ship-cost — Handoff Log

Session-by-session state. Updated by /log mid-session and /wrap at
session end.

For durable choices, see DECISIONS.md.
For the current work arc, see PLAN.md.
For things that didn't work, see FAILURES.md.

---

## 2026-05-20 — DS v2 brand kit, review fixes, polish

**Started from:** Project deployed and feature-complete. Requested Lailara DS v2 brand kit migration and code review.

**Did (7 commits, all deployed):**
1. Migrated all visual tokens to Lailara DS v2 — Hong Kong teal ramp, Chicago-20 accent, Red-42 brand red, London greyscale. 8 files changed.
2. Ran 6-agent code review, fixed all 7 findings (missed file, hardcoded hex values, red-as-background violation, unused tokens, missing semantic token).
3. Regenerated OG card with DS v2 palette (2x retina).
4. Fixed OG/README rounding — $33.2M → $33.1M to match what `Intl.NumberFormat` compact actually produces from $33,128,550.93.
5. Fixed SKU table column header overlap — switched from `.split(' ')[0]` to `DIMENSION_LABEL_SHORT`, removed `white-space: nowrap`.
6. Fixed margin benchmark logic — old calc divided total cost ($33.1M including lost revenue) by realized margin ($18.6M) = 178%, which is logically incoherent. Now shows cascading costs only ($9.5M) / realized margin = 51.3%.
7. Fixed SKU table horizontal scroll — tightened column widths to fit 852px container (was 1130px).
8. Updated parent `~/projects/active/CLAUDE.md` from DS v1 to DS v2 color tables (not in git — shared instruction file).

**State:** Fully deployed at https://shortships.lailarallc.com. Build clean. All DS v2 tokens applied, zero old palette values remaining. No known issues.

**Next:** Project is ship-ready. Only remaining optional item: real-device mobile testing on an actual phone.

---

## 2026-05-22 — wrap

**Started from:** Project fully deployed and ship-ready after DS v2 migration (2026-05-20). No open issues.

**Did:** Status check only. Confirmed project is ship-ready. Fixed stale PLAN.md checkboxes — Waves 1-4 and definition-of-done items were completed but never marked done.

**State:** Deployed at https://shortships.lailarallc.com. Build clean, 34/34 tests pass, DS v2 tokens applied. No known issues. All PLAN.md tasks and DoD items now marked complete.

**Next:** Project is shipped. Only optional item: real-device mobile testing on an actual phone. Otherwise, this project is done.

---

## 2026-05-17 16:15 — Full audit + data resync + deploy

**Started from:** Pipeline rebuilt (commit 6ee429b) with new cinderhaven-data but web app JSON never re-exported. Tool displayed $25.6M while databases held $33.2M.

**Did:** Ran 4-phase audit (AUDIT.md updated). Identified single root cause: missed `export_json.py` step. Re-exported JSON, updated hardcoded numbers in OG tags/methodology/README, deleted obsolete `add_kehe.py`, rewrote stale data/README.md. Tests 34/34, build clean. PR #7 merged and deployed to Cloudflare Workers.

**State:** Fully deployed at https://shortships.lailarallc.com with correct data ($33.2M, 50 SKUs, 66K orders, 3-year window). All definition-of-done criteria met. No known issues.

**Next:** Project is ship-ready — share with the prospect. Optional: regenerate OG card image to show $33.2M instead of $25.6M; real-device mobile testing on an actual phone.

---


## 2026-05-17 — Dataset realism alignment (from dataset-realism-improvement session)

**Started from:** DOWNSTREAM_AUDIT.md flagged short-ship-cost as
HIGH priority — hardcoded dates, SKU counts, and annualization
divisors all stale after the cinderhaven-data rebuild (50 SKUs,
157-week window, KeHE wholesale column added).

**Did:**
- Updated SRC paths from `published/` to `active/` cinderhaven-data
  (extract_cinderhaven.py, extract_velocity.py)
- WEEKS_IN_WINDOW: 104 → 157 (extract_velocity.py, deauthorization.py)
- WINDOW_START/END: 2024-05-11..2026-05-02 → 2024-01-06..2027-01-02
  (generate_orders.py, validate_cost_engine.py)
- Annualization divisor: /2.0 → /3.0 across 4 files (deauthorization.py,
  runner.py, export_json.py, validate_orders.py)
- KeHE wholesale: wholesale_unfi → wholesale_kehe via WHOLESALE_COL
  lookup (generate_orders.py)
- Table rename: retailer_requirements → retailer_rules (extract + docs)
- SKU count 90 → 50 in CLAUDE.md, AUDIT.md, data/README.md,
  docs/cost-engine-docs.md, extract_velocity.py docstring
- Rebuilt full pipeline: extract → velocity → orders → triage →
  DTC outcomes → returns → cost engine → buffer simulation
- Cost engine validation: 35/35 passed
- Order validation: 24/25 passed (1 statistical n=1 edge case)

**Key numbers post-rebuild:**
- 50 SKUs, 157-week window (Jan 2024–Jan 2027)
- 66K orders, 191K lines, $100.8M demand ($33.6M/yr)
- Shipped revenue: $24.7M/yr (matches ~$25M target)
- Total cost of shorts: $33.2M (44.7% of shipped)

**State:** short-ship-cost fully aligned with rebuilt cinderhaven-data.
Not yet committed.

**Flag:** `scripts/add_kehe.py` may be obsolete now that KeHE is
native in upstream data. Review separately.

**Next:** Commit these changes. Then continue downstream fixes per
DOWNSTREAM_AUDIT.md priority order: product-data-health-audit (HIGH),
contract-to-cash (MEDIUM), retailer-deduction-recovery (LOW-MED),
channel-profitability-analysis (LOW), trade-spend-data-diagnostic
(LOW), retail-velocity-decision-tool (LOW).

---

## 2026-05-07 — Project initialized

**Started from:** New project setup. 95% confidence interview
completed in chat.

**Did:** Ran full project interview covering business case, domain
context, cost dimensions, retailer ordering patterns, triage logic,
data requirements, tool/tech choices, and portfolio positioning.
Created CLAUDE.md, DECISIONS.md, HANDOFF.md, PLAN.md, FAILURES.md,
and chat project instructions. Six initial decisions captured.

**State:** All workflow docs created and ready to copy into repo.
Repo exists on GitHub (private, empty). No code yet. First arc
defined in PLAN.md: synthetic order data + cost engine.

**Next:** Copy workflow files into repo, set up slash commands,
first commit. Then begin first PLAN.md task: determine Cinderhaven
data consumption approach (full DB vs. self-contained extract).

---

## 2026-05-07 17:35

**What changed:** Completed PLAN task 1 — extracted 8 Cinderhaven tables (14,595 rows, 1.61 MB) into `data/cinderhaven_extract.db` via re-runnable `scripts/extract_cinderhaven.py`; added `data/README.md`.

**Why:** Self-contained extract was the chosen approach so the portfolio piece runs standalone without the 172 MB upstream DB. Schema, PKs, NOT NULL flags, and indexes preserved verbatim from source; cross-table joins verified.

**State:** Working — extract round-trips cleanly, joins (`product_master ⨝ sku_costs`) return expected rows. `sku_costs` already has all 6 retailer-specific wholesale prices and channel trade-spend rates; both MSRP and `wholesale_dtc` present, so DTC margin-leakage math is feasible out of the box. Existing `chargebacks` is historical actuals (~$88K, 18 mo), not a fine-schedule lookup. Untouched: order data, OTIF schedule, DTC cancellation/triage/deauth/distributor params, Walmart/Costco DC dimension — all explicitly out of scope for task 1.

**Next:** PLAN task 2 — design the synthetic order data model (schema for `original_orders`, `shipped_orders`, and the linkage between them) reflecting retailer-specific ordering patterns.

---

## 2026-05-07 18:48

**What changed:** Wrote `docs/order-data-schema.md` (six new tables) and `docs/cost-engine-benchmarks.md` (OTIF, fill rates, DTC cancellation, distributor returns, triage labor). Committed at `0c33f80`.

**Why:** PLAN task 2 — design the synthetic order data model and capture default cost-engine parameters before any code is written. Documentation only; nothing is built yet.

**State:** Working — schema spec covers `orders`, `order_lines_original`, `order_lines_shipped`, `order_shorts`, `dtc_outcomes`, `distributor_returns`, with linkage on `(order_id, sku)` and `order_line_id` as a per-table surrogate. Benchmarks doc lists Walmart/Costco/Whole Foods/UNFI/KeHE/Regional fine rules, channel-specific fill rates, the DTC hold-duration cancellation curve and 35/65 leakage split, 12%/5% distributor return rates, and 20-min × $30/hr × 90% triage labor. Untouched: order generators, OTIF compute, no synthetic data created. Three open implementation questions flagged in the schema doc (cache vs. recompute `quantity_shorted`; deliberate duplication of `unit_price`; one-line-per-SKU-per-order assumption).

**Next:** PLAN task 3 — design the short / triage logic that decides how original orders get edited down (priority hierarchy, due-date, completeness pressure, even-small-orders-shorted dynamic).

---

## 2026-05-07 19:04

**What changed:** Wrote `docs/triage-logic.md` (committed at `a4e896f`). Five-step weekly algorithm — production-as-supply sized to ~75% of demand, tier+due-date+completeness queue, top-down allocation, deliberate noise, separate DTC hold-for-complete path.

**Why:** PLAN task 3 — the order generator (task 4) needs a single canonical description of how the triage edits original orders down before any code is written. Doc also carries the user's framing note that the human triager is not the problem.

**State:** Working — algorithm spec is complete and consistent with the schema (task 2) and the benchmarks (task 2). Untouched: order generators, velocity rollup, fine compute, no synthetic data created. Four implementation parameters explicitly flagged as TBD in the doc itself (velocity source, completeness measure, noise frequencies, production stochasticity); these get resolved during PLAN task 4.

**Next:** PLAN task 4 — write the order generation scripts. First decision will be the velocity-input source (re-attach upstream scan_data vs. add a derived rollup table to the extract vs. flat file).

---

## 2026-05-07 20:40

**What changed:** PLAN task 4 — full synthetic order pipeline landed end-to-end. Six sub-tasks: sku_velocity rollup, generate_orders, KeHE split + retune, run_triage, generate_dtc_outcomes (+ ship_date NULL fix on cancelled DTC), generate_returns, validate_orders. Commits 3325335 → abc4762.

**Why:** This data layer underpins everything downstream — cost engine, interactive tool, narrative. Had to actually generate it before any analysis could mean anything.

**State:** Working — 43,110 orders, 125,748 lines original/shipped (1:1), 30,915 retail/distributor shorts, 38,792 dtc_outcomes, 32 distributor_returns. $51.9M shipped over 2 yr ($25.9M/yr, inside the $23-27M Cinderhaven target). Original demand +36% over shipped (mid-band of 25-40%). validate_orders.py runs 25 checks and all pass: channel fill rates ±3pp of target, channel revenue share ±3pp, promo-order alignment 100%, DTC cancel curve within ±7pp of doc, distributor returns within ±1pp of 12%/5%, no auth violations or invalid quantities. Algorithm departure flagged: strict tier priority + noise (per docs/triage-logic.md) does not land the documented fill targets with our synthetic demand because Costco's narrow SKU set overlaps Walmart's and Costco's generated case quantities exceed total brand supply on some authorized SKUs; switched to direct target-driven allocation with per-line Gaussian noise — user accepted when surfaced. Untouched: cost engine (PLAN task 5), buffer simulation (task 6), validation against Cinderhaven scan data (task 7), data-model documentation refresh (task 8).

**Next:** PLAN task 5 — build the cost engine that calculates the eight cost dimensions (lost revenue, OTIF fines, chargebacks, deauth risk, DTC cancellations, DTC-to-retail margin leakage, distributor returns, triage labor) from the order gap. All inputs are now in place.

---

## 2026-05-07 21:10

**What changed:** PLAN task 5 — cost engine across all 8 dimensions landed under `scripts/cost_engine/` (parameters.py, common.py, 8 modules, runner.py). Output materialized into new `data/short_ship_cost.db`. Commits c9e6a7c → 4f5d433.

**Why:** This converts the order data into the cost story — the whole reason the order data exists. Each dimension is its own module so the interactive tool can show / let users tune any one.

**State:** Working — engine produces $25.6M total cost of shorts on $51.9M shipped revenue (49.4% of shipped). Stack: lost_revenue $18.7M (36.1pp), deauthorization $5.86M (11.3pp), otif_fines $826K, chargebacks $75K, dtc_cancellations $50K, triage_labor $39K, distributor_returns $24K, dtc_margin_leakage $5K. Six output tables: cost_summary (8 rows), cost_by_retailer (33), cost_by_sku (404), cost_by_month (160), deauthorization_events (127), cost_parameters (26 — every tunable parameter). Doc updated: cost-engine-benchmarks.md UNFI line corrected to 3% of shorted goods value (was 2% of COGS) per task 5 spec. Untouched: buffer simulation (PLAN task 6), validation pass against Cinderhaven scan data (task 7), data-model documentation refresh (task 8), interactive tool (next arc).

**Next:** PLAN task 6 — add the buffer simulation layer. "What if fill rate moved from X% to Y%" recalculates every cost dimension at the new fill level and shows the recovery, framed as fine avoidance not production planning.

---

## 2026-05-07 21:16

**What changed:** Validation pass over cost engine outputs — DTC event counts, triage labor math, deauthorization concentration. No code or data changed.

**Why:** User flagged that DTC ($55K total) and triage ($39K) looked small, and wanted to confirm deauthorization ($5.86M) wasn't driven by 1–2 outliers.

**State:** All four numbers check out. DTC: 925 cancelled-by-customer + 484 purchased-in-store on 38,792 orders = 96.4% ship-complete; cost is correctly small because DTC is ~3% of revenue and ships nearly complete. Triage: 4,318 retail+distributor orders × 0.90 × $10 = $38,862 exactly. Deauthorization: 127 events (24 velocity-based, 103 distributor-consecutive-months); top 10 events = 42% of $5.86M total — meaningful concentration without being a 1–2 outlier story. Walmart's 2 events ($795K) are the clean small/outsized pattern; UNFI/KeHE's 103 events surface the chronic-low-fill narrative the project is built to make visible. Untouched: PLAN tasks 6–8.

**Next:** PLAN task 6 — buffer simulation layer.

---

## 2026-05-07 21:28

**What changed:** PLAN task 6 — buffer simulation across 80/85/90/95% target fill rates landed. `scripts/cost_engine/buffer_simulation.py` at commit `78a8808`; three new tables in `short_ship_cost.db`: `buffer_scenarios`, `buffer_scenario_details`, `buffer_deauth_recovery`.

**Why:** This is the "what would even modest fill-rate improvement save?" lever — framed as fine avoidance, not production planning. Required for the interactive tool's headline scenario comparison.

**State:** Working — total cost of shorts $25.6M baseline → $18.0M / $15.9M / $9.8M / $3.6M at 80/85/90/95% scenarios (86% recovery at 95%). Implementation copies orders DB to temp per scenario, lifts qty_shipped via `max(current, round(qty_ordered × target))`, flips proportional DTC cancellations back to shipped_complete, monkey-patches `common.ORDERS_DB` to point modules at the temp file, then cleans up. Existing dimension modules and `short_ship_orders.db` untouched. 4 of 5 validation criteria pass cleanly: lost-revenue recovery is proportional, deauth staircase clears at 90% threshold (125 of 127 events avoided at 95%), DTC cancellations decrease monotonically, triage labor stays flat. The 5th — "OTIF fines mostly disappear at 95%" — only achieves 38% reduction because Walmart's 98% line-level threshold isn't crossed by 95% lift; honest result, flagged in code and commit. Untouched: PLAN tasks 7 (validation pass) and 8 (data-model documentation).

**Next:** PLAN task 7 — validate the synthetic order data and cost engine against Cinderhaven's existing scan data and revenue benchmarks. Confirm the numbers tell a coherent story end-to-end before the interactive tool arc.

---

## 2026-05-07 22:12

**What changed:** PLAN tasks 7 + 8 — `scripts/validate_cost_engine.py` (35 PASS/FAIL checks across 9 sections, all passing) and `docs/cost-engine-docs.md` (interactive-tool reference). Commits `0796f2f` and `d8ea5e5`.

**Why:** Last gates before the interactive tool arc — confirm the order/cost data is internally consistent and document the schema so the tool developer can consume it without ambiguity.

**State:** Working — 35/35 checks pass: impossible values, FK integrity, duplicates, distribution sanity, cost-engine reconciliation, boundary, buffer baseline reproduction, OTIF threshold logic, deauth event integrity. Two issues surfaced and fixed during validation: (1) 45 retail/distributor orders had `ship_date < order_date` because `monday_of(due_date)` could go 6 days back when `due_date` was Sunday; fixed in `run_triage.py` with `max(week_monday, order_date)` and DB rows patched. (2) Buffer simulation didn't reproduce baseline at current fill rate; fixed by short-circuiting `recover_retail_shorts` and `recover_dtc_outcomes` when `target_fill <= current_fill`. Active-SKU check tightened to "well-established" — two late-launch SKUs (CHP-0054, CHP-0067) were authorized only in the final 5 weeks and had no orders; documented as realistic, not a defect. `docs/cost-engine-docs.md` covers DB inventory, every cost-DB table schema, cross-DB join paths, per-dimension definitions tied to `cost_parameters`, buffer-simulation algorithm and reading, and the honest known-limitations list. **PLAN arc complete.** Untouched: interactive tool (next arc).

**Next:** Begin the interactive tool arc — React or polished HTML/JS app per `DECISIONS.md`, hosted on Netlify or GitHub Pages, consuming the three SQLite files via the schema documented in `docs/cost-engine-docs.md`. First step is a new `PLAN.md` arc definition.

---

## 2026-05-07 22:20 — wrap

**Started from:** Project freshly initialized. CLAUDE.md, PLAN.md, HANDOFF.md, DECISIONS.md, FAILURES.md scaffolded earlier in the day. PLAN task 1 ("determine Cinderhaven data consumption approach") was first up.

**Did:** Worked through the entire eight-task PLAN arc in one extended session — Cinderhaven extract with synthesized KeHE distributor; schema, triage, and benchmarks docs; full synthetic order pipeline (orders, lines, shorts, DTC outcomes, distributor returns); modular cost engine across all eight dimensions with output in `data/short_ship_cost.db`; buffer simulation across 80/85/90/95% scenarios; 35-check validation script; and `docs/cost-engine-docs.md` as the single reference for the next arc. Settled on direct target-driven allocation in triage after three failed attempts (strict priority, noisy-tier scoring, fair-share with tier weights). Settled on per-(sku, week) supply-scaled allocation in the cost engine. Captured two new firm decisions for the interactive tool (React + JSON data delivery).

**State:** PLAN arc complete. Three SQLite DBs working and committed: `cinderhaven_extract.db` (1.6 MB), `short_ship_orders.db` (22 MB), `short_ship_cost.db` (0.5 MB). 35/35 validation checks pass. Headline: $25.6M total cost of shorts on $51.9M shipped revenue (49.4%); buffer simulation recovers 86% at 95% scenario. Open opinion items deferred to the tool arc: export mechanism (jsPDF / html2pdf / print-CSS), single page vs multi-view, hosting (Netlify vs GH Pages).

**Next:** Define a new PLAN.md arc for the interactive tool. Three open sub-decisions to settle before code: export mechanism, single-page vs multi-view, and Netlify vs GH Pages. React + JSON delivery already locked in (this wrap commit).

---

## 2026-05-08 — Arc 2 planning session

**Started from:** Arc 1 complete (tagged v0.1-data-and-cost-engine).
All eight tasks done, 35/35 validation, three DBs, docs written.

**Did:** Worked through all open decisions for the interactive tool
arc. Settled React (Vite), pre-computed JSON, Netlify, print CSS,
single scrollable page, Recharts. Drafted and reviewed PLAN.md arc 2
with Gemini adversarial review. Key additions from review: print
compatibility spike in task 1, validation.json in JSON export,
useMemo for parameter panel performance, dynamic deauthorization
threshold slider, "Other" category in drill-down aggregations,
print footer with snapshot metadata.

**State:** PLAN.md updated with arc 2. DECISIONS.md updated with six
new entries. No code written yet — arc 2 is planning-complete,
ready to build. First task is React scaffolding + Netlify deploy +
print spike.

**Next:** Begin task 1 — Vite + React scaffold, Netlify pipeline,
print compatibility spike with one Recharts SVG chart.

---

## 2026-05-08 11:05

**What changed:** PLAN arc-2 task 1 done — Vite + React app scaffolded
in `web/`, `web/netlify.toml` added, print-CSS spike rendering a
Recharts BarChart with window.print() — all three print checks
passed in Chrome. Commits 9258621 → 80f728e → f0efb85.

**Why:** Task 1 of the interactive-tool arc: prove the
local → GitHub → Netlify → print-PDF pipeline works end-to-end
before building any actual sections. Recharts' SVG output is the
piece that determines whether the print-CSS export decision holds.

**State:** Working — `npm run build` produces a 562 KB bundle
(159 KB gzipped, Recharts is ~370 KB of that — flag for code-split
later if it matters). `npm run dev` serves cleanly. Print preview
in Chrome rendered the BarChart as crisp SVG, hid the print button,
and scaled to the letter page. Vite default scaffold trimmed
(removed react/vite/hero assets, simplified App.css/index.css to a
neutral baseline). `web/netlify.toml` has base="web", command="npm
run build", publish="dist", NODE_VERSION=20, and a SPA-fallback
redirect. **Not yet deployed** — user will manually connect the
repo to Netlify and trigger the first build. Untouched: arc-2
tasks 2-11.

**Next:** User connects repo to Netlify (set Base directory to `web`
in the UI; the toml in `web/` handles the rest) and triggers the
first deploy. Once a public URL exists, begin task 2 — JSON export
script that reads the three DBs and outputs pre-aggregated data +
validation.json for the React app.

---

## 2026-05-08 11:32

**What changed:** PLAN arc-2 task 2 done — `scripts/export_json.py`
emits 8 pre-aggregated JSON files (81.5 KB total) under
`web/public/data/`: meta, cost_summary, cost_by_retailer,
cost_by_month, cost_by_sku, deauthorization_events,
buffer_scenarios, validation. Commit `077501c` pushed.

**Why:** The React app needs summary-level data, not raw order
lines. Pre-aggregating in Python keeps the browser fast, lets the
JS cost-math be tested against `validation.json`, and bundles the
parameter defaults the reset-to-baseline button restores.

**State:** Working — script is idempotent (deletes prior \*.json,
rewrites them) and prints a per-file size table plus a sanity check
(cost_summary total == validation total, $25,597,978.19, PASS). All
26 cost_parameters embedded in meta.json. cost_by_sku is top-20 +
"Other (62 SKUs)"; sum reconciles to $25,559,116.17 = headline minus
triage_labor (which has no SKU attribution by design — flagged in
the script docstring and inline). Percentages emitted as fractions
(0.36 not 36); dollars rounded to 2 dp, percentages to 4 dp. JSON
files are committed so Netlify has them at build time. Untouched:
arc-2 tasks 3-11 and the Netlify deploy connection.

**Next:** Task 3 — wireframe the page structure and visual language
(documented spec, not code). Builds Sections 1-4 reference this.

---

## 2026-05-08 11:57

**What changed:** PLAN arc-2 task 3 done — `docs/design-spec.md`
added (178 lines): page structure, typography (Playfair + Source
Sans Pro), color palette + dimension mapping, Economist chart
rules, per-section spec for Sections 1-4, parameter panel,
layout, print layout. Commit `6787b70` pushed.

**Why:** Tasks 4-9 build Sections 1-4 plus the parameter panel
and print CSS. They reference this spec for chart types, colors,
typography, copy voice, and layout instead of reinventing each.
Doc only — no code changed.

**State:** Working — spec is the agreed starting point, explicitly
non-locking ("Chart types and layouts may be adjusted after seeing
how they render"). Dimension color groups: navy/steel-blue/red/warm-
gray/light-gray, with related dimensions sharing a color (OTIF +
chargebacks; DTC cancellations + DTC leakage; distributor returns +
triage labor) — keeps the cost stack readable. Parameter panel is
specified as a non-reflowing 320px sidebar with sliders bound to
`cost_parameters`, validating against the JSON exported in task 2.
Untouched: arc-2 tasks 4-11 and the Netlify deploy connection.

**Next:** Task 4 — build Section 1 (the headline cost stack):
$25.6M callout, waterfall chart of the eight dimensions, contextual
benchmarks below. Pulls from `cost_summary.json` and `meta.json`.

---

## 2026-05-08 14:21

**What changed:** PLAN arc-2 task 4 done — Section 1 built as a
custom-SVG flow-split chart (left total block, sankey curves, right
blocks min 20px), sequential teal palette swapped in globally, and
a global time-range filter (Header dropdown + custom month inputs)
wired to all sections via React Context. Commits `fa0e56c` and
`acbf08e` pushed.

**Why:** Section 1 is the first thing a visitor sees. Spent the
session iterating on the chart form (waterfall → 2-tier → single
horizontal stack → vertical stack → flow-split) until composition
read at-a-glance. Added the filter so every downstream section
inherits time-range semantics without re-plumbing.

**State:** Working — `npm run build` clean, dev server at
:5178. Components: `Header`/`FilterBar`/`CostStack` plus
`lib/timeRange.jsx` (Context + `filterByMonth` helper).
`scripts/export_json.py` now also emits `orders_by_month.json`
(monthly shipped + demand). Filter recomputes total, dimension
breakdown, shipped/demand/fill, benchmarks. Deauthorization is
omitted under filter (events are SKU/retailer-level, not monthly)
with a footnote; buffer simulation will share the same caveat.
Hover dims non-selected flows; subtitle becomes a contextual
tooltip. `docs/design-spec.md` updated to document the teal
palette. Untouched: arc-2 tasks 5-11 and the Netlify deploy hookup.

**Next:** Task 5 — Section 2 (Where the Pain Lands): grouped
horizontal bar by retailer × dimension, top-20 SKU table with
"Other" row. Both will need to be filterable; `cost_by_retailer`
and `cost_by_sku` JSON currently lack monthly breakdown, so first
sub-step is extending `export_json.py` to add per-month variants
or accept the static-table tradeoff.

---

## 2026-05-08 17:56

**What changed:** PLAN arc-2 task 5 done — `cost_by_retailer.json`
now (dimension × retailer × month), `cost_by_sku.json` carries
`by_month` + `by_retailer` per row, and `RetailerDrilldown`
component renders a custom-SVG stacked-bar chart (12px min segment,
hover-breakdown chips) plus a sortable top-20 SKU heatmap table.
Commits `729d571`, `b536c12`, `fb37899` pushed.

**Why:** Section 2 is the drill-down from the headline. Adding
monthly granularity to retailer/SKU JSON lets the global
time-range filter flex Section 2 the same way it flexes Section 1.

**State:** Working — `npm run build` clean (212 KB / 67 KB gz),
Recharts no longer imported anywhere (custom SVG throughout). Cost
engine `aggregate_breakdowns` extended with `by_retailer_month`,
`by_sku_month`, and `by_sku_retailer` (additive — runner ignores
extras). Export script imports cost engine modules and runs them
once per export to capture the new aggregates. Bundle JSON now
253 KB (cost_by_sku is the bulk at 107 KB). Validation still
35/35 pass; `cost_summary` total reconciles. Section 2 chart click
filters the SKU table; sort headers work; heatmap shading uses
teal alpha (text always dark per request); Other row consistent
with the rest of the table. Untouched: arc-2 tasks 6-11 and the
Netlify deploy hookup.

**Next:** Task 6 — Section 3 (The Trend): monthly time series
across the 18-24 month window, stacked area chart by dimension,
declarative title based on whether costs are stable, growing, or
seasonal. Already has the data — `cost_by_month.json` is the input.

---

## 2026-05-08 18:14

**What changed:** PLAN arc-2 task 6 done — `TimeSeries` component:
Recharts stacked area, 7 monthly-attributed dimensions, dynamic
trend title (rising/eased/steady from first-half vs second-half
average), per-month tooltip with full breakdown, three stat blocks
(monthly avg, peak month, low month). Commit `9ad3133` pushed.

**Why:** Section 3 answers whether the cost-of-shorts story is
getting worse, stable, or seasonal. The dynamic title puts the
finding in plain English; the stat blocks reinforce with numbers.

**State:** Working — `npm run build` clean (600 KB / 170 KB gz —
Recharts back in the bundle for the AreaChart). Honors the global
time filter; recomputes title and stats on filter change. Layer
heights enforce a 12px minimum (~4% of plot area at peak month) so
small dimensions like DTC leakage stay visible against
lost_revenue. Y-axis shows padded scale; tooltip preserves real
values; footnote calls out the discrepancy. Deauthorization
omitted (events are SKU/retailer-level, not monthly), consistent
with Sections 1/2. Untouched: arc-2 tasks 7-11 and the Netlify
deploy hookup.

**Next:** Task 7 — Section 4 (What Recovery Looks Like): buffer
simulation staircase from `buffer_scenarios.json`, four scenarios
(80/85/90/95% fill rate), baseline reference at $25.6M, deauth
cliff annotation at 90%. Note that buffer_scenarios is full-period
only — when a time filter is active, show a note (same pattern as
deauth in Section 1).

---

## 2026-05-08 20:08

**What changed:** PLAN arc-2 task 7 done — Section 4 buffer
staircase shipped, plus three cross-cutting changes that reach all
four sections: shared `PinnedCallout` (dark card, click-to-pin
everywhere, hover tooltips removed), global dimension-toggle chips
in a header bar (excluded chips dashed + strikethrough), and
React.lazy code-split for the three Recharts-heavy sections so
Recharts ships in its own ~370 KB chunk after first paint. Also
forced `Intl.NumberFormat` to 2-decimal compact currency.
Commit `f220cc2` pushed.

**Why:** The user iterated on the Section 4 callout messaging
(two-step deauth narrative), then asked for click-to-pin to match
across all charts as the canonical interaction, plus dim toggles
because "what does the cost look like *without* deauth" is a
common question. Code-splitting cleared the build-time 500 KB
warning and improves first paint.

**State:** Working — `npm run build` clean, no chunk warnings.
Initial JS 208 KB / 66 KB gz; Recharts split to a 371 KB / 99 KB
gz lazy chunk that loads after Section 1 paints. `PinnedCallout`
is the canonical interaction surface across Sections 1-4: hover
no longer triggers tooltips, click pins a dark callout above the
chart with `Pinned — click again to unpin` hint and (where it
applies) a per-dimension breakdown. `DimensionToggle` lives in
its own bar below the header; toggle state is in
`TimeRangeContext.activeDims` and propagates to every section's
charts/tables/callouts/footnotes. Section 4 cliff callout hides
when deauthorization is toggled off. Untouched: arc-2 tasks 8-11
and the Netlify deploy hookup.

**Next:** Task 8 — parameter adjustment panel (collapsible right
sidebar with sliders for OTIF rates, deauth thresholds, distributor
fill threshold, DTC margin, triage cost). Sliders bind to
`meta.cost_parameters`; recompute via `useMemo`; reset-to-baseline
button; validate JS math against `validation.json`.

---

## 2026-05-08 20:37

**What changed:** PLAN arc-2 task 8 done — `ParameterPanel`
sidebar (collapsible, scrim, 360px) with sliders for OTIF,
deauth thresholds, margins, triage, chargebacks. Backed by
`utils/costEngine.js` which scales pre-aggregated JSON by
parameter ratios and re-filters deauth events on threshold
change; `AppShell` derives a single `scaled` data bundle that
all four sections consume. Validation indicator compares JS
totals to `validation.json`. Commit `c6d0c7f` pushed.

**Why:** Slider tweaks turn the tool from a static report into a
simulator. The "what if Walmart's threshold were 85%" question is
the lever a buyer/operator would actually pull, and the panel makes
that pull immediate.

**State:** Working — `npm run build` clean. Initial JS 218 KB /
69 KB gz; Recharts still in its 371 KB lazy chunk. `params` and
`baselineParams` live in `TimeRangeContext`; `paramsModified` is
exposed for the modified-dot indicator and the print footnote.
Reset-to-baseline button enabled only when modified. Validation
runs on first load and any time params equal baseline; on
mismatch, console.warn fires and panel shows ⚠. Buffer scenarios
use ratio scaling (approximation flagged in code comment); deauth
threshold lowering removes events accurately, raising velocity
thresholds is bounded by the events captured at baseline (limitation
inherent to shipping aggregates instead of raw orders). Untouched:
arc-2 tasks 9-11 (print CSS export, polish, Netlify deploy).

**Next:** Task 9 — print CSS export. Hook `window.print()` to a
stylesheet that hides parameter panel/filter chrome, paginates
sections cleanly, includes a footer with date and parameter
modifications snapshot.

---

## 2026-05-08 21:06

**What changed:** PLAN arc-2 task 9 done — print CSS in `App.css`
plus structural tweaks: per-page footer via `@page @bottom-left/right`
(brand text + page counter), section page breaks, staircase + cliff
kept together via wrapper, "Top products by cost" forced to a fresh
page using a global `.print-break-before` class. Header print
handler swaps `document.title` for a clean PDF filename and toggles
a `.printing` body class. Commit `b2d8e13` pushed.

**Why:** PDF export is what makes the tool client-shareable. Without
clean pagination it reads as a screen capture, not a document.

**State:** Working — `npm run build` clean. Print CSS hides
parameter panel, dim toggles, filter bar, print button, dark
pinned-callout cards, and "click to pin" instructional text. Print
metadata strip shows generation date + parameter state (lists which
params changed when modified). All four sections paginate; charts
stay together (`break-inside: avoid`); SKU table header repeats on
continuation pages (`thead { display: table-header-group }`).
`@page` rule sets letter / 0.6"-margin / running footer with brand
+ page counter. Sub-pixel limitation of `[class*='Module_xxx']`
selectors discovered (CSS-modules hash format isn't stable) and
worked around with global `.print-break-before` class. Untouched:
arc-2 tasks 10-11 (polish, Netlify deploy).

**Next:** Task 10 — polish pass. Walk each section, fix loading
states, edge cases, accessibility basics, final visual tuning.
Then task 11 — Netlify deploy with README link.

---

## 2026-05-08 21:08 — wrap

**Started from:** Arc 2 just defined; nothing built. PLAN.md
arc-2 listed 11 tasks.

**Did:** Built tasks 1-9 of arc-2 in one extended session: Vite +
React scaffold, JSON export with monthly granularity, design spec,
Section 1 (custom-SVG flow chart, ~5 form iterations to land on
flow-split), Section 2 (retailer + SKU heatmap), Section 3
(stacked area), Section 4 (buffer staircase + cliff callout).
Cross-cutting: global time-range filter (preset + custom),
extended cost-engine `aggregate_breakdowns` for retailer × month
and sku × month, shared dark `PinnedCallout` for click-to-pin
across all charts (no hover tooltips), global dimension-exclude
chips, React.lazy code-split (Recharts now lazy 371 KB),
parameter sidebar + JS scaling cost engine, print CSS with
paginated sections + repeating footer.

**State:** 9/11 arc-2 tasks complete. App live in dev mode at
:5178. Bundle 218 KB initial / 371 KB Recharts lazy. JS validation
matches `validation.json` baseline. Netlify config in place but
**not yet deployed**.

**Next:** Task 10 — polish pass (loading states, accessibility,
edge cases, visual tuning). Then task 11 — Netlify deploy + README
link.

---

## 2026-05-15 12:45

**What changed:** Completed all 27 tasks across 5 waves — tool transformed from dashboard to self-selling argument. PR #2 created and pushed.

**Why:** Audit found the analytical core is unique but presentation was too dashboard-y for a cold prospect (CEO, MBA, opens on phone). Every wave targets one part of that gap: narrative framing, insight lines, methodology appendix, cost engine tests, animations, and mobile layout.

**State:** Working — build clean, 34/34 tests pass, PR open at MsShawnP/short-ship-cost#2. Self-hosted fonts, animated number transitions (250ms, prefers-reduced-motion), Recharts chart animations, mobile bottom-sheet parameter panel, responsive breakpoints at 640px. Palette evaluated and kept (deltaE 8.7–15.5 between adjacent pairs). OG image placeholder referenced but not yet created.

**Next:** Merge PR #2 and deploy to Cloudflare Pages. Create the OG card image (`og-card.png`). Then real-device mobile testing on an actual phone.

---

## Session — 2026-05-15 (visual polish)

**Phase:** Build it right (Phase 2, step 7)
**Goal:** Fix dimension toggle chip layout and run mobile polish pass.
**Completed:** Full /clarify → /ce:brainstorm → /ce:plan → /ce:work workflow. Extracted Lailara design system to ~/projects/active/CLAUDE.md. Restructured DimensionToggle into label row + CSS grid (4x2 desktop, 2x4 mobile). Mobile polish: PinnedCallout stacks to 1 column, 44px touch targets on all buttons. Centered benchmark/stat grid values. PR #4 merged and deployed to Cloudflare Workers.
**Tried, didn't work:** Preview screenshot tool timed out every attempt — used preview_eval and preview_snapshot instead.
**State:** PR #4 merged. One extra commit (centering) on fix/visual-polish-dimension-toggle branch pushed but not yet merged to master.
**Next concrete action:** Merge the centering commit to master (open a new PR or merge directly), then redeploy.
**Blockers:** None

---

## Session — 2026-05-15 — wrap

**Phase:** Build it right (Phase 2, steps 7–9)
**Goal:** Transform the tool from a dashboard to a self-selling argument across 5 waves (27 tasks).
**Completed:** Wave 4 tests (34/34 pass), Wave 5 animations (useAnimatedValue hook, Recharts animation, prefers-reduced-motion), palette evaluation (keep — deltaE 8.7–15.5), mobile layout (640px breakpoints, bottom-sheet parameter panel, 44px touch targets). PR #2 created and pushed.
**Tried, didn't work:** Nothing notable. Preview screenshot tool timed out (known limitation), worked around with eval/inspect.
**State:** All 27/27 tasks complete. PR #2 open at MsShawnP/short-ship-cost#2. OG card image still a placeholder.
**Next concrete action:** Merge PR #2 and deploy to Cloudflare Pages. Create og-card.png.
**Blockers:** None

---

## 2026-05-16 15:38

**Started from:** Project feature-complete after 3 arcs + visual polish pass. All PRs merged. Requested fresh full audit.

**Did:** Ran 4-phase audit reassessment. 12/13 prior findings resolved. Found OG image uses relative path (social crawlers can't resolve). Fixed to absolute URL. Refreshed AUDIT.md.

**State:** Committed on worktree branch. OG fix applied. Not yet deployed — needs `npm run deploy`.

**Next:** Deploy the OG fix (`cd web && npm run deploy`). Project is then ready to share with the prospect. Optional: error boundaries (15 min), GitHub Actions CI (30 min).

---
