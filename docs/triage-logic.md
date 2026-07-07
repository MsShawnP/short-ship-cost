# Triage Logic

How original orders get edited down during synthetic data generation.
Documentation only; no code yet.

## Framing

The triage process is not the problem. The person doing the triage is
working heroically with a system that does not capture original orders,
with data that does not show fine structures, and against a fixed
production schedule they cannot influence. The problem is that the
business has no visibility into the cost of the decisions being forced
on this person. This project makes that cost visible.

Every step below is a model of a real human's daily work, not a
critique of it.

## Production output modeling

Production is the supply. There is essentially no inventory buffer; what
gets shipped this week comes off the line this week.

- **Schedule is fixed and weekly.** No rush orders, no flex, no
  overtime, no expediting. The admin works with what is produced.
- **Output per SKU is proportional to historical velocity.** Top
  sellers get more production time and produce more units per week.
  Slow movers get less. Velocity is sourced from the upstream
  Cinderhaven `scan_data` (not in this repo's extract) — see
  implementation notes below.
- **Total weekly production is sized to ~75% of average weekly
  demand.** This is the structural constraint that drives shorts
  across every channel. It is the mathematical reason the
  shipped-vs-original gap exists.
- **Output varies week to week.** Real production lines have noise.
  Realized output is the planned output plus a small stochastic
  term, occasionally negative enough to short Tier 1 retailers.

A SKU's available supply for a given week equals its realized
production output that week. There is no carry-over pool.

## Algorithm

Run weekly. For each production week, do the following.

### Step 1 — Determine available supply

Compute realized production output per SKU for the week. This becomes
the allocation pool for retail and distributor orders. (DTC is
allocated separately — see Step 5.)

### Step 2 — Queue orders by priority

Collect every retail and distributor order whose due date falls in
the week. Sort by:

1. **Retailer priority tier** — Tier 1 first.
   - Tier 1: Walmart, Costco
   - Tier 2: Whole Foods
   - Tier 3: UNFI, KeHE
   - Tier 4: Regional chains
   - Tier 5: DTC (handled separately in Step 5; not in the retail
     queue)
2. **Due date within tier** — soonest first.
3. **Completeness bump** — if allocating to this order would push it
   to 75%+ complete on dollar-weighted line value, bump it ahead of
   the next order at the same tier and due date. This reflects the
   admin's gut-feel routing to minimize fine exposure: getting an
   order to "almost complete" eats a smaller fine than leaving it
   half-done. The admin has no visibility into actual fine schedules
   and is reasoning by intuition.

### Step 3 — Allocate inventory top-down

Walk the sorted queue. For each line on each order:

- If supply ≥ requested quantity → ship in full. Deduct from supply.
- If 0 < supply < requested quantity → ship the available amount
  (partial short). Deduct the shipped amount from supply.
- If supply = 0 → drop the SKU from the order entirely. The line is
  recorded with `quantity_shipped = 0` and a short reason of
  `inventory_unavailable` or `production_delayed`.

By the time the queue reaches Tier 4 and Tier 5, supply on most SKUs
is gone. This produces the realistic pattern of regionals and lower-
priority distributor orders being shorted heavily even when Walmart
ships clean.

### Step 4 — Apply noise

The real world is not perfectly algorithmic. Inject controlled
randomness so the synthetic data does not look like a sorted list:

- Tier-jump events — occasionally a lower-tier order with a tomorrow
  due date jumps a higher-tier order with a later due date.
- Held-for-larger — occasionally a small order at any tier ships
  zero even when supply exists, because the admin held the units
  for a larger order coming the same week.
- Production-fell-behind — occasionally Tier 1 takes a partial
  short because realized production was below plan.
- Bump-not-checked — the completeness bump from Step 2 fires only
  some of the time. The admin does not always run the calculation.

The intended outcome: even Walmart gets shorted sometimes, and even
tiny one-case orders occasionally ship complete. Frequencies for
each event are parameters, set at implementation time alongside the
fill-rate targets in `cost-engine-benchmarks.md`.

### Step 5 — DTC handling

DTC orders do not enter the retail / distributor allocation queue.
They are evaluated against a separate availability check.

- For each DTC order, check whether every SKU on the order has unit
  availability ≥ requested.
- If yes → ship the order on `order_date`. Resolution =
  `shipped_complete`. `days_held = 0`.
- If no → hold the order. Set `hold_start_date = order_date`.
  Each subsequent day, evaluate the cancellation probability from
  `cost-engine-benchmarks.md`:
  - < 3 days held → 10% cancel
  - 3–7 days → 25% cancel
  - 7–14 days → 40% cancel
  - \> 14 days → 60% cancel
- A held order resolves when either (a) all SKUs become available
  (resolution = `shipped_complete`, `resolution_date` = the day
  availability was met) or (b) the customer cancels.
- On cancellation, split the outcome:
  - 35% → resolution = `purchased_in_store`. The brand still books
    a unit sale, but at the retail-channel wholesale price for
    whichever retailer carries the SKU, not the DTC price. The
    per-unit margin difference is the DTC-to-retail margin leakage.
  - 65% → resolution = `cancelled_by_customer`. The sale is lost.

DTC's separate pool is a deliberate simplification. In reality, DTC
units come from the same physical production as retail. Modeling them
separately keeps the algorithm tractable and reflects how the DTC
fulfillment system is operationally walled off in the legacy stack;
the cost is that DTC and retail cannot starve each other in the
synthetic data, even though they would in real life.

## Implementation notes — to specify at build time

These are open questions. They are flagged here so the order generator
in PLAN task 4 can resolve them once.

- **Velocity input for production sizing.** The model needs a per-SKU
  weekly demand and a per-SKU velocity rank to size production output.
  This data lives in the upstream `cinderhaven_product_master.db`'s
  `scan_data` table, which is *not* in this repo's extract. Options:
  (a) compute a per-SKU velocity rollup once from the upstream DB and
  add it as a small derived table in the extract; (b) compute it on
  the fly during generation by attaching the upstream DB; (c) pull a
  velocity table from a flat file.
- **Completeness measure.** The bump uses 75% completeness on
  *dollar-weighted line value* (units × per-unit price summed across
  lines). Fines hit on dollar shorts, so dollar-weighting is closer
  to what the admin's intuition is doing. Alternative: line-count
  completeness. Decide at build time.
- **Noise frequencies.** Tier-jump rate, held-for-larger rate,
  Tier 1 production-shortfall rate, and bump-not-checked rate are
  all parameters. Each must be set to produce overall fill rates
  consistent with the channel-level targets in
  `cost-engine-benchmarks.md` (Walmart ~78%, Costco ~80%, etc.) when
  averaged across the 3-year window.
- **Production output stochasticity.** Distribution and parameters
  for the per-week, per-SKU production noise term are not specified.
  A small Gaussian or beta noise around the planned weekly output
  is the default; magnitude to be tuned so Tier 1 occasionally
  shorts.
- **Order arrival vs. due date.** This algorithm assumes a weekly
  batch on due date. Orders received but not yet due are not part of
  the current-week pool. Whether early-arriving orders should be
  pre-allocated against future production is an implementation
  choice; the simplest model — strict weekly batch on due date — is
  the default unless a behavior gap appears during validation.
