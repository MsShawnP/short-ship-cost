"""
Extract revenue calibration targets from Cinderhaven Postgres into
data/calibration.json. Run periodically to keep synthetic order
targets aligned with actual warehouse revenue.

Unlike the rest of this project (stdlib-only), this script requires
psycopg2-binary. It is a one-time extract step, not part of the
main pipeline — generate_orders.py reads the JSON output with stdlib
json and works fine without Postgres.

Usage:
    1. Start Fly.io proxy:  flyctl proxy 5432 -a cinderhaven-db
    2. Run:  python scripts/extract_calibration.py
    3. Output: data/calibration.json (committed to repo)

Requires: psycopg2-binary
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import psycopg2
import psycopg2.extras

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "calibration.json"

REGIONAL_CHAINS = {
    "Southside Grocers",
    "Green Basket Market",
    "Prairie Provisions",
    "Mountain Pantry Co",
    "Harbor Fresh",
}


def connect():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        pw = os.environ.get("POSTGRES_PASSWORD")
        if not pw:
            print("Set DATABASE_URL or POSTGRES_PASSWORD.", file=sys.stderr)
            sys.exit(1)
        dsn = f"postgresql://postgres:REDACTED@localhost:5432/cinderhaven"
    return psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)


def main() -> int:
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT retailer, revenue FROM (
            SELECT dr.retailer_name AS retailer,
                   SUM(fo.total_value)::float AS revenue
            FROM public_marts.fct_retailer_orders fo
            JOIN public_marts.dim_retailers dr ON dr.retailer_id = fo.retailer_id
            GROUP BY dr.retailer_name
            UNION ALL
            SELECT dd.distributor_name AS retailer,
                   SUM(fo.total_value)::float AS revenue
            FROM public_marts.fct_distributor_orders fo
            JOIN public_marts.dim_distributors dd ON dd.distributor_id = fo.distributor_id
            GROUP BY dd.distributor_name
            UNION ALL
            SELECT 'DTC' AS retailer,
                   SUM(fo.gross_revenue)::float AS revenue
            FROM public_marts.fct_dtc_orders fo
        ) combined ORDER BY revenue DESC
    """)
    rows = cur.fetchall()
    conn.close()

    targets: dict[str, float] = {}
    regional_total = 0.0
    for r in rows:
        name = r["retailer"]
        rev = round(float(r["revenue"]), 2)
        if name in REGIONAL_CHAINS:
            regional_total += rev
        else:
            targets[name] = rev
    if regional_total > 0:
        targets["Regional"] = round(regional_total, 2)

    calibration = {
        "extracted": date.today().isoformat(),
        "source": "fct_retailer_orders + fct_distributor_orders + fct_dtc_orders",
        "revenue_targets_3yr": targets,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(calibration, indent=2) + "\n")
    print(f"Wrote {OUT}")
    print(f"  Channels: {len(targets)}")
    print(f"  Total: ${sum(targets.values()):,.0f}")
    for ch in sorted(targets, key=targets.get, reverse=True):
        print(f"    {ch:<20s} ${targets[ch]:>14,.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
