## Design System

Read `../lailara-design-system/LAILARA_DESIGN_SYSTEM.md` before any visual work — colors, typography, layout, components, charts, voice, interactions. It is the single source of truth.

---
# short-ship-cost — Project Context for Claude

## What this project is

A portfolio piece for Lailara LLC that quantifies the full cost of
short-shipping orders in a specialty food business. Built around
Cinderhaven Provisions (~$25M fictional brand, 50 SKUs). The project
queries causal fulfillment data from the Cinderhaven Data Platform
(Postgres), computes four cost dimensions (forgone revenue, compliance
fines, chargebacks, deductions), and presents findings through a
polished interactive tool with an exportable Economist-style analysis.
Total: $894K over 3 years ($298K/yr) at 99.3% portfolio fill
(99.2% retailer / 99.5% distributor). The interactive tool is built
in React 19 (Vite), deployed on Cloudflare Workers at
shortships.lailarallc.com, and designed to look like a product —
not a prototype.

**Business question this project answers:** What does it cost a
business when it can't fulfill retail partner orders as submitted,
and why must the original order be captured alongside the edited
order to make that cost visible?

## Domain context

This project models a business with these characteristics:

- Almost no inventory buffer — virtually everything is manufactured
  to order
- Production capacity is undersized for actual demand — the standard
  production schedule cannot keep up with orders AND build safety stock
- Every order goes through human triage: an EDI/sales admin checks
  inventory, prioritizes by retailer importance and fulfillment
  completeness, then escalates uncertain items to production
- The triage is blind — no visibility into retailer fine structures
  or the true cost of each prioritization decision
- The legacy system overwrites original orders with edited orders —
  there is literally no record of what was originally requested
- The business thinks it's a $20–25M company. Actual demand is likely
  $28–30M+. The gap is invisible because the evidence is destroyed
- The business has a goal to grow to $50M by 2030 but cannot get
  there while leaking unfulfilled demand it can't even measure
- The business is migrating to NetSuite — the message includes
  ensuring the new system captures both original and shipped orders

### Retailer ordering patterns

- **Walmart** — orders at DC level, highly variable (1 case to 100
  cases per order)
- **Costco** — orders against contracted volume for a time period,
  variable size per order
- **Whole Foods** — stocks to a target level across stores in an
  area/DC
- **UNFI/KeHE** — mixed: some do replenishment ordering based on
  actual demand, some over-order on trade promo and return unsold
  product or claim losses
- **Regionals** — smaller, more sporadic
- **DTC** — individual consumer orders, held until 100% complete
  before shipping (some cancel due to delays, some buy in-store
  instead at lower margin)

### Retailer triage priority

Loose hierarchy (Walmart/Costco → Whole Foods → UNFI/KeHE →
Regionals → DTC) but overridden by due dates and fulfillment
completeness ("can we get this order to 75% and eat a smaller fine?").
Even small 1-case orders get shorted because inventory simply does
not exist.

### Costs of a short (4 dimensions, each traceable to platform data)

1. Forgone revenue — units not shipped × wholesale price; secondary:
   forgone contribution margin at 52% of forgone revenue
2. Compliance fines — contractual OTIF fines applied to actual
   shortfall events, modeled from published retailer fine schedules
   (Walmart 3% of COGS, Costco $250 flat per any-short PO, etc.)
3. Chargebacks — event-driven chargebacks for short_ship reason,
   actual amounts from platform
4. Deductions — event-driven deductions for short_ship type, actual
   amounts withheld from remittance payments

### Buffer simulation

Included as a "what if" — models what a line-level fill floor
recovers across all four dimensions. At 99.3% average fill,
individual lines still fall below target; the simulation lifts the
floor (95%/97%/98%/99%) and recomputes forgone revenue and compliance
fines. Chargebacks and deductions are unaffected (actual platform
events, not fill-rate-dependent). Not a production planning tool.

## Stack and tools

- **Frontend:** React 19, Vite — D3 / custom SVG for primary charts,
  Recharts for time series and buffer staircase
- **Data pipeline:** Python (`scripts/rebuild_from_platform.py`) —
  queries Cinderhaven Data Platform Postgres, computes 4 dimensions,
  exports 8 JSON files to `web/public/data/`
- **Deployment:** Cloudflare Workers (`wrangler deploy`) at
  shortships.lailarallc.com
- **Export:** Print CSS (browser print-to-PDF)
- **Data source:** Cinderhaven Data Platform (Postgres) — causal
  fulfillment data from `fct_retailer_shipment_lines`,
  `fct_distributor_shipment_lines`, chargeback and deduction tables

## Cinderhaven data relationship

This project queries the Cinderhaven Data Platform (Postgres)
directly via `rebuild_from_platform.py`. It consumes causal
fulfillment data (shipment lines with units ordered vs shipped),
event-driven chargebacks and deductions, and SKU cost data. The
old self-contained SQLite extract (`cinderhaven_extract.db`) and
synthetic order database (`short_ship_orders.db`) no longer exist.
A local `data/short_ship_cost.db` is written as an archival artifact
but is not consumed by the React app.

## Project files

- CLAUDE.md (this file) — permanent rules and facts
- DECISIONS.md — durable choices and reasoning
- HANDOFF.md — current session state
- PLAN.md — current work arc
- FAILURES.md — things tried that didn't work

Read PLAN.md and HANDOFF.md at session start. DECISIONS.md and
FAILURES.md as relevant.

## Voice and standards

- Economist style for all written output: sober, declarative,
  data-forward, plain English that tells the truth as presented
  by the data
- Economist-style graphics: clean, clear labels, no decorative
  nonsense, charts that respect the reader's intelligence
- No marketing voice or consultant filler ("leverage," "synergy,"
  "best-in-class," "unlock," "drive value")
- No hedging that softens a real finding
- Charts must be readable by non-data-scientist, non-researcher
  audiences
- The interactive tool should look like a product, not a data
  science prototype

## Rules

### Honesty and judgment

- Say "I don't know" or "I can't verify this" instead of guessing.
  This applies to industry context, technical claims, what code did,
  and anything else.
- Tell me what I need to hear, not what I want to hear. If a decision
  looks wrong, say so. If code I wrote has problems, say so. Honest
  assessment, not validation.
- If a rule in this file is too vague to verify whether you're
  following it, flag it for revision rather than guessing at compliance.

### Building and proposing

- No speculative abstractions. If something isn't needed right now,
  don't build it. Helper functions get added when called by real code,
  not in anticipation. Parameters get added when there's a second use
  case, not the first.
- When proposing a tool, library, or approach, present at least two
  alternatives with tradeoffs, even if one is clearly preferred. Do
  not propose a single solution and move on. The default failure mode
  is taking the route with less friction instead of the route that
  best fits the project — challenge yourself before proposing.
- Tie proposals back to the business question this project is
  answering. If you can't connect a proposal to that question, the
  proposal is probably fluff and should be reconsidered.

### How to work the project

- Work in vertical slices, not horizontal phases. Build one section
  end-to-end (data → analysis → visualization → prose) before moving
  to the next. Visualizations should be reviewed and adjusted in their
  own slice, not deferred to a polish phase at the end.
- Do not start tasks outside the current PLAN.md arc without flagging
  it to the user first.
- Do not refactor unrelated code unprompted.
- Do not rename things unless asked.

## Working with PLAN.md

PLAN.md defines the current arc of work. Read it at session start.

- Mark tasks complete as they're finished, in the same commit as the
  work
- If a task is wrong-sized, in the wrong order, or no longer relevant,
  flag it rather than silently restructuring
- "Out of scope" items are decisions, not suggestions — do not pull
  them into the current arc without explicit user approval

## Session reminders

### Reminding the user to /log

Prompt the user to run /log when:

- A meaningful change just landed (file written, bug fixed, feature
  added, decision made)
- A natural pause point is reached (about to switch tasks, finished a
  chunk of work)
- Roughly 30-45 minutes have passed since the last /log and real work
  has happened since then

Format as a clearly separated note. Do not nag — one suggestion per
trigger.

### Reminding the user to /wrap

Prompt the user to run /wrap when:

- Context usage crosses 65%
- The user says anything that suggests they're stopping
- A natural milestone is reached
- 90+ minutes have passed and work is winding down

Format as a clearly separated note. Do not nag.

### Session start protocol

1. Read CLAUDE.md, PLAN.md, and HANDOFF.md
2. If HANDOFF.md's most recent entry is more than 24 hours old AND
   there are uncommitted changes, flag this — the previous session
   may have ended without /wrap
3. Briefly state the starting point from HANDOFF.md so the user
   confirms you're caught up
4. Confirm the current PLAN.md arc is still active

## Defaults

- Default to flagging gaps rather than filling with plausible-sounding
  but unverified content
- Default to short responses unless the task is substantive
- Default to asking before promoting a log entry to a DECISIONS.md
  entry
- Default to answering, not offering to answer
