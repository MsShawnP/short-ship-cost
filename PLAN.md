# short-ship-cost — Current Work Plan

The current arc of work. Updated when the arc changes, not every
session. For session-by-session state, see HANDOFF.md.

---

## Goal

Generate the synthetic order dataset (original orders and edited/shipped
orders) and build the cost engine that calculates all cost dimensions
of a short — validated against Cinderhaven's existing data.

## Why this arc, why now

Everything downstream (the interactive tool, the export, the narrative)
depends on realistic data and a correct cost engine. If the data
doesn't feel real or the cost math is wrong, the portfolio piece
falls apart. Data and engine first.

## Business question this arc answers

What does it cost a business when it can't fulfill retail partner
orders as submitted, and why must the original order be captured
alongside the edited order to make that cost visible?

## Tasks

- [ ] Determine Cinderhaven data consumption approach — full DB
      reference vs. self-contained extract. Decide based on what
      tables/columns are actually needed.
- [ ] Design the synthetic order data model: schema for original
      orders, edited orders, and the linkage between them. Include
      retailer-specific ordering patterns (Walmart DC-level, Costco
      contract-based, Whole Foods stock-level, distributors mixed,
      regionals sporadic, DTC individual).
- [ ] Design the short/triage logic: how orders get edited down.
      Reflect systemic high short rates (make-to-order, no inventory),
      loose retailer priority hierarchy, due-date and fulfillment-
      completeness factors, even small orders getting shorted.
- [ ] Write the order generation scripts. Original orders should
      total roughly 25–40% more than shipped orders (the gap). Same
      18–24 month window as existing Cinderhaven scan data.
- [ ] Build the cost engine — calculates all cost dimensions from
      the order gap:
      1. Lost revenue (units not shipped)
      2. OTIF fines (retailer-specific)
      3. Chargebacks
      4. Deauthorization risk (compounding future revenue loss)
      5. DTC full-order cancellations
      6. DTC-to-retail margin leakage
      7. Distributor returns/claims
      8. Triage labor tax
- [ ] Add buffer simulation layer — "what if fill rate improved
      from X% to Y%" showing recovery across all cost dimensions.
      Framed as fine avoidance, not production planning.
- [ ] Validate: revenue totals make sense against Cinderhaven's
      $23–27M annual wholesale revenue. Original order demand
      should be meaningfully higher. Short patterns should vary
      by retailer and SKU in realistic ways.
- [ ] Document the data model and cost engine logic so the
      interactive tool can consume it cleanly.

## Out of scope for this arc

- Interactive tool UI (that's the next arc)
- Export/PDF generation
- Production planning, manufacturing scheduling, or capacity
  optimization — the buffer simulation shows cost impact of
  improved fill rate without prescribing how to get there
- Moving the order data to a separate repo (do later if warranted)
- Connecting to actual client data

## Definition of done for this arc

- [ ] Synthetic order data generates successfully and covers all
      retailer types with realistic patterns
- [ ] Cost engine calculates all eight cost dimensions correctly
- [ ] Buffer simulation / fill rate "what if" works across all
      cost dimensions
- [ ] Revenue validation passes — shipped revenue aligns with
      Cinderhaven's $23–27M, original demand is 25–40% higher
- [ ] Data model is documented clearly enough for the interactive
      tool arc to consume without ambiguity

---

## Arc history

(No completed arcs yet)
