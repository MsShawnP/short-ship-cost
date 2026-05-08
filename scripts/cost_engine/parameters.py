"""Centralized cost-engine parameters. Every tunable number lives
here so the interactive tool can display and override them.

Each parameter has a value, a unit/basis, a description, and a
source (docs reference or PLAN task 5 spec). When the runner writes
short_ship_cost.db, it mirrors this dict into a `cost_parameters`
table so downstream consumers can see exactly what was used."""
from __future__ import annotations

REGIONAL_CHAINS = (
    "Southside Grocers", "Green Basket Market", "Prairie Provisions",
    "Mountain Pantry Co", "Harbor Fresh",
)

PARAMETERS: dict[str, dict] = {
    # OTIF fine rates and targets
    "otif_walmart_rate": {
        "value": 0.03, "unit": "fraction", "basis": "COGS",
        "level": "PO line", "target_fill": 0.98,
        "description": "Walmart OTIF fine rate, applied per non-compliant PO line",
        "source": "docs/cost-engine-benchmarks.md",
    },
    "otif_costco_flat_fee": {
        "value": 250.0, "unit": "USD", "basis": "flat per short event",
        "level": "PO", "target_fill": None,
        "description": "Costco appointment-window flat fee per PO with any short",
        "source": "docs/cost-engine-benchmarks.md",
    },
    "otif_whole_foods_rate": {
        "value": 0.02, "unit": "fraction", "basis": "COGS",
        "level": "PO", "target_fill": 0.95,
        "description": "Whole Foods OTIF fine rate per non-compliant PO",
        "source": "docs/cost-engine-benchmarks.md",
    },
    "otif_unfi_rate": {
        "value": 0.03, "unit": "fraction", "basis": "shorted goods value",
        "level": "PO", "target_fill": 0.95,
        "description": "UNFI fine rate, applied to shorted goods value when PO fill < 95%",
        "source": "PLAN task 5 spec (overrides earlier 2% of COGS in benchmarks doc)",
    },
    "otif_kehe_rate": {
        "value": 0.02, "unit": "fraction", "basis": "COGS",
        "level": "PO", "target_fill": 0.95,
        "description": "KeHE fine rate per PO below 95% fill rate",
        "source": "docs/cost-engine-benchmarks.md",
    },
    "otif_regional_rate": {
        "value": 0.01, "unit": "fraction", "basis": "COGS",
        "level": "PO", "target_fill": 0.90,
        "description": "Regional chain OTIF fine rate per non-compliant PO",
        "source": "docs/cost-engine-benchmarks.md",
    },

    # Chargeback fallback rates (used when historical chargebacks
    # table doesn't have rate-schedule detail tied to shorts)
    "chargeback_rate_walmart_costco": {
        "value": 0.005, "unit": "fraction", "basis": "shorted goods value",
        "description": "Estimated chargeback rate for Walmart and Costco",
        "source": "PLAN task 5 spec",
    },
    "chargeback_rate_other": {
        "value": 0.003, "unit": "fraction", "basis": "shorted goods value",
        "description": "Estimated chargeback rate for non-Walmart/Costco retailers",
        "source": "PLAN task 5 spec",
    },

    # Deauthorization thresholds (units per store per week)
    "deauth_velocity_walmart": {
        "value": 2.00, "unit": "units/store/week",
        "description": "Walmart delisting threshold",
        "source": "PLAN task 5 spec",
    },
    "deauth_velocity_costco": {
        "value": 5.00, "unit": "units/store/week",
        "description": "Costco delisting threshold",
        "source": "PLAN task 5 spec",
    },
    "deauth_velocity_whole_foods": {
        "value": 1.50, "unit": "units/store/week",
        "description": "Whole Foods delisting threshold",
        "source": "PLAN task 5 spec",
    },
    "deauth_velocity_regional": {
        "value": 1.00, "unit": "units/store/week",
        "description": "Regional chain delisting threshold",
        "source": "PLAN task 5 spec",
    },
    "deauth_distributor_fill_rate": {
        "value": 0.90, "unit": "fraction",
        "description": "UNFI/KeHE delisting threshold — fill rate below this for "
                       "consecutive months triggers deauthorization",
        "source": "PLAN task 5 spec",
    },
    "deauth_distributor_consecutive_months": {
        "value": 3, "unit": "months",
        "description": "UNFI/KeHE consecutive-months window for distributor deauth",
        "source": "PLAN task 5 spec",
    },
    "deauth_revenue_horizon_months": {
        "value": 12, "unit": "months",
        "description": "Annualized revenue window used to value a deauth event",
        "source": "PLAN task 5 spec",
    },

    # DTC cancellation curve (also in cost-engine-benchmarks.md;
    # mirrored here so the runner can write parameters table)
    "dtc_cancel_under_3_days": {
        "value": 0.10, "unit": "fraction",
        "description": "DTC cancellation rate when held < 3 days",
        "source": "docs/cost-engine-benchmarks.md",
    },
    "dtc_cancel_3_to_7_days": {
        "value": 0.25, "unit": "fraction",
        "description": "DTC cancellation rate when held 3-7 days",
        "source": "docs/cost-engine-benchmarks.md",
    },
    "dtc_cancel_7_to_14_days": {
        "value": 0.40, "unit": "fraction",
        "description": "DTC cancellation rate when held 7-14 days",
        "source": "docs/cost-engine-benchmarks.md",
    },
    "dtc_cancel_over_14_days": {
        "value": 0.60, "unit": "fraction",
        "description": "DTC cancellation rate when held > 14 days",
        "source": "docs/cost-engine-benchmarks.md",
    },

    # DTC margin leakage
    "dtc_margin_pct": {
        "value": 0.55, "unit": "fraction",
        "description": "DTC channel gross margin (used in margin leakage calc)",
        "source": "PLAN task 5 spec",
    },
    "wholesale_margin_pct": {
        "value": 0.35, "unit": "fraction",
        "description": "Wholesale channel gross margin (used in margin leakage calc)",
        "source": "PLAN task 5 spec",
    },

    # Distributor returns (rates already realized in the data — these
    # are documented for transparency)
    "distributor_unsold_promo_rate": {
        "value": 0.12, "unit": "fraction", "basis": "shipped promo cases",
        "description": "Share of UNFI/KeHE promo volume returned unsold",
        "source": "docs/cost-engine-benchmarks.md",
    },
    "distributor_claim_filed_rate": {
        "value": 0.05, "unit": "fraction", "basis": "shipped promo cases",
        "description": "Share of UNFI/KeHE promo volume claimed/written off",
        "source": "docs/cost-engine-benchmarks.md",
    },

    # Triage labor
    "triage_minutes_per_order": {
        "value": 20, "unit": "minutes",
        "description": "Minutes per triaged order edit (median)",
        "source": "docs/cost-engine-benchmarks.md",
    },
    "triage_hourly_rate": {
        "value": 30.0, "unit": "USD/hour",
        "description": "Blended hourly rate for EDI/sales admin team",
        "source": "docs/cost-engine-benchmarks.md",
    },
    "triage_share_of_orders": {
        "value": 0.90, "unit": "fraction",
        "description": "Share of retail/distributor orders requiring triage",
        "source": "docs/cost-engine-benchmarks.md",
    },
}


def get(key: str):
    return PARAMETERS[key]["value"]
