import { useTimeRange, PRESETS, formatMonthLabel } from '../lib/timeRange.jsx'
import styles from './FilterBar.module.css'

export default function FilterBar() {
  const {
    preset,
    setPreset,
    customStart,
    setCustomStart,
    customEnd,
    setCustomEnd,
    allMonths,
    isFiltered,
    startMonth,
    endMonth,
  } = useTimeRange()

  const minMonth = allMonths[0]
  const maxMonth = allMonths[allMonths.length - 1]

  return (
    <div className={`${styles.bar} no-print`}>
      <label className={styles.label}>
        Range
        <select
          className={styles.select}
          value={preset}
          onChange={(e) => setPreset(e.target.value)}
        >
          {PRESETS.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label}
            </option>
          ))}
        </select>
      </label>

      {preset === 'custom' && (
        <div className={styles.customInputs}>
          <input
            type="month"
            className={styles.month}
            min={minMonth}
            max={customEnd}
            value={customStart}
            onChange={(e) => setCustomStart(e.target.value)}
          />
          <span className={styles.dash}>&ndash;</span>
          <input
            type="month"
            className={styles.month}
            min={customStart}
            max={maxMonth}
            value={customEnd}
            onChange={(e) => setCustomEnd(e.target.value)}
          />
        </div>
      )}

      {isFiltered && preset !== 'custom' && (
        <span className={styles.activeNote}>
          {formatMonthLabel(startMonth)} &ndash; {formatMonthLabel(endMonth)}
        </span>
      )}
    </div>
  )
}
