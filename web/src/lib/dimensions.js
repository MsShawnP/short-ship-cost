// Ordered by magnitude (largest → smallest), matching color assignment.
export const DIMENSION_ORDER = [
  'lost_revenue',
  'deauthorization',
  'otif_fines',
  'chargebacks',
  'dtc_cancellations',
  'triage_labor',
  'distributor_returns',
  'dtc_margin_leakage',
]

export const DIMENSION_LABEL = {
  lost_revenue: 'Lost revenue',
  otif_fines: 'OTIF fines',
  chargebacks: 'Chargebacks',
  deauthorization: 'Deauthorization',
  dtc_cancellations: 'DTC cancellations',
  dtc_margin_leakage: 'DTC margin leakage',
  distributor_returns: 'Distributor returns',
  triage_labor: 'Triage labor',
}

export const DIMENSION_LABEL_SHORT = {
  lost_revenue: 'Lost revenue',
  otif_fines: 'OTIF fines',
  chargebacks: 'Chargebacks',
  deauthorization: 'Deauth.',
  dtc_cancellations: 'DTC cancel',
  dtc_margin_leakage: 'DTC leakage',
  distributor_returns: 'Distrib. returns',
  triage_labor: 'Triage',
}

// Hong Kong (teal) sequential ramp — Lailara DS v2, steps 5–85.
// Darkest at largest dimension, lightest at smallest.
export const DIMENSION_COLOR = {
  lost_revenue: '#063d32',
  deauthorization: '#0a5c4b',
  otif_fines: '#0e6e5a',
  chargebacks: '#158f75',
  dtc_cancellations: '#1fa282',
  triage_labor: '#35b595',
  distributor_returns: '#6dcdb5',
  dtc_margin_leakage: '#b5e4d8',
}
