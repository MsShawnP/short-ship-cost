"""
Add KeHE as a distinct aggregated distributor in the Cinderhaven
extract. KeHE is not present in the upstream Cinderhaven dataset
(which has only UNFI as a distributor), but it is a major distributor
in the short-ship-cost project scope and needs its own retailer
identity, SKU authorizations, and ordering patterns.

This script:
  1. Inserts a KEHE-AGG row into `stores` (mirroring UNFI-AGG).
  2. Mirrors every UNFI-AGG `distribution_log` entry with
     store_id = 'KEHE-AGG' so the same SKUs are authorized through
     KeHE that are authorized through UNFI. This reflects real-world
     distribution: brands that sell through UNFI usually also sell
     through KeHE on the same SKU set.

Idempotent — running twice does not duplicate rows.

KeHE pricing uses sku_costs.wholesale_kehe.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXTRACT_DB = REPO / "data" / "cinderhaven_extract.db"


def main() -> int:
    if not EXTRACT_DB.exists():
        print(f"ERROR: {EXTRACT_DB} not found")
        return 1

    db = sqlite3.connect(EXTRACT_DB)
    cur = db.cursor()

    # 1. Stores row
    cur.execute("SELECT 1 FROM stores WHERE store_id = 'KEHE-AGG'")
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO stores (store_id, retailer, chain_name, region, state, "
            "volume_tier, is_aggregated_channel) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("KEHE-AGG", "KeHE", "KeHE", None, None, None, 1),
        )
        print("Inserted KEHE-AGG row in stores.")
    else:
        print("KEHE-AGG row already in stores; skipping.")

    # 2. distribution_log entries mirroring UNFI-AGG
    cur.execute("SELECT COUNT(*) FROM distribution_log WHERE store_id = 'KEHE-AGG'")
    existing = cur.fetchone()[0]
    if existing == 0:
        cur.execute(
            "INSERT INTO distribution_log (sku, store_id, authorized_date, deauthorized_date) "
            "SELECT sku, 'KEHE-AGG', authorized_date, deauthorized_date "
            "FROM distribution_log WHERE store_id = 'UNFI-AGG'"
        )
        print(f"Mirrored UNFI-AGG distribution_log entries to KEHE-AGG: {cur.rowcount} rows.")
    else:
        print(f"KEHE-AGG already has {existing} distribution_log rows; skipping.")

    db.commit()

    # Verification report
    cur.execute("SELECT COUNT(*) FROM stores WHERE retailer = 'KeHE'")
    print(f"KeHE stores rows:                {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM distribution_log WHERE store_id = 'KEHE-AGG'")
    print(f"KeHE distribution_log rows:      {cur.fetchone()[0]}")
    cur.execute(
        "SELECT COUNT(DISTINCT sku) FROM distribution_log WHERE store_id = 'KEHE-AGG' "
        "AND deauthorized_date IS NULL"
    )
    print(f"KeHE active SKU count:           {cur.fetchone()[0]}")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
