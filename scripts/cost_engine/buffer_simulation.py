"""Buffer simulation: re-run the cost engine at a higher target fill
rate and compare against the as-is baseline.

The simulation does NOT regenerate orders or write back to
short_ship_orders.db. It copies the orders DB to a temp file,
modifies quantity_shipped on retail/distributor lines and recalibrates
DTC outcomes in the temp file, then runs every existing cost-engine
module against the temp file by monkey-patching common.ORDERS_DB.
After the scenarios run, the buffer_scenarios, buffer_scenario_details,
and buffer_deauth_recovery tables in short_ship_cost.db record the
deltas vs. baseline.

Recovery rule per line:
    new_shipped = max(current_shipped, round(qty_ordered * target_fill))
    capped at qty_ordered.

Lines already above target keep their value; lines below get lifted
to the target rate. Channel averages land slightly above the target
because the clamp is asymmetric (you can lift, never lower).

DTC: cancelled orders are randomly sampled and flipped to
shipped_complete in proportion to (1 - target) / (1 - current_fill),
modeling that better overall production reduces hold time and
therefore cancellations.

Triage labor stays flat by design — the orders count doesn't change,
and the spec says triage process doesn't go away just because outcomes
improve.
"""
from __future__ import annotations

import gc
import random
import shutil
import sqlite3
from pathlib import Path

from . import (
    chargebacks,
    common,
    deauthorization,
    distributor_returns,
    dtc_cancellations,
    dtc_margin_leakage,
    lost_revenue,
    otif_fines,
    triage_labor,
)
from .common import COST_DB, EXTRACT_DB, ORDERS_DB

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

SCENARIO_FILL_RATES = (0.80, 0.85, 0.90, 0.95)
SEED = 20260512

REPO = Path(__file__).resolve().parent.parent.parent
TEMP_DIR = REPO / "data" / "_buffer_temp"


def measure_overall_fill_rate() -> float:
    """Dollar-weighted overall fill rate across the whole order book."""
    db = sqlite3.connect(ORDERS_DB)
    db.execute(f"ATTACH DATABASE '{EXTRACT_DB}' AS ext")
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute(
        """
        SELECT
          SUM(CASE WHEN lo.unit_of_measure = 'case'
                   THEN lo.quantity_ordered * pm.case_pack_qty * lo.unit_price
                   ELSE lo.quantity_ordered * lo.unit_price END) AS demand,
          SUM(CASE WHEN ls.unit_of_measure = 'case'
                   THEN ls.quantity_shipped * pm.case_pack_qty * ls.unit_price
                   ELSE ls.quantity_shipped * ls.unit_price END) AS shipped
        FROM order_lines_original lo
        JOIN order_lines_shipped ls ON ls.original_line_id = lo.order_line_id
        JOIN ext.product_master pm  ON pm.sku = lo.sku
        """
    )
    r = cur.fetchone()
    db.close()
    return (r["shipped"] or 0) / (r["demand"] or 1)


def recover_retail_shorts(db: sqlite3.Connection, target_fill: float) -> int:
    """Lift quantity_shipped on each retail/distributor line to at least
    target_fill * quantity_ordered. Update order_shorts to match.
    Returns the number of lines actually modified.

    Uses temp tables for bulk update — much faster than per-row UPDATEs
    or UPDATE...FROM on 194K rows."""
    cur = db.cursor()
    cur.execute(
        """
        SELECT ls.order_line_id, ls.order_id, ls.sku,
               ls.quantity_shipped, lo.quantity_ordered
        FROM order_lines_shipped ls
        JOIN order_lines_original lo ON lo.order_line_id = ls.original_line_id
        JOIN orders o                ON o.order_id = ls.order_id
        WHERE o.channel_type IN ('retail', 'distributor')
          AND ls.quantity_shipped < lo.quantity_ordered
        """
    )
    rows = cur.fetchall()

    # Compute new values in Python
    shipped_updates = []   # (order_line_id, new_shipped)
    shorts_updates = []    # (order_id, sku, new_short)
    shorts_deletes = []    # (order_id, sku)

    for r in rows:
        target_qty = round(r["quantity_ordered"] * target_fill)
        new_shipped = max(r["quantity_shipped"], target_qty)
        new_shipped = min(r["quantity_ordered"], new_shipped)
        if new_shipped <= r["quantity_shipped"]:
            continue
        shipped_updates.append((r["order_line_id"], new_shipped))
        new_short = r["quantity_ordered"] - new_shipped
        if new_short == 0:
            shorts_deletes.append((r["order_id"], r["sku"]))
        else:
            shorts_updates.append((r["order_id"], r["sku"], new_short))

    if not shipped_updates:
        return 0

    # Bulk update via temp table — avoids 190K individual UPDATEs
    cur.execute("""
        CREATE TEMP TABLE _buf_shipped (
            order_line_id TEXT PRIMARY KEY,
            new_shipped INTEGER
        )
    """)
    cur.executemany(
        "INSERT INTO _buf_shipped VALUES (?, ?)", shipped_updates
    )
    cur.execute("""
        UPDATE order_lines_shipped
        SET quantity_shipped = b.new_shipped
        FROM _buf_shipped b
        WHERE order_lines_shipped.order_line_id = b.order_line_id
    """)
    cur.execute("DROP TABLE _buf_shipped")

    # Bulk delete fully-shipped shorts via temp table
    if shorts_deletes:
        cur.execute("""
            CREATE TEMP TABLE _buf_del (
                order_id TEXT, sku TEXT,
                PRIMARY KEY (order_id, sku)
            )
        """)
        cur.executemany("INSERT INTO _buf_del VALUES (?, ?)", shorts_deletes)
        cur.execute("""
            DELETE FROM order_shorts
            WHERE EXISTS (
                SELECT 1 FROM _buf_del d
                WHERE d.order_id = order_shorts.order_id
                  AND d.sku = order_shorts.sku
            )
        """)
        cur.execute("DROP TABLE _buf_del")

    # Bulk update remaining shorts via temp table
    if shorts_updates:
        cur.execute("""
            CREATE TEMP TABLE _buf_upd (
                order_id TEXT, sku TEXT, new_short INTEGER,
                PRIMARY KEY (order_id, sku)
            )
        """)
        cur.executemany(
            "INSERT INTO _buf_upd VALUES (?, ?, ?)", shorts_updates
        )
        cur.execute("""
            UPDATE order_shorts
            SET quantity_shorted = u.new_short
            FROM _buf_upd u
            WHERE order_shorts.order_id = u.order_id
              AND order_shorts.sku = u.sku
        """)
        cur.execute("DROP TABLE _buf_upd")

    return len(shipped_updates)


def recover_dtc_outcomes(
    db: sqlite3.Connection, target_fill: float, current_fill: float, rng: random.Random,
) -> int:
    """Flip a fraction of cancelled DTC orders back to shipped_complete.
    Fraction recovered = 1 - (1 - target) / (1 - current_fill), bounded
    [0, 1]. Lines on recovered orders get full quantity_shipped, ship_date
    is set, and dtc_outcomes resolution becomes shipped_complete with
    days_held=0."""
    if target_fill <= current_fill:
        return 0
    keep_factor = (1 - target_fill) / (1 - current_fill)
    keep_factor = max(0.0, min(1.0, keep_factor))

    cur = db.cursor()
    cur.execute(
        "SELECT order_id FROM dtc_outcomes "
        "WHERE resolution IN ('cancelled_by_customer', 'purchased_in_store')"
    )
    cancelled = [r[0] for r in cur.fetchall()]
    n_keep = int(round(len(cancelled) * keep_factor))
    rng.shuffle(cancelled)
    to_recover = cancelled[n_keep:]
    if not to_recover:
        return 0

    placeholders = ",".join("?" * len(to_recover))
    cur.execute(
        f"UPDATE dtc_outcomes "
        f"SET resolution = 'shipped_complete', days_held = 0, "
        f"    resolution_date = hold_start_date "
        f"WHERE order_id IN ({placeholders})",
        to_recover,
    )
    cur.execute(
        f"UPDATE order_lines_shipped SET quantity_shipped = ("
        f"  SELECT quantity_ordered FROM order_lines_original "
        f"  WHERE order_line_id = order_lines_shipped.original_line_id) "
        f"WHERE order_id IN ({placeholders})",
        to_recover,
    )
    cur.execute(
        f"UPDATE orders SET ship_date = ("
        f"  SELECT hold_start_date FROM dtc_outcomes "
        f"  WHERE dtc_outcomes.order_id = orders.order_id) "
        f"WHERE order_id IN ({placeholders})",
        to_recover,
    )
    return len(to_recover)


def shipped_revenue_in(db_path: Path) -> float:
    db = sqlite3.connect(db_path)
    db.execute(f"ATTACH DATABASE '{EXTRACT_DB}' AS ext")
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


def fill_rate_in(db_path: Path) -> float:
    db = sqlite3.connect(db_path)
    db.execute(f"ATTACH DATABASE '{EXTRACT_DB}' AS ext")
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute(
        """
        SELECT
          SUM(CASE WHEN lo.unit_of_measure = 'case'
                   THEN lo.quantity_ordered * pm.case_pack_qty * lo.unit_price
                   ELSE lo.quantity_ordered * lo.unit_price END) AS demand,
          SUM(CASE WHEN ls.unit_of_measure = 'case'
                   THEN ls.quantity_shipped * pm.case_pack_qty * ls.unit_price
                   ELSE ls.quantity_shipped * ls.unit_price END) AS shipped
        FROM order_lines_original lo
        JOIN order_lines_shipped ls ON ls.original_line_id = lo.order_line_id
        JOIN ext.product_master pm  ON pm.sku = lo.sku
        """
    )
    r = cur.fetchone()
    db.close()
    return (r["shipped"] or 0) / (r["demand"] or 1)


def simulate_at(target_fill: float, current_fill: float, rng: random.Random) -> dict:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_orders = TEMP_DIR / f"orders_{int(target_fill * 100):02d}.db"
    if temp_orders.exists():
        try:
            temp_orders.unlink()
        except PermissionError:
            # Leftover from a crashed run — overwrite it
            pass
    shutil.copy(ORDERS_DB, temp_orders)

    db = sqlite3.connect(temp_orders)
    db.row_factory = sqlite3.Row
    # Short-circuit when no improvement is asked for. At target <=
    # current_fill, "what if we did nothing" must reproduce baseline
    # exactly — the per-line lift would otherwise distort it because
    # individual lines below their channel target would still get
    # raised toward the global target.
    if target_fill > current_fill:
        n_retail_modified = recover_retail_shorts(db, target_fill)
        n_dtc_recovered = recover_dtc_outcomes(db, target_fill, current_fill, rng)
    else:
        n_retail_modified = 0
        n_dtc_recovered = 0
    db.commit()
    db.close()

    achieved_fill = fill_rate_in(temp_orders)
    shipped_rev = shipped_revenue_in(temp_orders)

    original_path = common.ORDERS_DB
    common.ORDERS_DB = temp_orders
    try:
        results: dict[str, dict] = {}
        for name, mod in MODULES:
            results[name] = mod.calculate()
    finally:
        common.ORDERS_DB = original_path

    # On Windows, SQLite file handles may linger after close().
    # Force GC to release them, then try to clean up. If it still
    # fails, main() will clean up the temp directory at the end.
    gc.collect()
    try:
        temp_orders.unlink()
    except PermissionError:
        pass  # cleaned up in main()

    return {
        "target_fill_rate": target_fill,
        "actual_fill_rate_achieved": achieved_fill,
        "shipped_revenue": shipped_rev,
        "results": results,
        "n_retail_modified": n_retail_modified,
        "n_dtc_recovered": n_dtc_recovered,
    }


def write_to_cost_db(scenarios: list[dict], baseline: dict[str, dict]) -> None:
    db = sqlite3.connect(COST_DB)
    cur = db.cursor()
    cur.executescript("""
        DROP TABLE IF EXISTS buffer_scenarios;
        DROP TABLE IF EXISTS buffer_scenario_details;
        DROP TABLE IF EXISTS buffer_deauth_recovery;

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
        CREATE TABLE buffer_deauth_recovery (
            target_fill_rate REAL NOT NULL,
            sku              TEXT NOT NULL,
            retailer         TEXT NOT NULL,
            trigger_type     TEXT NOT NULL,
            original_status  TEXT NOT NULL,
            simulated_status TEXT NOT NULL,
            PRIMARY KEY (target_fill_rate, sku, retailer, trigger_type)
        );
    """)

    baseline_total = sum(r["total_cost"] for r in baseline.values())

    for scen in scenarios:
        target = scen["target_fill_rate"]
        sim_total = sum(r["total_cost"] for r in scen["results"].values())
        recovery = baseline_total - sim_total
        recovery_pct = (recovery / baseline_total * 100) if baseline_total else 0
        cur.execute(
            "INSERT INTO buffer_scenarios VALUES (?, ?, ?, ?, ?)",
            (target, scen["actual_fill_rate_achieved"], sim_total, recovery, recovery_pct),
        )

        for dim, base_res in baseline.items():
            orig = base_res["total_cost"]
            sim = scen["results"][dim]["total_cost"]
            d_rec = orig - sim
            d_pct = (d_rec / orig * 100) if orig else 0
            cur.execute(
                "INSERT INTO buffer_scenario_details VALUES (?, ?, ?, ?, ?, ?)",
                (target, dim, orig, sim, d_rec, d_pct),
            )

        # Deauth events that disappeared at this fill rate
        baseline_events = {(e["sku"], e["retailer"], e["trigger_type"])
                           for e in baseline["deauthorization"]["detail_events"]}
        sim_events = {(e["sku"], e["retailer"], e["trigger_type"])
                      for e in scen["results"]["deauthorization"]["detail_events"]}
        avoided = baseline_events - sim_events
        for sku, retailer, trigger in avoided:
            cur.execute(
                "INSERT INTO buffer_deauth_recovery VALUES (?, ?, ?, ?, ?, ?)",
                (target, sku, retailer, trigger, "deauthorized", "avoided"),
            )

    db.commit()
    db.close()


def print_comparison(scenarios: list[dict], baseline: dict[str, dict]) -> None:
    dims = [name for name, _ in MODULES]
    print()
    header = f"{'Dimension':<22} {'Baseline':>14}"
    for s in scenarios:
        header += f" {int(s['target_fill_rate']*100)}%".rjust(14)
    print(header)
    print("-" * len(header))
    baseline_total = sum(r["total_cost"] for r in baseline.values())
    for d in dims:
        line = f"{d:<22} {baseline[d]['total_cost']:>14,.0f}"
        for s in scenarios:
            line += f" {s['results'][d]['total_cost']:>13,.0f}"
        print(line)
    print("-" * len(header))
    line = f"{'TOTAL':<22} {baseline_total:>14,.0f}"
    for s in scenarios:
        sim_total = sum(r["total_cost"] for r in s["results"].values())
        line += f" {sim_total:>13,.0f}"
    print(line)
    line = f"{'Recovery $':<22} {'-':>14}"
    for s in scenarios:
        sim_total = sum(r["total_cost"] for r in s["results"].values())
        line += f" {baseline_total - sim_total:>13,.0f}"
    print(line)
    line = f"{'Recovery %':<22} {'-':>14}"
    for s in scenarios:
        sim_total = sum(r["total_cost"] for r in s["results"].values())
        rec_pct = (baseline_total - sim_total) / baseline_total * 100
        line += f" {rec_pct:>12.1f}%"
    print(line)
    line = f"{'Achieved fill':<22} {'-':>14}"
    for s in scenarios:
        line += f" {s['actual_fill_rate_achieved']*100:>12.1f}%"
    print(line)
    print()


def main() -> int:
    import time as _time
    rng = random.Random(SEED)
    print("Computing baseline (current state)...", flush=True)
    current_fill = measure_overall_fill_rate()
    print(f"  Current overall fill rate: {current_fill*100:.1f}%", flush=True)

    t0 = _time.time()
    baseline: dict[str, dict] = {}
    for name, mod in MODULES:
        baseline[name] = mod.calculate()
    print(f"  Baseline computed in {_time.time()-t0:.1f}s", flush=True)

    scenarios: list[dict] = []
    for target in SCENARIO_FILL_RATES:
        print(f"\nSimulating target fill {int(target*100)}%...", flush=True)
        t0 = _time.time()
        scen = simulate_at(target, current_fill, rng)
        scenarios.append(scen)
        print(f"  achieved fill: {scen['actual_fill_rate_achieved']*100:.1f}%, "
              f"retail/distributor lines lifted: {scen['n_retail_modified']:,}, "
              f"DTC orders flipped: {scen['n_dtc_recovered']:,}")

    write_to_cost_db(scenarios, baseline)
    print(f"\nWrote buffer_scenarios, buffer_scenario_details, "
          f"buffer_deauth_recovery to {COST_DB}")
    print_comparison(scenarios, baseline)

    # Clean up temp directory (may contain leftover .db files on Windows)
    if TEMP_DIR.exists():
        for f in TEMP_DIR.glob("*.db"):
            try:
                f.unlink()
            except OSError:
                pass
        try:
            TEMP_DIR.rmdir()
        except OSError:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
