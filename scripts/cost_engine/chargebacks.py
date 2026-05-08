"""Cost dimension: retailer chargebacks beyond OTIF fines.

The Cinderhaven extract has a `chargebacks` table with historical
totals by retailer / month / reason / SKU, but those are pre-existing
data-quality and shipment chargebacks unrelated to this project's
generated shorts — using them as the rate schedule would be wrong
because they were not produced by our orders.

Approach used here: estimated chargeback rates applied to shorted
goods value:
  Walmart, Costco: 0.5% of shorted goods value
  Other retailers: 0.3% of shorted goods value
DTC orders generate no chargebacks.

Flagged in the cost_summary description so a viewer knows the source
is the fallback rate, not the historical table."""
from __future__ import annotations

from .common import aggregate_breakdowns, channel_of, empty_result, open_db
from .parameters import REGIONAL_CHAINS, get


def _rate_for(retailer: str) -> float:
    if retailer in ("Walmart", "Costco"):
        return get("chargeback_rate_walmart_costco")
    if retailer == "DTC":
        return 0.0
    return get("chargeback_rate_other")


def calculate() -> dict:
    db = open_db()
    cur = db.cursor()
    cur.execute(
        """
        SELECT
          o.retailer, o.channel_type,
          lo.sku,
          substr(o.order_date, 1, 7) AS month,
          (lo.quantity_ordered - ls.quantity_shipped) * pm.case_pack_qty * lo.unit_price AS shorted_value
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
        rate = _rate_for(r["retailer"])
        if rate <= 0 or r["shorted_value"] <= 0:
            continue
        rows.append({
            "retailer": channel_of(r["retailer"], r["channel_type"]),
            "sku": r["sku"],
            "month": r["month"],
            "cost": float(r["shorted_value"]) * rate,
        })
    db.close()

    result = empty_result(
        "chargebacks",
        "Estimated retailer chargebacks beyond OTIF — fallback rates "
        "of 0.5% (Walmart/Costco) and 0.3% (other) applied to shorted "
        "goods value. Cinderhaven's historical chargebacks table was "
        "not used because those rows reflect data-quality and "
        "shipment issues unrelated to our synthetic shorts.",
    )
    result["total_cost"] = sum(r["cost"] for r in rows)
    result.update(aggregate_breakdowns(rows))
    return result


if __name__ == "__main__":
    out = calculate()
    print(f"{out['dimension']:<20} ${out['total_cost']:>15,.0f}")
    for r in out["by_retailer"]:
        print(f"    {r['retailer']:<14} ${r['cost']:>14,.0f}")
