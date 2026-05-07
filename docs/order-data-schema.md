# Order Data Schema

Six new tables that together model order-as-submitted, order-as-shipped,
and the consequences of the gap between them. They sit alongside the
eight-table Cinderhaven extract in `data/cinderhaven_extract.db`; this
project will write them to that same database (or to a separate
`orders.db`, to be decided in the implementation task).

This is a design specification, not implementation. No tables exist
yet.

## The six tables

### 1. `orders`

One row per order received from a customer (retail partner, distributor,
or DTC consumer).

| Column | Type | Notes |
|---|---|---|
| `order_id` | TEXT, PK | Surrogate. Stable across original and shipped lines. |
| `retailer` | TEXT | Joins to `stores.retailer` and `sku_costs.wholesale_<retailer>`. |
| `channel_type` | TEXT | `retail`, `distributor`, `dtc`. Drives fine schedule and behavior model. |
| `order_date` | DATE | When the order was received. Used to look up SKU pricing in `price_history`. |
| `due_date` | DATE | Promised ship-by or appointment date. Drives OTIF compliance. |
| `ship_date` | DATE, nullable | When the (possibly edited) order actually shipped. NULL if not yet shipped. |
| `delivery_location` | TEXT | DC or store ID for retail; aggregated for DTC. Joins to `stores.store_id` for retail / distributor orders where applicable. |
| `order_type` | TEXT | `replenishment`, `promo`, `contract`, `dtc_consumer`. |

### 2. `order_lines_original`

One row per SKU on an order *as the customer submitted it*. This is the
table the legacy system overwrites in real life — capturing it is the
entire purpose of this project.

| Column | Type | Notes |
|---|---|---|
| `order_line_id` | TEXT, PK | Surrogate, unique within this table. |
| `order_id` | TEXT, FK → `orders.order_id` | |
| `sku` | TEXT, FK → `product_master.sku` | |
| `quantity_ordered` | INTEGER | In the unit specified by `unit_of_measure`. |
| `unit_of_measure` | TEXT | `case` for retail and distributor orders, `unit` for DTC. |
| `unit_price` | REAL | Per-unit wholesale price for this `(sku, retailer)` at `order_date`, sourced from `sku_costs.wholesale_<retailer>` or `price_history`. Stored on the line so revenue math is reproducible even if pricing changes later. |

### 3. `order_lines_shipped`

One row per SKU on an order *as actually shipped*, after triage. The
delta vs. `order_lines_original` is the short.

| Column | Type | Notes |
|---|---|---|
| `order_line_id` | TEXT, PK | Surrogate, unique within this table. |
| `order_id` | TEXT, FK → `orders.order_id` | |
| `sku` | TEXT, FK → `product_master.sku` | |
| `quantity_shipped` | INTEGER | Same UoM as the original line. May be 0 for a total drop. |
| `unit_of_measure` | TEXT | Must match the original line's UoM. |
| `unit_price` | REAL | Same value as the original line; carried for join-free revenue math. |

A line with `quantity_shipped = 0` is a complete drop — the SKU was
on the original order but did not ship at all. There is *not* a row
per shipped line plus a separate row for the dropped portion; the
shipped table represents what landed, full stop.

### 4. `order_shorts`

One row per shorted SKU on an order, with a reason. Strictly speaking
the *quantity* short is derivable from joining the two lines tables;
this table earns its keep by carrying the **reason**, which is not
recoverable from the quantity delta.

| Column | Type | Notes |
|---|---|---|
| `short_id` | TEXT, PK | Surrogate. |
| `order_id` | TEXT, FK → `orders.order_id` | |
| `sku` | TEXT, FK → `product_master.sku` | |
| `quantity_shorted` | INTEGER | `quantity_ordered − quantity_shipped`. |
| `short_reason` | TEXT | `inventory_unavailable`, `production_delayed`, `prioritized_to_other_retailer`, `sku_dropped_entirely`. |

### 5. `dtc_outcomes`

One row per DTC order, capturing what happened to it after the
hold-for-complete clock started. Retail and distributor orders do not
appear here.

| Column | Type | Notes |
|---|---|---|
| `order_id` | TEXT, PK / FK → `orders.order_id` | One outcome per DTC order. |
| `hold_start_date` | DATE | Usually equals `order_date` for DTC. |
| `resolution` | TEXT | `shipped_complete`, `cancelled_by_customer`, `purchased_in_store`. |
| `resolution_date` | DATE | When `resolution` was recorded. |
| `days_held` | INTEGER | `resolution_date − hold_start_date`. Stored for ease of analysis. |

The split between `cancelled_by_customer` and `purchased_in_store` is
where DTC-to-retail margin leakage shows up: a cancelled DTC order at
DTC pricing (`sku_costs.wholesale_dtc`) replaced by an in-store purchase
at retail-channel pricing represents a margin loss per unit.

### 6. `distributor_returns`

One row per returned line from a distributor (UNFI, KeHE). Retail and
DTC orders do not appear here.

| Column | Type | Notes |
|---|---|---|
| `return_id` | TEXT, PK | Surrogate. |
| `order_id` | TEXT, FK → `orders.order_id` | The originating order. |
| `sku` | TEXT, FK → `product_master.sku` | |
| `quantity_returned` | INTEGER | In the same UoM as the original order (cases). |
| `return_reason` | TEXT | `unsold_promo`, `damaged`, `expired`, `claim_filed`. |
| `return_date` | DATE | When the return / claim was processed. |
| `credit_amount` | REAL | Dollar credit issued to the distributor. |

## Notes

- **Unit of measure.** Retail and distributor orders are placed in
  **cases**. DTC consumer orders are in **units**. The `unit_of_measure`
  column on each line carries this explicitly and must be respected
  by every downstream calculation.
- **All `sku_costs` prices are per unit.** To get order revenue from a
  retail / distributor line, multiply
  `quantity_ordered × case_pack_qty × unit_price`, where
  `case_pack_qty` comes from `product_master`. For DTC lines, units are
  already units; multiply `quantity_ordered × unit_price`.
- **Distribution authorization is required.** Every
  `(sku, retailer)` pair appearing on an order must have an active
  authorization in `distribution_log` at `order_date` — i.e., a row
  with `authorized_date <= order_date` and either
  `deauthorized_date IS NULL` or `deauthorized_date > order_date`.
  Generation must enforce this.
- **Time window.** Orders span the same 18–24 month window as the
  existing Cinderhaven scan and pricing data (per
  `DECISIONS.md`, 2026-05-07).
- **Linkage between original and shipped lines.** Lines link by
  `(order_id, sku)`. `order_line_id` is a per-table surrogate;
  the same SKU on the same order has a row in
  `order_lines_original` and either a matching row in
  `order_lines_shipped` (any `quantity_shipped >= 0`) or, by convention,
  a matching row with `quantity_shipped = 0`. We assume one line per
  SKU per order; if a future requirement forces multiple lines for the
  same SKU on one order (split allocation across promo and
  non-promo, e.g.), the join key would need to widen.

## Things to flag

- **`order_shorts.quantity_shorted` duplicates derivable data.**
  Carrying it on the table is convenient for reporting but introduces a
  consistency obligation: it must equal
  `quantity_ordered − quantity_shipped` for the matching line. Either
  populate it from a generation-time computation and treat it as a
  cached value, or drop the column and rely on the join. To be decided
  at implementation time.
- **`unit_price` is duplicated across original and shipped lines.**
  Storing the same value twice is deliberate (lets revenue math run on
  one table without joining the other) but means the two values must be
  written together. A view layer over the two tables could enforce this
  if it becomes a problem.
- **`retailer_requirements` (in the Cinderhaven extract) is
  out of scope here.** It governs field-level data-quality compliance
  and feeds the existing `chargebacks` table — orthogonal to the
  short-ship cost model.
