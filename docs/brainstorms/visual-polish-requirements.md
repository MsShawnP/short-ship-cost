# Visual Polish Pass — Requirements

**Date:** 2026-05-15
**Scope:** Lightweight
**Status:** Ready for planning

## Problem

The dimension toggle chip bar at the top of the page wraps
unpredictably across 2-3 ragged lines. The "DIMENSIONS" label
and "click to exclude" hint sit inline with the first few chips,
then remaining chips spill to a second and sometimes third line.
On mobile (375px) it's worse — chips are cramped and the layout
looks unfinished. The tool's analytical content and chart quality
are strong; the chrome around it doesn't match.

## Requirements

### Dimension toggle layout

1. The "DIMENSIONS" label (and hint text) must be on its own line
   above the chips, not inline with them.
2. Chips must lay out in a clean grid: two rows of four on desktop,
   or four rows of two on mobile — no ragged wrapping.
3. The optional "Show all" reset button should sit at the end of
   the chip grid or on the label line, not disrupt chip alignment.
4. Chip sizing and spacing must be consistent — no variable gaps
   caused by flex-wrap math.

### Mobile polish (375px viewport)

5. Walk the page top to bottom at 375px and fix anything that looks
   rough: clipped text, horizontal overflow, cramped spacing,
   elements that don't breathe.
6. Existing mobile breakpoints (640px) and bottom-sheet parameter
   panel stay as-is — this is a tightening pass, not a rebuild.

## Non-goals

- No changes to chip colors, labels, or toggle behavior
- No narrative or copy changes
- No new features
- No changes to the desktop layout of sections 1-4 (charts,
  tables, callouts)
- No changes to print CSS

## Success criteria

- Dimension chips display in a clean 4x2 grid on desktop, 2x4
  on mobile — no ragged wrapping under any toggle state
- Page scrolls cleanly at 375px with no horizontal overflow
- `npm run build` succeeds with no new warnings
- Visual quality of the chrome matches the chart quality
