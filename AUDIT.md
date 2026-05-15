# Project Audit

## Phase 1: Baseline Assessment
**Date:** 2026-05-15
**Project:** short-ship-cost

### What Was Intended

A portfolio piece that makes the invisible cost of short-shipping
visible. The instinct at most companies is "it's no big deal, we
just didn't send them X cases" — but there are real-world cascading
costs (fines, deauthorization, DTC cancellations, margin leakage,
triage labor) that nobody measures because the original order gets
overwritten. The tool quantifies that full cost across eight
dimensions using synthetic data modeled on a ~$25M specialty food
brand (Cinderhaven Provisions).

Built for a specific prospect whose company has this exact problem
— orders come in, they don't store the original order, they only
see what was shipped, so it looks like 100% fill. But designed to
be general enough for any prospect with the same pattern.

### What Exists Today

A working, deployed interactive tool at
`short-ship-cost.msshawnp.workers.dev`.

**Data pipeline (Python):**
- Cinderhaven extract (8 tables, 14,595 rows)
- Synthetic order generator (43,110 orders, 125,748 lines, $51.9M
  shipped over 2 years)
- Modular cost engine calculating 8 dimensions ($25.6M total cost
  of shorts = 49.4% of shipped revenue)
- Buffer simulation at 80/85/90/95% fill rates
- 35-check validation suite (all passing)
- JSON export producing 9 pre-aggregated files (253 KB total)

**Interactive tool (React/Vite):**
- 4 sections: headline cost stack (custom SVG flow-split), retailer/
  SKU drill-down (stacked bars + heatmap table), time series
  (Recharts stacked area), buffer simulation (staircase + deauth cliff)
- Global time-range filter, dimension toggles, click-to-pin callouts
- Parameter adjustment panel with sliders, JS cost engine recalculation
- Print CSS export producing paginated Economist-style PDF
- Code-split (Recharts lazy-loaded)

**Documentation:**
- 5 docs (schema, cost-engine docs, design spec, triage logic,
  benchmarks)
- Full workflow files (CLAUDE.md, DECISIONS.md, HANDOFF.md, PLAN.md,
  FAILURES.md)
- Comprehensive README

### Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 8, CSS Modules |
| Charts | Recharts 2.15 + custom SVG |
| Data pipeline | Python, SQLite |
| Data delivery | Pre-aggregated JSON (no backend) |
| Hosting | Cloudflare Pages |
| Typography | Playfair Display + Source Sans 3 |

### Project Health Indicators

- **Activity:** Active — built in 5 days (May 7-12), deployed,
  last commit May 12. One contributor.
- **Documentation:** Unusually thorough. 5 design/spec docs,
  full decision log with rationale, failure log, session handoffs.
- **Test coverage:** Zero. No test files anywhere — not in
  Python, not in React. The 35-check validation script
  (`validate_cost_engine.py`) and order validation
  (`validate_orders.py`) are the closest thing, but they're
  one-shot scripts, not a test suite.
- **Dependencies:** Current. React 19, Vite 8, Recharts 2.15.
  No known vulnerabilities flagged in scan.

### Gap Analysis

The project is more complete than most portfolio pieces at this
stage — working tool, deployed, documented. But it was specced
and built before the user had a structured process. Claude Chat
drove most design decisions; Gemini reviewed. The decisions are
well-documented but haven't been stress-tested against:

1. **Prospect credibility.** Would someone who lives this problem
   daily find the numbers, the UX, and the framing convincing —
   or would they spot things that feel synthetic, oversimplified,
   or off?

2. **Zero test coverage.** The validation scripts verify data
   integrity but nothing guards against regressions. The JS cost
   engine (ratio-scaling approximation) has no automated tests
   against the Python output beyond a one-time manual check.

3. **Decision quality under pressure.** Five days of building
   means decisions were made fast. Some may be solid; some may
   be "path of least friction" choices that a slower review would
   have challenged (e.g., the ratio-scaling approximation for
   parameter changes, the teal-only palette, the flow-split chart
   form after 5 iterations).

4. **Polish vs. product.** The CLAUDE.md says "should look like
   a product, not a prototype." Unclear whether the current state
   meets that bar without actually opening it in a browser.

5. **The narrative.** The data and the tool exist, but does the
   story land? Does it walk the prospect from "it's no big deal"
   to "this is a $25M problem" in a way that feels inevitable
   rather than constructed?

### Audit Motivation

The user discussed the project with their best friend who works
at the company that has this exact problem. That conversation
raised the question: is this good enough to put in front of
someone who would immediately know whether it rings true? The
audit is about answering that before showing it.

---

## Phase 2: Internal Review
**Date:** 2026-05-15
**Dimensions reviewed:** Code quality, Architecture, Tests,
Documentation, Performance, Security, UX, DevEx

### Top Opportunities (by leverage)

| # | Finding | Dimension | Impact | Effort | Leverage | Severity |
|---|---------|-----------|--------|--------|----------|----------|
| 1 | Duplicate color map — `SEQUENTIAL_TEALS` in CostStack.jsx duplicates `DIMENSION_COLOR` from dimensions.js | Code quality | 3 | 1 | 3.0 | Important |
| 2 | No OG/meta tags for social sharing | Security/UX | 3 | 1 | 3.0 | Important |
| 3 | No methodology context visible on the page itself | UX | 5 | 2 | 2.5 | Critical |
| 4 | Duplicate `hexToRgba` in RetailerDrilldown + BufferSimulation | Code quality | 2 | 1 | 2.0 | Minor |
| 5 | Dimension ordering inconsistency (dimensions.js vs timeRange.jsx) | Code quality | 2 | 1 | 2.0 | Minor |
| 6 | Footer references `docs/cost-engine-docs.md` — a repo path meaningless to site visitors | UX | 2 | 1 | 2.0 | Minor |
| 7 | Google Fonts loaded from external CDN | Performance/Security | 2 | 1 | 2.0 | Minor |
| 8 | No Python dependency manifest (requirements.txt or pyproject.toml) | DevEx | 2 | 1 | 2.0 | Minor |
| 9 | Zero test coverage — 335 lines of JS financial math completely untested | Tests | 5 | 3 | 1.7 | Critical |
| 10 | No narrative prose between sections — tool assumes viewer already cares | UX | 4 | 3 | 1.3 | Important |
| 11 | Teal-only sequential palette — hard to distinguish 8 dimensions at a glance | UX | 3 | 3 | 1.0 | Important |
| 12 | TimeRangeContext bundles 3 concerns (time, dims, params) — unnecessary re-renders | Architecture | 3 | 3 | 1.0 | Important |
| 13 | No CI/CD pipeline — regressions unguarded | DevEx | 2 | 2 | 1.0 | Minor |

### Detailed Findings

#### Code Quality

**Good:** Consistent formatting, clear naming, good use of
`useMemo` to guard expensive computations, well-structured
component files, clean separation of data transforms from
rendering.

**Issues:**

1. **Duplicate color map (Important).** `CostStack.jsx:16-24`
   defines its own `SEQUENTIAL_TEALS` object with the exact same
   values as `DIMENSION_COLOR` in `lib/dimensions.js`. This means
   a color change requires editing two files, and they can drift.
   CostStack should import from dimensions.js like every other
   component does.

2. **Duplicate `hexToRgba` (Minor).** The same utility function
   appears in `RetailerDrilldown.jsx:109` and
   `BufferSimulation.jsx:25`. Should live in `lib/format.js`.

3. **Dimension ordering inconsistency (Minor).**
   `DIMENSION_ORDER` in `dimensions.js` orders dimensions
   alphabetically-ish (lost_revenue, otif_fines, chargebacks,
   deauthorization...). `ALL_DIMENSIONS` in `timeRange.jsx`
   orders by magnitude (lost_revenue, deauthorization, otif_fines,
   chargebacks...). These are both exported as "the canonical
   order." One source of truth, used everywhere.

#### Architecture

**Good:** Clean component boundaries. Lazy loading strategy is
sound. The cost engine abstraction (Python computes, JS scales
by ratios) is an honest tradeoff well-documented in code and
DECISIONS.md.

**Issues:**

4. **TimeRangeContext does too much (Important).**
   `lib/timeRange.jsx` bundles time-range state, dimension
   toggles, AND parameter state into a single context. When the
   user moves a parameter slider, every component that reads
   `useTimeRange()` re-renders — even `FilterBar` and
   `DimensionToggle` which don't use params. Splitting into
   `TimeRangeProvider`, `DimensionProvider`, and `ParamsProvider`
   would isolate re-renders. Not urgent for a 4-section page,
   but worth noting for production quality.

#### Tests

**Critical: Zero coverage.** No test files exist — not in Python,
not in React. The two validation scripts (`validate_orders.py`,
`validate_cost_engine.py`) are one-shot verifiers, not a test
suite.

The highest-risk gap is `utils/costEngine.js` — 335 lines of
financial math (ratio scaling, deauth event filtering, buffer
scenario scaling, summary derivation). The JS output is validated
against `validation.json` at runtime, but only at baseline params.
If any parameter-adjusted calculation produces wrong numbers, there
is nothing to catch it before a prospect sees it.

A focused test file covering `getRatios`, `filterDeauthEvents`,
`scaleCostByRetailer`, `scaleBufferScenarios`, and
`validateBaseline` with known inputs would be the highest-leverage
testing investment.

#### Documentation

**Good:** Unusually thorough for a portfolio project. README is
comprehensive. Design spec, cost-engine docs, and benchmarks are
well-written and honest about limitations.

**Issues:**

5. **Footer references a repo path (Minor).** The site footer
   says "methodology in `docs/cost-engine-docs.md`". A site
   visitor can't navigate to a local file path. Either link to
   the GitHub file or add a methodology section to the page.

#### Performance

**Good:** First paint is fast (~218 KB / 69 KB gz initial bundle).
Recharts is lazy-loaded (371 KB chunk loads after Section 1
paints). JSON data is 253 KB total — small enough that loading
all 9 files via `Promise.all` on startup is fine.

**Issues:**

6. **Google Fonts loaded from CDN (Minor).** Two font families
   loaded from `fonts.googleapis.com`. This adds a render-blocking
   request, a DNS lookup, and sends visitor data to Google. For a
   portfolio piece shown to a specific prospect, self-hosting the
   fonts (download woff2 files, serve from `/fonts/`) would be
   faster and more professional.

#### Security

**Good:** No user input handling beyond slider values. No API
calls. No authentication. Attack surface is near-zero for a
static site.

**Issues:**

7. **No OG/meta tags (Important).** The page has no
   `<meta name="description">`, no Open Graph tags, no Twitter
   card markup. If the prospect shares the URL in Slack or Teams,
   it will render as a bare link with no preview. For a portfolio
   piece designed to impress, the social card is the first
   impression. Easy to add to `index.html`.

#### UX

This is the dimension that matters most for the audit's stated
goal: "Is this good enough to show to a real prospect?"

**Good:** The flow-split chart is distinctive and communicates
the headline well. Click-to-pin is a clean interaction pattern.
The parameter panel is well-organized. Print CSS produces a
usable document. Loading and empty states are handled. Focus-
visible outlines and reduced-motion are present.

**Issues:**

8. **No methodology or "about" context on the page (Critical).**
   The tool opens with a $25.6M number and assumes the visitor
   trusts it. A prospect who lives this problem will immediately
   ask: "Where do these numbers come from? Is this real data?" A
   brief section (above or below the headline, or as a collapsible
   panel) explaining that this is synthetic data modeled on a
   ~$25M specialty food brand, with tunable parameters and
   documented methodology, would build credibility rather than
   requiring it upfront.

9. **No narrative between sections (Important).** Each section
   has a title and subtitle, but there's no connective prose that
   walks the reader from insight to insight. The Economist style
   the project aspires to isn't just clean charts — it's charts
   embedded in a narrative. Right now it reads more like a
   dashboard than an argument. For a prospect: the numbers need
   to *tell them something they didn't know*, not just display
   data they could have guessed.

10. **Teal-only palette (Important).** The sequential teal palette
    was a deliberate decision (DECISIONS.md). The tradeoff: it
    communicates magnitude hierarchy at a glance, but makes it
    hard to distinguish the 6 smaller dimensions from each other.
    In the flow-split chart (Section 1) the blocks have labels so
    it works. In the stacked area chart (Section 3) and heatmap
    (Section 2), similar-teal cells blur together. Worth
    reconsidering or at least A/B testing with a prospect's eye.

#### DevEx

**Good:** Dev setup is simple (`cd web && npm install &&
npm run dev`). Export script is idempotent. Vite HMR is fast.

**Issues:**

11. **No Python dependency manifest (Minor).** The data pipeline
    uses only stdlib (sqlite3, json, pathlib, collections,
    datetime) but this isn't documented. A `requirements.txt`
    (even if empty with a comment) or `pyproject.toml` tells the
    next developer they don't need to install anything.

12. **No CI/CD pipeline (Minor).** Deploy is manual via
    `npm run deploy`. No GitHub Actions for lint, build, or
    deploy. For a solo portfolio project this is fine, but means
    a typo can go live unguarded.

### Summary

The codebase is cleaner than expected for a 5-day build — good
component structure, honest documentation, working financial
math. The critical gaps are prospect-facing: the tool is a
dashboard when it needs to be an argument. It shows numbers
without establishing why the viewer should trust them or care.
The highest-leverage improvements are adding methodology context
to the page, testing the JS cost engine, and strengthening the
narrative flow between sections. The code-level fixes (duplicate
color map, utility dedup, OG tags) are quick wins that should
be done regardless.

---

## Phase 3: Landscape Scan
**Date:** 2026-05-15
**Category:** Supply chain short-ship cost analysis (commercial
tools) × interactive data storytelling (presentation quality)

### Competitors / Similar Projects

**Supply chain tools:**

| # | Name | URL | Description | Traction |
|---|------|-----|-------------|----------|
| 1 | SupplyPike | supplypike.com | OTIF compliance analytics + deduction dispute automation for Walmart suppliers | Acquired by SPS Commerce (2024) |
| 2 | Crisp | gocrisp.com | POS/inventory data aggregation across 40+ retailers for CPG brands; AI replenishment | $127M raised, 7K+ brands, 80+ of top 100 CPG |
| 3 | Alloy.ai | alloy.ai | Demand + inventory visibility with ML forecasting; OTIF fine dollar-cost framing | SAP partner, $1.5-4.5K/mo pricing |
| 4 | Vividly | govividly.com | Trade promo management + deduction recovery for CPG | $30M Series B (Jan 2025) |
| 5 | iNymbus | inymbus.com | RPA deduction management automation across 40+ retailers | Claims 30x processing speed |
| 6 | RetailPath | retailpath.xyz | Order visibility + autonomous dispute processing | Recent entrant (2025-26) |

**Data storytelling benchmarks:**

| # | Name | URL | Description | Why it matters |
|---|------|-----|-------------|----------------|
| 7 | NYT Rent vs Buy Calculator | nytimes.com/interactive/2014/upshot | Every assumption is a slider; break-even chart updates live | Gold standard for parameter-driven editorial tools |
| 8 | Nicky Case Explorable Explanations | ncase.me | "Place Your Bets" + "Sandbox Mode" interaction patterns | Framework for making data exploration feel like thinking |
| 9 | The Pudding | pudding.cool | Scrollytelling essays with animated transitions, full methodology | Benchmark for narrative + data fusion |
| 10 | FT Climate Game | ft.com/climate-game | 400-decision scenario simulator; 650K+ playthroughs; grounded in IEA data | Shows how scenario tools earn trust via sourcing |

### Feature Matrix

| Feature | This Project | SupplyPike | Crisp | Alloy.ai | NYT Calculator | Nicky Case |
|---------|:-----------:|:---------:|:-----:|:--------:|:--------------:|:----------:|
| Cost quantification of shorts | ✅ | ❌ | ❌ | 🟡 | ➖ | ➖ |
| Original vs shipped order comparison | ✅ | ❌ | ❌ | ❌ | ➖ | ➖ |
| Retailer-level drill-down | ✅ | ✅ | ✅ | ✅ | ➖ | ➖ |
| SKU-level analysis | ✅ | ✅ | ✅ | ✅ | ➖ | ➖ |
| OTIF fine calculation | ✅ | ✅ | ❌ | 🟡 | ➖ | ➖ |
| Deauthorization risk modeling | ✅ | ❌ | ❌ | ❌ | ➖ | ➖ |
| Cascading cost model (8 dimensions) | ✅ | ❌ | ❌ | ❌ | ➖ | ➖ |
| Buffer/scenario simulation | ✅ | ❌ | ❌ | 🟡 | ➖ | ➖ |
| Parameter adjustment (live sliders) | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Time-range filtering | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Export / PDF | ✅ | 🟡 CSV | ✅ | ✅ | ❌ | ❌ |
| Connected to real data | ❌ synthetic | ✅ | ✅ | ✅ | ➖ | ➖ |
| Multi-retailer live feeds | ❌ | 🟡 Walmart-only | ✅ 40+ | ✅ 350+ | ➖ | ➖ |
| Narrative storytelling flow | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Methodology visible on page | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Engagement hook (bet/predict/reveal) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Animated state transitions | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Scrollytelling | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

### Landscape Position

#### Table Stakes (standard in category)

Every supply chain tool has retailer and SKU drill-down, time
filtering, and export. This project has all of these.

**Missing table-stakes item:** Connected to real data. Every
commercial tool pulls from live retailer feeds. This project uses
synthetic data — which is fine for a portfolio piece, but the
page doesn't explain this to the viewer. A prospect might assume
it's real data they don't recognize, or worse, dismiss it as
made-up. The Phase 2 finding ("no methodology context on page")
is reinforced here.

#### Where This Project Is Stronger

1. **Cost quantification of the short itself.** No incumbent does
   this. SupplyPike, iNymbus, Vividly, and RetailPath all focus
   on recovering money *after* the short happened — disputing
   fines, automating chargebacks. They never ask "what did this
   short actually cost us across all dimensions?" This project
   answers that question.

2. **Original vs shipped order comparison.** No tool in the scan
   preserves and analyzes the gap between what was ordered and
   what was shipped as a first-class concept. This is the project's
   thesis and its sharpest differentiator.

3. **Deauthorization risk modeling.** No competitor models
   deauthorization as a cost dimension. This project quantifies
   the forward revenue lost when shelf placement disappears due
   to chronic underfill — $5.86M in the model. This is the number
   most likely to surprise a prospect.

4. **Buffer simulation.** "What would a 90% fill rate have saved?"
   is a question no incumbent answers. Alloy.ai does forward-
   looking demand planning but doesn't model retroactive cost
   recovery from improved fill.

5. **Live parameter adjustment.** Only the NYT Calculator and
   explorable explanations offer this level of "touch every
   assumption." The supply chain tools are dashboards that display
   data; this tool lets you stress-test the model.

#### Where This Project Is Weaker

1. **Not connected to real data.** Every supply chain tool's value
   prop starts with "connect your Walmart/Costco/UNFI data." This
   project can't do that — it's a portfolio piece with synthetic
   data. The weakness isn't the synthetic data itself; it's that
   the page doesn't make the viewer understand what they're
   looking at and why it's relevant to them.

2. **No narrative flow.** The best data storytelling (Pudding,
   Nicky Case, FT Climate Game) builds an argument section by
   section. This project displays four chart sections with titles
   but no connective prose. It reads as "here are four views of
   the data" instead of "here's why this costs you $25M and
   here's the one lever that matters most."

3. **No engagement hooks.** Nicky Case's "Place Your Bets"
   pattern — ask the viewer to predict the answer before revealing
   it — is exactly right for this project's opening. "What do you
   think short-shipping costs a $25M brand per year? $500K? $2M?
   $5M?" Then reveal: $25.6M. The surprise is the hook; the tool
   earns the right to the viewer's next 10 minutes.

4. **No animated transitions.** When the time range changes or a
   dimension is toggled, numbers snap to new values. The Pudding
   and NYT Calculator animate state transitions — the motion
   communicates magnitude of change. This is polish, not
   substance, but it's the kind of polish that separates "product"
   from "prototype" in a prospect's gut.

#### Unique Differentiators

1. **The thesis itself.** "The original order is destroyed, so
   the cost is invisible" is a framing no tool in the market
   uses. The commercial tools assume you know what your shorts
   cost; this tool proves you don't.

2. **Eight-dimension cost model.** No tool breaks short-ship cost
   into lost revenue + OTIF fines + chargebacks + deauthorization
   + DTC cancellations + DTC margin leakage + distributor returns
   + triage labor. The supply chain tools track 1-2 of these
   (usually OTIF fines and chargebacks).

3. **The deauthorization cliff.** The buffer simulation's
   staircase showing cost dropping sharply at 90% fill (where
   distributor deauth thresholds clear) is a visual nobody else
   has. It turns an abstract concept into a "there's a cliff,
   and you're on the wrong side of it" moment.

#### Category Trends

The supply chain analytics market is consolidating fast:
SupplyPike acquired by SPS Commerce, Crisp acquiring Atheon +
ClearBox, Alloy.ai partnering with SAP. The trend is toward
unified platforms that pull data from all retailers into one
view. AI agents (Crisp's Agent Studio, RetailPath's autonomous
disputes) are the 2025-26 story.

In data storytelling, the trend is toward explorable explanations
with full methodology transparency. The FT Climate Game proved
that scenario simulators can be both rigorous journalism and
viral engagement tools (650K+ plays). The Pudding consistently
ships the highest-quality interactive data essays in the field.

The gap both trends leave open: **nobody is building the
analytical argument for why the original order matters.** The
supply chain tools automate recovery from shorts; the data
storytelling tools don't touch supply chain. This project sits
in the unclaimed intersection.

### Summary

This project occupies a genuinely empty niche: no commercial
supply chain tool quantifies the full upstream cost of a short
across eight dimensions, and no data storytelling piece has tried
this domain. The analytical model (especially deauthorization
risk and the buffer cliff) is stronger than anything in the
market. The weakness is presentation, not substance — the
commercial tools are weaker analytically but feel more polished
because they connect to real data and follow dashboard
conventions the prospect already trusts. The data storytelling
benchmarks show what "product quality" means in practice:
narrative flow, methodology transparency, engagement hooks, and
animated transitions. Adding those qualities to this project's
unique analytical core would create something that doesn't exist
anywhere.

---

## Phase 4: Differentiation & Next Moves
**Date:** 2026-05-15

### Cross-Reference Summary

The audit's central finding is that this project's analytical
core is genuinely unique — no supply chain tool quantifies the
upstream cost of a short across eight dimensions, models
deauthorization risk, or lets you simulate buffer scenarios.
But the presentation doesn't match the substance. The internal
review (Phase 2) found the same gaps the landscape scan (Phase 3)
confirmed: no methodology transparency, no narrative flow, no
engagement hooks. These aren't just internal quality issues —
they're the exact qualities that separate the best data
storytelling (NYT, Pudding, FT, Nicky Case) from dashboards.

The prospect is a tinkerer who likes playing with data and
scenarios. The tool already supports that (sliders, toggles,
click-to-pin). What's missing is the setup: the tool drops him
into $25.6M without context, without earning trust, and without
a hook that makes him want to explore. The commercial supply
chain tools (SupplyPike, Crisp, Alloy) are weaker analytically
but feel more authoritative because they connect to real data and
follow conventions the prospect already trusts. This project
can't connect to real data — it's a portfolio piece. But it can
match or exceed the data storytelling standard for transparency,
narrative, and engagement. That's the strategic path.

The code-level fixes from Phase 2 (duplicate color map, utility
dedup, OG tags, footer fix) are quick wins that should be done
first — they prevent bugs and polish the surface before any
larger changes land.

### Ranked Next Moves

| # | Move | Category | Strategic | Internal | Effort | Score | Description |
|---|------|----------|-----------|----------|--------|-------|-------------|
| 1 | OG/meta tags + social card | Close gap | 4 | 3 | 1 | 7.0 | If the prospect shares the URL in Slack/Teams, the preview is the first impression. Add `<meta>` description, OG title/description/image, Twitter card. |
| 2 | Code cleanup bundle | Foundational | 1 | 3 | 1 | 4.0 | Fix duplicate `SEQUENTIAL_TEALS` in CostStack.jsx, extract `hexToRgba` to lib/format.js, consolidate dimension ordering to one source of truth, fix footer repo-path reference. |
| 3 | "Place Your Bets" engagement hook | Leapfrog | 5 | 3 | 2 | 4.0 | Before revealing $25.6M, ask the visitor to estimate: "What do you think short-shipping costs a $25M brand per year?" Show a range. Let them commit. Then reveal the model's answer. The surprise is the hook. Nobody in the supply chain or data storytelling space does this. Perfect for a tinkerer prospect. |
| 4 | Self-host fonts | Foundational | 1 | 2 | 1 | 3.0 | Download Playfair Display + Source Sans 3 woff2 files, serve from /fonts/. Eliminates Google Fonts render-blocking request, DNS lookup, and third-party data leak. |
| 5 | Narrative + methodology on the page | Leapfrog | 5 | 5 | 4 | 2.5 | Add connective prose between sections that walks the reader from "it's no big deal" → "this is a $25M problem" → "here's where it hits hardest" → "here's the one lever." Add methodology panel or section: synthetic data, ~$25M brand model, tunable parameters, documented assumptions. This is the single move that addresses the biggest Phase 2 finding AND the biggest Phase 3 gap. No supply chain tool does this; the best data storytelling always does. |
| 6 | JS cost engine tests | Foundational | 3 | 5 | 3 | 2.7 | Test `getRatios`, `filterDeauthEvents`, `scaleCostByRetailer`, `scaleBufferScenarios`, and `validateBaseline` with known inputs. The prospect will drag sliders — if the math is wrong at non-baseline params, credibility is gone. |
| 7 | Python dependency manifest | Foundational | 0 | 2 | 1 | 2.0 | Add `requirements.txt` (even empty with a comment) or `pyproject.toml` documenting stdlib-only deps. Prospect won't see this, but it closes a DevEx gap. |
| 8 | Animated state transitions | Close gap | 3 | 2 | 3 | 1.7 | Animate number changes, chart reflows, and filter transitions. The Pudding and NYT Calculator use motion to communicate magnitude. This is the polish that separates "product" from "prototype" in a prospect's gut. |
| 9 | Palette evaluation | Close gap | 2 | 3 | 3 | 1.7 | Test the teal-only palette with a fresh pair of eyes. If dimensions blur together in Sections 2-3, consider a divergent palette for the 6 smaller dims while keeping teal for lost_revenue and deauthorization. Don't change unless it's clearly better — the current palette was a deliberate decision. |

### Recommended Sequence

**Wave 1 — Quick wins (do first, < 1 hour total):**
Moves 1, 2, 4, 7. These are all effort-1 fixes that polish the
surface before any bigger changes. OG tags mean the URL looks
sharp if shared. Code cleanup prevents bugs during subsequent
work. Self-hosted fonts load faster. Dependency manifest closes
a gap.

**Wave 2 — The engagement layer (the differentiator):**
Move 3 ("Place Your Bets" hook). This is the single most
impactful change for the specific prospect: a tinkerer who likes
to play with data. The hook gives him something to react to
before he starts exploring. It also creates the emotional setup
that makes the narrative (Wave 3) land harder.

**Wave 3 — The narrative layer (the argument):**
Move 5 (narrative + methodology). This is the heaviest lift but
the most transformative. The tool goes from "dashboard with four
chart sections" to "argument that walks you to a conclusion."
Methodology transparency earns the trust that synthetic data
can't earn on its own. This should be done after the hook is in
place, because the hook creates the emotional context the
narrative builds on.

**Wave 4 — Safety net:**
Move 6 (JS cost engine tests). Write tests before the prospect
session, so slider interactions are verified at non-baseline
params. This can run in parallel with Waves 2-3 if time allows.

**Wave 5 — Polish (if time):**
Moves 8, 9 (animations, palette). Only if the prospect meeting
isn't imminent. These improve perceived quality but don't change
the argument.

### What NOT to Do

1. **Don't try to connect to real data.** The commercial tools'
   strength is live retailer feeds. Chasing that would require a
   backend, auth, EDI integration — months of work that turns a
   portfolio piece into a product. The better move is leaning into
   what synthetic data *can* do (tunable, explorable, transparent)
   and making that a feature, not an apology.

2. **Don't add scrollytelling.** The Pudding does it beautifully,
   but retrofitting scroll-driven reveals into a 4-section React
   app is a major architectural change. The "Place Your Bets"
   hook + narrative prose gets 80% of the engagement benefit at
   20% of the effort.

3. **Don't split TimeRangeContext yet.** Phase 2 flagged it as
   an architecture concern, but for a 4-section page the re-
   render cost is negligible. Splitting it now adds complexity
   without visible benefit. Revisit only if the page grows.

4. **Don't chase the supply chain tools' feature set.** Adding
   multi-retailer data feeds, EDI connectors, or AI agents would
   be playing their game on their field. This project's advantage
   is analytical depth and storytelling — invest there.

5. **Don't rebuild the palette without testing.** The teal palette
   was a deliberate decision with documented rationale. Evaluate
   it with the prospect in mind, but don't change it preemptively.
   If it works well enough in the flow-split chart (where the
   labels compensate), the risk is only in Sections 2-3 where
   small dimensions blur. A targeted fix (higher contrast on the
   lightest 3 shades) is better than a full redesign.
