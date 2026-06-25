# short-ship-cost — Current Work Plan

The current arc of work. Updated when the arc changes, not every
session. For session-by-session state, see HANDOFF.md.

---

## Current: Phase 3 — Post-reseed alignment

### Goal

Bring all documentation and cross-project references into alignment
with the current platform data ($894K/3yr at 99.3% fill after the
June 20 cinderhaven reseed).

### Tasks

- [ ] P3-1: Update README.md with current figures
    - Fill rate, total cost, dimension breakdown table, buffer
      simulation table all stale (show $6.6M/92.7% from June 14)
    - Shawn writes replacement prose; Claude reports figures

- [ ] P3-2: Update CINDERHAVEN_CANONICAL.md
    - BLOCKED on OTIF overlap scoping note
    - Thesis range ($1.4M–$3.1M) marked "awaiting regen"
    - Multiple figures marked awaiting regen

- [ ] P3-3: Thesis range recomputation
    - Ten decision figures reported in June 14 session
    - Need recomputation with post-reseed numbers
    - Decision 4 dropped from ~$11M/yr to $2.2M/yr (pre-reseed);
      will be lower still at 99.3% fill

- [ ] P3-4: Update check_canonical.py
    - Regression test may need new expected values

- [ ] P3-5: Verify deployed app matches current data
    - Confirm shortships.lailarallc.com shows $894K headline
    - If stale, redeploy

### Out of scope

- Do NOT touch lailara-website
- Do NOT write narrative prose — report figures, Shawn writes text
- Commit and push only after figure approval

---

## Completed: Arc 4 — Dashboard to argument (2026-05-15)

### Goal (archived)

Transform the tool into a self-selling argument that works cold
— a CEO with an MBA opens it on his phone from a friend's text,
and within 90 seconds he sees someone who understands his business
and can do rigorous data work.

## Why this arc, why now

A full 4-phase audit (AUDIT.md) found the analytical core is
genuinely unique — no supply chain tool quantifies the full
upstream cost of a short across eight dimensions. The weakness is
presentation: the tool is a dashboard when it needs to be an
argument. The prospect arrives cold (friend recommended, no
context on what the tool is), is overcommitted, and may open it
on his phone first.

## Business question this arc answers

Same as always: What does it cost a business when it can't
fulfill retail partner orders as submitted? But the tool must
also demonstrate: this person understands your problem and can
do the data work to make it visible.

## Audience

CEO with an MBA at the prospect company. Hands-on, overcommitted,
lean operation. Arrives cold via a friend's recommendation —
evaluating data capabilities, not expecting a specific insight.
May open on phone first; will explore on desktop if hooked.

## Design principles for this arc

- **Direct, not clever.** Sharp framing statement drops him into
  the number. No prediction games or gimmicks.
- **Insight lines, not paragraphs.** One-line declarative
  statements embedded in charts ("Walmart bears 38% of the cost
  — driven by OTIF fines, not lost revenue"). The chart is the
  explanation; the text points at the insight. Nobody sits idle
  reading.
- **Methodology is an appendix.** Available for anyone who wants
  to verify, not on page 1.
- **Interactive means intuitive.** Every interaction answers a
  question the viewer already has. No features for features' sake.
- **Animations communicate, not decorate.** Motion shows magnitude
  of change. Required, not optional.
- **Mobile is required.** Works well on mobile, shines on desktop.
  Real scenario: CEO gets a text with the link, opens it on his
  phone between meetings.

## Tasks

### Wave 1 — Quick wins

- [x] OG/meta tags + social card — add `<meta>` description,
      OG title/description/image, Twitter card to `index.html`.
      Consider a static screenshot as OG image.
- [x] Code cleanup bundle — fix duplicate `SEQUENTIAL_TEALS` in
      `CostStack.jsx` (import from `lib/dimensions.js`), extract
      `hexToRgba` to `lib/format.js`, consolidate dimension
      ordering to one canonical export, fix footer repo-path
      reference.
- [x] Self-host fonts — download Playfair Display + Source Sans 3
      woff2 files, serve from `web/public/fonts/`, remove Google
      Fonts `<link>`, add local `@font-face` declarations.
- [x] Python dependency manifest — add `requirements.txt` or
      minimal `pyproject.toml` documenting stdlib-only deps.

### Wave 2 — Direct framing statement

- [x] Opening framing — replace the current cold open with a
      sharp 2-3 sentence statement that sets up the problem in
      plain English: the original order is overwritten, the cost
      disappears, here's what it actually looks like. Then drop
      straight into the $25.6M headline. Must work on mobile.
      Print CSS should include it as the document's opening.

### Wave 3 — Narrative + methodology

- [x] Insight lines between sections — add one-line declarative
      statements above or below each chart that tell the viewer
      what the data means. Not paragraphs. "Walmart bears 38% of
      the cost" not "In this section you will see a breakdown by
      retailer." Dynamic where possible (driven by the data, not
      hardcoded). Economist voice.
- [x] Methodology appendix — collapsible "About this analysis"
      section at the bottom of the page. Covers: synthetic data
      modeled on a ~$25M brand, 43K orders, 8 cost dimensions,
      all parameters tunable, methodology documented. Frame as
      transparency, not caveat. Replace footer repo-path reference
      with a link to this section.

### Wave 4 — Safety net

- [x] JS cost engine tests — test file for `utils/costEngine.js`
      covering all exported functions at baseline params (match
      `validation.json`) AND at modified params (known-input
      snapshots). Install vitest or use Node's built-in test
      runner.

### Wave 5 — Polish + mobile

- [x] Animated state transitions — animate number changes
      (count-up on headline, smooth interpolation on benchmarks),
      chart reflows on filter/toggle changes, parameter
      recalculations. Respect `prefers-reduced-motion`. 150-300ms,
      purposeful — motion communicates magnitude.
- [x] Palette evaluation — review teal palette in Sections 2-3.
      If lightest 3 shades are indistinguishable at normal viewing
      distance, increase contrast on those only. Test side by side
      before changing.
- [x] Mobile experience — upgrade from "responsive but desktop-
      primary" to "works well on mobile, shines on desktop." Key
      areas: flow-split chart readability at small widths, SKU
      table horizontal scroll, parameter panel as full-screen
      bottom sheet on mobile, touch targets for click-to-pin,
      print button placement. Test on actual phone viewport.

## Out of scope for this arc

- Connecting to real/live retailer data
- Scrollytelling retrofit
- Splitting TimeRangeContext
- "Place Your Bets" or prediction-style opening
- Multi-retailer data feeds, EDI connectors, AI agents
- Full palette redesign (targeted fix only if evaluation warrants)

## Definition of done for this arc

- [x] URL shared in Slack renders a rich preview card
- [x] No duplicate code between components (colors, utilities)
- [x] Fonts load from the app's own domain
- [x] Opening framing statement sets up the problem before the
      headline number
- [x] Each section has a declarative insight line that tells the
      viewer what the data means
- [x] Methodology section available as a collapsible appendix
- [x] JS cost engine has automated tests at baseline and non-
      baseline params, all passing
- [x] Animations on number changes, chart reflows, and parameter
      recalculations; respects prefers-reduced-motion
- [x] Tool works well on mobile (tested at phone viewport)
- [x] Parameter panel usable on mobile (full-screen sheet or
      drawer)
- [x] The tool reads as a self-selling argument, not a dashboard

---

## Decomposition

### Wave 1 — Quick wins

Goal: Clean up code debt and polish the surface before bigger
changes land.

- [x] 1A: OG/meta tags + social card
    - Depends on: none
    - Add `<meta name="description">`, OG title/description/image,
      Twitter card to `web/index.html`. Use a static screenshot
      or generate a simple branded card as the OG image file.
    - Done when: pasting the URL into Slack/Teams preview shows
      title, description, and image (test via opengraph.xyz or
      similar validator)

- [x] 1B: Code cleanup — deduplicate colors and utilities
    - Depends on: none
    - Remove `SEQUENTIAL_TEALS` from `CostStack.jsx`, import
      `DIMENSION_COLOR` from `lib/dimensions.js`. Extract
      `hexToRgba` from `RetailerDrilldown.jsx` and
      `BufferSimulation.jsx` into `lib/format.js`. Remove
      `DIMENSION_ORDER` from `dimensions.js` and
      `ALL_DIMENSIONS` from `timeRange.jsx` — pick one canonical
      export, use it everywhere.
    - Done when: `npm run build` succeeds, grep finds zero
      duplicate definitions of color maps or `hexToRgba`, and
      only one file exports the dimension order array

- [x] 1C: Fix footer repo-path reference
    - Depends on: none
    - Replace `docs/cost-engine-docs.md` in the footer with
      either a link to the GitHub file or (better, since Wave 3
      adds methodology) a placeholder "Methodology" text that
      Wave 3 will link to the appendix.
    - Done when: footer text makes sense to a non-developer
      visitor — no local file paths

- [x] 1D: Self-host fonts
    - Depends on: none
    - Download Playfair Display (400/500/700) and Source Sans 3
      (400/600/700) woff2 files. Place in `web/public/fonts/`.
      Add `@font-face` declarations in `index.css` or a new
      `fonts.css`. Remove Google Fonts `<link>` from
      `index.html`.
    - Done when: dev server loads with no requests to
      `fonts.googleapis.com` (verify in Network tab), and
      typography renders identically

- [x] 1E: Python dependency manifest
    - Depends on: none
    - Add `requirements.txt` with a comment explaining stdlib-only
      deps, or a minimal `pyproject.toml`.
    - Done when: file exists at repo root and a new developer
      would understand they don't need to `pip install` anything

### Wave 2 — Direct framing statement

Goal: Replace the cold open with a sharp problem statement that
earns the first 90 seconds.

- [x] 2A: Write framing copy
    - Depends on: none
    - Draft 2-3 sentences in Economist voice that set up the
      problem: original order overwritten, cost disappears,
      here's what it actually looks like. Write as plain text
      first, iterate on voice before touching code. The copy
      must work for someone who doesn't know what short-shipping
      is.
    - Done when: copy is written, reviewed, and reads as a sharp
      opening — not marketing, not academic, not apologetic

- [x] 2B: Implement framing component
    - Depends on: 2A
    - Add the framing copy as a component or section above the
      existing `CostStack` headline in `App.jsx`. Style it
      consistent with the design spec — Playfair Display for any
      lead-in, Source Sans for body. Must not push the $25.6M
      number below the fold on desktop.
    - Done when: dev server shows the framing text above the
      headline number, and the number is still visible without
      scrolling on a 1440px-wide / 900px-tall viewport

- [x] 2C: Verify framing on mobile + print
    - Depends on: 2B
    - Test at 375px width (iPhone SE). Framing text must be
      readable and the headline number visible within one scroll.
      Verify print CSS includes the framing as the document's
      opening paragraph.
    - Done when: mobile viewport shows framing + headline without
      excessive scrolling; print preview starts with the framing

### Wave 3 — Narrative + methodology

Goal: Add insight lines that tell the viewer what the data means,
and a methodology appendix for anyone who wants to verify.

- [x] 3A: Section 1 insight line
    - Depends on: 1B (needs clean dimension imports)
    - Add a data-driven declarative line to the CostStack section.
      Dynamic: compute from the data (e.g., "Lost revenue alone
      accounts for {X}% — the remaining {Y} in cascading costs
      are invisible because the original order is overwritten").
    - Done when: insight line renders below the headline, updates
      when time range or dimension toggles change, and reads as
      a finding — not a description of the chart

- [x] 3B: Section 2 insight line
    - Depends on: 1B
    - Add a data-driven declarative line to RetailerDrilldown.
      Dynamic: identify the top retailer and its dominant cost
      dimension from the data (e.g., "{Retailer} bears {X}% of
      the cost — driven by {dimension}").
    - Done when: insight line renders, updates on filter changes,
      and correctly reflects the top retailer from current data

- [x] 3C: Section 3 insight line (existing dynamic title sufficient)
    - Depends on: 1B
    - Add a data-driven declarative line to TimeSeries. The
      existing dynamic title already does trend detection
      (rising/eased/steady). Evaluate whether it's sufficient
      as an insight line or needs strengthening. If sufficient,
      mark done.
    - Done when: Section 3 has a declarative insight that tells
      the viewer whether costs are getting worse

- [x] 3D: Section 4 insight line (existing title + cliff callout sufficient)
    - Depends on: 1B
    - Add a data-driven declarative line to BufferSimulation.
      The existing title already says "At 90% fill rate, {X} in
      costs disappear." Evaluate whether it's sufficient. If the
      deauth cliff callout already serves as the insight, mark
      done.
    - Done when: Section 4 has a clear "so what" statement that
      tells the viewer the one lever that matters most

- [x] 3E: Methodology appendix
    - Depends on: 1C (footer reference needs updating)
    - Add a collapsible "About this analysis" section at the
      bottom of the page, above the footer. Content: synthetic
      data modeled on a ~$25M specialty food brand, 43K orders
      over 2 years, 8 cost dimensions, all parameters tunable
      via the sidebar panel, full methodology documented. Frame
      as transparency. Collapsed by default. Update footer to
      link to this section instead of the repo path.
    - Done when: collapsible section renders, starts collapsed,
      expands on click, and contains methodology overview;
      footer links to it; print CSS includes the methodology
      expanded

- [x] 3F: Verify narrative flow end-to-end
    - Depends on: 2B, 3A, 3B, 3C, 3D, 3E
    - Read the page top to bottom as the CEO would. Framing →
      headline → insight → drill-down → insight → trend →
      insight → recovery → insight → methodology. Does it read
      as an argument? Flag any place where the flow breaks or
      the viewer would be confused.
    - Done when: the page tells a story from "the cost is
      invisible" to "here's the one lever" without requiring
      the viewer to figure it out themselves

### Wave 4 — Safety net

Goal: Test the JS cost engine so slider interactions are safe
before the prospect uses them.

- [x] 4A: Set up test runner
    - Depends on: none
    - Install vitest (or configure Node's built-in test runner)
      in `web/`. Add a `test` script to `package.json`. Create
      an empty test file that imports from `utils/costEngine.js`
      and runs one trivial assertion.
    - Done when: `npm test` runs and passes

- [x] 4B: Baseline validation tests
    - Depends on: 4A
    - Load `validation.json` and the baseline JSON data files.
      Run `summaryFromMonthly`, `scaleCostByRetailer`,
      `scaleCostBySku`, `scaleBufferScenarios` at baseline
      params. Assert each dimension total matches
      `validation.json` within $1 tolerance.
    - Done when: `npm test` passes with per-dimension baseline
      assertions

- [x] 4C: Parameter-adjusted tests
    - Depends on: 4B
    - Create 2-3 known-input scenarios: double the Walmart OTIF
      rate, lower deauth distributor threshold to 0.8, zero out
      triage labor. For each, compute expected outputs by hand
      (or derive from the ratio logic), assert the JS functions
      match. Test `filterDeauthEvents` with threshold changes.
    - Done when: `npm test` passes with non-baseline parameter
      scenarios and deauth event filtering assertions

- [x] 4D: Edge case tests
    - Depends on: 4B
    - Test `getRatios` with zero baseline values (should return
      1, not NaN/Infinity). Test `clampCost` with negative and
      non-finite inputs. Test `validateBaseline` with a
      deliberately wrong input (should return mismatches).
    - Done when: `npm test` passes with edge case assertions

### Wave 5 — Polish + mobile

Goal: Make the tool feel alive and work on any screen.

- [x] 5A: Animate headline number
    - Depends on: 2B (framing component exists)
    - Add a count-up animation on the $25.6M headline when it
      first appears (or when its value changes from a filter/
      param change). Use `requestAnimationFrame`, not a library.
      150-300ms duration. Respect `prefers-reduced-motion` (snap
      to final value).
    - Done when: headline number counts up on load; changing a
      parameter causes a smooth transition to the new value;
      `prefers-reduced-motion` skips the animation

- [x] 5B: Animate benchmark numbers + stat blocks
    - Depends on: 5A (reuse the animation utility)
    - Apply the same count-up/interpolation to the three
      benchmark values in Section 1 and the three stat blocks
      in Section 3. Extract the animation logic into a reusable
      hook or utility.
    - Done when: all numeric displays animate on value change;
      animation utility is shared, not duplicated

- [x] 5C: Animate chart transitions
    - Depends on: none
    - When time range or dimension toggles change, animate the
      chart reflows: flow-split paths morph, stacked area layers
      transition, bar heights interpolate. For Recharts
      components, enable `isAnimationActive` with short duration.
      For custom SVG (CostStack), add CSS transitions on path `d`
      or use interpolated re-renders. Respect reduced-motion.
    - Done when: toggling a dimension or changing the time range
      produces a visible, smooth transition in all 4 sections

- [x] 5D: Palette evaluation
    - Depends on: none
    - Take screenshots of Sections 2 and 3 at current palette.
      Evaluate whether the lightest 3 teal shades
      (`#93DCD2`, `#BDEEE8`, `#6BCABD`) are distinguishable at
      normal viewing distance. If not, increase contrast on those
      3 only. Test both versions side by side.
    - Done when: decision is made (keep or adjust) and documented
      in DECISIONS.md with rationale

- [x] 5E: Mobile — layout and typography
    - Depends on: 1D (fonts self-hosted), 2B (framing exists)
    - At 375px width: ensure framing text, headline, benchmarks,
      and section titles are readable. Reduce headline font size.
      Stack benchmarks vertically. Ensure no horizontal overflow.
      Add CSS breakpoints in `tokens.css` or component CSS
      modules.
    - Done when: at 375px viewport, page scrolls vertically only
      (no horizontal scroll), all text is readable, headline
      number is prominent

- [x] 5F: Mobile — charts
    - Depends on: 5E
    - Flow-split chart: test SVG viewBox scaling at narrow widths.
      Labels may need to move below blocks instead of beside
      them. Recharts sections: verify `ResponsiveContainer` fills
      width. Stacked bar labels: ensure they don't overlap at
      small widths. SKU table: add horizontal scroll wrapper if
      not already working at 375px.
    - Done when: all 4 section charts are readable and
      interactive at 375px; no clipped or overlapping labels

- [x] 5G: Mobile — parameter panel
    - Depends on: 5E
    - Convert the 360px fixed sidebar to a full-screen bottom
      sheet on viewports < 768px. Slide up from bottom, scrim
      behind, close button at top, scrollable body. Touch-
      friendly slider targets (min 44px hit area). Keep desktop
      behavior unchanged.
    - Done when: at 375px viewport, "Adjust parameters" opens a
      full-screen sheet from the bottom; sliders are usable with
      touch; closing returns to the analysis

- [x] 5H: Mobile — touch targets and interactions
    - Depends on: 5F, 5G
    - Ensure click-to-pin works with touch (no hover dependency).
      Verify all interactive elements (dimension chips, filter
      dropdowns, sort headers, print button) have minimum 44px
      touch targets. Test pinned callout dismissal on touch.
    - Done when: all interactive elements work on touch device
      (or phone-width browser with touch simulation); no element
      requires hover to function

- [x] 5I: Mobile + animation integration test
    - Depends on: 5A, 5B, 5C, 5F, 5G, 5H
    - Full walkthrough at 375px: open page, read framing, see
      headline animate, scroll through all 4 sections, pin a
      retailer, change time range (verify chart animation),
      open parameter panel (verify bottom sheet), adjust a
      slider (verify number animation), print. Flag anything
      broken.
    - Done when: complete walkthrough passes on phone-width
      viewport with no broken interactions, clipped content,
      or janky animations

---

### Arc 3 — Dashboard to argument (completed 2026-05-15)

27 tasks across 5 waves: narrative framing, insight lines,
methodology appendix, JS cost engine tests (34/34 pass), animated
number transitions, Recharts chart animations, mobile bottom-sheet
parameter panel, responsive breakpoints at 640px. OG social card
image added. Palette evaluated and kept (deltaE 8.7-15.5).

---

## Goal (2026-05-15)

Visual polish pass — fix sloppy dimension toggle layout and
tighten mobile presentation. No narrative/copy changes, no new
features. Quality pass at own pace (no deadline).

Specific issues:
- Dimension toggle chips wrap unpredictably across 2-3 ragged
  lines mixed with label text. Should be one clean row or two
  even rows.
- General mobile polish — anything that looks rough at phone width.

Side deliverable: extracted the full short-ship-cost design system
(colors, fonts, layout, interaction patterns) to
`~/projects/active/CLAUDE.md` as the official Lailara LLC standard.

## Tasks

- [x] U1: Fix dimension toggle layout — label row + chip grid
      (4x2 desktop, 2x4 mobile)
- [x] U2: Mobile polish pass at 375px — scan and fix
- [x] U3: Center benchmark/stat grid values (CostStack + TimeSeries)

---

## Decomposition: Data resync and deploy

Goal: Bring the deployed web app into alignment with the rebuilt
pipeline (50 SKUs, 157 weeks, $33.2M total cost) and clean up
dead artifacts.

Steps:

- [x] D1: Re-export JSON from rebuilt databases
    - Depends on: none
    - Run `python scripts/export_json.py` from repo root.
    - Done when: script prints "PASS" sanity check and all 9 JSON
      files in `web/public/data/` have `last_updated` timestamps
      from today, `meta.json` shows 50 SKUs and ~66K orders

- [x] D2: Verify tests pass with new data
    - Depends on: D1
    - Run `cd web && npm test`
    - Done when: 34/34 tests pass (validates JS cost engine still
      reconciles against the new validation.json)

- [x] D3: Update hardcoded numbers in methodology section
    - Depends on: D1 (need actual numbers from new meta.json)
    - Edit `web/src/App.jsx` lines 269–273: update order count,
      line count, and time window description to match new data
    - Done when: methodology text says "74,306 orders and 272,352
      line items over a 3-year window" (or whatever meta.json shows)

- [x] D4: Update OG/Twitter meta descriptions
    - Depends on: D1 (need new headline total)
    - Edit `web/index.html` lines 9 and 14: replace "$25.6M" with
      the new rounded total from validation.json
    - Done when: `grep "og:description" web/index.html` shows the
      new dollar amount

- [x] D5: Update README.md headline numbers
    - Depends on: D1
    - Edit `README.md` lines 24 and 39–41: update order count,
      shipped revenue, headline cost, and percentage
    - Done when: README numbers match the new pipeline output

- [x] D6: Build and deploy
    - Depends on: D2, D3, D4, D5
    - Run `cd web && npm run build && npm run deploy`
    - Done when: build succeeds with 0 errors/warnings, deploy
      completes, live URL shows new headline number

- [x] D7: Clean up dead code and stale docs
    - Depends on: none (independent)
    - Delete `scripts/add_kehe.py`. Rewrite `data/README.md`
      "What this project will add" section to describe what exists.
    - Done when: `add_kehe.py` is gone, `data/README.md` has no
      references to tables that "will be" built

---

## Arc history

### Arc 1 — Synthetic order data + cost engine (completed 2026-05-07)

Generated synthetic order dataset (43,110 orders, 125,748 lines,
$51.9M shipped over 18-24 months) and built modular cost engine
calculating all eight cost dimensions. Total cost of shorts: $25.6M
= 49.4% of shipped revenue. Buffer simulation shows 86% recovery at
95% fill rate with deauthorization cliff at 90%. 35/35 validation
checks pass. Three databases (cinderhaven_extract.db, short_ship_orders.db,
short_ship_cost.db) documented in docs/cost-engine-docs.md.

### Arc 2 — Interactive tool (completed 2026-05-08)

Built the React app in 11 tasks: Vite scaffold, JSON export,
design spec, 4 sections (flow-split, retailer/SKU drill-down,
time series, buffer staircase), parameter panel with JS cost
engine, print CSS, polish pass, Cloudflare Pages deploy. Custom
SVG charts, click-to-pin callouts, global time-range filter,
dimension toggles, code-split Recharts. 218 KB initial / 371 KB
lazy chunk. Deployed to shortships.lailarallc.com.
