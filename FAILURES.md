# short-ship-cost — Failure Log

What was attempted that didn't work, why it didn't work, and what was
tried next.

Lower bar than DECISIONS.md — capture failures even when they didn't
produce a durable rule. The whole point: future-you (or future-Claude)
shouldn't re-attempt dead ends because the lesson got lost.

---

## Format

### YYYY-MM-DD — [One-line failure description]

**Attempted:** [What was tried]

**Why it didn't work:** [Concrete reason, not "it broke." If the
failure mode was technical, name the specific issue. If the failure
mode was scope or approach, name that.]

**What we tried instead:** [The next attempt, which may also have
failed and may have its own entry below]

**Status:** Resolved / open / abandoned

**Tags:** [keywords for future text-search — e.g., "rendering, pandoc,
quarto" or "scope, scrollytelling, decoration"]

---

## Entries

### 2026-05-07 — Strict tier priority + noise didn't produce documented channel fill targets

**Attempted:** The triage algorithm in `docs/triage-logic.md` calls for "walk the sorted queue strict-priority and apply noise" with channel fill targets at Walmart 78%, Costco 80%, Whole Foods 75%, UNFI/KeHE 70%, Regional 65%. Implemented exactly that in `scripts/run_triage.py` first pass.

**Why it didn't work:** Strict priority drove Walmart to 87%+ and starved Tier 3-4 channels to under 45%. Cranking noise (TIER_JUMP_PROB up to 30%, production_scale up to 1.85x) helped Tier 2 a little but nothing pushed UNFI/KeHE/Regional anywhere near targets. Costco specifically collapsed to 30-45% because its 9 authorized SKUs all overlap with Walmart's, and on those shared SKUs Walmart's much-larger demand swamps Costco's inside any priority-respecting allocation.

**What we tried instead:** (a) Fair-share with tier weights — made everyone uniform around 50% because Costco's small demand share is unaffected by weight differentiation. (b) Per-(sku, week) supply scaling at production_scale=1.4 — still ran 25pp under target due to bursty per-SKU per-week demand. (c) Direct target-driven allocation — for each line, ship `round(qty × (target_fill[channel] + N(0, 0.15)))`, capped at requested qty, with a 4% per-(sku, week) production_delayed event reducing some SKUs to 40% of intended. This produces channel fills within ±2.5pp of every target by construction.

**Status:** Resolved (target-driven allocation in production)

**Tags:** triage, allocation, fill-rate-targets, tier-priority, costco

### 2026-05-07 — Buffer simulation initial design didn't reproduce baseline at current fill rate

**Attempted:** First version of `scripts/cost_engine/buffer_simulation.py` lifted every line below the target rate to target, with no guard for `target ≤ current_fill`. Validation check "running at current fill should reproduce baseline within $1/dim" failed by $4.9M on lost_revenue alone.

**Why it didn't work:** The per-line lift fired even when target = current. Lines below their channel's effective rate (e.g., Regional at 63% effective) got raised toward the OVERALL current rate (73.4%), distorting the per-line distribution and shifting all downstream cost calculations.

**What we tried instead:** Short-circuited both `recover_retail_shorts` and `recover_dtc_outcomes` when `target_fill <= current_fill` so the simulation copies the orders DB but makes no modifications. Higher target scenarios (80/85/90/95%) unchanged because all are above the 73.4% current. Validation now passes.

**Status:** Resolved

**Tags:** buffer-simulation, baseline-reproduction, fill-rate, cost-engine

### 2026-05-07 — Costco demand exceeded total brand supply on some authorized low-velocity SKUs

**Attempted:** The order generator uses velocity-weighted SKU sampling without replacement within each retailer's authorized SKU set. Costco only has 9 authorized SKUs and orders 6-15 lines per PO with case quantities of 30-300, so almost every Costco order touches every authorized SKU with large quantities.

**Why it didn't work:** Costco's auth list includes a few low-velocity SKUs (CHP-0014 rank 66, CHP-0037 rank 77). Costco's generated 2-year demand on CHP-0014 was 13× the entire brand's 2-year supply for that SKU. Real Costco wouldn't carry low-velocity SKUs at that volume — the generator's velocity weighting wasn't aggressive enough at filtering when the auth set is small.

**What we tried instead:** Didn't roll back to the generator (sub-task 4 was already running and re-tuning was disruptive). Instead acknowledged in the cost engine's triage that strict priority can't repair this and switched to direct target-driven allocation, which sidesteps the per-SKU competition. Documented the underlying generator artifact in commit messages and `docs/cost-engine-docs.md` known-limitations section.

**Status:** Worked-around, not fixed at the source

**Tags:** generator, sku-selection, costco, velocity-weighting

---
