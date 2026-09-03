"""Rebuild short-ship cost analysis from the cinderhaven-data-platform
causal fulfillment data.

Queries the local Docker Postgres replica directly.  Computes 4
dimensions (forgone_revenue, compliance_fines, chargebacks, deductions),
writes data/short_ship_cost.db, exports JSON for the React app, and
prints the figure summary.

Run from repo root:
    python scripts/rebuild_from_platform.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras

REPO = Path(__file__).resolve().parent.parent
COST_DB = REPO / "data" / "short_ship_cost.db"
JSON_DIR = REPO / "web" / "public" / "data"

CONTRIBUTION_MARGIN_PCT = 0.52
TOP_N_SKUS = 20
DOLLAR_PLACES = 2
PCT_PLACES = 4

# DB connection -- set DATABASE_URL in .env (see .env.example).
# We require the full URL rather than assembling one from a password variable:
# interpolating the credential into a connection string inline would reintroduce
# the pattern the gitleaks rule forbids, and would duplicate connection config
# that .env already owns.
def _bootstrap_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for candidate in [REPO / ".env", REPO.parent / ".env"]:
        if candidate.exists():
            load_dotenv(candidate)
            return


_bootstrap_env()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise EnvironmentError(
        "Set DATABASE_URL in .env before running the pipeline (see .env.example)."
    )

CHANNEL_MAP = {
    "RET-WALMART": "Walmart",
    "RET-COSTCO": "Costco",
    "RET-WHOLEFOODS": "Whole Foods",
    "RET-SPROUTS": "Sprouts",
    "RET-KROGER": "Kroger",
    "RET-REGIONAL": "Regional",
    "DIST-UNFI": "UNFI",
    "DIST-KEHE": "KeHE",
    "DIST-DPI": "DPI Northwest",
}

FINE_SCHEDULE = {
    "Walmart":    ("line_cogs",       0.03,  0.98),
    "Costco":     ("flat",            250.0, 0.0),
    "Whole Foods":("po_cogs",         0.02,  0.95),
    "Sprouts":    ("po_cogs",         0.01,  0.90),
    "Kroger":     ("po_cogs",         0.01,  0.90),
    "Regional":   ("po_cogs",         0.01,  0.90),
    "UNFI":       ("shorted_value",   0.03,  0.95),
    "KeHE":       ("po_cogs",         0.02,  0.95),
    "DPI Northwest": ("po_cogs",      0.01,  0.90),
}


def pg_connect():
    return psycopg2.connect(DATABASE_URL)


def ch(partner_id: str) -> str:
    return CHANNEL_MAP.get(partner_id, partner_id)


# ---------------------------------------------------------------------------
# Dimension 1: Forgone revenue (+ contribution margin)
# ---------------------------------------------------------------------------

def compute_forgone_revenue(conn) -> dict:
    sql_retailer = """
        SELECT
            o.retailer_id          AS partner_id,
            sl.sku,
            to_char(s.ship_date, 'YYYY-MM') AS month,
            sl.units_ordered - sl.units_shipped AS units_short,
            ol.unit_price,
            sc.cogs_per_unit
        FROM raw.retailer_shipment_lines sl
        JOIN raw.retailer_shipments s  ON sl.shipment_id = s.shipment_id
        JOIN raw.retailer_orders o     ON s.order_id = o.order_id
        JOIN raw.retailer_order_lines ol ON o.order_id = ol.order_id AND sl.sku = ol.sku
        JOIN raw.sku_costs sc          ON sl.sku = sc.sku
        WHERE sl.units_shipped < sl.units_ordered
    """
    sql_distributor = """
        SELECT
            o.distributor_id       AS partner_id,
            sl.sku,
            to_char(s.ship_date, 'YYYY-MM') AS month,
            sl.units_ordered - sl.units_shipped AS units_short,
            ol.unit_price,
            sc.cogs_per_unit
        FROM raw.distributor_shipment_lines sl
        JOIN raw.distributor_shipments s  ON sl.shipment_id = s.shipment_id
        JOIN raw.distributor_orders o     ON s.order_id = o.order_id
        JOIN raw.distributor_order_lines ol ON o.order_id = ol.order_id AND sl.sku = ol.sku
        JOIN raw.sku_costs sc             ON sl.sku = sc.sku
        WHERE sl.units_shipped < sl.units_ordered
    """
    rows = []
    totals = {"revenue": 0.0, "contribution": 0.0}
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        for sql in (sql_retailer, sql_distributor):
            cur.execute(sql)
            for r in cur:
                rev = float(r["units_short"]) * float(r["unit_price"])
                cogs = float(r["units_short"]) * float(r["cogs_per_unit"])
                contrib = rev - cogs
                totals["revenue"] += rev
                totals["contribution"] += contrib
                rows.append({
                    "retailer": ch(r["partner_id"]),
                    "sku": r["sku"],
                    "month": r["month"],
                    "cost": rev,
                    "contribution": contrib,
                })

    result = _build_result(
        "forgone_revenue",
        "Units not shipped × wholesale price. Secondary: forgone contribution margin.",
        rows,
    )
    result["forgone_contribution"] = totals["contribution"]
    return result


# ---------------------------------------------------------------------------
# Dimension 2: Compliance fines (modeled from contractual schedules)
# ---------------------------------------------------------------------------

def _load_po_lines(conn) -> dict:
    """Load all PO lines with shipment data, grouped by (order_id, channel)."""
    po_data = defaultdict(lambda: {"lines": [], "channel": None, "month": None})

    sql_retailer = """
        SELECT
            o.order_id,
            o.retailer_id AS partner_id,
            sl.sku,
            to_char(s.ship_date, 'YYYY-MM') AS month,
            sl.units_ordered,
            sl.units_shipped,
            ol.unit_price,
            sc.cogs_per_unit
        FROM raw.retailer_shipment_lines sl
        JOIN raw.retailer_shipments s  ON sl.shipment_id = s.shipment_id
        JOIN raw.retailer_orders o     ON s.order_id = o.order_id
        JOIN raw.retailer_order_lines ol ON o.order_id = ol.order_id AND sl.sku = ol.sku
        JOIN raw.sku_costs sc          ON sl.sku = sc.sku
    """
    sql_distributor = """
        SELECT
            o.order_id,
            o.distributor_id AS partner_id,
            sl.sku,
            to_char(s.ship_date, 'YYYY-MM') AS month,
            sl.units_ordered,
            sl.units_shipped,
            ol.unit_price,
            sc.cogs_per_unit
        FROM raw.distributor_shipment_lines sl
        JOIN raw.distributor_shipments s  ON sl.shipment_id = s.shipment_id
        JOIN raw.distributor_orders o     ON s.order_id = o.order_id
        JOIN raw.distributor_order_lines ol ON o.order_id = ol.order_id AND sl.sku = ol.sku
        JOIN raw.sku_costs sc             ON sl.sku = sc.sku
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        for sql in (sql_retailer, sql_distributor):
            cur.execute(sql)
            for r in cur:
                oid = r["order_id"]
                po_data[oid]["lines"].append({
                    "sku": r["sku"],
                    "units_ordered": int(r["units_ordered"]),
                    "units_shipped": int(r["units_shipped"]),
                    "unit_price": float(r["unit_price"]),
                    "cogs": float(r["cogs_per_unit"]),
                })
                po_data[oid]["channel"] = ch(r["partner_id"])
                po_data[oid]["month"] = r["month"]
    return dict(po_data)


def compute_compliance_fines(conn, po_data: dict | None = None) -> dict:
    if po_data is None:
        po_data = _load_po_lines(conn)

    rows = []
    for order_id, payload in po_data.items():
        channel = payload["channel"]
        month = payload["month"]
        lines = payload["lines"]
        schedule = FINE_SCHEDULE.get(channel)
        if not schedule:
            continue
        basis_kind, rate, target = schedule

        po_demand_value = sum(L["units_ordered"] * L["unit_price"] for L in lines)
        po_shipped_value = sum(L["units_shipped"] * L["unit_price"] for L in lines)
        po_demand_cogs = sum(L["units_ordered"] * L["cogs"] for L in lines)
        shorted_value = po_demand_value - po_shipped_value
        po_fill = po_shipped_value / po_demand_value if po_demand_value else 1.0

        if basis_kind == "line_cogs":
            for L in lines:
                if L["units_ordered"] == 0:
                    continue
                line_fill = L["units_shipped"] / L["units_ordered"]
                if line_fill < target:
                    line_cogs = L["units_ordered"] * L["cogs"]
                    rows.append({
                        "retailer": channel,
                        "sku": L["sku"],
                        "month": month,
                        "cost": rate * line_cogs,
                    })

        elif basis_kind == "flat":
            if po_shipped_value < po_demand_value:
                shortages = [(L["sku"], (L["units_ordered"] - L["units_shipped"]) * L["unit_price"])
                             for L in lines if L["units_shipped"] < L["units_ordered"]]
                if shortages:
                    shortages.sort(key=lambda x: x[1], reverse=True)
                    rows.append({
                        "retailer": channel,
                        "sku": shortages[0][0],
                        "month": month,
                        "cost": rate,
                    })

        elif basis_kind == "po_cogs":
            if po_fill < target and po_demand_value > 0:
                fine = rate * po_demand_cogs
                for L in lines:
                    share = (L["units_ordered"] * L["unit_price"]) / po_demand_value
                    rows.append({
                        "retailer": channel,
                        "sku": L["sku"],
                        "month": month,
                        "cost": fine * share,
                    })

        elif basis_kind == "shorted_value":
            if po_fill < target and shorted_value > 0:
                fine = rate * shorted_value
                for L in lines:
                    L_short = (L["units_ordered"] - L["units_shipped"]) * L["unit_price"]
                    if L_short > 0:
                        rows.append({
                            "retailer": channel,
                            "sku": L["sku"],
                            "month": month,
                            "cost": fine * (L_short / shorted_value),
                        })

    return _build_result(
        "compliance_fines",
        "Contractual OTIF fines applied to real shortfall events. "
        "Rates from industry-standard retailer compliance programs.",
        rows,
    )


# ---------------------------------------------------------------------------
# Dimension 3: Short-ship chargebacks (actual event-driven)
# ---------------------------------------------------------------------------

def compute_chargebacks(conn) -> dict:
    sql = """
        SELECT retailer_id AS partner_id, sku,
               to_char(month, 'YYYY-MM') AS month,
               amount::float AS cost
        FROM raw.retailer_chargebacks
        WHERE reason = 'short_ship'
        UNION ALL
        SELECT distributor_id AS partner_id, sku,
               to_char(month, 'YYYY-MM') AS month,
               amount::float AS cost
        FROM raw.distributor_chargebacks
        WHERE reason = 'short_ship'
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur:
            rows.append({
                "retailer": ch(r["partner_id"]),
                "sku": r["sku"],
                "month": r["month"],
                "cost": float(r["cost"]),
            })
    return _build_result(
        "chargebacks",
        "Event-driven chargebacks for short_ship reason. "
        "Actual amounts from platform — no fallback rates.",
        rows,
    )


# ---------------------------------------------------------------------------
# Dimension 4: Short-ship deductions (actual event-driven)
# ---------------------------------------------------------------------------

def compute_deductions(conn) -> dict:
    """Query short_ship deductions and attribute to SKUs by order-line
    demand share.  Deductions are order-level — a naive JOIN to
    order_lines fans out the amount across every SKU on the order."""
    sql_retailer = """
        SELECT rd.deduction_id,
               rd.retailer_id AS partner_id,
               rd.order_id,
               to_char(rd.deduction_date, 'YYYY-MM') AS month,
               rd.amount::float AS cost
        FROM raw.retailer_deductions rd
        WHERE rd.deduction_type = 'short_ship'
    """
    sql_dist = """
        SELECT dd.deduction_id,
               dd.distributor_id AS partner_id,
               dd.order_id,
               to_char(dd.deduction_date, 'YYYY-MM') AS month,
               dd.amount::float AS cost
        FROM raw.distributor_deductions dd
        WHERE dd.deduction_type = 'short_ship'
    """
    # Load order-line shares for SKU attribution
    order_sku_shares = {}  # order_id -> [{sku, share}]
    share_sql = """
        SELECT order_id, sku, line_total::float AS lt
        FROM raw.retailer_order_lines
        UNION ALL
        SELECT order_id, sku, line_total::float AS lt
        FROM raw.distributor_order_lines
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(share_sql)
        order_totals = defaultdict(float)
        order_lines_raw = defaultdict(list)
        for r in cur:
            order_lines_raw[r["order_id"]].append({"sku": r["sku"], "lt": r["lt"]})
            order_totals[r["order_id"]] += r["lt"]
        for oid, lines in order_lines_raw.items():
            total = order_totals[oid]
            if total > 0:
                order_sku_shares[oid] = [
                    {"sku": L["sku"], "share": L["lt"] / total}
                    for L in lines
                ]
            else:
                order_sku_shares[oid] = [
                    {"sku": L["sku"], "share": 1.0 / len(lines)}
                    for L in lines
                ]

    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        for sql in (sql_retailer, sql_dist):
            cur.execute(sql)
            for r in cur:
                channel = ch(r["partner_id"])
                month = r["month"]
                cost = float(r["cost"])
                oid = r["order_id"]

                shares = order_sku_shares.get(oid)
                if shares:
                    for s in shares:
                        rows.append({
                            "retailer": channel,
                            "sku": s["sku"],
                            "month": month,
                            "cost": cost * s["share"],
                        })
                else:
                    rows.append({
                        "retailer": channel,
                        "sku": "UNATTRIBUTED",
                        "month": month,
                        "cost": cost,
                    })

    return _build_result(
        "deductions",
        "Event-driven deductions for short_ship type. "
        "Actual amounts withheld from remittance payments.",
        rows,
    )


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _build_result(dimension: str, description: str, rows: list[dict]) -> dict:
    by_retailer = defaultdict(float)
    by_sku = defaultdict(float)
    by_month = defaultdict(float)
    by_retailer_month = defaultdict(float)
    by_sku_month = defaultdict(float)
    by_sku_retailer = defaultdict(float)
    total = 0.0

    for r in rows:
        cost = r["cost"]
        retailer = r["retailer"]
        sku = r.get("sku")
        month = r.get("month")
        total += cost
        by_retailer[retailer] += cost
        if sku:
            by_sku[sku] += cost
        if month:
            by_month[month] += cost
        if retailer and month:
            by_retailer_month[(retailer, month)] += cost
        if sku and month:
            by_sku_month[(sku, month)] += cost
        if sku and retailer:
            by_sku_retailer[(sku, retailer)] += cost

    return {
        "dimension": dimension,
        "description": description,
        "total_cost": total,
        "by_retailer": [{"retailer": k, "cost": v} for k, v in sorted(by_retailer.items())],
        "by_sku": [{"sku": k, "cost": v} for k, v in sorted(by_sku.items(), key=lambda x: -x[1])],
        "by_month": [{"month": k, "cost": v} for k, v in sorted(by_month.items())],
        "by_retailer_month": [
            {"retailer": r, "month": m, "cost": v}
            for (r, m), v in sorted(by_retailer_month.items())
        ],
        "by_sku_month": [
            {"sku": s, "month": m, "cost": v}
            for (s, m), v in sorted(by_sku_month.items())
        ],
        "by_sku_retailer": [
            {"sku": s, "retailer": r, "cost": v}
            for (s, r), v in sorted(by_sku_retailer.items())
        ],
    }


# ---------------------------------------------------------------------------
# Revenue and fill-rate queries
# ---------------------------------------------------------------------------

def compute_revenue_and_fill(conn) -> dict:
    """Compute invoiced revenue and fill rates from platform data."""
    sql = """
        WITH retailer AS (
            SELECT
                SUM(sl.units_ordered * ol.unit_price) AS demand,
                SUM(sl.units_shipped * ol.unit_price) AS shipped,
                COUNT(DISTINCT o.order_id) AS orders,
                COUNT(*) AS lines
            FROM raw.retailer_shipment_lines sl
            JOIN raw.retailer_shipments s ON sl.shipment_id = s.shipment_id
            JOIN raw.retailer_orders o ON s.order_id = o.order_id
            JOIN raw.retailer_order_lines ol ON o.order_id = ol.order_id AND sl.sku = ol.sku
        ),
        distributor AS (
            SELECT
                SUM(sl.units_ordered * ol.unit_price) AS demand,
                SUM(sl.units_shipped * ol.unit_price) AS shipped,
                COUNT(DISTINCT o.order_id) AS orders,
                COUNT(*) AS lines
            FROM raw.distributor_shipment_lines sl
            JOIN raw.distributor_shipments s ON sl.shipment_id = s.shipment_id
            JOIN raw.distributor_orders o ON s.order_id = o.order_id
            JOIN raw.distributor_order_lines ol ON o.order_id = ol.order_id AND sl.sku = ol.sku
        )
        SELECT
            r.demand AS ret_demand, r.shipped AS ret_shipped,
            r.orders AS ret_orders, r.lines AS ret_lines,
            d.demand AS dist_demand, d.shipped AS dist_shipped,
            d.orders AS dist_orders, d.lines AS dist_lines
        FROM retailer r, distributor d
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        r = cur.fetchone()

    ret_demand = float(r["ret_demand"] or 0)
    ret_shipped = float(r["ret_shipped"] or 0)
    dist_demand = float(r["dist_demand"] or 0)
    dist_shipped = float(r["dist_shipped"] or 0)

    total_demand = ret_demand + dist_demand
    total_shipped = ret_shipped + dist_shipped

    return {
        "retailer_demand": ret_demand,
        "retailer_shipped": ret_shipped,
        "retailer_fill": ret_shipped / ret_demand if ret_demand else 0,
        "retailer_orders": int(r["ret_orders"]),
        "retailer_lines": int(r["ret_lines"]),
        "distributor_demand": dist_demand,
        "distributor_shipped": dist_shipped,
        "distributor_fill": dist_shipped / dist_demand if dist_demand else 0,
        "distributor_orders": int(r["dist_orders"]),
        "distributor_lines": int(r["dist_lines"]),
        "total_demand": total_demand,
        "total_shipped": total_shipped,
        "overall_fill": total_shipped / total_demand if total_demand else 0,
        "total_orders": int(r["ret_orders"]) + int(r["dist_orders"]),
        "total_lines": int(r["ret_lines"]) + int(r["dist_lines"]),
    }


def compute_time_window(conn) -> tuple[str, str]:
    sql = """
        SELECT MIN(d)::text, MAX(d)::text FROM (
            SELECT ship_date AS d FROM raw.retailer_shipments
            UNION ALL
            SELECT ship_date AS d FROM raw.distributor_shipments
        ) t
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchone()


def compute_orders_by_month(conn) -> list[dict]:
    sql = """
        SELECT
            to_char(s.ship_date, 'YYYY-MM') AS month,
            SUM(sl.units_shipped * ol.unit_price) AS shipped_revenue,
            SUM(sl.units_ordered * ol.unit_price) AS demand,
            COUNT(DISTINCT o.order_id) AS order_count
        FROM raw.retailer_shipment_lines sl
        JOIN raw.retailer_shipments s ON sl.shipment_id = s.shipment_id
        JOIN raw.retailer_orders o ON s.order_id = o.order_id
        JOIN raw.retailer_order_lines ol ON o.order_id = ol.order_id AND sl.sku = ol.sku
        GROUP BY 1
        UNION ALL
        SELECT
            to_char(s.ship_date, 'YYYY-MM') AS month,
            SUM(sl.units_shipped * ol.unit_price) AS shipped_revenue,
            SUM(sl.units_ordered * ol.unit_price) AS demand,
            COUNT(DISTINCT o.order_id) AS order_count
        FROM raw.distributor_shipment_lines sl
        JOIN raw.distributor_shipments s ON sl.shipment_id = s.shipment_id
        JOIN raw.distributor_orders o ON s.order_id = o.order_id
        JOIN raw.distributor_order_lines ol ON o.order_id = ol.order_id AND sl.sku = ol.sku
        GROUP BY 1
    """
    merged = defaultdict(lambda: {"shipped": 0.0, "demand": 0.0, "orders": 0})
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur:
            m = r["month"]
            merged[m]["shipped"] += float(r["shipped_revenue"] or 0)
            merged[m]["demand"] += float(r["demand"] or 0)
            merged[m]["orders"] += int(r["order_count"])

    return [
        {"month": m, "shipped_revenue": round(v["shipped"], 2),
         "demand": round(v["demand"], 2), "order_count": v["orders"]}
        for m, v in sorted(merged.items())
    ]


# ---------------------------------------------------------------------------
# Buffer simulation
# ---------------------------------------------------------------------------

BUFFER_TARGETS = (0.95, 0.97, 0.98, 0.99)


def simulate_buffer(conn, baseline_results: dict, rev_info: dict) -> list[dict]:
    """Simulate 'what if fill were higher' for forgone revenue and
    compliance fines.  Chargebacks and deductions are actual events —
    scaled proportionally to remaining short ratio."""
    po_data = _load_po_lines(conn)
    current_fill = rev_info["overall_fill"]

    scenarios = []
    for target in BUFFER_TARGETS:
        sim_results = {}

        # Forgone revenue: lift each short line to target
        sim_forgone = _simulate_forgone_at(conn, target)
        sim_results["forgone_revenue"] = sim_forgone

        # Compliance fines: recompute with lifted fill
        sim_fines = _simulate_fines_at(po_data, target)
        sim_results["compliance_fines"] = sim_fines

        # Chargebacks and deductions: scale by remaining short ratio
        if current_fill < 1.0:
            remaining_short_ratio = (1.0 - target) / (1.0 - current_fill)
            remaining_short_ratio = max(0.0, min(1.0, remaining_short_ratio))
        else:
            remaining_short_ratio = 0.0

        for dim in ("chargebacks", "deductions"):
            base = baseline_results[dim]["total_cost"]
            sim_results[dim] = {
                "dimension": dim,
                "total_cost": base * remaining_short_ratio,
            }

        sim_total = sum(r["total_cost"] for r in sim_results.values())
        base_total = sum(baseline_results[d]["total_cost"] for d in sim_results)
        recovery = base_total - sim_total
        recovery_pct = (recovery / base_total * 100) if base_total else 0

        # Compute achieved fill (approximate)
        achieved = min(target, 1.0)

        scenarios.append({
            "target_fill_rate": target,
            "actual_fill_rate_achieved": achieved,
            "total_cost": sim_total,
            "total_recovery": recovery,
            "recovery_pct": recovery_pct,
            "by_dimension": {
                dim: {
                    "original": baseline_results[dim]["total_cost"],
                    "simulated": sim_results[dim]["total_cost"],
                    "recovery": baseline_results[dim]["total_cost"] - sim_results[dim]["total_cost"],
                    "recovery_pct": (
                        (baseline_results[dim]["total_cost"] - sim_results[dim]["total_cost"])
                        / baseline_results[dim]["total_cost"] * 100
                    ) if baseline_results[dim]["total_cost"] else 0,
                }
                for dim in sim_results
            },
        })

    return scenarios


def _simulate_forgone_at(conn, target: float) -> dict:
    """Recompute forgone revenue as if each line shipped at least target%."""
    sql_retailer = """
        SELECT
            o.retailer_id AS partner_id, sl.sku,
            to_char(s.ship_date, 'YYYY-MM') AS month,
            sl.units_ordered, sl.units_shipped,
            ol.unit_price
        FROM raw.retailer_shipment_lines sl
        JOIN raw.retailer_shipments s  ON sl.shipment_id = s.shipment_id
        JOIN raw.retailer_orders o     ON s.order_id = o.order_id
        JOIN raw.retailer_order_lines ol ON o.order_id = ol.order_id AND sl.sku = ol.sku
        WHERE sl.units_shipped < sl.units_ordered
    """
    sql_distributor = """
        SELECT
            o.distributor_id AS partner_id, sl.sku,
            to_char(s.ship_date, 'YYYY-MM') AS month,
            sl.units_ordered, sl.units_shipped,
            ol.unit_price
        FROM raw.distributor_shipment_lines sl
        JOIN raw.distributor_shipments s  ON sl.shipment_id = s.shipment_id
        JOIN raw.distributor_orders o     ON s.order_id = o.order_id
        JOIN raw.distributor_order_lines ol ON o.order_id = ol.order_id AND sl.sku = ol.sku
        WHERE sl.units_shipped < sl.units_ordered
    """
    total = 0.0
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        for sql in (sql_retailer, sql_distributor):
            cur.execute(sql)
            for r in cur:
                ordered = int(r["units_ordered"])
                shipped = int(r["units_shipped"])
                new_shipped = max(shipped, round(ordered * target))
                new_shipped = min(ordered, new_shipped)
                still_short = ordered - new_shipped
                if still_short > 0:
                    total += still_short * float(r["unit_price"])

    return {"dimension": "forgone_revenue", "total_cost": total}


def _simulate_fines_at(po_data: dict, target: float) -> dict:
    """Recompute compliance fines as if each line shipped at least target%."""
    total = 0.0
    for order_id, payload in po_data.items():
        channel = payload["channel"]
        lines = payload["lines"]
        schedule = FINE_SCHEDULE.get(channel)
        if not schedule:
            continue
        basis_kind, rate, threshold = schedule

        sim_lines = []
        for L in lines:
            new_shipped = max(L["units_shipped"], round(L["units_ordered"] * target))
            new_shipped = min(L["units_ordered"], new_shipped)
            sim_lines.append({**L, "units_shipped": new_shipped})

        po_demand_value = sum(L["units_ordered"] * L["unit_price"] for L in sim_lines)
        po_shipped_value = sum(L["units_shipped"] * L["unit_price"] for L in sim_lines)
        po_demand_cogs = sum(L["units_ordered"] * L["cogs"] for L in sim_lines)
        shorted_value = po_demand_value - po_shipped_value
        po_fill = po_shipped_value / po_demand_value if po_demand_value else 1.0

        if basis_kind == "line_cogs":
            for L in sim_lines:
                if L["units_ordered"] == 0:
                    continue
                line_fill = L["units_shipped"] / L["units_ordered"]
                if line_fill < threshold:
                    total += rate * L["units_ordered"] * L["cogs"]

        elif basis_kind == "flat":
            if po_shipped_value < po_demand_value:
                total += rate

        elif basis_kind == "po_cogs":
            if po_fill < threshold:
                total += rate * po_demand_cogs

        elif basis_kind == "shorted_value":
            if po_fill < threshold and shorted_value > 0:
                total += rate * shorted_value

    return {"dimension": "compliance_fines", "total_cost": total}


# ---------------------------------------------------------------------------
# Write SQLite cost DB
# ---------------------------------------------------------------------------

def write_cost_db(results: dict, rev_info: dict, scenarios: list[dict]) -> None:
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
        CREATE TABLE cost_parameters (
            name        TEXT PRIMARY KEY,
            value       REAL,
            unit        TEXT,
            basis       TEXT,
            level       TEXT,
            description TEXT,
            source      TEXT
        );
        CREATE TABLE buffer_scenarios (
            target_fill_rate          REAL PRIMARY KEY,
            actual_fill_rate_achieved REAL NOT NULL,
            total_cost                REAL NOT NULL,
            total_recovery            REAL NOT NULL,
            recovery_pct              REAL NOT NULL
        );
        CREATE TABLE buffer_scenario_details (
            target_fill_rate REAL NOT NULL,
            dimension        TEXT NOT NULL,
            original_cost    REAL NOT NULL,
            simulated_cost   REAL NOT NULL,
            recovery_amount  REAL NOT NULL,
            recovery_pct     REAL NOT NULL,
            PRIMARY KEY (target_fill_rate, dimension)
        );
    """)

    shipped = rev_info["total_shipped"]
    for dim, res in results.items():
        pct = (res["total_cost"] / shipped * 100) if shipped else 0
        cur.execute(
            "INSERT INTO cost_summary VALUES (?, ?, ?, ?)",
            (dim, res["total_cost"], pct, res["description"]),
        )
        for r in res["by_retailer"]:
            cur.execute(
                "INSERT INTO cost_by_retailer VALUES (?, ?, ?)",
                (dim, r["retailer"], r["cost"]),
            )
        for r in res["by_sku"]:
            cur.execute(
                "INSERT INTO cost_by_sku VALUES (?, ?, ?)",
                (dim, r["sku"], r["cost"]),
            )
        for r in res["by_month"]:
            cur.execute(
                "INSERT INTO cost_by_month VALUES (?, ?, ?)",
                (dim, r["month"], r["cost"]),
            )

    for name, info in FINE_SCHEDULE.items():
        basis_kind, rate, target = info
        cur.execute(
            "INSERT INTO cost_parameters VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"fine_{name.lower().replace(' ', '_')}",
             rate, "USD" if basis_kind == "flat" else "fraction",
             basis_kind, "PO" if basis_kind != "line_cogs" else "line",
             f"{name} compliance fine schedule",
             "docs/cost-engine-benchmarks.md"),
        )

    for scen in scenarios:
        cur.execute(
            "INSERT INTO buffer_scenarios VALUES (?, ?, ?, ?, ?)",
            (scen["target_fill_rate"], scen["actual_fill_rate_achieved"],
             scen["total_cost"], scen["total_recovery"], scen["recovery_pct"]),
        )
        for dim, detail in scen["by_dimension"].items():
            cur.execute(
                "INSERT INTO buffer_scenario_details VALUES (?, ?, ?, ?, ?, ?)",
                (scen["target_fill_rate"], dim,
                 detail["original"], detail["simulated"],
                 detail["recovery"], detail["recovery_pct"]),
            )

    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Print summary
# ---------------------------------------------------------------------------

def print_summary(results: dict, rev_info: dict, scenarios: list[dict]) -> None:
    shipped = rev_info["total_shipped"]
    demand = rev_info["total_demand"]
    print()
    print("=" * 72)
    print("  SHORT-SHIP COST REBUILD — PLATFORM CAUSAL DATA")
    print("=" * 72)
    print()
    print(f"  Retailer fill rate:      {rev_info['retailer_fill']*100:.1f}%")
    print(f"  Distributor fill rate:   {rev_info['distributor_fill']*100:.1f}%")
    print(f"  Overall fill rate:       {rev_info['overall_fill']*100:.1f}%")
    print()
    print(f"  Total demand (invoiced): ${demand:>15,.0f}  (${demand/3:,.0f}/yr)")
    print(f"  Total shipped:           ${shipped:>15,.0f}  (${shipped/3:,.0f}/yr)")
    print(f"  Total orders:            {rev_info['total_orders']:>15,}")
    print(f"  Total shipment lines:    {rev_info['total_lines']:>15,}")
    print()

    dims = ["forgone_revenue", "compliance_fines", "chargebacks", "deductions"]
    print(f"  {'#':<3}{'DIMENSION':<22}{'TOTAL COST (3yr)':>18}{'ANNUAL':>14}{'% OF SHIPPED':>14}")
    print("  " + "-" * 68)
    grand = 0.0
    for i, dim in enumerate(dims, 1):
        res = results[dim]
        pct = (res["total_cost"] / shipped * 100) if shipped else 0
        annual = res["total_cost"] / 3
        grand += res["total_cost"]
        print(f"  {i:<3}{dim:<22}${res['total_cost']:>16,.0f}  ${annual:>11,.0f}  {pct:>12.2f}%")
    grand_pct = (grand / shipped * 100) if shipped else 0
    print("  " + "-" * 68)
    print(f"  {'TOTAL':>25}${grand:>16,.0f}  ${grand/3:>11,.0f}  {grand_pct:>12.2f}%")
    print()

    fr = results["forgone_revenue"]
    print(f"  Forgone contribution margin (3yr): ${fr.get('forgone_contribution', 0):>12,.0f}")
    print(f"  Forgone contribution margin (ann): ${fr.get('forgone_contribution', 0)/3:>12,.0f}")
    print()

    print("  BY CHANNEL:")
    print(f"  {'Channel':<18}", end="")
    for dim in dims:
        print(f"{dim[:16]:>16}", end="")
    print(f"{'TOTAL':>14}")
    print("  " + "-" * 80)
    channels = sorted({r["retailer"] for res in results.values() for r in res["by_retailer"]})
    for ch_name in channels:
        print(f"  {ch_name:<18}", end="")
        row_total = 0.0
        for dim in dims:
            val = sum(r["cost"] for r in results[dim]["by_retailer"] if r["retailer"] == ch_name)
            row_total += val
            print(f"${val:>14,.0f}", end="")
        print(f"  ${row_total:>11,.0f}")
    print()

    # Buffer scenarios
    print("  BUFFER SCENARIOS (what if fill were higher?):")
    print(f"  {'Target':>8}{'Total Cost':>16}{'Recovery $':>14}{'Recovery %':>12}")
    print("  " + "-" * 50)
    print(f"  {'Baseline':>8}  ${grand:>13,.0f}{'—':>14}{'—':>12}")
    for s in scenarios:
        print(f"  {s['target_fill_rate']*100:>7.0f}%  ${s['total_cost']:>13,.0f}"
              f"  ${s['total_recovery']:>11,.0f}  {s['recovery_pct']:>10.1f}%")
    print()
    print(f"  Wrote {COST_DB}")
    print()


# ---------------------------------------------------------------------------
# JSON export for React app
# ---------------------------------------------------------------------------

def _rd(v: float) -> float:
    return round(v, DOLLAR_PLACES)


def _rp(v: float) -> float:
    return round(v, PCT_PLACES)


def _write_json(path: Path, data) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(text, encoding="utf-8")
    return path.stat().st_size


def _build_meta(rev_info: dict, start_date: str, end_date: str, total_skus: int = 50) -> dict:
    params = {}
    for name, info in FINE_SCHEDULE.items():
        basis_kind, rate, threshold = info
        key = f"fine_{name.lower().replace(' ', '_')}"
        params[key] = {
            "value": rate,
            "unit": "USD" if basis_kind == "flat" else "fraction",
            "basis": basis_kind,
            "level": "PO" if basis_kind != "line_cogs" else "line",
            "description": f"{name} compliance fine schedule",
        }
    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "time_window": {"start": start_date, "end": end_date},
        "total_skus": total_skus,
        "shipped_revenue": _rd(rev_info["total_shipped"]),
        "total_demand": _rd(rev_info["total_demand"]),
        "total_orders": rev_info["total_orders"],
        "total_lines": rev_info["total_lines"],
        "overall_fill_rate": _rp(rev_info["overall_fill"]),
        "retailer_fill_rate": _rp(rev_info["retailer_fill"]),
        "distributor_fill_rate": _rp(rev_info["distributor_fill"]),
        "contribution_margin_pct": CONTRIBUTION_MARGIN_PCT,
        "cost_parameters": params,
    }


def _build_cost_summary(results: dict, shipped: float) -> list[dict]:
    rows = []
    for dim in ("forgone_revenue", "compliance_fines", "chargebacks", "deductions"):
        res = results[dim]
        pct = (res["total_cost"] / shipped) if shipped else 0
        rows.append({
            "dimension": dim,
            "total_cost": _rd(res["total_cost"]),
            "pct_of_shipped": _rp(pct),
            "description": res["description"],
        })
    return rows


def _build_cost_by_month(results: dict) -> list[dict]:
    rows = []
    for dim in ("forgone_revenue", "compliance_fines", "chargebacks", "deductions"):
        for r in results[dim]["by_month"]:
            rows.append({
                "month": r["month"],
                "dimension": dim,
                "cost": _rd(r["cost"]),
            })
    rows.sort(key=lambda x: (x["month"], x["dimension"]))
    return rows


def _build_cost_by_retailer(results: dict) -> list[dict]:
    rows = []
    for dim in ("forgone_revenue", "compliance_fines", "chargebacks", "deductions"):
        for r in results[dim].get("by_retailer_month", []):
            rows.append({
                "retailer": r["retailer"],
                "dimension": dim,
                "month": r["month"],
                "cost": _rd(r["cost"]),
            })
    rows.sort(key=lambda x: (x["retailer"], x["dimension"], x["month"]))
    return rows


def _build_cost_by_sku(results: dict, conn) -> list[dict]:
    sku_dim: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    sku_dim_month: dict[str, dict[str, dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(float))
    )
    sku_retailer: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for dim in ("forgone_revenue", "compliance_fines", "chargebacks", "deductions"):
        res = results[dim]
        for r in res.get("by_sku", []):
            sku_dim[r["sku"]][dim] += r["cost"]
        for r in res.get("by_sku_month", []):
            sku_dim_month[r["sku"]][r["month"]][dim] += r["cost"]
        for r in res.get("by_sku_retailer", []):
            sku_retailer[r["sku"]][r["retailer"]] += r["cost"]

    sku_totals = {sku: sum(d.values()) for sku, d in sku_dim.items()}

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT sku, product_name, product_line FROM raw.product_master")
        pm = {r["sku"]: (r["product_name"], r["product_line"]) for r in cur}

    sorted_skus = sorted(sku_totals.items(), key=lambda kv: -kv[1])
    top = sorted_skus[:TOP_N_SKUS]
    rest = sorted_skus[TOP_N_SKUS:]

    def by_month_rows(month_map):
        return [
            {"month": m, **{d: _rd(c) for d, c in sorted(dims.items())}}
            for m, dims in sorted(month_map.items())
        ]

    rows = []
    for sku, total in top:
        name, line = pm.get(sku, (sku, "Unknown"))
        rows.append({
            "sku": sku,
            "product_name": name,
            "product_line": line,
            "total_cost": _rd(total),
            "by_dimension": {d: _rd(c) for d, c in sorted(sku_dim[sku].items())},
            "by_retailer": {r: _rd(c) for r, c in sorted(sku_retailer[sku].items())},
            "by_month": by_month_rows(sku_dim_month[sku]),
        })

    if rest:
        other_total = sum(t for _, t in rest)
        other_by_dim: dict[str, float] = defaultdict(float)
        other_by_retailer: dict[str, float] = defaultdict(float)
        other_by_month: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for sku, _ in rest:
            for d, c in sku_dim[sku].items():
                other_by_dim[d] += c
            for r, c in sku_retailer[sku].items():
                other_by_retailer[r] += c
            for month, dim_costs in sku_dim_month[sku].items():
                for d, c in dim_costs.items():
                    other_by_month[month][d] += c
        rows.append({
            "sku": "Other",
            "product_name": f"Other ({len(rest)} SKUs)",
            "product_line": "Other",
            "total_cost": _rd(other_total),
            "by_dimension": {d: _rd(c) for d, c in sorted(other_by_dim.items())},
            "by_retailer": {r: _rd(c) for r, c in sorted(other_by_retailer.items())},
            "by_month": by_month_rows(other_by_month),
        })

    return rows


def _build_buffer_scenarios(scenarios: list[dict]) -> dict:
    out = []
    for s in scenarios:
        out.append({
            "target_fill_rate": _rp(s["target_fill_rate"]),
            "achieved_fill_rate": _rp(s["actual_fill_rate_achieved"]),
            "total_cost": _rd(s["total_cost"]),
            "total_recovery": _rd(s["total_recovery"]),
            "recovery_pct": _rp(s["recovery_pct"] / 100.0),
            "by_dimension": {
                dim: {
                    "original": _rd(detail["original"]),
                    "simulated": _rd(detail["simulated"]),
                    "recovery": _rd(detail["recovery"]),
                    "recovery_pct": _rp(detail["recovery_pct"] / 100.0),
                }
                for dim, detail in s["by_dimension"].items()
            },
        })
    return {"scenarios": out}


def _build_validation(results: dict, rev_info: dict) -> dict:
    totals = {}
    for dim in ("forgone_revenue", "compliance_fines", "chargebacks", "deductions"):
        totals[dim] = _rd(results[dim]["total_cost"])
    totals["total"] = _rd(sum(totals.values()))
    return {
        "baseline_totals": totals,
        "shipped_revenue": _rd(rev_info["total_shipped"]),
        "overall_fill_rate": _rp(rev_info["overall_fill"]),
    }


def export_json(conn, results: dict, rev_info: dict, scenarios: list[dict],
                orders_by_month: list[dict], start_date: str, end_date: str) -> None:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    for f in JSON_DIR.glob("*.json"):
        f.unlink()

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(DISTINCT sku) FROM raw.product_master")
        total_skus = cur.fetchone()[0]

    meta = _build_meta(rev_info, start_date, end_date, total_skus=total_skus)
    outputs = {
        "meta.json": meta,
        "cost_summary.json": _build_cost_summary(results, rev_info["total_shipped"]),
        "cost_by_month.json": _build_cost_by_month(results),
        "cost_by_retailer.json": _build_cost_by_retailer(results),
        "cost_by_sku.json": _build_cost_by_sku(results, conn),
        "orders_by_month.json": orders_by_month,
        "buffer_scenarios.json": _build_buffer_scenarios(scenarios),
        "validation.json": _build_validation(results, rev_info),
    }

    sizes = {name: _write_json(JSON_DIR / name, payload) for name, payload in outputs.items()}

    summary_total = sum(r["total_cost"] for r in outputs["cost_summary.json"])
    val_total = outputs["validation.json"]["baseline_totals"]["total"]
    matches = abs(summary_total - val_total) < 1.0

    total_size = sum(sizes.values())
    print()
    print(f"  Exported {len(outputs)} JSON files to {JSON_DIR.relative_to(REPO)}/")
    for name, size in sizes.items():
        print(f"    {name:<32} {size / 1024:>8.1f} KB")
    print(f"    {'TOTAL':<32} {total_size / 1024:>8.1f} KB")
    print(f"    sanity check (<$1 diff): {'PASS' if matches else 'FAIL'}")
    if not matches:
        print(f"    WARNING: cost_summary total ${summary_total:,.2f} != validation total ${val_total:,.2f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("Connecting to platform Postgres (local replica)...", flush=True)
    conn = pg_connect()

    print("Computing revenue and fill rates...", flush=True)
    rev_info = compute_revenue_and_fill(conn)
    start_date, end_date = compute_time_window(conn)

    print("Dimension 1: forgone_revenue...", flush=True)
    d1 = compute_forgone_revenue(conn)

    print("Dimension 2: compliance_fines...", flush=True)
    d2 = compute_compliance_fines(conn)

    print("Dimension 3: chargebacks...", flush=True)
    d3 = compute_chargebacks(conn)

    print("Dimension 4: deductions...", flush=True)
    d4 = compute_deductions(conn)

    results = {
        "forgone_revenue": d1,
        "compliance_fines": d2,
        "chargebacks": d3,
        "deductions": d4,
    }

    print("Running buffer simulations...", flush=True)
    scenarios = simulate_buffer(conn, results, rev_info)

    print("Computing orders by month...", flush=True)
    orders_by_month = compute_orders_by_month(conn)

    print("Writing cost database...", flush=True)
    write_cost_db(results, rev_info, scenarios)

    print("Exporting JSON for React app...", flush=True)
    export_json(conn, results, rev_info, scenarios, orders_by_month,
                start_date, end_date)

    conn.close()

    print_summary(results, rev_info, scenarios)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
