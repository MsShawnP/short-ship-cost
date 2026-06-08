"""
Extract Cinderhaven orders and reference data from Postgres into local
SQLite for the short-ship-cost pipeline.

Replaces:
  - extract_cinderhaven.py (reference data from old SQLite source)
  - extract_velocity.py (sku_velocity from old SQLite scan_data)
  - generate_orders.py (synthetic order generation)

Outputs:
  data/cinderhaven_extract.db   — product_master, sku_costs, stores,
                                  distribution_log, promotions, sku_velocity
  data/short_ship_orders.db     — orders, order_lines_original

Postgres source: Cinderhaven raw.* tables via flyctl proxy or DATABASE_URL.
Falls back to cached local files when Postgres is unreachable.

Usage:
    python scripts/extract_postgres.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

REPO = Path(__file__).resolve().parent.parent
EXTRACT_DB = REPO / "data" / "cinderhaven_extract.db"
ORDERS_DB = REPO / "data" / "short_ship_orders.db"

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"host=localhost port=5432 dbname=cinderhaven user=postgres"
    f" password={os.environ.get('POSTGRES_PASSWORD', '')}",
)

WEEKS_IN_WINDOW = 157  # 2023-01-06 .. 2026-01-02


def _sqlite_row(d: dict) -> dict:
    """Convert Postgres types (Decimal, date) to SQLite-compatible Python types."""
    return {
        k: (float(v) if isinstance(v, Decimal)
             else str(v) if isinstance(v, date)
             else v)
        for k, v in d.items()
    }


def connect_postgres():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_session(readonly=True)
        return conn
    except psycopg2.OperationalError as e:
        print(f"WARNING: Postgres unavailable — {e}", file=sys.stderr)
        return None


# ── Reference data extraction ───────────────────────────────────────

def extract_reference_data(pg) -> None:
    print("Extracting reference data into cinderhaven_extract.db ...")
    cur = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if EXTRACT_DB.exists():
        EXTRACT_DB.unlink()
    EXTRACT_DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(EXTRACT_DB)
    lc = db.cursor()

    # product_master
    cur.execute(
        "SELECT sku, product_name, product_line, msrp, case_pack_qty "
        "FROM raw.product_master ORDER BY sku"
    )
    rows = cur.fetchall()
    lc.execute("""
        CREATE TABLE product_master (
            sku             TEXT PRIMARY KEY,
            product_name    TEXT NOT NULL,
            product_line    TEXT NOT NULL,
            msrp            REAL NOT NULL,
            case_pack_qty   INTEGER NOT NULL
        )
    """)
    lc.executemany(
        "INSERT INTO product_master VALUES (:sku, :product_name, :product_line, :msrp, :case_pack_qty)",
        [_sqlite_row(r) for r in rows],
    )
    print(f"  product_master: {len(rows)} rows")

    # sku_costs
    cur.execute(
        "SELECT sku, cogs_per_unit, wholesale_walmart, wholesale_costco, "
        "wholesale_whole_foods, wholesale_sprouts, wholesale_regional, "
        "wholesale_unfi, wholesale_kehe, wholesale_dtc "
        "FROM raw.sku_costs ORDER BY sku"
    )
    rows = cur.fetchall()
    lc.execute("""
        CREATE TABLE sku_costs (
            sku                     TEXT PRIMARY KEY,
            cogs_per_unit           REAL NOT NULL,
            wholesale_walmart       REAL,
            wholesale_costco        REAL,
            wholesale_whole_foods   REAL,
            wholesale_sprouts       REAL,
            wholesale_regional      REAL,
            wholesale_unfi          REAL,
            wholesale_kehe          REAL,
            wholesale_dtc           REAL
        )
    """)
    lc.executemany(
        "INSERT INTO sku_costs VALUES "
        "(:sku, :cogs_per_unit, :wholesale_walmart, :wholesale_costco, "
        ":wholesale_whole_foods, :wholesale_sprouts, :wholesale_regional, "
        ":wholesale_unfi, :wholesale_kehe, :wholesale_dtc)",
        [_sqlite_row(r) for r in rows],
    )
    print(f"  sku_costs: {len(rows)} rows")

    # stores (join retailers for plain name)
    cur.execute(
        "SELECT s.store_id, r.name AS retailer, s.region, s.state "
        "FROM raw.stores s "
        "JOIN raw.retailers r ON r.retailer_id = s.retailer_id "
        "ORDER BY s.store_id"
    )
    rows = cur.fetchall()
    lc.execute("""
        CREATE TABLE stores (
            store_id    TEXT PRIMARY KEY,
            retailer    TEXT NOT NULL,
            region      TEXT,
            state       TEXT
        )
    """)
    lc.executemany(
        "INSERT INTO stores VALUES (:store_id, :retailer, :region, :state)",
        [_sqlite_row(r) for r in rows],
    )
    print(f"  stores: {len(rows)} rows")

    # distribution_log
    cur.execute(
        "SELECT sku, store_id, authorized_date, deauthorized_date "
        "FROM raw.distribution_log ORDER BY sku, store_id"
    )
    rows = cur.fetchall()
    lc.execute("""
        CREATE TABLE distribution_log (
            sku                 TEXT NOT NULL,
            store_id            TEXT NOT NULL,
            authorized_date     DATE NOT NULL,
            deauthorized_date   DATE
        )
    """)
    lc.execute("CREATE INDEX idx_distlog_sku ON distribution_log(sku)")
    lc.execute("CREATE INDEX idx_distlog_store ON distribution_log(store_id)")
    lc.executemany(
        "INSERT INTO distribution_log VALUES "
        "(:sku, :store_id, :authorized_date, :deauthorized_date)",
        [_sqlite_row(r) for r in rows],
    )
    print(f"  distribution_log: {len(rows)} rows")

    # promotions (join retailers for plain name)
    cur.execute(
        "SELECT r.name AS retailer, p.sku, p.start_week, p.end_week "
        "FROM raw.promotions p "
        "JOIN raw.retailers r ON r.retailer_id = p.retailer_id "
        "ORDER BY p.start_week"
    )
    rows = cur.fetchall()
    lc.execute("""
        CREATE TABLE promotions (
            retailer    TEXT NOT NULL,
            sku         TEXT NOT NULL,
            start_week  DATE NOT NULL,
            end_week    DATE NOT NULL
        )
    """)
    lc.execute("CREATE INDEX idx_promos_sku ON promotions(sku)")
    lc.execute("CREATE INDEX idx_promos_retailer ON promotions(retailer)")
    lc.executemany(
        "INSERT INTO promotions VALUES (:retailer, :sku, :start_week, :end_week)",
        [_sqlite_row(r) for r in rows],
    )
    print(f"  promotions: {len(rows)} rows")

    # sku_velocity (aggregated from scan_data)
    cur.execute(f"""
        SELECT sku,
               SUM(units_sold) * 1.0 / {WEEKS_IN_WINDOW} AS avg_weekly_units,
               SUM(units_sold) * 1.0 / {WEEKS_IN_WINDOW} * 52 AS total_annual_units
        FROM raw.scan_data
        GROUP BY sku
        ORDER BY avg_weekly_units DESC
    """)
    velocity_rows = cur.fetchall()
    lc.execute("""
        CREATE TABLE sku_velocity (
            sku                 TEXT PRIMARY KEY,
            avg_weekly_units    REAL NOT NULL,
            total_annual_units  REAL NOT NULL,
            velocity_rank       INTEGER NOT NULL
        )
    """)
    ranked = [
        (r["sku"], float(r["avg_weekly_units"]), float(r["total_annual_units"]), rank + 1)
        for rank, r in enumerate(velocity_rows)
    ]
    lc.executemany("INSERT INTO sku_velocity VALUES (?, ?, ?, ?)", ranked)
    print(f"  sku_velocity: {len(ranked)} rows")

    db.commit()
    db.close()
    size_mb = os.path.getsize(EXTRACT_DB) / (1024 * 1024)
    print(f"  -> {EXTRACT_DB}  ({size_mb:.2f} MB)")


# ── Order data extraction ───────────────────────────────────────────

def extract_orders(pg) -> None:
    print("\nExtracting orders into short_ship_orders.db ...")
    cur = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Fetch case_pack_qty for unit-to-case conversion
    cur.execute("SELECT sku, case_pack_qty FROM raw.product_master")
    case_pack = {r["sku"]: r["case_pack_qty"] for r in cur.fetchall()}

    # Retailer orders
    cur.execute(
        "SELECT o.order_id, r.name AS retailer, "
        "       o.po_date, o.requested_ship_date "
        "FROM raw.retailer_orders o "
        "JOIN raw.retailers r ON r.retailer_id = o.retailer_id "
        "ORDER BY o.po_date, o.order_id"
    )
    retailer_orders = cur.fetchall()

    # Distributor orders
    cur.execute(
        "SELECT o.order_id, d.name AS retailer, o.po_date "
        "FROM raw.distributor_orders o "
        "JOIN raw.distributors d ON d.distributor_id = o.distributor_id "
        "ORDER BY o.po_date, o.order_id"
    )
    distributor_orders = cur.fetchall()

    # Promo order IDs (retailer orders with SKUs on promotion at order date)
    cur.execute(
        "SELECT DISTINCT o.order_id "
        "FROM raw.retailer_orders o "
        "JOIN raw.retailer_order_lines ol ON ol.order_id = o.order_id "
        "JOIN raw.promotions p ON p.sku = ol.sku AND p.retailer_id = o.retailer_id "
        "WHERE o.po_date >= p.start_week AND o.po_date <= p.end_week"
    )
    promo_retail = {r["order_id"] for r in cur.fetchall()}

    # Distributor promo orders (UNFI/KeHE orders with promoted SKUs)
    cur.execute(
        "SELECT DISTINCT o.order_id "
        "FROM raw.distributor_orders o "
        "JOIN raw.distributor_order_lines ol ON ol.order_id = o.order_id "
        "JOIN raw.promotions p ON p.sku = ol.sku "
        "WHERE o.po_date >= p.start_week AND o.po_date <= p.end_week"
    )
    promo_dist = {r["order_id"] for r in cur.fetchall()}

    promo_ids = promo_retail | promo_dist

    # Retailer order lines
    cur.execute(
        "SELECT ol.order_id, ol.sku, ol.units_ordered, ol.unit_price "
        "FROM raw.retailer_order_lines ol "
        "ORDER BY ol.order_id, ol.sku"
    )
    retailer_lines = cur.fetchall()

    # Distributor order lines
    cur.execute(
        "SELECT ol.order_id, ol.sku, ol.units_ordered, ol.unit_price "
        "FROM raw.distributor_order_lines ol "
        "ORDER BY ol.order_id, ol.sku"
    )
    distributor_lines = cur.fetchall()

    # DTC / Shopify orders
    cur.execute(
        "SELECT order_id, created_at::date AS order_date "
        "FROM raw.shopify_orders "
        "ORDER BY created_at, order_id"
    )
    dtc_orders = cur.fetchall()

    # DTC order lines (already in units, not cases)
    cur.execute(
        "SELECT order_id, sku, quantity, unit_price "
        "FROM raw.shopify_order_lines "
        "ORDER BY order_id, sku"
    )
    dtc_lines = cur.fetchall()

    # Build local SQLite
    if ORDERS_DB.exists():
        ORDERS_DB.unlink()
    ORDERS_DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(ORDERS_DB)
    lc = db.cursor()

    lc.executescript("""
        CREATE TABLE orders (
            order_id            TEXT PRIMARY KEY,
            retailer            TEXT NOT NULL,
            channel_type        TEXT NOT NULL,
            order_date          DATE NOT NULL,
            due_date            DATE NOT NULL,
            ship_date           DATE,
            delivery_location   TEXT NOT NULL,
            order_type          TEXT NOT NULL
        );
        CREATE INDEX idx_orders_retailer_date ON orders(retailer, order_date);
        CREATE INDEX idx_orders_due_date ON orders(due_date);

        CREATE TABLE order_lines_original (
            order_line_id       TEXT PRIMARY KEY,
            order_id            TEXT NOT NULL,
            sku                 TEXT NOT NULL,
            quantity_ordered    INTEGER NOT NULL,
            unit_of_measure     TEXT NOT NULL,
            unit_price          REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );
        CREATE INDEX idx_lines_orig_order ON order_lines_original(order_id);
        CREATE INDEX idx_lines_orig_sku ON order_lines_original(sku);
    """)

    # Insert retailer orders
    order_rows = []
    for r in retailer_orders:
        po = r["po_date"]
        due = r["requested_ship_date"] or (po + timedelta(days=7))
        order_type = "promo" if r["order_id"] in promo_ids else "standard"
        order_rows.append((
            r["order_id"], r["retailer"], "retail",
            str(po), str(due), None, r["retailer"], order_type,
        ))

    # Insert distributor orders
    for r in distributor_orders:
        po = r["po_date"]
        due = po + timedelta(days=7)
        order_type = "promo" if r["order_id"] in promo_ids else "standard"
        order_rows.append((
            r["order_id"], r["retailer"], "distributor",
            str(po), str(due), None, r["retailer"], order_type,
        ))

    # Insert DTC orders (ship same day)
    for r in dtc_orders:
        od = r["order_date"]
        order_rows.append((
            r["order_id"], "DTC", "dtc",
            str(od), str(od), None, "DTC-CONSUMER", "standard",
        ))

    lc.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        order_rows,
    )
    n_retail = len(retailer_orders)
    n_dist = len(distributor_orders)
    n_dtc = len(dtc_orders)
    print(f"  orders: {len(order_rows)} rows ({n_retail} retail + {n_dist} distributor + {n_dtc} DTC)")

    # Insert order lines (convert Postgres units to cases)
    line_rows = []
    line_seq_by_order: dict[str, int] = {}
    mismatches = 0

    for src_lines in (retailer_lines, distributor_lines):
        for r in src_lines:
            oid = r["order_id"]
            sku = r["sku"]
            pack = case_pack.get(sku, 1)
            units = r["units_ordered"]
            cases = units // pack
            if units % pack != 0:
                mismatches += 1
                cases = max(1, cases)

            seq = line_seq_by_order.get(oid, 0) + 1
            line_seq_by_order[oid] = seq
            line_id = f"L-{oid}-{seq:03d}"

            line_rows.append((
                line_id, oid, sku, cases, "case", float(r["unit_price"]),
            ))

    # DTC lines stay in units (consumer quantities)
    for r in dtc_lines:
        oid = r["order_id"]
        seq = line_seq_by_order.get(oid, 0) + 1
        line_seq_by_order[oid] = seq
        line_id = f"L-{oid}-{seq:03d}"
        line_rows.append((
            line_id, oid, r["sku"], r["quantity"], "unit", float(r["unit_price"]),
        ))

    lc.executemany(
        "INSERT INTO order_lines_original VALUES (?, ?, ?, ?, ?, ?)",
        line_rows,
    )
    print(f"  order_lines_original: {len(line_rows)} rows")
    if mismatches:
        print(f"  WARNING: {mismatches} lines had non-integer case conversion")

    db.commit()
    db.close()
    size_mb = os.path.getsize(ORDERS_DB) / (1024 * 1024)
    print(f"  -> {ORDERS_DB}  ({size_mb:.2f} MB)")


# ── Main ────────────────────────────────────────────────────────────

def main() -> int:
    pg = connect_postgres()

    if pg is None:
        if EXTRACT_DB.exists() and ORDERS_DB.exists():
            print("Using cached local databases (Postgres unavailable).")
            return 0
        print("ERROR: Postgres unreachable and no cached local data.", file=sys.stderr)
        print("Start the proxy:  flyctl proxy 5432 -a cinderhaven-db", file=sys.stderr)
        return 1

    try:
        extract_reference_data(pg)
        extract_orders(pg)
    finally:
        pg.close()

    print("\nExtraction complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
