# Interactive Tool — Design Spec

Reference document for building the single-page React app.
Chart types and layouts may be adjusted after seeing how they
render — this is the starting point, not a locked contract.

---

## Page structure (top to bottom)

1. **Header** — Cinderhaven Provisions branding, title
   ("Cost of Short-Shipping Analysis"), print/export button
2. **Section 1: The Cost Stack** — headline number,
   eight-dimension breakdown
3. **Section 2: Where the Pain Lands** — retailer and SKU
   drill-down
4. **Section 3: The Trend** — monthly time series
5. **Section 4: What Recovery Looks Like** — buffer simulation
   staircase
6. **Parameter panel** — collapsible right sidebar for
   threshold/rate adjustments
7. **Footer** — data window, methodology note, Lailara LLC
   credit

---

## Typography

- **Headlines:** Playfair Display (Google Fonts), serif
- **Body / chart labels / UI:** Source Sans Pro (Google Fonts),
  sans-serif
- **Headline sizes:** Section titles 28px, chart titles 20px,
  callout numbers 48px
- **Body size:** 16px base, chart labels 12–14px, footnotes 11px
- **Line height:** 1.5 for body, 1.2 for headlines

---

## Color palette

### Primary
- **Background:** #F8F6F1 (warm off-white)
- **Data primary:** the darkest tone of the dimension palette below

### Dimension color mapping (sequential teal, darkest = largest)
- Lost revenue: #0A3D3D
- Deauthorization: #14605C
- OTIF fines: #1F8078
- Chargebacks: #2A9D93
- DTC cancellations: #45B5AA
- Triage labor: #6BCABD
- Distributor returns: #93DCD2
- DTC margin leakage: #BDEEE8

The palette is sequential by magnitude rank, not categorical. The same dimension reads the same color page-wide so the eye can track it across sections.

### Text
- Body text: #2A2A2A (dark charcoal, not pure black)
- Secondary text / annotations: #6B6B6B
- Chart gridlines: #E5E0D8

---

## Chart style rules (Economist-inspired)

- No chart borders or boxes — charts float on the page
- Horizontal gridlines only — no vertical gridlines
- Labels directly on the data — minimize legends
- Left-aligned titles above each chart — bold, declarative,
  tells you what the chart says, not what it shows
  (e.g., "Short-shipping costs Cinderhaven $25.6M" not
  "Cost Summary by Dimension")
- Axis labels minimal — no redundant axis titles if the
  chart title already explains the metric. Y-axis gets a
  unit label ($M, %), X-axis usually self-explanatory
- No 3D, no gradients, no shadows, no rounded corners on bars
- Source/footnote line below each chart — small text,
  left-aligned
- Use Intl.NumberFormat for all currency display ($25.6M
  not $25,597,978)

---

## Section 1: The Cost Stack

- **Callout:** $25.6M as a large number (48px Playfair Display),
  with "49.4% of shipped revenue" beneath it in secondary text
- **Chart:** Waterfall chart — starts at $0, builds through each
  cost dimension to $25.6M total. Lost revenue is the large
  first block, then cascading costs stack on top. Final bar
  is the total. Color-coded by dimension mapping above.
- **Chart title:** Declarative — e.g., "Beyond the revenue gap:
  $6.9M in cascading costs the business cannot see"
- **Contextual benchmarks below chart:** total cost as % of
  shipped revenue, as % of estimated gross margin

---

## Section 2: Where the Pain Lands

- **Chart 1:** Grouped horizontal bar chart — retailers on
  Y-axis, cost on X-axis, bars color-coded by dimension group.
  Shows which retailers bear the most cost and what kind.
- **Chart 2 / Table:** Sortable table of top 20 SKUs by total
  cost, with dimension breakdown per row. Include "Other
  (62 SKUs)" row. Footnote explaining triage labor is excluded
  from SKU attribution ($39K difference from headline total).
- **Interaction:** Click a retailer bar to filter the SKU table
  to that retailer's SKUs only.

---

## Section 3: The Trend

- **Chart:** Stacked area chart — months on X-axis, cost ($) on
  Y-axis, areas colored by dimension group. Shows whether the
  problem is growing, seasonal, or stable.
- **Chart title:** Declarative based on what the data shows
  (e.g., "The cost of shorts held steady — the business never
  saw it improving or worsening")

---

## Section 4: What Recovery Looks Like

- **Chart 1:** Stepped bar chart — four scenarios (80/85/90/95%)
  on X-axis, total cost on Y-axis. Horizontal dashed line at
  baseline ($25.6M). Each bar shows the reduced total cost at
  that fill rate. The 90% bar gets a visual annotation
  highlighting the deauthorization cliff (vertical marker or
  background shading with label).
- **Chart 2:** Small multiples or table showing per-dimension
  recovery at each scenario. Emphasize that OTIF stays sticky
  (Walmart's 98% threshold) while deauth drops off a cliff
  at 90%.
- **Chart title:** e.g., "At 90% fill rate, $15.8M in costs
  disappear — most of it from distributor deauthorization"

---

## Parameter panel

- Collapsible right sidebar, 320px wide
- When open, main content does not reflow (stays at 900px)
- **Controls:** Sliders for:
  - OTIF fine rates (per retailer)
  - Deauthorization velocity thresholds (per retailer)
  - Distributor fill rate threshold (the 90% cliff — draggable)
  - DTC margin spread
  - Triage labor rate and time per edit
- Each slider shows current value and baseline default
- **Reset to Baseline button** at top of panel
- Changes trigger recalculation via useMemo — no stutter
- Recalculated totals update all sections in real time

---

## Layout

- Max content width: 900px, centered
- Charts: 800–900px wide with padding
- Section spacing: 60px minimum between sections
- Parameter panel: 320px sidebar, does not push main content

---

## Print layout (@media print)

- Parameter panel hidden
- Print button hidden
- Each section starts on a new page (page-break-before)
- Background color set to white (not off-white)
- Footer on every printed page: "Cost of Short-Shipping —
  Cinderhaven Provisions" left-aligned, page number
  right-aligned
- Small text in footer: date generated, parameter snapshot
  (whether defaults or user-modified values)
- Charts scale to fit printed page width without distortion
- Chart animations disabled before print renders
