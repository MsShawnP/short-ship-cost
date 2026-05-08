"""Cost dimension: triage labor.

The hidden tax on every retail/distributor order: human time spent
manually editing the PO to match available supply. DTC orders go
through automated fulfillment with no admin edit, so they are
excluded here even though they appear in the orders table.

Per docs/cost-engine-benchmarks.md:
- 20 minutes per order edit (median)
- $30/hour blended rate (= $10 per edit)
- ~90% of orders require triage in the current state

Cost = triage_share * orders * (minutes/60) * hourly_rate
     = 0.90 * orders * (20/60) * 30
     = orders * $9 (close to $10/order)
"""
from __future__ import annotations

from .common import aggregate_breakdowns, channel_of, empty_result, open_db
from .parameters import get


def calculate() -> dict:
    db = open_db()
    cur = db.cursor()
    cur.execute(
        """
        SELECT
          o.retailer, o.channel_type,
          substr(o.order_date, 1, 7) AS month,
          COUNT(*) AS n
        FROM orders o
        WHERE o.channel_type IN ('retail', 'distributor')
        GROUP BY o.retailer, o.channel_type, month
        """
    )
    minutes = get("triage_minutes_per_order")
    hourly = get("triage_hourly_rate")
    share = get("triage_share_of_orders")
    cost_per_triaged_order = (minutes / 60.0) * hourly
    cost_per_order_blended = share * cost_per_triaged_order

    rows = []
    for r in cur.fetchall():
        rows.append({
            "retailer": channel_of(r["retailer"], r["channel_type"]),
            "sku": None,
            "month": r["month"],
            "cost": r["n"] * cost_per_order_blended,
        })
    db.close()

    result = empty_result(
        "triage_labor",
        f"Manual order-edit labor at {minutes} min/order × "
        f"${hourly}/hr × {int(share*100)}% of retail/distributor "
        "orders. DTC orders are excluded — they go through automated "
        "fulfillment with no manual edit.",
    )
    result["total_cost"] = sum(r["cost"] for r in rows)
    result.update(aggregate_breakdowns(rows))
    return result


if __name__ == "__main__":
    out = calculate()
    print(f"{out['dimension']:<20} ${out['total_cost']:>15,.0f}")
    for r in out["by_retailer"]:
        print(f"    {r['retailer']:<14} ${r['cost']:>14,.0f}")
