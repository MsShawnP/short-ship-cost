# short-ship-cost — Handoff Log

Session-by-session state. Updated by /log mid-session and /wrap at
session end.

For durable choices, see DECISIONS.md.
For the current work arc, see PLAN.md.
For things that didn't work, see FAILURES.md.

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
