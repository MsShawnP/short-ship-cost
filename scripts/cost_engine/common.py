"""Shared helpers for cost-engine modules: DB connection, channel
mapping, line-revenue computation, and the standard module return
shape."""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .parameters import REGIONAL_CHAINS

REPO = Path(__file__).resolve().parent.parent.parent
EXTRACT_DB = REPO / "data" / "cinderhaven_extract.db"
ORDERS_DB = REPO / "data" / "short_ship_orders.db"
COST_DB = REPO / "data" / "short_ship_cost.db"


def open_db() -> sqlite3.Connection:
    """Return an orders-DB connection with cinderhaven_extract attached
    as `ext` and Row factory enabled."""
    db = sqlite3.connect(ORDERS_DB)
    db.execute(f"ATTACH DATABASE '{EXTRACT_DB}' AS ext")
    db.row_factory = sqlite3.Row
    return db


def channel_of(retailer: str, channel_type: str) -> str:
    """Map raw retailer + channel_type to a reporting channel name."""
    if channel_type == "dtc":
        return "DTC"
    if retailer in REGIONAL_CHAINS:
        return "Regional"
    return retailer


def line_revenue_expr(qty_col: str) -> str:
    """SQL fragment that computes revenue for a single line, respecting
    case vs unit UoM. Caller must have lo (or ls) aliased on the
    line table and pm aliased on product_master."""
    return (
        f"CASE WHEN {qty_col[:2]}.unit_of_measure = 'case' "
        f"     THEN {qty_col} * pm.case_pack_qty * {qty_col[:2]}.unit_price "
        f"     ELSE {qty_col} * {qty_col[:2]}.unit_price END"
    )


def empty_result(dimension: str, description: str) -> dict:
    return {
        "dimension": dimension,
        "description": description,
        "total_cost": 0.0,
        "by_retailer": [],
        "by_sku": [],
        "by_month": [],
        "detail_events": [],
    }


def aggregate_breakdowns(rows: Iterable[dict]) -> dict:
    """Take a list of {retailer, sku, order_date_month, cost} rows
    and return three aggregated lists: by_retailer, by_sku, by_month."""
    by_retailer: dict[str, float] = defaultdict(float)
    by_sku: dict[str, float] = defaultdict(float)
    by_month: dict[str, float] = defaultdict(float)
    for r in rows:
        by_retailer[r["retailer"]] += r["cost"]
        if r.get("sku"):
            by_sku[r["sku"]] += r["cost"]
        if r.get("month"):
            by_month[r["month"]] += r["cost"]
    return {
        "by_retailer": [{"retailer": k, "cost": v} for k, v in sorted(by_retailer.items())],
        "by_sku": [{"sku": k, "cost": v} for k, v in sorted(by_sku.items(), key=lambda x: -x[1])],
        "by_month": [{"month": k, "cost": v} for k, v in sorted(by_month.items())],
    }
