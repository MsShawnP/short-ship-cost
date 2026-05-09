const compactCurrency = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const fullCurrency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

const percent = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

export const fmtCompact = (v) => compactCurrency.format(v)
export const fmtFull = (v) => fullCurrency.format(v)
export const fmtPct = (v) => percent.format(v)

export const fmtMillions = (v) => `$${(v / 1e6).toFixed(0)}M`
