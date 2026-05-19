"""Upload short-ship-cost pipeline results to Postgres.

Reads the local SQLite databases (short_ship_orders.db, short_ship_cost.db)
and writes shortage simulation results to raw.shortage_* tables in Postgres.
This makes shortage events queryable from other tools — e.g., retailer-
deduction-recovery can join a deduction to the shortage that caused it.

Tables written:
  raw.shortage_order_shorts          — which order lines were shorted
  raw.shortage_dtc_outcomes          — DTC hold / cancel / ship outcomes
  raw.shortage_distributor_returns   — distributor return events
  raw.shortage_cost_summary          — 8-dimension cost totals
  raw.shortage_cost_by_retailer      — cost broken down by retailer
  raw.shortage_cost_by_sku           — cost broken down by SKU
  raw.shortage_cost_by_month         — cost broken down by month
  raw.shortage_deauth_events         — specific deauthorization events
  raw.shortage_cost_parameters       — model parameters used
  raw.shortage_buffer_scenarios      — what-if fill rate scenarios
  raw.shortage_buffer_details        — per-dimension scenario breakdown
  raw.shortage_buffer_deauth         — deauth events avoided per scenario

Usage:
    python scripts/upload_to_postgres.py

Requires flyctl proxy running on localhost:5432, or DATABASE_URL env var.
Idempotent — truncates and reloads all tables on each run.
"""
from __future__ import annotations

import io
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

REPO = Path(__file__).resolve().parent.parent
ORDERS_DB = REPO / "data" / "short_ship_orders.db"
COST_DB = REPO / "data" / "short_ship_cost.db"

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"host=localhost port=5432 dbname=cinderhaven user=postgres"
    f" password={os.environ.get('POSTGRES_PASSWORD', '')}",
)

# ── DDL ────────────────────────────────────────────────────────────────

DDL = """
-- Triage / simulation outputs (from short_ship_orders.db)

CREATE TABLE IF NOT EXISTS raw.shortage_order_shorts (
    short_id            TEXT PRIMARY KEY,
    order_id            TEXT NOT NULL,
    sku                 TEXT NOT NULL,
    quantity_shorted    INTEGER NOT NULL,
    short_reason        TEXT NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.shortage_dtc_outcomes (
    order_id            TEXT PRIMARY KEY,
    hold_start_date     DATE NOT NULL,
    resolution          TEXT NOT NULL,
    resolution_date     DATE NOT NULL,
    days_held           INTEGER NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.shortage_distributor_returns (
    return_id           TEXT PRIMARY KEY,
    order_id            TEXT NOT NULL,
    sku                 TEXT NOT NULL,
    quantity_returned   INTEGER NOT NULL,
    return_reason       TEXT NOT NULL,
    return_date         DATE NOT NULL,
    credit_amount       NUMERIC(12,2) NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Cost engine outputs (from short_ship_cost.db)

CREATE TABLE IF NOT EXISTS raw.shortage_cost_summary (
    dimension                   TEXT PRIMARY KEY,
    total_cost                  NUMERIC(14,2) NOT NULL,
    pct_of_shipped_revenue      NUMERIC(8,4) NOT NULL,
    description                 TEXT NOT NULL,
    loaded_at                   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.shortage_cost_by_retailer (
    dimension           TEXT NOT NULL,
    retailer            TEXT NOT NULL,
    cost                NUMERIC(14,2) NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (dimension, retailer)
);

CREATE TABLE IF NOT EXISTS raw.shortage_cost_by_sku (
    dimension           TEXT NOT NULL,
    sku                 TEXT NOT NULL,
    cost                NUMERIC(14,2) NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (dimension, sku)
);

CREATE TABLE IF NOT EXISTS raw.shortage_cost_by_month (
    dimension           TEXT NOT NULL,
    month               TEXT NOT NULL,
    cost                NUMERIC(14,2) NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (dimension, month)
);

CREATE TABLE IF NOT EXISTS raw.shortage_deauth_events (
    sku                                     TEXT NOT NULL,
    retailer                                TEXT NOT NULL,
    trigger_type                            TEXT NOT NULL,
    velocity_without_shorts                 NUMERIC(10,4),
    velocity_with_shorts                    NUMERIC(10,4),
    threshold                               NUMERIC(10,4),
    fill_rate                               NUMERIC(8,4),
    consecutive_months_below_threshold      INTEGER,
    annualized_revenue_lost                 NUMERIC(14,2) NOT NULL,
    loaded_at                               TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (sku, retailer, trigger_type)
);

CREATE TABLE IF NOT EXISTS raw.shortage_cost_parameters (
    name                TEXT NOT NULL,
    value               NUMERIC(14,4),
    unit                TEXT,
    basis               TEXT,
    level               TEXT,
    description         TEXT,
    source              TEXT,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Buffer simulation results

CREATE TABLE IF NOT EXISTS raw.shortage_buffer_scenarios (
    target_fill_rate            NUMERIC(6,4) PRIMARY KEY,
    actual_fill_rate_achieved   NUMERIC(6,4) NOT NULL,
    total_cost                  NUMERIC(14,2) NOT NULL,
    total_recovery              NUMERIC(14,2) NOT NULL,
    recovery_pct                NUMERIC(8,4) NOT NULL,
    loaded_at                   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.shortage_buffer_details (
    target_fill_rate    NUMERIC(6,4) NOT NULL,
    dimension           TEXT NOT NULL,
    original_cost       NUMERIC(14,2) NOT NULL,
    simulated_cost      NUMERIC(14,2) NOT NULL,
    recovery_amount     NUMERIC(14,2) NOT NULL,
    recovery_pct        NUMERIC(8,4) NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (target_fill_rate, dimension)
);

CREATE TABLE IF NOT EXISTS raw.shortage_buffer_deauth (
    target_fill_rate    NUMERIC(6,4) NOT NULL,
    sku                 TEXT NOT NULL,
    retailer            TEXT NOT NULL,
    trigger_type        TEXT NOT NULL,
    original_status     TEXT NOT NULL,
    simulated_status    TEXT NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (target_fill_rate, sku, retailer, trigger_type)
);
"""

# Table name → (source db, source table, columns for COPY)
TABLE_MAP = [
    # From orders DB
    ("shortage_order_shorts", ORDERS_DB, "order_shorts",
     ["short_id", "order_id", "sku", "quantity_shorted", "short_reason"]),
    ("shortage_dtc_outcomes", ORDERS_DB, "dtc_outcomes",
     ["order_id", "hold_start_date", "resolution", "resolution_date", "days_held"]),
    ("shortage_distributor_returns", ORDERS_DB, "distributor_returns",
     ["return_id", "order_id", "sku", "quantity_returned", "return_reason",
      "return_date", "credit_amount"]),
    # From cost DB
    ("shortage_cost_summary", COST_DB, "cost_summary",
     ["dimension", "total_cost", "pct_of_shipped_revenue", "description"]),
    ("shortage_cost_by_retailer", COST_DB, "cost_by_retailer",
     ["dimension", "retailer", "cost"]),
    ("shortage_cost_by_sku", COST_DB, "cost_by_sku",
     ["dimension", "sku", "cost"]),
    ("shortage_cost_by_month", COST_DB, "cost_by_month",
     ["dimension", "month", "cost"]),
    ("shortage_deauth_events", COST_DB, "deauthorization_events",
     ["sku", "retailer", "trigger_type", "velocity_without_shorts",
      "velocity_with_shorts", "threshold", "fill_rate",
      "consecutive_months_below_threshold", "annualized_revenue_lost"]),
    ("shortage_cost_parameters", COST_DB, "cost_parameters",
     ["name", "value", "unit", "basis", "level", "description", "source"]),
    # Buffer simulation (may not exist yet)
    ("shortage_buffer_scenarios", COST_DB, "buffer_scenarios",
     ["target_fill_rate", "actual_fill_rate_achieved", "total_cost",
      "total_recovery", "recovery_pct"]),
    ("shortage_buffer_details", COST_DB, "buffer_scenario_details",
     ["target_fill_rate", "dimension", "original_cost", "simulated_cost",
      "recovery_amount", "recovery_pct"]),
    ("shortage_buffer_deauth", COST_DB, "buffer_deauth_recovery",
     ["target_fill_rate", "sku", "retailer", "trigger_type",
      "original_status", "simulated_status"]),
]


def copy_from_sqlite(pg_cur, pg_table: str, sqlite_path: Path,
                     sqlite_table: str, columns: list[str]) -> int:
    """Read rows from SQLite and bulk-load into Postgres via COPY."""
    db = sqlite3.connect(sqlite_path)
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    # Check if source table exists
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (sqlite_table,),
    )
    if not cur.fetchone():
        db.close()
        return -1  # table doesn't exist

    cols_sql = ", ".join(columns)
    cur.execute(f"SELECT {cols_sql} FROM {sqlite_table}")
    rows = cur.fetchall()
    db.close()

    if not rows:
        return 0

    buf = io.StringIO()
    for row in rows:
        vals = []
        for v in row:
            if v is None:
                vals.append("\\N")
            else:
                vals.append(str(v).replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n"))
        buf.write("\t".join(vals) + "\n")
    buf.seek(0)

    copy_sql = f"COPY raw.{pg_table} ({cols_sql}) FROM STDIN WITH (FORMAT text, NULL '\\N')"
    pg_cur.copy_expert(copy_sql, buf)
    return len(rows)


def main() -> int:
    # Verify SQLite DBs exist
    for db_path in [ORDERS_DB, COST_DB]:
        if not db_path.exists():
            print(f"ERROR: {db_path} not found. Run the pipeline first.", file=sys.stderr)
            return 1

    try:
        pg = psycopg2.connect(DATABASE_URL)
        pg.autocommit = False
    except psycopg2.OperationalError as e:
        print(f"ERROR: Cannot connect to Postgres — {e}", file=sys.stderr)
        print("Start flyctl proxy: flyctl proxy 5432 -a cinderhaven-data-platform", file=sys.stderr)
        return 1

    cur = pg.cursor()

    # Create tables if they don't exist
    print("Creating tables (if needed)...")
    cur.execute(DDL)

    # Truncate all tables before reload
    all_pg_tables = [t[0] for t in TABLE_MAP]
    for t in all_pg_tables:
        cur.execute(f"TRUNCATE raw.{t}")
    print(f"Truncated {len(all_pg_tables)} tables.")

    # Load each table
    total_rows = 0
    for pg_table, sqlite_path, sqlite_table, columns in TABLE_MAP:
        count = copy_from_sqlite(cur, pg_table, sqlite_path, sqlite_table, columns)
        if count == -1:
            print(f"  {pg_table}: skipped (source table {sqlite_table} not found)")
        elif count == 0:
            print(f"  {pg_table}: 0 rows (empty source)")
        else:
            print(f"  {pg_table}: {count:,} rows")
            total_rows += count

    pg.commit()
    print(f"\nDone. {total_rows:,} total rows loaded into Postgres.")
    cur.close()
    pg.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
