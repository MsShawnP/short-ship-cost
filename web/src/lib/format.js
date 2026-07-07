const compactCurrency = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 1,
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

const safe = (v) => (Number.isFinite(v) ? v : 0)

export const fmtCompact = (v) => compactCurrency.format(safe(v))
export const fmtFull = (v) => fullCurrency.format(safe(v))
export const fmtPct = (v) => percent.format(safe(v))

export const fmtMillions = (v) => `$${(safe(v) / 1e6).toFixed(0)}M`

export function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}
