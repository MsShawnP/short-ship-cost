"""Cost dimension: DTC cancelled-by-customer lost revenue.

For DTC orders with resolution = 'cancelled_by_customer' (not
purchased_in_store — those are leakage, see dtc_margin_leakage.py),
the entire order value is lost since DTC is hold-for-complete and
the customer never bought.

Lost revenue per cancelled order = sum of qty_ordered * unit_price
across the order's lines (DTC lines are in units, not cases)."""
from __future__ import annotations

from .common import aggregate_breakdowns, empty_result, open_db


def calculate() -> dict:
    db = open_db()
    cur = db.cursor()
    cur.execute(
        """
        SELECT
          o.retailer,                      -- always 'DTC'
          lo.sku,
          substr(o.order_date, 1, 7) AS month,
          (lo.quantity_ordered * lo.unit_price) AS cost
        FROM orders o
        JOIN order_lines_original lo ON lo.order_id = o.order_id
        JOIN dtc_outcomes do          ON do.order_id = o.order_id
        WHERE do.resolution = 'cancelled_by_customer'
        """
    )
    rows = []
    for r in cur.fetchall():
        rows.append({
            "retailer": "DTC",
            "sku": r["sku"],
            "month": r["month"],
            "cost": float(r["cost"]),
        })
    db.close()

    result = empty_result(
        "dtc_cancellations",
        "Lost revenue from DTC orders the customer cancelled while "
        "held for complete fulfillment — full order value, since "
        "nothing shipped.",
    )
    result["total_cost"] = sum(r["cost"] for r in rows)
    result.update(aggregate_breakdowns(rows))
    return result


if __name__ == "__main__":
    out = calculate()
    print(f"{out['dimension']:<20} ${out['total_cost']:>15,.0f}")
    print(f"  cancelled-by-customer line count: {sum(1 for _ in [])}, total above")
