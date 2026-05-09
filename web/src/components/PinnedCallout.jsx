import styles from './PinnedCallout.module.css'

/**
 * Dark callout shown above a chart when an item is pinned. Used for the
 * click-to-pin pattern across every section.
 *
 * Props:
 *   title: string — e.g. "KeHE", "Lost revenue", "Sep 2025", "Target 90% fill".
 *   subtitle: string — e.g. "$2.1M (8.4% of all retailers)".
 *   breakdown: optional array of { color, label, value, pct } rows.
 *   onUnpin: () => void — clicking the hint or the chart element again unpins.
 */
export default function PinnedCallout({
  title,
  subtitle,
  breakdown,
  onUnpin,
}) {
  return (
    <div className={styles.callout}>
      <div className={styles.head}>
        <span className={styles.title}>{title}</span>
        {subtitle && <span className={styles.subtitle}>{subtitle}</span>}
        <button
          type="button"
          className={`${styles.unpinButton} no-print`}
          onClick={onUnpin}
        >
          Pinned &mdash; click again to unpin
        </button>
      </div>
      {breakdown && breakdown.length > 0 && (
        <div className={styles.breakdown}>
          {breakdown.map((b) => (
            <div key={b.label} className={styles.row}>
              <span
                className={styles.swatch}
                style={{ background: b.color }}
              />
              <span className={styles.label}>{b.label}</span>
              <span className={styles.value}>{b.value}</span>
              {b.pct !== undefined && b.pct !== null && (
                <span className={styles.pct}>{b.pct}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
