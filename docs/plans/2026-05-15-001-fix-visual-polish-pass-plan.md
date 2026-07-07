---
title: "fix: Visual polish — dimension toggle layout and mobile tightening"
status: active
origin: docs/brainstorms/visual-polish-requirements.md
created: 2026-05-15
depth: lightweight
---

# fix: Visual polish — dimension toggle layout and mobile tightening

## Summary

The dimension toggle chip bar wraps unpredictably across 2-3
ragged lines because the label, hint, and 8 chips share a single
flex-wrap container. Fix by separating the label row from the
chip grid, then do a mobile polish pass at 375px.

## Problem Frame

The interactive tool's charts, callouts, and typography look
sharp — Economist-quality. But the chrome above them (dimension
toggles) looks unfinished: ragged wrapping, label text mixed
inline with chips, inconsistent gap sizing. On mobile it's
worse. The gap between chart quality and control quality
undermines the overall impression.

## Scope Boundaries

**In scope:**
- Restructure `DimensionToggle` into label row + chip grid
- CSS grid layout: 4 columns desktop, 2 columns mobile
- Mobile polish pass: fix anything visually rough at 375px
- Existing behavior (toggle, reset, dim state) unchanged

**Out of scope:**
- Chip colors, labels, or interaction behavior
- Narrative or copy changes
- New features
- Desktop chart/table/callout layout
- Print CSS

## Key Technical Decisions

**Grid vs flex for chips.** CSS Grid with explicit column
counts (`repeat(4, 1fr)` / `repeat(2, 1fr)`) guarantees even
rows. Flex-wrap can't ensure even distribution without
JavaScript or fixed chip widths. Grid is the right tool here.

**Label row structure.** Move "DIMENSIONS" label, hint text,
and "Show all" button into their own row above the grid. Label
and hint left-aligned, "Show all" right-aligned (via
`margin-left: auto` or flex justify). This removes them from
the chip flow entirely.

**Chip sizing.** Switch from `auto`-width chips to `1fr` grid
cells so all chips fill their column evenly. The chip button
inside each cell can either fill the cell (`width: 100%`) or
stay intrinsic with the cell providing alignment. Filling the
cell is cleaner — consistent hit targets, consistent visual
weight.

## Implementation Units

### U1. Fix dimension toggle layout

**Goal:** Restructure the dimension toggle bar from a single
flex-wrap container into a label row + chip grid that renders
as clean 4x2 on desktop, 2x4 on mobile.

**Requirements:** R1-R4 from origin doc.

**Dependencies:** None.

**Files:**
- `web/src/components/DimensionToggle.jsx` (modify)
- `web/src/components/DimensionToggle.module.css` (modify)

**Approach:**

Split the current single `.bar` div into two elements:

1. **Label row** — a flex container with:
   - "DIMENSIONS" label (left)
   - "click to exclude" hint (left, after label)
   - "Show all" reset button (right, via `margin-left: auto`)
   
2. **Chip grid** — a CSS grid container with:
   - `grid-template-columns: repeat(4, 1fr)` on desktop
   - `grid-template-columns: repeat(2, 1fr)` on mobile (≤640px)
   - Consistent gap (6-8px)
   - Each chip button fills its grid cell (`width: 100%`)

The outer wrapper keeps the existing `max-width`,
`margin: auto`, and padding from `.bar`.

**Patterns to follow:** The existing `.benchmarks` grid in
`CostStack.module.css` uses the same `grid-template-columns`
+ mobile override pattern. Follow that convention.

**Test scenarios:**

Test expectation: none — pure layout/CSS change with no
behavioral change. Verify visually.

**Verification:**
- At desktop width (≥641px): chips display in 2 rows of 4,
  label row above with "Show all" right-aligned
- At mobile width (375px): chips display in 4 rows of 2
- Toggle a dimension off: "Show all" appears without
  disrupting grid alignment
- Toggle all off then back on: layout remains stable
- `npm run build` succeeds with no new warnings

### U2. Mobile polish pass

**Goal:** Walk the page at 375px viewport and fix anything
that looks visually rough — clipped text, horizontal overflow,
cramped spacing, elements that don't breathe.

**Requirements:** R5-R6 from origin doc.

**Dependencies:** U1 (dimension toggle fix should land first
so mobile pass evaluates the new layout).

**Files:**
- `web/src/components/DimensionToggle.module.css` (likely)
- `web/src/components/Header.module.css` (likely)
- `web/src/components/CostStack.module.css` (possibly)
- `web/src/components/RetailerDrilldown.module.css` (possibly)
- `web/src/components/TimeSeries.module.css` (possibly)
- `web/src/components/BufferSimulation.module.css` (possibly)
- `web/src/App.css` (possibly)

Exact files depend on what the 375px walkthrough reveals.
This unit is intentionally defined as a scan-and-fix pass
rather than pre-enumerating issues.

**Approach:**

Open the dev server, resize to 375px, and scroll top to
bottom. Fix issues as found. Common mobile issues to watch for:

- Header controls wrapping awkwardly or overflowing
- Section titles truncating or line-breaking oddly
- Chart footnotes or source lines overflowing
- Horizontal scrollbars appearing on the page body
- Touch targets smaller than 44px
- Spacing that's too tight (elements not breathing)

Do not rebuild any component. Fixes should be CSS-only
adjustments within existing `@media (max-width: 640px)` blocks.

**Patterns to follow:** Existing mobile overrides in
`CostStack.module.css` (reduces font sizes, stacks benchmarks
vertically) set the convention.

**Test scenarios:**

Test expectation: none — visual CSS fixes. Verify via
viewport testing.

**Verification:**
- Page scrolls vertically only at 375px — no horizontal
  overflow on any section
- All text is readable without zooming
- All interactive elements have ≥44px touch targets
- No clipped content or overlapping elements
- `npm run build` succeeds with no new warnings
