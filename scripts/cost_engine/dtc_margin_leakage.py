"""Cost dimension: DTC-to-retail margin leakage.

For DTC orders with resolution = 'purchased_in_store' the customer
gave up on the held DTC order and bought the same product in-store
instead. The brand still earns wholesale margin (~35%) on the
in-store purchase, but loses the spread to DTC margin (~55%) it
would have earned on the original DTC order.

Leakage per order = order_value × (dtc_margin - wholesale_margin)
                  = order_value × 20% (default).

`order_value` here is the original DTC order value (sum of
qty * unit_price at DTC pricing)."""
from __future__ import annotations

from .common import aggregate_breakdowns, empty_result, open_db
from .parameters import get


def calculate() -> dict:
    db = open_db()
    cur = db.cursor()
    margin_diff = get("dtc_margin_pct") - get("wholesale_margin_pct")
    cur.execute(
        """
        SELECT
          lo.sku,
          substr(o.order_date, 1, 7) AS month,
          (lo.quantity_ordered * lo.unit_price) AS order_value
        FROM orders o
        JOIN order_lines_original lo ON lo.order_id = o.order_id
        JOIN dtc_outcomes do          ON do.order_id = o.order_id
        WHERE do.resolution = 'purchased_in_store'
        """
    )
    rows = []
    for r in cur.fetchall():
        rows.append({
            "retailer": "DTC",
            "sku": r["sku"],
            "month": r["month"],
            "cost": float(r["order_value"]) * margin_diff,
        })
    db.close()

    result = empty_result(
        "dtc_margin_leakage",
        f"Margin lost when DTC customers gave up on a held order and "
        f"bought in-store instead — order_value × "
        f"(dtc_margin - wholesale_margin) = order_value × "
        f"{margin_diff*100:.0f}%.",
    )
    result["total_cost"] = sum(r["cost"] for r in rows)
    result.update(aggregate_breakdowns(rows))
    return result


if __name__ == "__main__":
    out = calculate()
    print(f"{out['dimension']:<20} ${out['total_cost']:>15,.0f}")
