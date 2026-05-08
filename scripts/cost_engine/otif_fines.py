"""Cost dimension: OTIF fines.

Fine schedule (parameters.py):
- Walmart: 3% of line COGS, applied per non-compliant PO line (fill < 98%)
- Costco:  $250 flat per PO with any short
- Whole Foods: 2% of PO COGS, applied when PO fill < 95%
- UNFI:    3% of shorted goods VALUE, applied when PO fill < 95%
- KeHE:    2% of PO COGS, applied when PO fill < 95%
- Regional: 1% of PO COGS, applied when PO fill < 90%
- DTC:     no OTIF fines

Fill rate is computed dollar-weighted over the PO (or line for
Walmart). PO fill = sum(shipped_revenue) / sum(ordered_revenue).
"""
from __future__ import annotations

from collections import defaultdict

from .common import aggregate_breakdowns, channel_of, empty_result, open_db
from .parameters import REGIONAL_CHAINS, get


def _retailer_rule(retailer: str) -> tuple[str, float, float]:
    """Return (basis_kind, rate_or_fee, target_fill_threshold).
    basis_kind is one of: 'walmart_line_cogs', 'costco_flat',
    'po_cogs', 'unfi_shorted_value'."""
    if retailer == "Walmart":
        return ("walmart_line_cogs", get("otif_walmart_rate"), 0.98)
    if retailer == "Costco":
        return ("costco_flat", get("otif_costco_flat_fee"), 0.0)  # Costco fires on any short
    if retailer == "Whole Foods":
        return ("po_cogs", get("otif_whole_foods_rate"), 0.95)
    if retailer == "UNFI":
        return ("unfi_shorted_value", get("otif_unfi_rate"), 0.95)
    if retailer == "KeHE":
        return ("po_cogs", get("otif_kehe_rate"), 0.95)
    if retailer in REGIONAL_CHAINS:
        return ("po_cogs", get("otif_regional_rate"), 0.90)
    return ("none", 0.0, 0.0)


def calculate() -> dict:
    db = open_db()
    cur = db.cursor()

    # Pull every retail/distributor PO with its lines and per-SKU cost.
    cur.execute(
        """
        SELECT
          o.order_id, o.retailer, o.channel_type,
          substr(o.order_date, 1, 7) AS month,
          lo.sku,
          lo.quantity_ordered, ls.quantity_shipped,
          pm.case_pack_qty,
          lo.unit_price,
          sc.cogs_per_unit
        FROM orders o
        JOIN order_lines_original lo ON lo.order_id = o.order_id
        JOIN order_lines_shipped ls  ON ls.original_line_id = lo.order_line_id
        JOIN ext.product_master pm   ON pm.sku = lo.sku
        JOIN ext.sku_costs sc        ON sc.sku = lo.sku
        WHERE o.channel_type IN ('retail', 'distributor')
        ORDER BY o.order_id
        """
    )

    # Group lines by order_id
    po_data: dict[str, dict] = defaultdict(lambda: {"lines": [], "meta": None})
    for r in cur.fetchall():
        po_data[r["order_id"]]["lines"].append(dict(r))
        po_data[r["order_id"]]["meta"] = (r["retailer"], r["channel_type"], r["month"])
    db.close()

    rows: list[dict] = []
    for order_id, payload in po_data.items():
        retailer, channel_type, month = payload["meta"]
        lines = payload["lines"]
        basis_kind, rate, target = _retailer_rule(retailer)
        if basis_kind == "none":
            continue

        # Per-line aggregates we need
        po_demand_value = sum(L["quantity_ordered"] * L["case_pack_qty"] * L["unit_price"] for L in lines)
        po_shipped_value = sum(L["quantity_shipped"] * L["case_pack_qty"] * L["unit_price"] for L in lines)
        po_demand_cogs = sum(L["quantity_ordered"] * L["case_pack_qty"] * L["cogs_per_unit"] for L in lines)
        shorted_value = po_demand_value - po_shipped_value
        any_short = po_shipped_value < po_demand_value
        po_fill = po_shipped_value / po_demand_value if po_demand_value else 1.0

        if basis_kind == "walmart_line_cogs":
            # Per-line fines for non-compliant lines (fill < 98%)
            for L in lines:
                line_demand = L["quantity_ordered"]
                line_ship = L["quantity_shipped"]
                if line_demand == 0:
                    continue
                line_fill = line_ship / line_demand
                if line_fill < target:
                    line_cogs = line_demand * L["case_pack_qty"] * L["cogs_per_unit"]
                    fine = rate * line_cogs
                    rows.append({
                        "retailer": channel_of(retailer, channel_type),
                        "sku": L["sku"],
                        "month": month,
                        "cost": fine,
                    })

        elif basis_kind == "costco_flat":
            if any_short:
                # Attribute the flat fee to the largest-shorted SKU on the PO
                shortages = [
                    (L["sku"], (L["quantity_ordered"] - L["quantity_shipped"])
                     * L["case_pack_qty"] * L["unit_price"])
                    for L in lines
                ]
                shortages.sort(key=lambda x: x[1], reverse=True)
                worst_sku = shortages[0][0]
                rows.append({
                    "retailer": channel_of(retailer, channel_type),
                    "sku": worst_sku,
                    "month": month,
                    "cost": rate,
                })

        elif basis_kind == "po_cogs":
            if po_fill < target:
                fine = rate * po_demand_cogs
                # Attribute the PO-level fine across SKUs by demand share
                if po_demand_value > 0:
                    for L in lines:
                        line_demand_value = L["quantity_ordered"] * L["case_pack_qty"] * L["unit_price"]
                        share = line_demand_value / po_demand_value
                        rows.append({
                            "retailer": channel_of(retailer, channel_type),
                            "sku": L["sku"],
                            "month": month,
                            "cost": fine * share,
                        })

        elif basis_kind == "unfi_shorted_value":
            if po_fill < target:
                fine = rate * shorted_value
                # Attribute by each SKU's share of shorted value
                if shorted_value > 0:
                    for L in lines:
                        L_short = (L["quantity_ordered"] - L["quantity_shipped"]) \
                                  * L["case_pack_qty"] * L["unit_price"]
                        if L_short > 0:
                            rows.append({
                                "retailer": channel_of(retailer, channel_type),
                                "sku": L["sku"],
                                "month": month,
                                "cost": fine * (L_short / shorted_value),
                            })

    result = empty_result(
        "otif_fines",
        "Retailer-specific OTIF fines per the schedule in "
        "docs/cost-engine-benchmarks.md (with UNFI updated to 3% of "
        "shorted goods value per PLAN task 5)",
    )
    result["total_cost"] = sum(r["cost"] for r in rows)
    result.update(aggregate_breakdowns(rows))
    return result


if __name__ == "__main__":
    out = calculate()
    print(f"{out['dimension']:<20} ${out['total_cost']:>15,.0f}")
    print("  by retailer:")
    for r in out["by_retailer"]:
        print(f"    {r['retailer']:<14} ${r['cost']:>14,.0f}")
