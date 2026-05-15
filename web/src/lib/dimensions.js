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

// Sequential teal palette, darkest at largest dimension → lightest at smallest.
// Used by all sections so the same dimension reads the same color page-wide.
export const DIMENSION_COLOR = {
  lost_revenue: '#0A3D3D',
  deauthorization: '#14605C',
  otif_fines: '#1F8078',
  chargebacks: '#2A9D93',
  dtc_cancellations: '#45B5AA',
  triage_labor: '#6BCABD',
  distributor_returns: '#93DCD2',
  dtc_margin_leakage: '#BDEEE8',
}
