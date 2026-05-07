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
