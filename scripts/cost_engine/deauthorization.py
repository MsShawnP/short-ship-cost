"""Cost dimension: deauthorization events triggered by shorts.

Two mechanisms:

1. Retailer velocity-based (Walmart, Costco, Whole Foods, Kroger,
   Sprouts, Regional Group)
   For each (sku, retailer) pair:
     velocity_without_shorts = qty_ordered / store_count / 157 weeks
     velocity_with_shorts    = qty_shipped / store_count / 157 weeks
   If velocity_without_shorts > threshold AND velocity_with_shorts <
   threshold, the short pushed the SKU below the delisting threshold.
   Thresholds (units/store/week): Walmart 2.50, Costco 10.00,
   WF 1.50, Kroger 2.50, Sprouts 1.50, Regional 1.50.
   Cost: 12 months of annualized revenue for that (sku, retailer).

2. Distributor fill-rate-based (UNFI, KeHE, DPI Northwest)
   For each (sku, distributor), compute monthly fill rate. If 3+
   consecutive months fall below 90%, the SKU is delisted.
   Cost: 12 months of annualized revenue for that (sku, distributor).

Annualized = total 3-year revenue / 3.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .common import aggregate_breakdowns, channel_of, empty_result, open_db
from .parameters import REGIONAL_CHAINS, get


VELOCITY_THRESHOLD = {
    "Walmart": get("deauth_velocity_walmart"),
    "Costco": get("deauth_velocity_costco"),
    "Whole Foods": get("deauth_velocity_whole_foods"),
    "Kroger": get("deauth_velocity_kroger"),
    "Sprouts": get("deauth_velocity_sprouts"),
    "Regional Group": get("deauth_velocity_regional"),
}

WEEKS_IN_WINDOW = 157


def _velocity_events(db) -> list[dict]:
    """For each (sku, retailer) pair under a velocity-threshold rule,
    determine whether shorts pushed velocity below the delist line."""
    cur = db.cursor()

    # Per (sku, retailer) distributed store counts — velocity measured
    # only at stores that carry the SKU, not the entire chain.
    cur.execute("""
        SELECT s.retailer, dl.sku, COUNT(DISTINCT dl.store_id) AS n
        FROM ext.distribution_log dl
        JOIN ext.stores s ON s.store_id = dl.store_id
        WHERE s.retailer NOT IN ('DTC', 'UNFI', 'KeHE', 'DPI Northwest')
        GROUP BY s.retailer, dl.sku
    """)
    dist_store_counts = {(r["retailer"], r["sku"]): r["n"] for r in cur.fetchall()}

    # Per (sku, retailer): qty_ordered units, qty_shipped units, revenue
    cur.execute(
        """
        SELECT
          o.retailer,
          lo.sku,
          SUM(lo.quantity_ordered * pm.case_pack_qty) AS demand_units,
          SUM(ls.quantity_shipped * pm.case_pack_qty) AS shipped_units,
          SUM(lo.quantity_ordered * pm.case_pack_qty * lo.unit_price) AS demand_value,
          SUM(ls.quantity_shipped * pm.case_pack_qty * ls.unit_price) AS shipped_value
        FROM orders o
        JOIN order_lines_original lo ON lo.order_id = o.order_id
        JOIN order_lines_shipped ls  ON ls.original_line_id = lo.order_line_id
        JOIN ext.product_master pm   ON pm.sku = lo.sku
        WHERE o.channel_type = 'retail'
        GROUP BY o.retailer, lo.sku
        """
    )

    events: list[dict] = []
    for r in cur.fetchall():
        retailer = r["retailer"]
        threshold = VELOCITY_THRESHOLD.get(retailer)
        if threshold is None:
            continue
        store_n = dist_store_counts.get((retailer, r["sku"]), 0)
        if store_n <= 0:
            continue
        demand_units = r["demand_units"] or 0
        shipped_units = r["shipped_units"] or 0
        v_without = demand_units / store_n / WEEKS_IN_WINDOW
        v_with = shipped_units / store_n / WEEKS_IN_WINDOW
        if v_without > threshold and v_with < threshold:
            annualized_rev = (r["shipped_value"] or 0) / 3.0
            events.append({
                "sku": r["sku"],
                "retailer": retailer,
                "trigger_type": "velocity_below_threshold",
                "velocity_without_shorts": round(v_without, 4),
                "velocity_with_shorts": round(v_with, 4),
                "threshold": threshold,
                "fill_rate": (shipped_units / demand_units) if demand_units else 0,
                "consecutive_months_below_threshold": None,
                "annualized_revenue_lost": round(annualized_rev, 2),
            })
    return events


def _consecutive_months_below(values: list[tuple[str, float]], threshold: float, n: int) -> bool:
    """Given a list of (month, fill_rate) sorted ascending by month,
    return True if any window of n consecutive months falls below
    threshold."""
    streak = 0
    for _m, fill in values:
        if fill < threshold:
            streak += 1
            if streak >= n:
                return True
        else:
            streak = 0
    return False


def _distributor_events(db) -> list[dict]:
    cur = db.cursor()
    threshold = get("deauth_distributor_fill_rate")
    n_required = get("deauth_distributor_consecutive_months")

    cur.execute(
        """
        SELECT
          o.retailer,
          lo.sku,
          substr(o.order_date, 1, 7) AS month,
          SUM(lo.quantity_ordered * pm.case_pack_qty * lo.unit_price) AS demand_value,
          SUM(ls.quantity_shipped * pm.case_pack_qty * ls.unit_price) AS shipped_value
        FROM orders o
        JOIN order_lines_original lo ON lo.order_id = o.order_id
        JOIN order_lines_shipped ls  ON ls.original_line_id = lo.order_line_id
        JOIN ext.product_master pm   ON pm.sku = lo.sku
        WHERE o.retailer IN ('UNFI', 'KeHE', 'DPI Northwest')
        GROUP BY o.retailer, lo.sku, month
        ORDER BY o.retailer, lo.sku, month
        """
    )

    monthly_by_pair: dict[tuple[str, str], list[tuple[str, float]]] = defaultdict(list)
    revenue_by_pair: dict[tuple[str, str], float] = defaultdict(float)
    for r in cur.fetchall():
        key = (r["retailer"], r["sku"])
        demand = r["demand_value"] or 0
        shipped = r["shipped_value"] or 0
        fill = shipped / demand if demand > 0 else 1.0
        monthly_by_pair[key].append((r["month"], fill))
        revenue_by_pair[key] += shipped

    events: list[dict] = []
    for (retailer, sku), monthly in monthly_by_pair.items():
        if _consecutive_months_below(monthly, threshold, n_required):
            shipped_total = revenue_by_pair[(retailer, sku)]
            annualized_rev = shipped_total / 3.0
            min_fill = min(f for _, f in monthly)
            events.append({
                "sku": sku,
                "retailer": retailer,
                "trigger_type": "distributor_consecutive_months",
                "velocity_without_shorts": None,
                "velocity_with_shorts": None,
                "threshold": threshold,
                "fill_rate": round(min_fill, 4),
                "consecutive_months_below_threshold": n_required,
                "annualized_revenue_lost": round(annualized_rev, 2),
            })
    return events


def calculate() -> dict:
    db = open_db()
    events = _velocity_events(db) + _distributor_events(db)
    db.close()

    rows = []
    for e in events:
        rows.append({
            "retailer": channel_of(e["retailer"], "retail"),
            "sku": e["sku"],
            "month": None,
            "cost": e["annualized_revenue_lost"],
        })

    result = empty_result(
        "deauthorization",
        "Forward-looking revenue at risk from short-caused "
        "deauthorizations: 12 months of annualized revenue for each "
        "SKU x retailer pair where shorts pushed velocity below the "
        "delist threshold (or where fill stayed below 90% for 3+ "
        "consecutive months at UNFI/KeHE/DPI Northwest).",
    )
    result["total_cost"] = sum(r["cost"] for r in rows)
    result.update(aggregate_breakdowns(rows))
    result["detail_events"] = events
    return result


if __name__ == "__main__":
    out = calculate()
    print(f"{out['dimension']:<20} ${out['total_cost']:>15,.0f}")
    print(f"  Events: {len(out['detail_events'])}")
    for e in out["detail_events"][:10]:
        print(f"    {e['retailer']:<14} {e['sku']} "
              f"trig={e['trigger_type'][:18]:<18} ${e['annualized_revenue_lost']:>10,.0f}")
