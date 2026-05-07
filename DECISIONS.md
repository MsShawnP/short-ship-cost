# short-ship-cost — Decisions Log

Permanent record of choices that should survive session turnover.
If a decision is reversed, strike it through and add the replacement
below — don't delete.

---

## Format

Each entry:
- **Date** — when decided
- **Decision** — one sentence, imperative voice
- **Why** — the reasoning, including what was tried and rejected
- **Scope** — what this applies to (file, chunk, deliverable, or "global")
- **Do not** — explicit anti-instructions, if any

---

## Architecture & Pipeline

### 2026-05-07 — Use Cinderhaven Provisions as the fictional brand for all data and narrative
- **Why:** Cinderhaven is the shared synthetic dataset across the portfolio. Using it maintains consistency and allows future cross-referencing between projects. This is a portfolio piece, not a client deliverable.
- **Scope:** Global
- **Do not:** Use the prospective lead's company name, data, or identifiable details anywhere in this project.

### 2026-05-07 — Build the interactive tool in React or polished HTML/JS, hosted on Netlify or GitHub Pages
- **Why:** The portfolio already has Streamlit (velocity tool), R/Shiny (health audit), Python CLI tools, and SQL. The gap is a product-quality interactive web tool that a non-technical executive would open in a browser. This fills that gap and demonstrates front-end data storytelling.
- **Scope:** Interactive tool deliverable
- **Do not:** Use Streamlit, Power BI, or Shiny for this project's interactive piece.

### 2026-05-07 — Use the same 18–24 month time window as existing Cinderhaven scan data
- **Why:** Keeps the door open for future projects to JOIN the order data with scan data. Consistency across the Cinderhaven dataset.
- **Scope:** Synthetic order data generation
- **Do not:** Create a different time window that would make cross-referencing impossible.

---

## Data & Schema

### 2026-05-07 — Generate synthetic order data (original + edited) as a new data layer, not modify existing Cinderhaven tables
- **Why:** The existing Cinderhaven dataset has scan data (POS sell-through), not order transactions. Orders are a different data layer. Keep them separate. Order data lives in this repo for now, may move to a separate repo later.
- **Scope:** Data generation
- **Do not:** Add order tables to the cinderhaven-data repo during this project.

### 2026-05-07 — Model three short behaviors by channel
- **Why:** The real-world pattern: retail partners either accept backorders or lose the sale; DTC orders are held until 100% complete, causing cancellations and margin leakage to retail.
- **Scope:** Order generation logic
- **Do not:** Treat all channels the same way for shorts.

---

## Visualization

(No entries yet)

---

## Output Formats

### 2026-05-07 — The export/takeaway document is generated from the tool, not a separate static deliverable
- **Why:** More useful — user configures their view and exports a snapshot with analysis. Also a stronger portfolio piece (shows the tool produces client-ready output). Economist style: plain English, data-forward, clean graphics.
- **Scope:** Export feature
- **Do not:** Build a separate static PDF or document disconnected from the interactive tool.

---

## Writing & Voice

### 2026-05-07 — Economist style for all written output and export
- **Why:** Plain English that tells the truth as presented by the data. Sharp charts with clear labels. No decorative nonsense. Distinct from typical dashboard/consulting-deck aesthetic. Matches the portfolio's voice.
- **Scope:** Global — interactive tool, export, README, all prose
- **Do not:** Use McKinsey/consulting-deck style, marketing language, or data-science-prototype aesthetics.

---

## Reversed / Superseded

(No reversed decisions yet)
