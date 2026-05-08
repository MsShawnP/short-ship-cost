"""Export pre-aggregated JSON for the React interactive tool.

Reads cinderhaven_extract.db, short_ship_orders.db, and short_ship_cost.db
and writes a fixed set of JSON files to web/public/data/. The browser
never touches raw order lines; everything is grouped here so the React
app can render directly.

Run from the repo root:

    python scripts/export_json.py

The script is idempotent — it deletes any existing *.json in the output
directory and rewrites them.
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXTRACT_DB = REPO / "data" / "cinderhaven_extract.db"
ORDERS_DB = REPO / "data" / "short_ship_orders.db"
COST_DB = REPO / "data" / "short_ship_cost.db"
OUT_DIR = REPO / "web" / "public" / "data"

DOLLAR_PLACES = 2
PCT_PLACES = 4
TOP_N_SKUS = 20


def round_dollar(v: float | None) -> float | None:
    return None if v is None else round(v, DOLLAR_PLACES)


def round_pct(v: float | None) -> float | None:
    return None if v is None else round(v, PCT_PLACES)


def open_cost_db() -> sqlite3.Connection:
    db = sqlite3.connect(COST_DB)
    db.execute(f"ATTACH DATABASE '{ORDERS_DB}' AS ord")
    db.execute(f"ATTACH DATABASE '{EXTRACT_DB}' AS ext")
    db.row_factory = sqlite3.Row
    return db


def write_json(path: Path, data) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(text, encoding="utf-8")
    return path.stat().st_size


# ---- Builders --------------------------------------------------------------


def build_meta(db: sqlite3.Connection) -> dict:
    cur = db.cursor()

    cur.execute("SELECT MIN(order_date), MAX(order_date) FROM ord.orders")
    start, end = cur.fetchone()

    cur.execute("SELECT COUNT(*) FROM ord.orders")
    total_orders = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM ext.product_master")
    total_skus = cur.fetchone()[0]

    cur.execute(
        """
        SELECT
          SUM(CASE WHEN ls.unit_of_measure = 'case'
                   THEN ls.quantity_shipped * pm.case_pack_qty * ls.unit_price
                   ELSE ls.quantity_shipped * ls.unit_price END) AS shipped,
          SUM(CASE WHEN lo.unit_of_measure = 'case'
                   THEN lo.quantity_ordered * pm.case_pack_qty * lo.unit_price
                   ELSE lo.quantity_ordered * lo.unit_price END) AS demand
        FROM ord.order_lines_shipped ls
        JOIN ord.order_lines_original lo ON lo.order_line_id = ls.original_line_id
        JOIN ext.product_master pm        ON pm.sku = ls.sku
        """
    )
    row = cur.fetchone()
    shipped_revenue = float(row["shipped"] or 0)
    demand = float(row["demand"] or 0)
    overall_fill = (shipped_revenue / demand) if demand else 0.0

    # /2 to match the arc-1 docs ($25.9M/yr); honest given the ~720-day window.
    shipped_revenue_annual = shipped_revenue / 2.0

    cur.execute(
        "SELECT name, value, unit, basis, level, description, source "
        "FROM cost_parameters ORDER BY name"
    )
    params = {}
    for r in cur.fetchall():
        params[r["name"]] = {
            "value": r["value"],
            "unit": r["unit"],
            "basis": r["basis"],
            "level": r["level"],
            "description": r["description"],
            "source": r["source"],
        }

    return {
        "last_updated": datetime.fromtimestamp(
            COST_DB.stat().st_mtime, tz=timezone.utc
        ).isoformat(),
        "time_window": {"start": start, "end": end},
        "shipped_revenue": round_dollar(shipped_revenue),
        "shipped_revenue_annual": round_dollar(shipped_revenue_annual),
        "total_orders": total_orders,
        "total_skus": total_skus,
        "overall_fill_rate": round_pct(overall_fill),
        "cost_parameters": params,
    }


def build_cost_summary(db: sqlite3.Connection) -> list[dict]:
    cur = db.cursor()
    cur.execute(
        "SELECT dimension, total_cost, pct_of_shipped_revenue, description "
        "FROM cost_summary ORDER BY total_cost DESC"
    )
    rows = []
    for r in cur.fetchall():
        rows.append({
            "dimension": r["dimension"],
            "total_cost": round_dollar(r["total_cost"]),
            # cost_summary stores percent on a 0-100 scale; emit a fraction.
            "pct_of_shipped": round_pct(r["pct_of_shipped_revenue"] / 100.0),
            "description": r["description"],
        })
    return rows


def build_cost_by_retailer(db: sqlite3.Connection) -> list[dict]:
    cur = db.cursor()
    cur.execute(
        "SELECT retailer, dimension, cost FROM cost_by_retailer "
        "ORDER BY retailer, dimension"
    )
    return [
        {
            "retailer": r["retailer"],
            "dimension": r["dimension"],
            "cost": round_dollar(r["cost"]),
        }
        for r in cur.fetchall()
    ]


def build_cost_by_month(db: sqlite3.Connection) -> list[dict]:
    cur = db.cursor()
    cur.execute(
        "SELECT month, dimension, cost FROM cost_by_month "
        "ORDER BY month, dimension"
    )
    return [
        {
            "month": r["month"],
            "dimension": r["dimension"],
            "cost": round_dollar(r["cost"]),
        }
        for r in cur.fetchall()
    ]


def build_cost_by_sku(db: sqlite3.Connection) -> list[dict]:
    """Top-N SKUs by total cost across attributed dimensions, plus an
    'Other' row aggregating the remaining SKUs. The drill-down sums to
    (cost_summary total - triage_labor), since triage_labor has no SKU
    attribution. The React app should surface that gap."""
    cur = db.cursor()

    cur.execute("SELECT sku, dimension, cost FROM cost_by_sku")
    by_sku: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in cur.fetchall():
        by_sku[r["sku"]][r["dimension"]] += r["cost"]

    sku_totals = {sku: sum(d.values()) for sku, d in by_sku.items()}

    cur.execute("SELECT sku, product_name, product_line FROM ext.product_master")
    pm = {r["sku"]: (r["product_name"], r["product_line"]) for r in cur.fetchall()}

    sorted_skus = sorted(sku_totals.items(), key=lambda kv: -kv[1])
    top = sorted_skus[:TOP_N_SKUS]
    rest = sorted_skus[TOP_N_SKUS:]

    rows = []
    for sku, total in top:
        name, line = pm.get(sku, (sku, "Unknown"))
        rows.append({
            "sku": sku,
            "product_name": name,
            "product_line": line,
            "total_cost": round_dollar(total),
            "by_dimension": {
                d: round_dollar(c) for d, c in sorted(by_sku[sku].items())
            },
        })

    if rest:
        other_total = sum(t for _, t in rest)
        other_by_dim: dict[str, float] = defaultdict(float)
        for sku, _ in rest:
            for d, c in by_sku[sku].items():
                other_by_dim[d] += c
        rows.append({
            "sku": "Other",
            "product_name": f"Other ({len(rest)} SKUs)",
            "product_line": "Other",
            "total_cost": round_dollar(other_total),
            "by_dimension": {
                d: round_dollar(c) for d, c in sorted(other_by_dim.items())
            },
        })

    return rows


def build_deauthorization_events(db: sqlite3.Connection) -> list[dict]:
    cur = db.cursor()
    cur.execute(
        """
        SELECT sku, retailer, trigger_type,
               velocity_without_shorts, velocity_with_shorts,
               threshold, fill_rate,
               consecutive_months_below_threshold,
               annualized_revenue_lost
        FROM deauthorization_events
        ORDER BY annualized_revenue_lost DESC
        """
    )
    rows = []
    for r in cur.fetchall():
        rows.append({
            "sku": r["sku"],
            "retailer": r["retailer"],
            "trigger_type": r["trigger_type"],
            "velocity_without_shorts": round_pct(r["velocity_without_shorts"]),
            "velocity_with_shorts": round_pct(r["velocity_with_shorts"]),
            "threshold": r["threshold"],
            "fill_rate": round_pct(r["fill_rate"]),
            "consecutive_months_below_threshold": r[
                "consecutive_months_below_threshold"
            ],
            "annualized_revenue_lost": round_dollar(r["annualized_revenue_lost"]),
        })
    return rows


def build_buffer_scenarios(db: sqlite3.Connection) -> dict:
    cur = db.cursor()
    cur.execute(
        "SELECT target_fill_rate, actual_fill_rate_achieved, total_cost, "
        "       total_recovery, recovery_pct "
        "FROM buffer_scenarios ORDER BY target_fill_rate"
    )
    summary_rows = cur.fetchall()

    cur.execute(
        "SELECT target_fill_rate, dimension, original_cost, "
        "       simulated_cost, recovery_amount, recovery_pct "
        "FROM buffer_scenario_details"
    )
    detail_by_target: dict[float, dict[str, dict]] = defaultdict(dict)
    for r in cur.fetchall():
        detail_by_target[r["target_fill_rate"]][r["dimension"]] = {
            "original": round_dollar(r["original_cost"]),
            "simulated": round_dollar(r["simulated_cost"]),
            "recovery": round_dollar(r["recovery_amount"]),
            # recovery_pct stored on 0-100 scale; emit a fraction.
            "recovery_pct": round_pct(r["recovery_pct"] / 100.0),
        }

    scenarios = []
    for r in summary_rows:
        target = r["target_fill_rate"]
        scenarios.append({
            "target_fill_rate": round_pct(target),
            "achieved_fill_rate": round_pct(r["actual_fill_rate_achieved"]),
            "total_cost": round_dollar(r["total_cost"]),
            "total_recovery": round_dollar(r["total_recovery"]),
            "recovery_pct": round_pct(r["recovery_pct"] / 100.0),
            "by_dimension": detail_by_target.get(target, {}),
        })

    return {"scenarios": scenarios}


def build_validation(db: sqlite3.Connection, meta: dict) -> dict:
    cur = db.cursor()
    cur.execute("SELECT dimension, total_cost FROM cost_summary")
    totals = {r["dimension"]: round_dollar(r["total_cost"]) for r in cur.fetchall()}
    totals["total"] = round_dollar(sum(totals.values()))
    return {
        "baseline_totals": totals,
        "shipped_revenue": meta["shipped_revenue"],
        "overall_fill_rate": meta["overall_fill_rate"],
    }


# ---- Driver ----------------------------------------------------------------


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for f in OUT_DIR.glob("*.json"):
        f.unlink()

    db = open_cost_db()
    try:
        meta = build_meta(db)
        outputs = {
            "meta.json": meta,
            "cost_summary.json": build_cost_summary(db),
            "cost_by_retailer.json": build_cost_by_retailer(db),
            "cost_by_month.json": build_cost_by_month(db),
            "cost_by_sku.json": build_cost_by_sku(db),
            "deauthorization_events.json": build_deauthorization_events(db),
            "buffer_scenarios.json": build_buffer_scenarios(db),
            "validation.json": build_validation(db, meta),
        }
    finally:
        db.close()

    sizes = {name: write_json(OUT_DIR / name, payload) for name, payload in outputs.items()}

    summary_total = sum(r["total_cost"] for r in outputs["cost_summary.json"])
    val_total = outputs["validation.json"]["baseline_totals"]["total"]
    matches = abs(summary_total - val_total) < 1.0

    total_size = sum(sizes.values())
    print()
    print(f"Exported {len(outputs)} files to {OUT_DIR.relative_to(REPO)}/")
    for name, size in sizes.items():
        print(f"  {name:<32} {size / 1024:>8.1f} KB")
    print(f"  {'TOTAL':<32} {total_size / 1024:>8.1f} KB")
    print()
    print(f"cost_summary total:      ${summary_total:>15,.2f}")
    print(f"validation total:        ${val_total:>15,.2f}")
    print(f"sanity check (<$1 diff): {'PASS' if matches else 'FAIL'}")
    if not matches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
