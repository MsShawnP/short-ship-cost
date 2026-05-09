import {
  ALL_DIMENSIONS,
  useTimeRange,
} from '../lib/timeRange.jsx'
import { DIMENSION_LABEL, DIMENSION_COLOR } from '../lib/dimensions.js'
import styles from './DimensionToggle.module.css'

export default function DimensionToggle() {
  const { activeDims, toggleDim, resetDims } = useTimeRange()
  const allOn = activeDims.size === ALL_DIMENSIONS.length

  return (
    <div className={`${styles.bar} no-print`}>
      <span className={styles.label}>Dimensions</span>
      <span className={styles.hint}>click to exclude</span>
      {ALL_DIMENSIONS.map((dim) => {
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
  )
}
