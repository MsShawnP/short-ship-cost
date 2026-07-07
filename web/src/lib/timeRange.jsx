import { createContext, useCallback, useContext, useMemo, useState } from 'react'

import { DIMENSION_ORDER } from './dimensions.js'

const TimeRangeContext = createContext(null)

export const PRESETS = [
  { id: 'full', label: 'Full period', monthsBack: null },
  { id: 'last_12', label: 'Last 12 months', monthsBack: 12 },
  { id: 'last_6', label: 'Last 6 months', monthsBack: 6 },
  { id: 'last_3', label: 'Last 3 months', monthsBack: 3 },
  { id: 'custom', label: 'Custom range', monthsBack: null },
]

export function TimeRangeProvider({
  allMonths,
  baselineParams,
  children,
}) {
  const firstMonth = allMonths[0]
  const lastMonth = allMonths[allMonths.length - 1]

  const [preset, setPreset] = useState('full')
  const [customStart, setCustomStart] = useState(firstMonth)
  const [customEnd, setCustomEnd] = useState(lastMonth)
  const [activeDims, setActiveDims] = useState(() => new Set(DIMENSION_ORDER))
  const [params, setParams] = useState(() => ({ ...(baselineParams || {}) }))

  const range = useMemo(() => {
    if (preset === 'full') {
      return { startMonth: firstMonth, endMonth: lastMonth, isFiltered: false }
    }
    if (preset === 'custom') {
      const isFull = customStart === firstMonth && customEnd === lastMonth
      return {
        startMonth: customStart,
        endMonth: customEnd,
        isFiltered: !isFull,
      }
    }
    const def = PRESETS.find((p) => p.id === preset)
    if (!def || !def.monthsBack) {
      return { startMonth: firstMonth, endMonth: lastMonth, isFiltered: false }
    }
    const endIdx = allMonths.length - 1
    const startIdx = Math.max(0, endIdx - def.monthsBack + 1)
    return {
      startMonth: allMonths[startIdx],
      endMonth: lastMonth,
      isFiltered: startIdx > 0,
    }
  }, [preset, customStart, customEnd, allMonths, firstMonth, lastMonth])

  const toggleDim = useCallback((dim) => {
    setActiveDims((prev) => {
      const next = new Set(prev)
      if (next.has(dim)) next.delete(dim)
      else next.add(dim)
      return next
    })
  }, [])

  const resetDims = useCallback(() => {
    setActiveDims(new Set(DIMENSION_ORDER))
  }, [])

  const setParam = useCallback((key, value) => {
    setParams((prev) => ({ ...prev, [key]: value }))
  }, [])

  const resetParams = useCallback(() => {
    setParams({ ...(baselineParams || {}) })
  }, [baselineParams])

  const paramsModified = useMemo(() => {
    if (!baselineParams) return false
    for (const k of Object.keys(baselineParams)) {
      if (params[k] !== baselineParams[k]) return true
    }
    return false
  }, [params, baselineParams])

  const value = {
    ...range,
    preset,
    setPreset,
    customStart,
    customEnd,
    setCustomStart,
    setCustomEnd,
    allMonths,
    activeDims,
    toggleDim,
    resetDims,
    params,
    baselineParams,
    setParam,
    resetParams,
    paramsModified,
  }

  return (
    <TimeRangeContext.Provider value={value}>
      {children}
    </TimeRangeContext.Provider>
  )
}

export function useTimeRange() {
  const ctx = useContext(TimeRangeContext)
  if (!ctx) throw new Error('useTimeRange must be used inside TimeRangeProvider')
  return ctx
}

export function filterByMonth(rows, range) {
  return rows.filter(
    (r) => r.month >= range.startMonth && r.month <= range.endMonth,
  )
}

export function formatMonthLabel(monthStr) {
  // 'YYYY-MM' → 'May 2024'
  const [y, m] = monthStr.split('-').map(Number)
  const d = new Date(Date.UTC(y, m - 1, 1))
  return d.toLocaleString('en-US', {
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  })
}
