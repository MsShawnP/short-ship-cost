# Short-Ship Cost — Client Data Input Specification

Short-Ship Cost prices your fulfillment shortfall: units ordered vs shipped, the
fill rate, and the forgone value of what wasn't shipped — valued at your chosen
**basis** (wholesale revenue or contribution margin). Money tool: the basis is a
required declaration and is printed on every figure. Not POS-shaped, so it uses
the generic column contract. Map your headers in `engagement.yml`.

## §Shipments — the order-line ledger (required)
One row per order line (a SKU on an order).

| Column | Type | Required | Used for |
|---|---|---|---|
| `line_id` | identifier (text) | **required, unique** | the line key |
| `retailer` | string | **required** | per-retailer rollup |
| `sku` | identifier (text) | **required** | item |
| `ship_date` | date | **required** | window |
| `units_ordered` | number ≥ 0 | **required** | fill-rate denominator; shortfall |
| `units_shipped` | number ≥ 0 | **required** | fill-rate numerator |
| `unit_price` | number ≥ 0 | **required** | forgone value at the **revenue** basis |
| `unit_margin` | number ≥ 0 | **required when basis = margin** | forgone value at the **margin** basis |

Shorted units = `max(units_ordered − units_shipped, 0)`. Forgone = shorted units ×
(unit_price if basis = revenue, else unit_margin). Fill rate = shipped ÷ ordered.

## Required declaration (`basis.forgone_basis`)
`revenue` (shorted units × wholesale price) or `margin` (shorted units ×
contribution margin). Carried into the provenance footer and printed next to the
forgone figure — a revenue number can never be read as margin. When `margin`,
`unit_margin` becomes a required column (so a margin engagement can't silently
value at revenue).

## Column mapping (`engagement.yml`)
```yaml
client: {name: Your Brand}
engagement: {id: YB-2026-08}
as_of_date: 2026-06-30
basis:
  forgone_basis: revenue
inputs:
  input: client-data/shipments.csv
columns:
  line_id: "Order Line"
  units_ordered: "Qty Ordered"
  units_shipped: "Qty Shipped"
  unit_price: "Unit Cost"
```
