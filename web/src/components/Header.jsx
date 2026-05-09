import FilterBar from './FilterBar.jsx'
import styles from './Header.module.css'

export default function Header({ rightSlot }) {
  return (
    <header className={styles.header}>
      <div>
        <div className={styles.brandName}>Cinderhaven Provisions</div>
        <div className={styles.brandSub}>Cost of Short-Shipping Analysis</div>
      </div>
      <div className={styles.controls}>
        <FilterBar />
        {rightSlot}
        <button
          type="button"
          className={`${styles.printButton} no-print`}
          onClick={() => window.print()}
        >
          Print / Export PDF
        </button>
      </div>
    </header>
  )
}
