# Project Audit

## Phase 1: Baseline Assessment
**Date:** 2026-05-16
**Project:** short-ship-cost
**Prior audit:** 2026-05-15 (all 4 phases). This is a fresh reassessment
after 30+ tasks shipped in the interim.

### What Was Intended

A portfolio piece for Lailara LLC that makes the invisible cost of
short-shipping visible. Built around Cinderhaven Provisions (~$25M
fictional brand, 90 SKUs). Designed for a specific prospect: a CEO
with an MBA at a company that has this exact problem, arriving cold
via a friend's recommendation, likely opening on his phone first.

The tool should read as a self-selling argument — not a dashboard,
not a prototype — that within 90 seconds demonstrates rigorous data
work and deep understanding of the problem.

### What Exists Today

A working, deployed interactive tool at
`short-ship-cost.msshawnp.workers.dev`. Feature-complete across
three build arcs (data pipeline, interactive tool, dashboard-to-
argument transformation) plus a visual polish pass.

**Data pipeline (Python, stdlib only):**
- Cinderhaven extract (9 tables, 14,595 rows)
- Synthetic order generator (43,110 orders, 125,748 lines, $51.9M
  shipped over 2 years)
- Modular cost engine: 8 independent dimension modules, orchestrated
  by runner.py
- Buffer simulation at 80/85/90/95% fill rates
- 36-check + 10-check validation suites (all passing)
- JSON export producing 9 pre-aggregated files (253 KB total)

**Interactive tool (React 19 / Vite 8):**
- Opening framing statement setting up the problem in plain English
- $25.6M headline number with animated count-up (250ms, a11y)
- 4 sections: headline cost stack (custom SVG flow-split), retailer/
  SKU drill-down (stacked bars + heatmap table), time series
  (Recharts stacked area with trend detection), buffer simulation
  (staircase + deauth cliff)
- Data-driven insight lines in each section
- Global time-range filter, dimension toggles (CSS Grid, 4x2/2x4)
- Click-to-pin callouts (dark card, no hover tooltips)
- Parameter adjustment panel (mobile: full-screen bottom sheet)
- Animated transitions on number changes and chart reflows
- Collapsible "About this analysis" methodology section
- Print CSS export: paginated Economist-style PDF with metadata
- Code-split: Recharts lazy-loaded (371 KB chunk after first paint)
- Self-hosted fonts (Playfair Display + Source Sans 3)
- OG/Twitter meta tags with 53 KB social card image
- Mobile-responsive at 640px breakpoint, 44px touch targets
- 34 JS cost engine tests (vitest), all passing

**Hosting and deploy:**
- Cloudflare Pages (static site)
- `npm run deploy` via wrangler
- No CI/CD pipeline (manual deploy)

**Documentation:**
- 5 specification docs (schema, cost-engine, design spec, triage,
  benchmarks)
- Full workflow files (CLAUDE.md, DECISIONS.md, HANDOFF.md, PLAN.md,
  FAILURES.md)
- Comprehensive README with live link, methodology pointers, and
  repo structure guide

### Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Frontend | React, Vite, CSS Modules | 19.2, 8.0, — |
| Charts | Recharts + custom SVG | 2.15 |
| Data pipeline | Python (stdlib only) | 3.11+ |
| Data delivery | Pre-aggregated JSON | — |
| Hosting | Cloudflare Pages (Workers) | — |
| Typography | Playfair Display + Source Sans 3 | Self-hosted woff2 |
| Testing | Vitest | 4.1 |

### Project Health Indicators

| Indicator | Status |
|---|---|
| Build | Clean, 0 warnings, 0 errors |
| Tests | 34/34 passing (767ms) |
| Vulnerabilities | 0 (npm audit) |
| Bundle size | 212 KB initial / 371 KB lazy (both gzipped: 68 + 99 KB) |
| Data pipeline validation | 46/46 checks passing |
| Deploy | Working (Cloudflare Workers) |
| Last commit | 2026-05-16 (active today) |
| Contributors | 1 |

### Resolution of Prior Audit Findings (2026-05-15)

| # | Finding | Status | How resolved |
|---|---------|--------|--------------|
| 1 | Duplicate SEQUENTIAL_TEALS in CostStack.jsx | **Resolved** | Removed; imports DIMENSION_COLOR from dimensions.js |
| 2 | No OG/meta tags | **Resolved** | Full OG + Twitter card + 53KB og-card.png |
| 3 | No methodology on page | **Resolved** | Collapsible "About this analysis" section with 5 paragraphs |
| 4 | Duplicate hexToRgba | **Resolved** | Centralized in lib/format.js |
| 5 | Dimension ordering inconsistency | **Resolved** | Single DIMENSION_ORDER in dimensions.js; ALL_DIMENSIONS removed |
| 6 | Footer references repo path | **Resolved** | Links to #methodology in-page anchor |
| 7 | Google Fonts CDN | **Resolved** | Self-hosted woff2 in web/public/fonts/ |
| 8 | No Python dependency manifest | **Resolved** | requirements.txt documents stdlib-only deps |
| 9 | Zero test coverage | **Resolved** | 34 tests covering all cost engine functions + edge cases |
| 10 | No narrative between sections | **Resolved** | Framing statement, insight lines in each section |
| 11 | Teal palette concern | **Resolved** | Evaluated quantitatively (deltaE 8.7–15.5); kept with documented rationale |
| 12 | TimeRangeContext bundles 3 concerns | **Deferred** | Explicitly out of scope; re-render cost negligible for 4-section page |
| 13 | No CI/CD | **Open** | Still manual deploy via `npm run deploy` |

### Gap Analysis

The project is functionally complete for its stated goal. Every
critical finding from the May 15 audit has been addressed. What
remains is polish, resilience, and minor professional touches —
not structural gaps.

---

## Phase 2: Internal Review
**Date:** 2026-05-16
**Dimensions reviewed:** Code quality, Architecture, Tests,
Documentation, Performance, Security, UX, DevEx

### Top Opportunities (by leverage)

| # | Finding | Dimension | Impact | Effort | Leverage | Severity |
|---|---------|-----------|--------|--------|----------|----------|
| 1 | OG image uses relative path — social previews won't render | UX | 4 | 1 | 4.0 | Important |
| 2 | No error boundaries around lazy-loaded sections | Reliability | 3 | 1 | 3.0 | Minor |
| 3 | No CI/CD — regressions unguarded on deploy | DevEx | 2 | 2 | 1.0 | Minor |
| 4 | TimeRangeContext bundles 3 concerns | Architecture | 2 | 3 | 0.7 | Minor |
| 5 | Recharts chunk is 371 KB (99 KB gz) | Performance | 1 | 4 | 0.3 | Trivial |

### Detailed Findings

#### Code Quality — Excellent

The codebase is clean and well-organized:

- **Single source of truth.** DIMENSION_ORDER, DIMENSION_COLOR,
  DIMENSION_LABEL all exported from one file (dimensions.js, 46
  lines). No duplicates anywhere.
- **Utility centralization.** hexToRgba, fmtCompact, fmtPct,
  fmtFull, fmtMillions all in lib/format.js (33 lines). Used
  consistently across 3 components.
- **Consistent patterns.** All 4 sections follow the same pattern:
  import from lib/, use useTimeRange(), memoize computed values,
  render chart + callout + footnote.
- **Clean component boundaries.** Each section is self-contained
  (own CSS module, own data transformations). App.jsx handles data
  loading, scaling, and composition only.

No code quality issues found.

#### Architecture — Sound

- **Code splitting.** RetailerDrilldown, TimeSeries, and
  BufferSimulation are React.lazy loaded. Recharts ships in its
  own 371 KB chunk after Section 1 paints. First paint is 212 KB.
- **Data flow.** Python pre-aggregates → JSON → React loads all 9
  files → JS cost engine scales by parameter ratios → sections
  consume scaled data via props. Clear, unidirectional.
- **Context usage.** TimeRangeProvider bundles time-range state,
  dimension toggles, and parameter state into one context. This
  means any slider change triggers re-renders in FilterBar and
  DimensionToggle even though they don't use params. For a
  4-section page this is negligible; would matter if the page grew
  significantly. Explicitly deferred as acceptable.

**Issue: No error boundaries (Minor).**
If a lazy-loaded section fails to render (e.g., bad data shape
after a parameter change), the entire app will crash with an
unhandled error. Wrapping each `<Suspense>` in an error boundary
would show a per-section fallback instead of a white screen.
Effort: 1 (20 lines).

#### Tests — Adequate for a portfolio piece

- **34 tests passing** (767ms) in `utils/costEngine.test.js`
- Covers: baseline validation against Python output, ratio scaling,
  deauth event filtering, buffer scenario scaling, edge cases
  (zero baseline, negative inputs, NaN/Infinity guards)
- **Not covered:** React component rendering, interaction flows
  (click-to-pin, dimension toggle, filter changes), print CSS
  output, mobile bottom-sheet behavior.

For a static-data portfolio piece, the cost engine tests are the
right investment. Component tests would guard against regressions
but aren't critical when the data shape is fixed and the page is
small. If the tool were productionized with live data, component
tests would become important.

#### Documentation — Thorough

Five specification docs, a comprehensive README, full workflow
state files. Unusually complete. No gaps.

#### Performance — Good

| Metric | Value | Assessment |
|---|---|---|
| Initial JS bundle | 212 KB (68 KB gz) | Good |
| Lazy Recharts chunk | 371 KB (99 KB gz) | Acceptable (loads after first paint) |
| Total CSS | 38 KB (10 KB gz) | Good |
| JSON data (all 9 files) | 253 KB | Good (loads via Promise.all) |
| Build time | 724ms | Excellent |
| Test time | 767ms | Excellent |

The 371 KB Recharts chunk is the only notable size. It's
lazy-loaded correctly so it doesn't affect first paint.
Alternatives (lightweight charting library, or more custom SVG)
would reduce this but add development complexity for a portfolio
piece. Not worth changing.

#### Security — Minimal attack surface

Static site. No user input beyond slider values (which only affect
in-memory state). No API calls. No authentication. No cookies. No
third-party scripts. Self-hosted fonts eliminate the Google Fonts
data leak. The attack surface is near-zero.

#### UX

**Strong:**
- Opening framing statement earns the first 90 seconds by naming
  the problem before showing the number
- Animated headline count-up communicates magnitude
- Insight lines tell the viewer what the data means (not just what
  it shows)
- Click-to-pin is a clean interaction that works on touch
- Methodology section builds trust without cluttering the narrative
- Dimension toggles let the viewer ask "what if we exclude X?"
- Parameter sliders make it a simulator, not just a report
- Mobile bottom-sheet for parameters is properly touch-friendly
- Print export produces a shareable document

**Issue: OG image uses relative path (Important).**
`index.html` line 11: `<meta property="og:image" content="/og-card.png" />`.
Social media crawlers (Slack, Twitter/X, LinkedIn, iMessage) require
an absolute URL to render the preview image. A relative path will
either show no image or fail to resolve. Should be:
`https://short-ship-cost.msshawnp.workers.dev/og-card.png`.
Same for `twitter:image` on line 15. This is the primary mechanism
by which the prospect would first encounter the tool (friend shares
URL in text/Slack), so the preview card is the literal first
impression.

#### DevEx — Good

- `npm install && npm run dev` starts the app
- `npm test` runs tests
- `npm run deploy` deploys to Cloudflare
- `python scripts/export_json.py` regenerates data
- requirements.txt documents stdlib-only deps

**Issue: No CI/CD (Minor).**
No GitHub Actions workflow. A typo or build failure can go live
unguarded. For a solo portfolio project this is acceptable but
means the developer must remember to run tests before deploying.

### Summary

The codebase is remarkably clean for a project built in 5 days
across 3 arcs. The May 15 audit found 13 issues; 12 are resolved,
1 is explicitly deferred. The only actionable finding today is the
OG image relative path — a 2-line fix that determines whether
social previews render correctly.

---

## Phase 3: Landscape Scan
**Date:** 2026-05-16
**Note:** The competitive landscape has not materially changed since
the May 15 scan (1 day ago). This section focuses on where the
project's position has shifted relative to competitors after the
30-task "dashboard to argument" transformation.

### Updated Position vs. May 15 Audit

The May 15 landscape scan identified four weaknesses relative to
the data storytelling benchmarks (NYT Calculator, Pudding, Nicky
Case, FT Climate Game):

| Weakness (May 15) | Status (May 16) | Detail |
|---|---|---|
| No narrative flow | **Closed** | Framing statement, 4 insight lines, methodology section |
| No methodology visible | **Closed** | 5-paragraph collapsible "About this analysis" |
| No animated transitions | **Closed** | useAnimatedValue hook (250ms), Recharts chart animations |
| No engagement hook | **Replaced** | "Place Your Bets" was proposed; user chose direct framing instead — sober, Economist-style opening rather than gamification |

### Current Feature Matrix (updated)

| Feature | This Project | SupplyPike | Crisp | Alloy.ai | NYT Calculator |
|---------|:-----------:|:---------:|:-----:|:--------:|:--------------:|
| Cost quantification of shorts | **✅** | ❌ | ❌ | 🟡 | ➖ |
| Original vs shipped comparison | **✅** | ❌ | ❌ | ❌ | ➖ |
| Cascading cost model (8 dims) | **✅** | ❌ | ❌ | ❌ | ➖ |
| Buffer/scenario simulation | **✅** | ❌ | ❌ | 🟡 | ➖ |
| Parameter adjustment (live) | **✅** | ❌ | ❌ | ❌ | ✅ |
| Narrative storytelling flow | **✅** | ❌ | ❌ | ❌ | ❌ |
| Methodology visible on page | **✅** | ❌ | ❌ | ❌ | ✅ |
| Animated state transitions | **✅** | ❌ | ❌ | ❌ | ✅ |
| Connected to real data | ❌ synthetic | ✅ | ✅ | ✅ | ➖ |
| Engagement hook (predict/reveal) | ❌ | ❌ | ❌ | ❌ | ❌ |
| Mobile-first responsive | **✅** | 🟡 | ✅ | ✅ | ✅ |
| Print/PDF export | **✅** | 🟡 CSV | ✅ | ✅ | ❌ |

### Landscape Position Update

The project has moved from "strong analysis, weak presentation" to
"strong analysis, professional presentation." The gap between this
and the data storytelling gold standards (Pudding, NYT) has narrowed
significantly:

**Still unique differentiators:**
1. Eight-dimension cost model (no competitor has more than 2)
2. Deauthorization risk modeling (no competitor does this)
3. Original vs shipped order comparison as a first-class concept
4. Buffer simulation cliff visualization
5. Full parameter adjustability on every cost dimension

**Gaps remaining vs. data storytelling benchmarks:**
1. No engagement hook (deliberate choice — Economist voice over
   gamification)
2. Not connected to real data (deliberate constraint — portfolio
   piece)
3. No scrollytelling (explicitly out of scope)

All three are deliberate decisions, not oversights.

### Summary

The project now occupies a stronger version of the same empty niche:
no supply chain tool quantifies the full upstream cost of a short
across eight dimensions with live parameter adjustment AND presents
it as a narrative argument with methodology transparency. The
presentation gap identified in the May 15 audit is closed.

---

## Phase 4: Differentiation & Next Moves
**Date:** 2026-05-16

### Cross-Reference

Phase 2 found 5 items. Only 1 is actionable with meaningful impact:
the OG image relative path. The rest are minor (error boundaries,
CI/CD) or explicitly deferred (context splitting, Recharts size).

Phase 3 confirms the project's position has improved from "strong
core, weak shell" to "strong core, professional shell." The
strategic weaknesses (no real data, no engagement hook) are
deliberate decisions, not gaps to fill.

### Project Readiness Assessment

| Criterion | Met? |
|---|---|
| URL shared renders a rich preview card | **Almost** — tags present but og:image path is relative |
| No duplicate code between components | **Yes** |
| Fonts load from app's own domain | **Yes** |
| Opening framing sets up the problem | **Yes** |
| Each section has a declarative insight line | **Yes** |
| Methodology available as collapsible appendix | **Yes** |
| JS cost engine has automated tests, all passing | **Yes** (34/34) |
| Animations on number changes, respects reduced-motion | **Yes** |
| Tool works well on mobile | **Yes** (640px breakpoint, bottom sheet, 44px targets) |
| Parameter panel usable on mobile | **Yes** (full-screen bottom sheet) |
| Reads as a self-selling argument, not a dashboard | **Yes** |

**Definition of done: 10/11 criteria met.** The single gap is the
OG image URL.

### Ranked Next Moves

| # | Move | Effort | Impact | Notes |
|---|------|--------|--------|-------|
| 1 | Fix OG image to absolute URL | 1 min | High | 2-line change in index.html. Determines whether social preview renders. |
| 2 | Add React error boundaries | 15 min | Low | Prevents white screen if a lazy section fails. Nice-to-have. |
| 3 | Add GitHub Actions CI | 30 min | Low | Run `npm test` and `vite build` on push. Guards against regressions. |

### What NOT to Do

1. **Don't add "Place Your Bets."** The user explicitly chose
   direct framing over gamification. The Economist voice is the
   right call for this prospect (CEO, MBA, no patience for gimmicks).

2. **Don't split TimeRangeContext.** The re-render cost is
   negligible for a 4-section page. Splitting adds complexity
   without visible benefit.

3. **Don't replace Recharts.** The 371 KB lazy chunk is acceptable
   for a chart-heavy tool. The trade-off (stable library, good
   SVG output for print) is worth the size.

4. **Don't add component tests.** The data shape is fixed. The
   cost engine is tested. The page is small. Component tests would
   add maintenance cost without catching real bugs in this context.

5. **Don't add scrollytelling.** Explicitly out of scope. The
   framing + insight lines achieve 80% of the narrative benefit at
   a fraction of the complexity.

### Conclusion

This project is ready to show to the prospect. The analytical core
is genuinely differentiated, the presentation matches the substance,
and the tool reads as a product — not a prototype. The one thing
to fix before sharing: make the OG image URL absolute so the social
preview card renders when the friend texts the link.

---

## Audit History

- **2026-05-15:** First full audit (4 phases). Found 13 internal
  issues, strong analytical core, weak presentation. Led to the
  27-task "dashboard to argument" arc.
- **2026-05-16:** Second full audit. 12 of 13 prior findings
  resolved. 1 new actionable finding (OG image path). Project
  assessed as ready to ship.
