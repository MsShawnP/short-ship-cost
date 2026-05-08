"""Cost dimension: distributor returns.

Read directly from the distributor_returns table populated by
scripts/generate_returns.py. Cost = credit_amount per return row
(the dollar value the brand credits back to the distributor for
returned/claimed product)."""
from __future__ import annotations

from .common import aggregate_breakdowns, empty_result, open_db


def calculate() -> dict:
    db = open_db()
    cur = db.cursor()
    cur.execute(
        """
        SELECT
          o.retailer,
          r.sku,
          substr(r.return_date, 1, 7) AS month,
          r.credit_amount AS cost
        FROM distributor_returns r
        JOIN orders o ON o.order_id = r.order_id
        """
    )
    rows = [
        {
            "retailer": r["retailer"],
            "sku": r["sku"],
            "month": r["month"],
            "cost": float(r["cost"]),
        }
        for r in cur.fetchall()
    ]
    db.close()

    result = empty_result(
        "distributor_returns",
        "Distributor return and claim credits issued to UNFI/KeHE "
        "for unsold promo and written-off product, summed from the "
        "distributor_returns table.",
    )
    result["total_cost"] = sum(r["cost"] for r in rows)
    result.update(aggregate_breakdowns(rows))
    return result


if __name__ == "__main__":
    out = calculate()
    print(f"{out['dimension']:<20} ${out['total_cost']:>15,.0f}")
