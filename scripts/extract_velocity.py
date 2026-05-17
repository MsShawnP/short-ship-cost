"""
Aggregate per-SKU velocity from the upstream Cinderhaven scan_data
and write it as a derived `sku_velocity` table in this repo's
`data/cinderhaven_extract.db`.

Purpose: the order generator (PLAN task 4) needs per-SKU weekly
demand and a velocity rank to size production output proportionally.
scan_data itself is excluded from the extract for size reasons; this
small rollup (50 rows) carries the signal we need.

Definitions:
- avg_weekly_units: total units sold across all stores in the
  157-week window, divided by 157. A blended rate.
- total_annual_units: avg_weekly_units * 52. Annualized projection.
- velocity_rank: 1 = highest weekly volume, 50 = lowest.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = Path(r"C:/Users/mssha/projects/active/cinderhaven-data/data/cinderhaven_product_master.db")
DEST = REPO / "data" / "cinderhaven_extract.db"

WEEKS_IN_WINDOW = 157  # Cinderhaven scan_data spans 2024-01-01 .. 2026-12-31


def main() -> int:
    if not SRC.exists():
        print(f"ERROR: source DB not found at {SRC}")
        return 1
    if not DEST.exists():
        print(f"ERROR: extract DB not found at {DEST} — run extract_cinderhaven.py first")
        return 1

    src = sqlite3.connect(SRC)
    cur_src = src.cursor()
    cur_src.execute(
        f"""
        SELECT sku, SUM(units_sold) * 1.0 / {WEEKS_IN_WINDOW} AS avg_weekly_units,
               SUM(units_sold) * 1.0 / {WEEKS_IN_WINDOW} * 52 AS total_annual_units
        FROM scan_data
        GROUP BY sku
        ORDER BY avg_weekly_units DESC
        """
    )
    rows = [(sku, awu, tau, rank + 1) for rank, (sku, awu, tau) in enumerate(cur_src.fetchall())]
    src.close()

    if not rows:
        print("ERROR: no rows returned from scan_data")
        return 1

    dest = sqlite3.connect(DEST)
    cur_dest = dest.cursor()
    cur_dest.execute("DROP TABLE IF EXISTS sku_velocity")
    cur_dest.execute(
        """
        CREATE TABLE sku_velocity (
            sku                 TEXT PRIMARY KEY,
            avg_weekly_units    REAL NOT NULL,
            total_annual_units  REAL NOT NULL,
            velocity_rank       INTEGER NOT NULL
        )
        """
    )
    cur_dest.executemany(
        "INSERT INTO sku_velocity VALUES (?, ?, ?, ?)",
        rows,
    )
    dest.commit()

    cur_dest.execute("SELECT COUNT(*), SUM(avg_weekly_units), SUM(total_annual_units) FROM sku_velocity")
    n, awu, tau = cur_dest.fetchone()
    print(f"Wrote sku_velocity to {DEST}")
    print(f"  rows:                       {n}")
    print(f"  brand-wide avg weekly units: {awu:,.0f}")
    print(f"  brand-wide annual units:     {tau:,.0f}")

    cur_dest.execute(
        "SELECT sku, avg_weekly_units, total_annual_units, velocity_rank "
        "FROM sku_velocity ORDER BY velocity_rank LIMIT 5"
    )
    print("  top 5 SKUs by velocity:")
    for r in cur_dest.fetchall():
        print(f"    {r[0]}  awu={r[1]:>9.1f}  annual={r[2]:>10,.0f}  rank={r[3]}")
    cur_dest.execute(
        "SELECT sku, avg_weekly_units, total_annual_units, velocity_rank "
        "FROM sku_velocity ORDER BY velocity_rank DESC LIMIT 5"
    )
    print("  bottom 5 SKUs by velocity:")
    for r in cur_dest.fetchall():
        print(f"    {r[0]}  awu={r[1]:>9.1f}  annual={r[2]:>10,.0f}  rank={r[3]}")

    dest.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
