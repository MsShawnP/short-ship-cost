"""
Generate synthetic original orders (orders + order_lines_original) for
the 3-year (157-week) Cinderhaven window. Output goes into a new SQLite file
at data/short_ship_orders.db, separate from the Cinderhaven extract.

Per docs/order-data-schema.md:
- Retail and distributor orders are in cases.
- DTC orders are in units.
- All sku_costs prices are per unit. Revenue = qty * pack_qty * unit_price
  for retail/distributor; qty * unit_price for DTC.
- Every (sku, retailer) on an order must have an active authorization
  in distribution_log at order_date.

Volume targets calibrated to Postgres revenue (~$3.9M over 2yr,
scaled to 3yr window). Channel mix from fct tables:
    UNFI         $845K/3yr   (distributor, largest channel)
    DPI Northwest $830K/3yr  (regional distributor)
    KeHE         $726K/3yr   (distributor)
    DTC          $550K/3yr   (DTC/Shopify)
    Sprouts      $524K/3yr   (retailer, 90 stores)
    Whole Foods  $509K/3yr   (retailer, 120 stores)
    Regional Grp $493K/3yr   (retailer, 40 stores)
    Kroger       $491K/3yr   (retailer, 150 stores)
    Walmart      $482K/3yr   (retailer, 180 stores)
    Costco       $466K/3yr   (retailer, 60 stores)
    TOTAL       ~$5.9M/3yr   (~$2.0M/yr)
"""
from __future__ import annotations

import json
import math
import random
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXTRACT_DB = REPO / "data" / "cinderhaven_extract.db"
CALIBRATION_FILE = REPO / "data" / "calibration.json"
ORDERS_DB = REPO / "data" / "short_ship_orders.db"

# 157-week Cinderhaven window aligned with scan_data
WINDOW_START = date(2023, 1, 6)
WINDOW_END = date(2026, 1, 2)

REGIONAL_CHAINS = {
    "Kroger",
    "Sprouts",
    "Regional Group",
}

WHOLESALE_COL = {
    "Walmart": "wholesale_walmart",
    "Costco": "wholesale_costco",
    "Whole Foods": "wholesale_whole_foods",
    "Sprouts": "wholesale_sprouts",
    "Kroger": "wholesale_regional",
    "Regional Group": "wholesale_regional",
    "DPI Northwest": "wholesale_regional",
    "UNFI": "wholesale_unfi",
    "KeHE": "wholesale_kehe",
    "DTC": "wholesale_dtc",
}

SEED = 20260507  # reproducibility


@dataclass(frozen=True)
class AuthWindow:
    auth_start: date
    deauth_end: date | None  # None = still active

    def contains(self, d: date) -> bool:
        if d < self.auth_start:
            return False
        if self.deauth_end is not None and d >= self.deauth_end:
            return False
        return True


def parse_date(s: str) -> date:
    return date.fromisoformat(s)


def load_reference_data() -> dict:
    db = sqlite3.connect(EXTRACT_DB)
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    cur.execute("SELECT sku, case_pack_qty, msrp FROM product_master")
    case_pack = {r["sku"]: (r["case_pack_qty"], r["msrp"]) for r in cur.fetchall()}

    cur.execute("SELECT * FROM sku_costs")
    sku_costs = {r["sku"]: dict(r) for r in cur.fetchall()}

    cur.execute("SELECT sku, avg_weekly_units, velocity_rank FROM sku_velocity")
    velocity = {r["sku"]: (r["avg_weekly_units"], r["velocity_rank"]) for r in cur.fetchall()}

    cur.execute("SELECT store_id, retailer, region, state FROM stores")
    stores = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT sku, store_id, authorized_date, deauthorized_date FROM distribution_log")
    auth_rows = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT * FROM promotions")
    promos = [dict(r) for r in cur.fetchall()]

    db.close()

    return {
        "case_pack": case_pack,
        "sku_costs": sku_costs,
        "velocity": velocity,
        "stores": stores,
        "auth_rows": auth_rows,
        "promos": promos,
    }


def build_auth_index(refs: dict) -> dict[tuple[str, str], list[AuthWindow]]:
    """Map (retailer, sku) -> list of AuthWindows by collapsing per-store
    authorizations to the retailer level. A SKU is considered authorized
    at the retailer level if any store of that retailer has an active
    authorization at the date in question."""
    store_to_retailer = {s["store_id"]: s["retailer"] for s in refs["stores"]}
    by_pair: dict[tuple[str, str], list[AuthWindow]] = defaultdict(list)
    for row in refs["auth_rows"]:
        retailer = store_to_retailer.get(row["store_id"])
        if retailer is None:
            continue
        win = AuthWindow(
            auth_start=parse_date(row["authorized_date"]),
            deauth_end=parse_date(row["deauthorized_date"]) if row["deauthorized_date"] else None,
        )
        by_pair[(retailer, row["sku"])].append(win)
    return by_pair


def is_authorized(auth_idx: dict, retailer: str, sku: str, d: date) -> bool:
    for w in auth_idx.get((retailer, sku), ()):
        if w.contains(d):
            return True
    return False


def authorized_skus_for(auth_idx: dict, retailer: str, d: date) -> list[str]:
    out = []
    for (r, sku), wins in auth_idx.items():
        if r != retailer:
            continue
        if any(w.contains(d) for w in wins):
            out.append(sku)
    return out


def build_promo_index(refs: dict) -> dict:
    """Map (retailer, sku) -> list of (start_week, end_week) date ranges."""
    out: dict[tuple[str, str], list[tuple[date, date]]] = defaultdict(list)
    for p in refs["promos"]:
        out[(p["retailer"], p["sku"])].append(
            (parse_date(p["start_week"]), parse_date(p["end_week"]))
        )
    return out


def is_on_promo(promo_idx: dict, retailer: str, sku: str, d: date) -> bool:
    for start, end in promo_idx.get((retailer, sku), ()):
        if start <= d <= end:
            return True
    return False


def velocity_weights(skus: list[str], velocity: dict) -> list[float]:
    """Weight each SKU by its avg_weekly_units, with a small floor so
    long-tail SKUs still get occasional orders."""
    return [max(velocity[s][0], 0.5) for s in skus]


def weighted_sample_no_replace(skus: list[str], weights: list[float], k: int, rng: random.Random) -> list[str]:
    if k >= len(skus):
        return list(skus)
    pool = list(skus)
    w = list(weights)
    out = []
    for _ in range(k):
        total = sum(w)
        if total <= 0:
            break
        r = rng.uniform(0, total)
        acc = 0.0
        for i, wi in enumerate(w):
            acc += wi
            if acc >= r:
                out.append(pool[i])
                pool.pop(i)
                w.pop(i)
                break
    return out


def lognormal_qty(lo: int, hi: int, rng: random.Random) -> int:
    """Sample from log-uniform between lo and hi, biasing toward small."""
    if lo < 1:
        lo = 1
    log_lo, log_hi = math.log(lo), math.log(hi)
    return max(1, round(math.exp(rng.uniform(log_lo, log_hi))))


def all_weeks() -> list[date]:
    """All Mondays within the window."""
    out = []
    d = WINDOW_START
    while d.weekday() != 0:
        d += timedelta(days=1)
    while d <= WINDOW_END:
        out.append(d)
        d += timedelta(days=7)
    return out


def all_months() -> list[date]:
    """First-of-month dates within the window."""
    out = []
    y, m = WINDOW_START.year, WINDOW_START.month
    while True:
        d = date(y, m, 1)
        if d > WINDOW_END:
            break
        if d >= WINDOW_START:
            out.append(d)
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def generate_walmart(refs: dict, auth: dict, promo: dict, rng: random.Random) -> tuple[list[dict], list[dict]]:
    """Walmart: one DC = (region, state). Weekly orders per DC with skip
    probability. 3-6 lines, log-quantities 1-5 cases, velocity-weighted.
    """
    dcs = sorted({(s["region"], s["state"]) for s in refs["stores"] if s["retailer"] == "Walmart"})
    velocity = refs["velocity"]
    orders, lines = [], []
    seq = 0
    line_seq = 0
    for week in all_weeks():
        for region, state in dcs:
            if rng.random() > 0.06:
                continue
            order_date = week + timedelta(days=rng.randint(0, 4))
            available = [s for s in authorized_skus_for(auth, "Walmart", order_date)]
            if not available:
                continue
            lo, hi = min(3, len(available)), min(6, len(available))
            n_lines = rng.randint(lo, hi) if hi >= lo else hi
            if n_lines == 0:
                continue
            picked = weighted_sample_no_replace(
                available, velocity_weights(available, velocity), n_lines, rng
            )
            seq += 1
            order_id = f"WMT-{seq:06d}"
            order_type = "replenishment"
            if any(is_on_promo(promo, "Walmart", s, order_date) for s in picked):
                order_type = "promo"
            due = order_date + timedelta(days=rng.randint(7, 10))
            orders.append({
                "order_id": order_id,
                "retailer": "Walmart",
                "channel_type": "retail",
                "order_date": order_date.isoformat(),
                "due_date": due.isoformat(),
                "ship_date": None,
                "delivery_location": f"WMT-DC-{region}-{state}",
                "order_type": order_type,
            })
            for sku in picked:
                on_promo = is_on_promo(promo, "Walmart", sku, order_date)
                qty = lognormal_qty(2, 16 if on_promo else 12, rng)
                line_seq += 1
                lines.append({
                    "order_line_id": f"WMT-L-{line_seq:07d}",
                    "order_id": order_id,
                    "sku": sku,
                    "quantity_ordered": qty,
                    "unit_of_measure": "case",
                    "unit_price": refs["sku_costs"][sku]["wholesale_walmart"],
                })
    return orders, lines


def generate_costco(refs: dict, auth: dict, promo: dict, rng: random.Random) -> tuple[list[dict], list[dict]]:
    """Costco: monthly orders per region. Larger orders against
    contracted volume. 4-8 lines, 2-15 cases each."""
    regions = sorted({s["region"] for s in refs["stores"] if s["retailer"] == "Costco"})
    velocity = refs["velocity"]
    orders, lines = [], []
    seq = 0
    line_seq = 0
    for month_start in all_months():
        for region in regions:
            if rng.random() > 0.85:
                continue
            order_date = month_start + timedelta(days=rng.randint(0, 14))
            if order_date > WINDOW_END:
                continue
            available = authorized_skus_for(auth, "Costco", order_date)
            if not available:
                continue
            lo, hi = min(4, len(available)), min(8, len(available))
            n_lines = rng.randint(lo, hi) if hi >= lo else hi
            if n_lines == 0:
                continue
            picked = weighted_sample_no_replace(
                available, velocity_weights(available, velocity), n_lines, rng
            )
            seq += 1
            order_id = f"CST-{seq:05d}"
            order_type = "contract"
            if any(is_on_promo(promo, "Costco", s, order_date) for s in picked):
                order_type = "promo"
            due = order_date + timedelta(days=rng.randint(14, 21))
            orders.append({
                "order_id": order_id,
                "retailer": "Costco",
                "channel_type": "retail",
                "order_date": order_date.isoformat(),
                "due_date": due.isoformat(),
                "ship_date": None,
                "delivery_location": f"CST-{region}",
                "order_type": order_type,
            })
            for sku in picked:
                on_promo = is_on_promo(promo, "Costco", sku, order_date)
                qty = lognormal_qty(4, 35 if on_promo else 25, rng)
                line_seq += 1
                lines.append({
                    "order_line_id": f"CST-L-{line_seq:06d}",
                    "order_id": order_id,
                    "sku": sku,
                    "quantity_ordered": qty,
                    "unit_of_measure": "case",
                    "unit_price": refs["sku_costs"][sku]["wholesale_costco"],
                })
    return orders, lines


def generate_whole_foods(refs: dict, auth: dict, promo: dict, rng: random.Random) -> tuple[list[dict], list[dict]]:
    """Whole Foods: weekly stock-to-level per region. 3-6 lines, 1-5 cases."""
    regions = sorted({s["region"] for s in refs["stores"] if s["retailer"] == "Whole Foods"})
    velocity = refs["velocity"]
    orders, lines = [], []
    seq = 0
    line_seq = 0
    for week in all_weeks():
        for region in regions:
            if rng.random() > 0.50:
                continue
            order_date = week + timedelta(days=rng.randint(0, 4))
            available = authorized_skus_for(auth, "Whole Foods", order_date)
            if not available:
                continue
            lo, hi = min(3, len(available)), min(6, len(available))
            n_lines = rng.randint(lo, hi) if hi >= lo else hi
            if n_lines == 0:
                continue
            picked = weighted_sample_no_replace(
                available, velocity_weights(available, velocity), n_lines, rng
            )
            seq += 1
            order_id = f"WFM-{seq:06d}"
            order_type = "replenishment"
            if any(is_on_promo(promo, "Whole Foods", s, order_date) for s in picked):
                order_type = "promo"
            due = order_date + timedelta(days=rng.randint(5, 8))
            orders.append({
                "order_id": order_id,
                "retailer": "Whole Foods",
                "channel_type": "retail",
                "order_date": order_date.isoformat(),
                "due_date": due.isoformat(),
                "ship_date": None,
                "delivery_location": f"WFM-{region}",
                "order_type": order_type,
            })
            for sku in picked:
                on_promo = is_on_promo(promo, "Whole Foods", sku, order_date)
                qty = lognormal_qty(2, 16 if on_promo else 10, rng)
                line_seq += 1
                lines.append({
                    "order_line_id": f"WFM-L-{line_seq:07d}",
                    "order_id": order_id,
                    "sku": sku,
                    "quantity_ordered": qty,
                    "unit_of_measure": "case",
                    "unit_price": refs["sku_costs"][sku]["wholesale_whole_foods"],
                })
    return orders, lines


def _generate_distributor(
    refs: dict,
    auth: dict,
    rng: random.Random,
    *,
    retailer: str,
    delivery_location: str,
    id_prefix: str,
    line_prefix: str,
    line_lo: int,
    line_hi: int,
    qty_lo: int,
    qty_hi: int,
    promo_qty_lo: int,
    promo_qty_hi: int,
) -> tuple[list[dict], list[dict]]:
    """Twice-weekly replenishment + promo over-orders. Used by both UNFI
    and KeHE; KeHE shares the UNFI promo schedule because the upstream
    promotions table has no KeHE-specific entries — distributor promo
    deals from CPG brands typically run through both distributors at the
    same time."""
    velocity = refs["velocity"]
    orders, lines = [], []
    seq = 0
    line_seq = 0
    price_col = WHOLESALE_COL[retailer]

    # Replenishment: Mon + Thu per week
    for week in all_weeks():
        for offset in (0, 3):
            order_date = week + timedelta(days=offset)
            if order_date > WINDOW_END:
                continue
            available = authorized_skus_for(auth, retailer, order_date)
            if not available:
                continue
            lo, hi = min(line_lo, len(available)), min(line_hi, len(available))
            n_lines = rng.randint(lo, hi) if hi >= lo else hi
            if n_lines == 0:
                continue
            picked = weighted_sample_no_replace(
                available, velocity_weights(available, velocity), n_lines, rng
            )
            seq += 1
            order_id = f"{id_prefix}-R-{seq:05d}"
            due = order_date + timedelta(days=rng.randint(5, 8))
            orders.append({
                "order_id": order_id,
                "retailer": retailer,
                "channel_type": "distributor",
                "order_date": order_date.isoformat(),
                "due_date": due.isoformat(),
                "ship_date": None,
                "delivery_location": delivery_location,
                "order_type": "replenishment",
            })
            for sku in picked:
                qty = lognormal_qty(qty_lo, qty_hi, rng)
                line_seq += 1
                lines.append({
                    "order_line_id": f"{line_prefix}-L-{line_seq:07d}",
                    "order_id": order_id,
                    "sku": sku,
                    "quantity_ordered": qty,
                    "unit_of_measure": "case",
                    "unit_price": refs["sku_costs"][sku][price_col],
                })

    # Promo over-orders: one per UNFI promo, applied to both distributors
    for p in refs["promos"]:
        if p["retailer"] != "UNFI":
            continue
        order_date = parse_date(p["start_week"]) - timedelta(days=rng.randint(7, 14))
        if order_date < WINDOW_START or order_date > WINDOW_END:
            continue
        if not is_authorized(auth, retailer, p["sku"], order_date):
            continue
        seq += 1
        order_id = f"{id_prefix}-P-{seq:05d}"
        due = order_date + timedelta(days=rng.randint(5, 8))
        orders.append({
            "order_id": order_id,
            "retailer": retailer,
            "channel_type": "distributor",
            "order_date": order_date.isoformat(),
            "due_date": due.isoformat(),
            "ship_date": None,
            "delivery_location": delivery_location,
            "order_type": "promo",
        })
        qty = lognormal_qty(promo_qty_lo, promo_qty_hi, rng)
        line_seq += 1
        lines.append({
            "order_line_id": f"{line_prefix}-L-{line_seq:07d}",
            "order_id": order_id,
            "sku": p["sku"],
            "quantity_ordered": qty,
            "unit_of_measure": "case",
            "unit_price": refs["sku_costs"][p["sku"]][price_col],
        })
    return orders, lines


def generate_unfi(refs: dict, auth: dict, promo: dict, rng: random.Random) -> tuple[list[dict], list[dict]]:
    """UNFI: twice-weekly replenishment + promo over-orders. Target ~$845K/3yr."""
    return _generate_distributor(
        refs, auth, rng,
        retailer="UNFI", delivery_location="UNFI-AGG",
        id_prefix="UNFI", line_prefix="UNFI",
        line_lo=4, line_hi=8,
        qty_lo=3, qty_hi=22,
        promo_qty_lo=25, promo_qty_hi=78,
    )


def generate_kehe(refs: dict, auth: dict, promo: dict, rng: random.Random) -> tuple[list[dict], list[dict]]:
    """KeHE: twice-weekly replenishment + promo over-orders. Target ~$726K/3yr."""
    return _generate_distributor(
        refs, auth, rng,
        retailer="KeHE", delivery_location="KEHE-AGG",
        id_prefix="KEHE", line_prefix="KEHE",
        line_lo=3, line_hi=6,
        qty_lo=4, qty_hi=28,
        promo_qty_lo=25, promo_qty_hi=84,
    )


def generate_dpi_northwest(refs: dict, auth: dict, promo: dict, rng: random.Random) -> tuple[list[dict], list[dict]]:
    """DPI Northwest: regional distributor. Target ~$830K/3yr."""
    return _generate_distributor(
        refs, auth, rng,
        retailer="DPI Northwest", delivery_location="DPI-AGG",
        id_prefix="DPI", line_prefix="DPI",
        line_lo=4, line_hi=7,
        qty_lo=3, qty_hi=20,
        promo_qty_lo=20, promo_qty_hi=65,
    )


def generate_regionals(refs: dict, auth: dict, promo: dict, rng: random.Random) -> tuple[list[dict], list[dict]]:
    """Three regional retailers (Kroger, Sprouts, Regional Group),
    weekly orders per chain. 3-6 lines, 1-7 cases."""
    velocity = refs["velocity"]
    orders, lines = [], []
    seq = 0
    line_seq = 0
    for week in all_weeks():
        for chain in sorted(REGIONAL_CHAINS):
            if rng.random() > 0.95:
                continue
            order_date = week + timedelta(days=rng.randint(0, 4))
            available = authorized_skus_for(auth, chain, order_date)
            if not available:
                continue
            lo, hi = min(3, len(available)), min(6, len(available))
            n_lines = rng.randint(lo, hi) if hi >= lo else hi
            if n_lines == 0:
                continue
            picked = weighted_sample_no_replace(
                available, velocity_weights(available, velocity), n_lines, rng
            )
            seq += 1
            order_id = f"RGN-{seq:06d}"
            order_type = "replenishment"
            if any(is_on_promo(promo, chain, s, order_date) for s in picked):
                order_type = "promo"
            due = order_date + timedelta(days=rng.randint(5, 9))
            orders.append({
                "order_id": order_id,
                "retailer": chain,
                "channel_type": "retail",
                "order_date": order_date.isoformat(),
                "due_date": due.isoformat(),
                "ship_date": None,
                "delivery_location": f"RGN-{chain.replace(' ', '-')}",
                "order_type": order_type,
            })
            for sku in picked:
                on_promo = is_on_promo(promo, chain, sku, order_date)
                qty = lognormal_qty(4, 45 if on_promo else 35, rng)
                line_seq += 1
                lines.append({
                    "order_line_id": f"RGN-L-{line_seq:07d}",
                    "order_id": order_id,
                    "sku": sku,
                    "quantity_ordered": qty,
                    "unit_of_measure": "case",
                    "unit_price": refs["sku_costs"][sku][WHOLESALE_COL[chain]],
                })
    return orders, lines


def generate_dtc(refs: dict, auth: dict, promo: dict, rng: random.Random) -> tuple[list[dict], list[dict]]:
    """DTC: ~100 consumer orders/week, 1-4 lines each, 1-3 units per line.
    Units, not cases. Target ~$550K/3yr."""
    velocity = refs["velocity"]
    orders, lines = [], []
    seq = 0
    line_seq = 0
    weeks = all_weeks()
    target_orders_per_week = 100
    for week in weeks:
        n_orders = rng.randint(int(target_orders_per_week * 0.85), int(target_orders_per_week * 1.15))
        for _ in range(n_orders):
            order_date = week + timedelta(days=rng.randint(0, 6))
            if order_date > WINDOW_END:
                continue
            available = authorized_skus_for(auth, "DTC", order_date)
            if not available:
                continue
            n_lines = rng.choices([1, 2, 3, 4, 5], weights=[25, 35, 25, 10, 5])[0]
            picked = weighted_sample_no_replace(
                available, velocity_weights(available, velocity), n_lines, rng
            )
            seq += 1
            order_id = f"DTC-{seq:07d}"
            due = order_date  # DTC ships same-day if available
            orders.append({
                "order_id": order_id,
                "retailer": "DTC",
                "channel_type": "dtc",
                "order_date": order_date.isoformat(),
                "due_date": due.isoformat(),
                "ship_date": None,
                "delivery_location": "DTC-CONSUMER",
                "order_type": "dtc_consumer",
            })
            for sku in picked:
                qty = rng.choices([1, 2, 3, 4], weights=[40, 35, 18, 7])[0]
                line_seq += 1
                lines.append({
                    "order_line_id": f"DTC-L-{line_seq:08d}",
                    "order_id": order_id,
                    "sku": sku,
                    "quantity_ordered": qty,
                    "unit_of_measure": "unit",
                    "unit_price": refs["sku_costs"][sku]["wholesale_dtc"],
                })
    return orders, lines


def write_to_db(path: Path, orders: list[dict], lines: list[dict]) -> None:
    if path.exists():
        path.unlink()
    db = sqlite3.connect(path)
    cur = db.cursor()
    cur.executescript("""
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
    cur.executemany(
        "INSERT INTO orders VALUES (:order_id, :retailer, :channel_type, :order_date, "
        ":due_date, :ship_date, :delivery_location, :order_type)",
        orders,
    )
    cur.executemany(
        "INSERT INTO order_lines_original VALUES (:order_line_id, :order_id, :sku, "
        ":quantity_ordered, :unit_of_measure, :unit_price)",
        lines,
    )
    db.commit()
    db.close()


def _load_calibration_targets() -> tuple[dict[str, float], str]:
    """Load 3-year revenue targets from calibration.json if present,
    otherwise fall back to hardcoded defaults."""
    fallback = {
        "UNFI": 845_000,
        "DPI Northwest": 830_000,
        "KeHE": 726_000,
        "DTC": 550_000,
        "Sprouts": 524_000,
        "Whole Foods": 509_000,
        "Regional Group": 493_000,
        "Kroger": 491_000,
        "Walmart": 482_000,
        "Costco": 466_000,
    }
    if not CALIBRATION_FILE.exists():
        return fallback, "hardcoded (run extract_calibration.py to sync)"
    try:
        cal = json.loads(CALIBRATION_FILE.read_text())
        targets = cal.get("revenue_targets_3yr", {})
        if not targets:
            return fallback, "hardcoded (calibration.json missing revenue_targets_3yr)"
        return targets, f"calibration.json ({cal.get('extracted', 'unknown date')})"
    except (json.JSONDecodeError, KeyError):
        return fallback, "hardcoded (calibration.json unreadable)"


def report_revenue(orders: list[dict], lines: list[dict], refs: dict) -> None:
    """Compute per-channel original-demand revenue and report against
    target. Revenue = qty * pack * unit_price for retail/distributor;
    qty * unit_price for DTC."""
    pack = {sku: cp[0] for sku, cp in refs["case_pack"].items()}
    by_order = {o["order_id"]: o for o in orders}
    by_channel: dict[str, float] = defaultdict(float)
    line_count_by_channel: dict[str, int] = defaultdict(int)
    for L in lines:
        o = by_order[L["order_id"]]
        if L["unit_of_measure"] == "case":
            rev = L["quantity_ordered"] * pack[L["sku"]] * L["unit_price"]
        else:
            rev = L["quantity_ordered"] * L["unit_price"]
        by_channel[o["retailer"]] += rev
        line_count_by_channel[o["retailer"]] += 1

    target_3yr, target_source = _load_calibration_targets()
    print()
    print(f"Targets: {target_source}")
    print(f"{'Channel':<16} {'Orders':>8} {'Lines':>10} {'Revenue ($)':>16} {'Target':>14} {'Diff':>10}")
    print("-" * 78)
    order_count_by_ch: dict[str, int] = defaultdict(int)
    for o in orders:
        order_count_by_ch[o["retailer"]] += 1
    report_order = [
        "UNFI", "DPI Northwest", "KeHE", "Walmart", "Costco",
        "Whole Foods", "Sprouts", "Kroger", "Regional Group", "DTC",
    ]
    total_rev = 0.0
    for ch in report_order:
        rev = by_channel.get(ch, 0)
        total_rev += rev
        target = target_3yr.get(ch, 0)
        diff_pct = (rev - target) / target * 100 if target else 0
        print(f"{ch:<16} {order_count_by_ch.get(ch, 0):>8,} {line_count_by_channel.get(ch, 0):>10,} "
              f"${rev:>15,.0f} ${target:>13,} {diff_pct:>+9.1f}%")
    target_total = sum(target_3yr.values())
    diff_pct = (total_rev - target_total) / target_total * 100
    print("-" * 78)
    print(f"{'TOTAL':<16} {len(orders):>8,} {len(lines):>10,} ${total_rev:>15,.0f} ${target_total:>13,} {diff_pct:>+9.1f}%")


def main() -> int:
    if not EXTRACT_DB.exists():
        print(f"ERROR: {EXTRACT_DB} not found")
        return 1
    rng = random.Random(SEED)
    refs = load_reference_data()
    auth = build_auth_index(refs)
    promo = build_promo_index(refs)

    print("Generating original orders...")
    all_orders: list[dict] = []
    all_lines: list[dict] = []
    for fn, label in [
        (generate_walmart, "Walmart"),
        (generate_costco, "Costco"),
        (generate_whole_foods, "Whole Foods"),
        (generate_unfi, "UNFI"),
        (generate_kehe, "KeHE"),
        (generate_dpi_northwest, "DPI Northwest"),
        (generate_regionals, "Regionals"),
        (generate_dtc, "DTC"),
    ]:
        os_, ls_ = fn(refs, auth, promo, rng)
        print(f"  {label:<14} {len(os_):>7,} orders, {len(ls_):>8,} lines")
        all_orders.extend(os_)
        all_lines.extend(ls_)

    print(f"\nTotal: {len(all_orders):,} orders, {len(all_lines):,} lines")
    write_to_db(ORDERS_DB, all_orders, all_lines)
    print(f"Wrote {ORDERS_DB}")

    report_revenue(all_orders, all_lines, refs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
