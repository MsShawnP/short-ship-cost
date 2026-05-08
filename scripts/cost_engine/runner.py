"""Cost-engine orchestration. Calls every dimension module, materializes
the results into data/short_ship_cost.db, and prints the eight-row
summary table.

Tables written:
- cost_summary           — one row per dimension
- cost_by_retailer       — dimension x retailer
- cost_by_sku            — dimension x sku
- cost_by_month          — dimension x month
- deauthorization_events — detailed log of each deauth event
- cost_parameters        — every tunable parameter from parameters.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from . import (
    chargebacks,
    deauthorization,
    distributor_returns,
    dtc_cancellations,
    dtc_margin_leakage,
    lost_revenue,
    otif_fines,
    triage_labor,
)
from .common import COST_DB, open_db
from .parameters import PARAMETERS

MODULES = [
    ("lost_revenue", lost_revenue),
    ("otif_fines", otif_fines),
    ("chargebacks", chargebacks),
    ("deauthorization", deauthorization),
    ("dtc_cancellations", dtc_cancellations),
    ("dtc_margin_leakage", dtc_margin_leakage),
    ("distributor_returns", distributor_returns),
    ("triage_labor", triage_labor),
]


def total_shipped_revenue() -> float:
    db = open_db()
    cur = db.cursor()
    cur.execute(
        """
        SELECT SUM(CASE WHEN ls.unit_of_measure = 'case'
                        THEN ls.quantity_shipped * pm.case_pack_qty * ls.unit_price
                        ELSE ls.quantity_shipped * ls.unit_price END)
        FROM order_lines_shipped ls
        JOIN ext.product_master pm ON pm.sku = ls.sku
        """
    )
    val = cur.fetchone()[0] or 0
    db.close()
    return float(val)


def write_cost_db(results: list[dict], shipped_revenue: float) -> None:
    if COST_DB.exists():
        COST_DB.unlink()
    db = sqlite3.connect(COST_DB)
    cur = db.cursor()
    cur.executescript("""
        CREATE TABLE cost_summary (
            dimension              TEXT PRIMARY KEY,
            total_cost             REAL NOT NULL,
            pct_of_shipped_revenue REAL NOT NULL,
            description            TEXT NOT NULL
        );
        CREATE TABLE cost_by_retailer (
            dimension TEXT NOT NULL,
            retailer  TEXT NOT NULL,
            cost      REAL NOT NULL,
            PRIMARY KEY (dimension, retailer)
        );
        CREATE TABLE cost_by_sku (
            dimension TEXT NOT NULL,
            sku       TEXT NOT NULL,
            cost      REAL NOT NULL,
            PRIMARY KEY (dimension, sku)
        );
        CREATE TABLE cost_by_month (
            dimension TEXT NOT NULL,
            month     TEXT NOT NULL,
            cost      REAL NOT NULL,
            PRIMARY KEY (dimension, month)
        );
        CREATE TABLE deauthorization_events (
            sku                                  TEXT NOT NULL,
            retailer                             TEXT NOT NULL,
            trigger_type                         TEXT NOT NULL,
            velocity_without_shorts              REAL,
            velocity_with_shorts                 REAL,
            threshold                            REAL,
            fill_rate                            REAL,
            consecutive_months_below_threshold   INTEGER,
            annualized_revenue_lost              REAL NOT NULL,
            PRIMARY KEY (sku, retailer, trigger_type)
        );
        CREATE TABLE cost_parameters (
            name        TEXT PRIMARY KEY,
            value       REAL,
            unit        TEXT,
            basis       TEXT,
            level       TEXT,
            description TEXT,
            source      TEXT
        );
    """)

    for res in results:
        pct = (res["total_cost"] / shipped_revenue * 100) if shipped_revenue else 0
        cur.execute(
            "INSERT INTO cost_summary VALUES (?, ?, ?, ?)",
            (res["dimension"], res["total_cost"], pct, res["description"]),
        )
        for r in res["by_retailer"]:
            cur.execute(
                "INSERT INTO cost_by_retailer VALUES (?, ?, ?)",
                (res["dimension"], r["retailer"], r["cost"]),
            )
        for r in res["by_sku"]:
            cur.execute(
                "INSERT INTO cost_by_sku VALUES (?, ?, ?)",
                (res["dimension"], r["sku"], r["cost"]),
            )
        for r in res["by_month"]:
            cur.execute(
                "INSERT INTO cost_by_month VALUES (?, ?, ?)",
                (res["dimension"], r["month"], r["cost"]),
            )

    # Deauth events
    for res in results:
        for e in res.get("detail_events", []) or []:
            cur.execute(
                "INSERT INTO deauthorization_events VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (e["sku"], e["retailer"], e["trigger_type"],
                 e.get("velocity_without_shorts"),
                 e.get("velocity_with_shorts"),
                 e.get("threshold"),
                 e.get("fill_rate"),
                 e.get("consecutive_months_below_threshold"),
                 e["annualized_revenue_lost"]),
            )

    # Parameters
    for name, p in PARAMETERS.items():
        cur.execute(
            "INSERT INTO cost_parameters VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, float(p["value"]) if isinstance(p["value"], (int, float)) else None,
             p.get("unit"), p.get("basis"), p.get("level"),
             p.get("description"), p.get("source")),
        )

    db.commit()
    db.close()


def print_summary(results: list[dict], shipped_revenue: float) -> None:
    print(f"\n  Shipped revenue (2yr): ${shipped_revenue:,.0f}  "
          f"(${shipped_revenue/2:,.0f}/yr)\n")
    print(f"  {'#':<3}{'DIMENSION':<24}{'TOTAL COST':>16}{'% OF SHIPPED':>16}")
    print("  " + "-" * 60)
    grand_total = 0.0
    for i, res in enumerate(results, 1):
        pct = (res["total_cost"] / shipped_revenue * 100) if shipped_revenue else 0
        grand_total += res["total_cost"]
        print(f"  {i:<3}{res['dimension']:<24}${res['total_cost']:>14,.0f}{pct:>15.2f}%")
    grand_pct = (grand_total / shipped_revenue * 100) if shipped_revenue else 0
    print("  " + "-" * 60)
    print(f"  {'TOTAL COST OF SHORTS':<27}${grand_total:>14,.0f}{grand_pct:>15.2f}%")
    print()


def main() -> int:
    print("Running cost engine...")
    shipped_revenue = total_shipped_revenue()
    results = []
    for name, mod in MODULES:
        print(f"  {name}...")
        results.append(mod.calculate())

    write_cost_db(results, shipped_revenue)
    print(f"\nWrote {COST_DB}")
    print_summary(results, shipped_revenue)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
