"""
Resolve every DTC order through the hold-for-complete path described
in docs/triage-logic.md Step 5 and parametrized in
docs/cost-engine-benchmarks.md.

Inputs (from data/short_ship_orders.db):
    orders, order_lines_original (DTC subset only)

Outputs (into the same DB):
    dtc_outcomes               — one row per DTC order
    order_lines_shipped        — DTC rows added (retail/distributor
                                 already populated by run_triage.py)
    orders.ship_date           — populated for shipped/cancelled DTC orders
                                 (= resolution_date)

Mechanics:
- Per-line per-day availability probability = 0.85.
- Order ships the day every SKU on the order rolls available
  simultaneously. If still not all available by day MAX_HOLD_DAYS,
  the order is forced to cancel.
- Cumulative cancellation probability is regime-based on days_held:
    days 1-2  -> 10%
    days 3-6  -> 25%
    days 7-13 -> 40%
    day 14+   -> 60%
  (days_held = 0 orders ship immediately and never face cancellation.)
- Of cancellations, 35% resolve as purchased_in_store (DTC-to-retail
  margin leakage); 65% as cancelled_by_customer (lost entirely).
"""
from __future__ import annotations

import random
import sqlite3
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ORDERS_DB = REPO / "data" / "short_ship_orders.db"

PER_LINE_DAILY_AVAILABILITY = 0.85
MAX_HOLD_DAYS = 30
PURCHASED_IN_STORE_PROB = 0.35
SEED = 20260509


def parse_date(s: str) -> date:
    return date.fromisoformat(s)


def cumulative_cancel_prob(days_held: int) -> float:
    """The regime curve from docs/cost-engine-benchmarks.md."""
    if days_held <= 0:
        return 0.0
    if days_held < 3:
        return 0.10
    if days_held < 7:
        return 0.25
    if days_held < 14:
        return 0.40
    return 0.60


def simulate_hold(n_lines: int, rng: random.Random) -> int:
    """Return days_held for an order. Day 0 = immediate availability.
    Each day, redraw availability for the order; the first day all
    lines roll available simultaneously is the ship day.

    Equivalent to: days_held is the smallest d such that on day d
    every one of the n_lines independent Bernoulli(0.85) draws came
    up True. P(all available on a single day) = 0.85^n."""
    p_all_available = PER_LINE_DAILY_AVAILABILITY ** n_lines
    for d in range(0, MAX_HOLD_DAYS + 1):
        if rng.random() < p_all_available:
            return d
    return MAX_HOLD_DAYS  # forced to cancel after this


def main() -> int:
    if not ORDERS_DB.exists():
        print(f"ERROR: {ORDERS_DB} not found")
        return 1

    rng = random.Random(SEED)
    db = sqlite3.connect(ORDERS_DB)
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    # Load DTC orders and their lines
    cur.execute("SELECT * FROM orders WHERE channel_type = 'dtc' ORDER BY order_date")
    dtc_orders = [dict(r) for r in cur.fetchall()]
    cur.execute(
        "SELECT * FROM order_lines_original WHERE order_id IN ("
        "  SELECT order_id FROM orders WHERE channel_type = 'dtc')"
    )
    lines_by_order: dict[str, list[dict]] = defaultdict(list)
    for r in cur.fetchall():
        lines_by_order[r["order_id"]].append(dict(r))

    print(f"Resolving {len(dtc_orders):,} DTC orders...")

    outcomes: list[dict] = []
    shipped_lines: list[dict] = []
    ship_dates: dict[str, str] = {}

    counters = {
        "shipped_complete_day_0": 0,
        "shipped_complete_after_hold": 0,
        "cancelled_by_customer": 0,
        "purchased_in_store": 0,
    }
    line_seq = 0

    for o in dtc_orders:
        order_lines = lines_by_order[o["order_id"]]
        n_lines = len(order_lines)
        order_date = parse_date(o["order_date"])

        days_held = simulate_hold(n_lines, rng)

        # Apply cancellation curve
        cancel_prob = cumulative_cancel_prob(days_held)
        is_cancelled = (days_held > 0 and rng.random() < cancel_prob) or (
            days_held >= MAX_HOLD_DAYS
        )

        if is_cancelled:
            if rng.random() < PURCHASED_IN_STORE_PROB:
                resolution = "purchased_in_store"
            else:
                resolution = "cancelled_by_customer"
            counters[resolution] += 1
            quantity_shipped_factor = 0
        else:
            resolution = "shipped_complete"
            counters[
                "shipped_complete_day_0" if days_held == 0
                else "shipped_complete_after_hold"
            ] += 1
            quantity_shipped_factor = 1

        # Resolution date — same day for shipped (day-0) orders;
        # otherwise the day the hold resolved.
        resolution_date = order_date + timedelta(days=days_held)

        outcomes.append({
            "order_id": o["order_id"],
            "hold_start_date": order_date.isoformat(),
            "resolution": resolution,
            "resolution_date": resolution_date.isoformat(),
            "days_held": days_held,
        })

        # ship_date = resolution_date for shipped or cancelled
        ship_dates[o["order_id"]] = resolution_date.isoformat()

        for L in order_lines:
            line_seq += 1
            shipped_lines.append({
                "order_line_id": f"S-{o['order_id']}-{line_seq:04d}",
                "order_id": o["order_id"],
                "sku": L["sku"],
                "quantity_shipped": L["quantity_ordered"] * quantity_shipped_factor,
                "unit_of_measure": "unit",
                "unit_price": L["unit_price"],
                "original_line_id": L["order_line_id"],
            })

    # Write outputs. dtc_outcomes is fresh; order_lines_shipped and
    # orders are appended/updated.
    cur.executescript("""
        DROP TABLE IF EXISTS dtc_outcomes;
        CREATE TABLE dtc_outcomes (
            order_id          TEXT PRIMARY KEY,
            hold_start_date   DATE NOT NULL,
            resolution        TEXT NOT NULL,
            resolution_date   DATE NOT NULL,
            days_held         INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );
        CREATE INDEX idx_dtc_outcomes_resolution ON dtc_outcomes(resolution);
    """)
    cur.executemany(
        "INSERT INTO dtc_outcomes VALUES "
        "(:order_id, :hold_start_date, :resolution, :resolution_date, :days_held)",
        outcomes,
    )
    cur.executemany(
        "INSERT INTO order_lines_shipped VALUES "
        "(:order_line_id, :order_id, :sku, :quantity_shipped, :unit_of_measure, "
        ":unit_price, :original_line_id)",
        shipped_lines,
    )
    cur.executemany(
        "UPDATE orders SET ship_date = :ship_date WHERE order_id = :order_id",
        [{"order_id": k, "ship_date": v} for k, v in ship_dates.items()],
    )
    db.commit()

    # Reporting
    total = len(dtc_orders)
    print(f"  shipped on day 0:          {counters['shipped_complete_day_0']:,} "
          f"({counters['shipped_complete_day_0']/total*100:.1f}%)")
    print(f"  shipped after hold:        {counters['shipped_complete_after_hold']:,} "
          f"({counters['shipped_complete_after_hold']/total*100:.1f}%)")
    print(f"  cancelled by customer:     {counters['cancelled_by_customer']:,} "
          f"({counters['cancelled_by_customer']/total*100:.1f}%)")
    print(f"  purchased in store:        {counters['purchased_in_store']:,} "
          f"({counters['purchased_in_store']/total*100:.1f}%)")
    cancelled = counters["cancelled_by_customer"] + counters["purchased_in_store"]
    print(f"  total cancellations:       {cancelled:,} ({cancelled/total*100:.1f}%)")

    # Distribution check vs the curve
    print()
    cur.execute(
        "SELECT CASE "
        "  WHEN days_held = 0 THEN '0' "
        "  WHEN days_held < 3 THEN '1-2' "
        "  WHEN days_held < 7 THEN '3-6' "
        "  WHEN days_held < 14 THEN '7-13' "
        "  ELSE '14+' END AS bucket, "
        "  COUNT(*) AS n, "
        "  SUM(CASE WHEN resolution IN ('cancelled_by_customer', 'purchased_in_store') THEN 1 ELSE 0 END) AS canc "
        "FROM dtc_outcomes GROUP BY bucket ORDER BY MIN(days_held)"
    )
    print(f"  {'days_held':<10} {'n':>8} {'cancel %':>10} {'expected':>10}")
    expected = {"0": 0, "1-2": 10, "3-6": 25, "7-13": 40, "14+": 60}
    for r in cur.fetchall():
        bucket, n, c = r["bucket"], r["n"], r["canc"]
        pct = c / n * 100 if n else 0
        print(f"  {bucket:<10} {n:>8,} {pct:>9.1f}% {expected.get(bucket, 0):>9.0f}%")

    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
