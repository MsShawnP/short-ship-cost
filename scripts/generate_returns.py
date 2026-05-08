"""
Generate distributor returns and claims for UNFI / KeHE promo orders.

Per docs/cost-engine-benchmarks.md:
- 12% of promo volume returned unsold (reason = unsold_promo)
- 5% of promo volume claimed / written off (reason = claim_filed)
- Non-promo distributor return rates are negligible (modeled as zero)

For each shipped line on a UNFI / KeHE promo order, two stochastic
draws happen at the case level:
- unsold cases ~ Binomial(qty_shipped, 0.12)
- claim cases  ~ Binomial(qty_shipped, 0.05)

Each return row carries quantity_returned (cases), return_date in
[ship_date + 30, ship_date + 90], and a credit_amount in dollars
equal to quantity_returned * case_pack_qty * unit_price.

Inputs (from data/short_ship_orders.db):
    orders, order_lines_shipped (UNFI / KeHE promo subset)

Reference:
    cinderhaven_extract.product_master.case_pack_qty

Output:
    distributor_returns table.
"""
from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXTRACT_DB = REPO / "data" / "cinderhaven_extract.db"
ORDERS_DB = REPO / "data" / "short_ship_orders.db"

UNSOLD_PROMO_RATE = 0.12
CLAIM_FILED_RATE = 0.05
RETURN_LAG_MIN_DAYS = 30
RETURN_LAG_MAX_DAYS = 90
PROMO_DISTRIBUTORS = ("UNFI", "KeHE")
SEED = 20260510


def parse_date(s: str) -> date:
    return date.fromisoformat(s)


def main() -> int:
    if not ORDERS_DB.exists() or not EXTRACT_DB.exists():
        print("ERROR: required DB(s) missing")
        return 1

    rng = random.Random(SEED)
    db = sqlite3.connect(ORDERS_DB)
    db.execute(f"ATTACH DATABASE '{EXTRACT_DB}' AS ext")
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    # Pull every shipped line from UNFI / KeHE promo orders.
    placeholders = ",".join("?" * len(PROMO_DISTRIBUTORS))
    cur.execute(
        f"""
        SELECT
          o.order_id, o.retailer, o.ship_date,
          ls.sku, ls.quantity_shipped, ls.unit_price,
          pm.case_pack_qty
        FROM orders o
        JOIN order_lines_shipped ls ON ls.order_id = o.order_id
        JOIN ext.product_master pm  ON pm.sku = ls.sku
        WHERE o.order_type = 'promo'
          AND o.retailer IN ({placeholders})
          AND ls.quantity_shipped > 0
          AND o.ship_date IS NOT NULL
        ORDER BY o.order_id, ls.sku
        """,
        PROMO_DISTRIBUTORS,
    )
    candidate_lines = [dict(r) for r in cur.fetchall()]
    print(f"Promo lines eligible for return generation: {len(candidate_lines):,}")

    returns: list[dict] = []
    return_seq = 0

    for L in candidate_lines:
        qty = L["quantity_shipped"]
        pack = L["case_pack_qty"] or 1
        unit_price = L["unit_price"]
        ship_d = parse_date(L["ship_date"])

        unsold = rng.binomialvariate(qty, UNSOLD_PROMO_RATE)
        claimed = rng.binomialvariate(qty, CLAIM_FILED_RATE)

        for q, reason in ((unsold, "unsold_promo"), (claimed, "claim_filed")):
            if q <= 0:
                continue
            return_seq += 1
            return_d = ship_d + timedelta(days=rng.randint(RETURN_LAG_MIN_DAYS, RETURN_LAG_MAX_DAYS))
            credit = q * pack * unit_price
            returns.append({
                "return_id": f"RTN-{L['retailer']}-{return_seq:06d}",
                "order_id": L["order_id"],
                "sku": L["sku"],
                "quantity_returned": q,
                "return_reason": reason,
                "return_date": return_d.isoformat(),
                "credit_amount": round(credit, 2),
            })

    cur.executescript("""
        DROP TABLE IF EXISTS distributor_returns;
        CREATE TABLE distributor_returns (
            return_id          TEXT PRIMARY KEY,
            order_id           TEXT NOT NULL,
            sku                TEXT NOT NULL,
            quantity_returned  INTEGER NOT NULL,
            return_reason      TEXT NOT NULL,
            return_date        DATE NOT NULL,
            credit_amount      REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );
        CREATE INDEX idx_returns_order ON distributor_returns(order_id);
        CREATE INDEX idx_returns_reason ON distributor_returns(return_reason);
    """)
    cur.executemany(
        "INSERT INTO distributor_returns VALUES "
        "(:return_id, :order_id, :sku, :quantity_returned, :return_reason, "
        ":return_date, :credit_amount)",
        returns,
    )
    db.commit()

    # Summary report
    cur.execute(
        "SELECT return_reason, COUNT(*) AS n, SUM(quantity_returned) AS qty, "
        "SUM(credit_amount) AS credit FROM distributor_returns GROUP BY return_reason"
    )
    print()
    print(f"  {'reason':<16} {'rows':>8} {'cases':>10} {'credit $':>14}")
    print("  " + "-" * 50)
    for r in cur.fetchall():
        print(f"  {r['return_reason']:<16} {r['n']:>8,} {r['qty']:>10,} {r['credit']:>14,.0f}")

    # Rate validation
    total_promo_cases = sum(L["quantity_shipped"] for L in candidate_lines)
    cur.execute(
        "SELECT return_reason, SUM(quantity_returned) FROM distributor_returns "
        "GROUP BY return_reason"
    )
    print()
    print(f"  Total UNFI/KeHE promo cases shipped: {total_promo_cases:,}")
    for reason, q in cur.fetchall():
        rate = q / total_promo_cases if total_promo_cases else 0
        print(f"  {reason:<16} share of promo volume: {rate*100:5.2f}%")

    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
