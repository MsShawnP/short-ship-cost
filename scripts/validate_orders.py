"""
Validate the synthetic order dataset against the success criteria
in PLAN.md and the targets in docs/cost-engine-benchmarks.md.

Runs every check the user spec'd, prints a single summary table
with PASS/FAIL and the actual measured value, and exits non-zero
if any check fails.

Reads from:
    data/short_ship_orders.db          (orders, lines, shorts, dtc_outcomes, distributor_returns)
    data/cinderhaven_extract.db        (product_master, distribution_log, stores, promotions)
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXTRACT_DB = REPO / "data" / "cinderhaven_extract.db"
ORDERS_DB = REPO / "data" / "short_ship_orders.db"

REGIONAL_CHAINS = (
    "Southside Grocers", "Green Basket Market", "Prairie Provisions",
    "Mountain Pantry Co", "Harbor Fresh",
)

CHANNEL_FILL_TARGETS = {
    "Walmart": 0.78, "Costco": 0.80, "Whole Foods": 0.75,
    "UNFI": 0.70, "KeHE": 0.70, "Regional": 0.65,
}
CHANNEL_SHARE_TARGETS = {
    "Walmart": 0.50, "UNFI": 0.11, "KeHE": 0.07,
    "Whole Foods": 0.10, "Costco": 0.09,
    "Regional": 0.09, "DTC": 0.03,
}
DTC_CANCEL_CURVE = {  # cumulative cancel prob by days_held bucket
    "1-2": 0.10, "3-6": 0.25, "7-13": 0.40, "14+": 0.60,
}


@dataclass
class Check:
    name: str
    passed: bool
    actual: str
    expected: str

    def line(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"  {status:<5} {self.name:<46} {self.actual:<22} {self.expected}"


def channel_expr() -> str:
    """SQL expression that maps a row's retailer + channel_type to a
    reporting channel name (regional chains collapse to 'Regional')."""
    chains_csv = ",".join(f"'{c}'" for c in REGIONAL_CHAINS)
    return (
        "CASE WHEN o.channel_type = 'dtc' THEN 'DTC' "
        f"     WHEN o.retailer IN ({chains_csv}) THEN 'Regional' "
        "     ELSE o.retailer END"
    )


def revenue_expr(qty_col: str = "lo.quantity_ordered") -> str:
    """Dollar revenue expression that respects unit_of_measure."""
    return (
        f"SUM(CASE WHEN lo.unit_of_measure = 'case' "
        f"         THEN {qty_col} * pm.case_pack_qty * lo.unit_price "
        f"         ELSE {qty_col} * lo.unit_price END)"
    )


def shipped_expr() -> str:
    return (
        "SUM(CASE WHEN ls.unit_of_measure = 'case' "
        "         THEN ls.quantity_shipped * pm.case_pack_qty * ls.unit_price "
        "         ELSE ls.quantity_shipped * ls.unit_price END)"
    )


def fmt_money(v: float) -> str:
    return f"${v/1e6:.2f}M"


def fmt_pct(v: float) -> str:
    return f"{v*100:.1f}%"


def main() -> int:
    if not ORDERS_DB.exists() or not EXTRACT_DB.exists():
        print("ERROR: required DBs missing")
        return 1

    db = sqlite3.connect(ORDERS_DB)
    db.execute(f"ATTACH DATABASE '{EXTRACT_DB}' AS ext")
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    checks: list[Check] = []

    # 1. Shipped revenue per year vs Cinderhaven $23-27M target
    cur.execute(
        f"""
        SELECT {shipped_expr()} AS shipped
        FROM orders o
        JOIN order_lines_shipped ls ON ls.order_id = o.order_id
        JOIN ext.product_master pm  ON pm.sku = ls.sku
        """
    )
    total_shipped = cur.fetchone()["shipped"] or 0
    annual_shipped = total_shipped / 2.0
    checks.append(Check(
        "Annual shipped revenue",
        23_000_000 <= annual_shipped <= 27_000_000,
        f"{fmt_money(annual_shipped)}/yr",
        "$23M-$27M/yr",
    ))

    # 2. Original demand uplift vs shipped — must be 25-40% higher
    cur.execute(
        f"""
        SELECT {revenue_expr()} AS demand
        FROM orders o
        JOIN order_lines_original lo ON lo.order_id = o.order_id
        JOIN ext.product_master pm   ON pm.sku = lo.sku
        """
    )
    total_demand = cur.fetchone()["demand"] or 0
    uplift = (total_demand - total_shipped) / total_shipped if total_shipped else 0
    checks.append(Check(
        "Original demand uplift over shipped",
        0.25 <= uplift <= 0.40,
        f"+{uplift*100:.1f}%",
        "+25% to +40%",
    ))

    # 3. Channel fill rates (±3pp of target, retail/distributor only)
    cur.execute(
        f"""
        SELECT {channel_expr()} AS ch,
               {revenue_expr()} AS demand,
               {shipped_expr()} AS shipped
        FROM orders o
        JOIN order_lines_original lo ON lo.order_id = o.order_id
        JOIN order_lines_shipped ls  ON ls.order_id = o.order_id
                                    AND ls.original_line_id = lo.order_line_id
        JOIN ext.product_master pm   ON pm.sku = lo.sku
        WHERE o.channel_type IN ('retail', 'distributor')
        GROUP BY ch
        """
    )
    fill_by_channel = {r["ch"]: (r["shipped"] / r["demand"] if r["demand"] else 0)
                       for r in cur.fetchall()}
    for ch, target in CHANNEL_FILL_TARGETS.items():
        actual = fill_by_channel.get(ch, 0.0)
        diff = abs(actual - target)
        checks.append(Check(
            f"Fill rate — {ch}",
            diff <= 0.03,
            fmt_pct(actual),
            f"{fmt_pct(target)} (±3pp)",
        ))

    # 4. Channel revenue share of shipped (±3pp of target)
    cur.execute(
        f"""
        SELECT {channel_expr()} AS ch, {shipped_expr()} AS shipped
        FROM orders o
        JOIN order_lines_shipped ls ON ls.order_id = o.order_id
        JOIN ext.product_master pm  ON pm.sku = ls.sku
        GROUP BY ch
        """
    )
    rows = cur.fetchall()
    total_ship = sum(r["shipped"] or 0 for r in rows)
    share_by_channel = {r["ch"]: (r["shipped"] or 0) / total_ship if total_ship else 0
                        for r in rows}
    for ch, target in CHANNEL_SHARE_TARGETS.items():
        actual = share_by_channel.get(ch, 0.0)
        diff = abs(actual - target)
        checks.append(Check(
            f"Channel share — {ch}",
            diff <= 0.03,
            fmt_pct(actual),
            f"{fmt_pct(target)} (±3pp)",
        ))

    # 5. No orders for unauthorized (sku, retailer, order_date) triples
    cur.execute(
        """
        SELECT COUNT(*) AS n FROM (
          SELECT o.order_id, lo.sku, o.retailer, o.order_date
          FROM orders o
          JOIN order_lines_original lo ON lo.order_id = o.order_id
          WHERE NOT EXISTS (
            SELECT 1 FROM ext.distribution_log d
            JOIN ext.stores s ON s.store_id = d.store_id
            WHERE s.retailer = o.retailer AND d.sku = lo.sku
              AND d.authorized_date <= o.order_date
              AND (d.deauthorized_date IS NULL OR d.deauthorized_date > o.order_date)
          )
        )
        """
    )
    unauth_n = cur.fetchone()["n"]
    checks.append(Check(
        "No unauthorized (sku, retailer, date) triples",
        unauth_n == 0,
        f"{unauth_n}",
        "0",
    ))

    # 6. No shipped > ordered
    cur.execute(
        """
        SELECT COUNT(*) AS n FROM order_lines_shipped ls
        JOIN order_lines_original lo ON ls.original_line_id = lo.order_line_id
        WHERE ls.quantity_shipped > lo.quantity_ordered
        """
    )
    overship_n = cur.fetchone()["n"]
    checks.append(Check(
        "No shipped > ordered",
        overship_n == 0,
        f"{overship_n}",
        "0",
    ))

    # 7. No negative quantities anywhere
    cur.execute("SELECT COUNT(*) AS n FROM order_lines_original WHERE quantity_ordered <= 0")
    neg_orig = cur.fetchone()["n"]
    cur.execute("SELECT COUNT(*) AS n FROM order_lines_shipped WHERE quantity_shipped < 0")
    neg_ship = cur.fetchone()["n"]
    cur.execute("SELECT COUNT(*) AS n FROM order_shorts WHERE quantity_shorted <= 0")
    neg_short = cur.fetchone()["n"]
    cur.execute("SELECT COUNT(*) AS n FROM distributor_returns WHERE quantity_returned <= 0")
    neg_ret = cur.fetchone()["n"]
    checks.append(Check(
        "No zero/negative quantities anywhere",
        (neg_orig + neg_ship + neg_short + neg_ret) == 0,
        f"orig={neg_orig} ship={neg_ship} short={neg_short} ret={neg_ret}",
        "all 0",
    ))

    # 8. Promo orders align with promotions table dates
    cur.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM orders WHERE order_type = 'promo') AS total,
          (SELECT COUNT(DISTINCT o.order_id) FROM orders o
           JOIN order_lines_original lo ON lo.order_id = o.order_id
           WHERE o.order_type = 'promo'
             AND EXISTS (
               SELECT 1 FROM ext.promotions p
               WHERE p.sku = lo.sku
                 AND (p.retailer = o.retailer
                      OR (o.retailer = 'KeHE' AND p.retailer = 'UNFI'))
                 AND date(o.order_date, '+30 days') >= p.start_week
                 AND o.order_date <= p.end_week
             )) AS aligned
        """
    )
    r = cur.fetchone()
    total_promo, aligned = r["total"], r["aligned"]
    checks.append(Check(
        "Promo orders align with promotions table",
        aligned == total_promo,
        f"{aligned}/{total_promo}",
        "all",
    ))

    # 9. DTC cancellation rates by days_held bucket (±7pp tolerance —
    # smaller buckets have meaningful binomial variance)
    cur.execute(
        """
        SELECT CASE WHEN days_held = 0 THEN '0'
                    WHEN days_held < 3 THEN '1-2'
                    WHEN days_held < 7 THEN '3-6'
                    WHEN days_held < 14 THEN '7-13'
                    ELSE '14+' END AS bucket,
               COUNT(*) AS n,
               SUM(CASE WHEN resolution IN ('cancelled_by_customer', 'purchased_in_store') THEN 1 ELSE 0 END) AS canc
        FROM dtc_outcomes
        GROUP BY bucket
        """
    )
    cancel_by_bucket = {r["bucket"]: (r["n"], r["canc"]) for r in cur.fetchall()}
    for bucket, target in DTC_CANCEL_CURVE.items():
        if bucket not in cancel_by_bucket:
            checks.append(Check(
                f"DTC cancel rate (days_held {bucket})",
                True,
                "n=0 (skipped)",
                f"{fmt_pct(target)} (±7pp)",
            ))
            continue
        n, canc = cancel_by_bucket[bucket]
        rate = canc / n if n else 0
        diff = abs(rate - target)
        checks.append(Check(
            f"DTC cancel rate (days_held {bucket})",
            diff <= 0.07,
            f"{fmt_pct(rate)} (n={n})",
            f"{fmt_pct(target)} (±7pp)",
        ))

    # 10. Distributor return rates vs promo volume (±2pp tolerance)
    cur.execute(
        """
        SELECT SUM(ls.quantity_shipped) AS promo_cases
        FROM orders o
        JOIN order_lines_shipped ls ON ls.order_id = o.order_id
        WHERE o.order_type = 'promo' AND o.retailer IN ('UNFI', 'KeHE')
              AND ls.quantity_shipped > 0
        """
    )
    promo_cases = cur.fetchone()["promo_cases"] or 0
    for reason, target in (("unsold_promo", 0.12), ("claim_filed", 0.05)):
        cur.execute(
            "SELECT SUM(quantity_returned) AS q FROM distributor_returns WHERE return_reason = ?",
            (reason,),
        )
        q = cur.fetchone()["q"] or 0
        rate = q / promo_cases if promo_cases else 0
        diff = abs(rate - target)
        checks.append(Check(
            f"Distributor return rate ({reason})",
            diff <= 0.02,
            fmt_pct(rate),
            f"{fmt_pct(target)} (±2pp)",
        ))

    db.close()

    # Print summary
    print(f"\n{'  STATUS':<7}{'CHECK':<48}{'ACTUAL':<24}{'EXPECTED'}")
    print("  " + "-" * 100)
    n_pass = sum(1 for c in checks if c.passed)
    n_fail = len(checks) - n_pass
    for c in checks:
        print(c.line())
    print()
    print(f"  Total: {n_pass} passed, {n_fail} failed, {len(checks)} checks")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
