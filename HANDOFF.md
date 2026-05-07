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
