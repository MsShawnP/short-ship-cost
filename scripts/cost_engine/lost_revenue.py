"""Cost dimension: lost revenue from short-shipped orders.

Scope: retail and distributor channels only. DTC cancellation losses
are accounted in dtc_cancellations.py to avoid double-counting.

Per line: (qty_ordered - qty_shipped) * pack * unit_price.
"""
from __future__ import annotations

from .common import aggregate_breakdowns, channel_of, empty_result, open_db


def calculate() -> dict:
    db = open_db()
    cur = db.cursor()
    cur.execute(
        """
        SELECT
          o.retailer, o.channel_type,
          lo.sku,
          substr(o.order_date, 1, 7) AS month,
          (lo.quantity_ordered - ls.quantity_shipped) * pm.case_pack_qty * lo.unit_price AS cost
        FROM orders o
        JOIN order_lines_original lo ON lo.order_id = o.order_id
        JOIN order_lines_shipped ls  ON ls.original_line_id = lo.order_line_id
        JOIN ext.product_master pm   ON pm.sku = lo.sku
        WHERE o.channel_type IN ('retail', 'distributor')
          AND ls.quantity_shipped < lo.quantity_ordered
        """
    )
    rows = []
    for r in cur.fetchall():
        rows.append({
            "retailer": channel_of(r["retailer"], r["channel_type"]),
            "sku": r["sku"],
            "month": r["month"],
            "cost": float(r["cost"]),
        })
    db.close()

    result = empty_result(
        "lost_revenue",
        "Lost revenue from short-shipped retail and distributor lines "
        "(qty_ordered - qty_shipped) × pack × unit_price",
    )
    result["total_cost"] = sum(r["cost"] for r in rows)
    result.update(aggregate_breakdowns(rows))
    return result


if __name__ == "__main__":
    out = calculate()
    print(f"{out['dimension']:<20} ${out['total_cost']:>15,.0f}")
    print(f"  by retailer (top): {out['by_retailer'][:4]}")
    print(f"  by month (first 3): {out['by_month'][:3]}")
