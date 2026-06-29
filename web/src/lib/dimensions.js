// Ordered by magnitude (largest → smallest), matching color assignment.
export const DIMENSION_ORDER = [
  'forgone_revenue',
  'compliance_fines',
  'chargebacks',
  'deductions',
]

export const DIMENSION_LABEL = {
  forgone_revenue: 'Forgone revenue',
  compliance_fines: 'Compliance fines',
  chargebacks: 'Chargebacks',
  deductions: 'Deductions',
}

export const DIMENSION_LABEL_SHORT = {
  forgone_revenue: 'Forgone rev.',
  compliance_fines: 'Fines',
  chargebacks: 'Chargebacks',
  deductions: 'Deductions',
}

// Hong Kong (teal) sequential ramp — Lailara DS v2.
// 4-series stops: 15, 35, 55, 85. Darkest = largest dimension.
export const DIMENSION_COLOR = {
  forgone_revenue: '#0a5c4b',
  compliance_fines: '#158f75',
  chargebacks: '#35b595',
  deductions: '#b5e4d8',
}
