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
// Four steps, darkest at largest dimension, lightest at smallest.
export const DIMENSION_COLOR = {
  forgone_revenue: '#063d32',
  compliance_fines: '#0e6e5a',
  chargebacks: '#1fa282',
  deductions: '#6dcdb5',
}
