# Cost Engine Benchmarks

> **SUPERSEDED (2026-07-30).** This document describes the retired synthetic
> 8-dimension cost engine ($18.7M-lineage figures). The shipped tool reads
> platform shipment lines at 99.2%/99.5% fill and reports the 4-dimension
> $894K/36-month stack ($523K forgone revenue + $165K fines + $119K
> chargebacks + $87K deductions; $643K economic loss at margin basis).
> See README.md "Provenance" for the retirement of the $33.1M and $6.6M
> lineages. Kept for design history only.


These are industry-average defaults for a ~$25M make-to-order specialty
food company. Walmart's 3% COGS fine schedule is well-documented;
Costco, Whole Foods, UNFI, KeHE, and regional fine rates are reasonable
estimates from published ranges. DTC cancellation behavior and
distributor return rates are modeled assumptions. Every parameter
below is adjustable — the interactive tool will let users override
each one and watch the cost stack respond.

## OTIF fines

Applied to non-compliant POs (or PO lines, where the retailer charges
at line level). "Non-compliant" means the shipment fell below the
retailer's fill-rate target.

| Retailer | Rate | Basis | Compliance target |
|---|---|---|---|
| Walmart | 3% | of COGS, per non-compliant PO line | 98% |
| Costco | $250 flat | per short event (missed appointment window) | n/a — event-based |
| Whole Foods | 2% | of COGS, per non-compliant PO | 95% |
| UNFI | 3% | of shorted goods value, per PO below fill-rate target | 95% |
| KeHE | 2% | of COGS, per PO below fill-rate target | 95% |
| Regionals | 1% | of COGS, per non-compliant PO | 90% |

COGS for the fine calculation is the per-unit `cogs_per_unit` from
`sku_costs`, multiplied by units ordered for the line or PO. UNFI
is the exception — its 3% fine is applied to the shorted goods'
*wholesale value*, not COGS, so the formula is
`quantity_shorted × pack × unit_price × 0.03`.

## Fill rates

These are the target fill rates that drive the synthetic shipped-vs-
original gap. Lower fill rate → more shorts → higher fines, lost
revenue, deauth risk, and DTC cancellations.

| Channel | Default fill rate | Notes |
|---|---|---|
| Overall | ~75% | Blended target across channels. |
| Walmart | ~78% | Top of the triage hierarchy. |
| Costco | ~80% | Highest priority, contract-anchored. |
| Whole Foods | ~75% | Mid-tier priority. |
| UNFI | ~70% | Distributor; mixed promo/replenishment. |
| KeHE | ~70% | Distributor; mixed promo/replenishment. |
| Regionals | ~65% | Smallest, most sporadic; gets shorted first. |
| DTC | ~85% unit availability | But held for 100% complete — fill rate at the *order* level is much lower than 85%. |

DTC's number is unit-level availability, not order-level fill. A DTC
order ships only when 100% of its lines are available; a 15% per-line
unavailability rate compounds across multi-line orders, which is why
DTC cancellations are non-trivial even with high unit availability.

## DTC cancellations

Probability that a held-incomplete DTC order is cancelled by the
customer, by hold duration:

| Hold duration | Cancellation rate |
|---|---|
| < 3 days | 10% |
| 3 – 7 days | 25% |
| 7 – 14 days | 40% |
| > 14 days | 60% |

Of the cancellations:

- **35%** purchase the product in-store. The brand still gets the unit
  sale but at retail-channel wholesale pricing instead of DTC pricing;
  the per-unit margin difference is the *DTC-to-retail margin leakage*.
- **65%** are lost entirely. No replacement purchase.

## Distributor returns

Applies to UNFI and KeHE orders. Retail-direct and DTC orders do not
have this exposure.

- **12%** of promo-period volume is returned unsold.
- **5%** of promo-period volume is claimed or written off (damage,
  expiry, deduction without product return).
- Non-promo return rates are negligible and modeled as zero.

Returns generate `credit_amount` against the original order; claims
reduce realized revenue without a physical return.

## Triage labor

The hidden tax on every shorted order: human time spent editing it.

- **20 minutes** per order edit (median).
- **$30/hr** blended labor rate (EDI / sales admin team).
- **~90%** of orders require some triage in the current state.

A 20-minute edit at $30/hr is $10 per triaged order. At ~90%
triage rate the per-order tax is ~$9. Multiplied across an order
volume consistent with $25M annual wholesale revenue, this becomes
material.

## A note on adjustability

Every number on this page is a default, not a fact about the world.
The interactive tool will expose each parameter as a control so a
viewer can:

- Replace Walmart's 3% with a contract-specific rate.
- Adjust fill rates up to model a buffer-improvement scenario.
- Tighten or loosen DTC cancellation curves.
- Zero out a category to isolate its contribution to the total.

Any number cited in the export or narrative must come from the
parameters in effect when the export was generated, not from this
document.
