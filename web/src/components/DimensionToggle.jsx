import { DIMENSION_COLOR, DIMENSION_LABEL, DIMENSION_ORDER } from '../lib/dimensions.js'
import { useTimeRange } from '../lib/timeRange.jsx'
import styles from './DimensionToggle.module.css'

export default function DimensionToggle() {
  const { activeDims, toggleDim, resetDims } = useTimeRange()
  const allOn = activeDims.size === DIMENSION_ORDER.length

  return (
    <div className={`${styles.bar} no-print`}>
      <div className={styles.labelRow}>
        <span className={styles.label}>Dimensions</span>
        <span className={styles.hint}>click to exclude</span>
        {!allOn && (
          <button
            type="button"
            className={styles.reset}
            onClick={resetDims}
          >
            Show all
          </button>
        )}
      </div>
      <div className={styles.chipGrid}>
        {DIMENSION_ORDER.map((dim) => {
          const on = activeDims.has(dim)
          return (
            <button
              key={dim}
              type="button"
              className={`${styles.chip} ${on ? styles.chipActive : styles.chipInactive}`}
              onClick={() => toggleDim(dim)}
              aria-pressed={on}
            >
              <span
                className={styles.swatch}
                style={{ background: DIMENSION_COLOR[dim] }}
              />
              {DIMENSION_LABEL[dim]}
            </button>
          )
        })}
      </div>
    </div>
  )
}
