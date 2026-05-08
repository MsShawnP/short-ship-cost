import styles from './Header.module.css'

export default function Header() {
  return (
    <header className={styles.header}>
      <div>
        <div className={styles.brandName}>Cinderhaven Provisions</div>
        <div className={styles.brandSub}>Cost of Short-Shipping Analysis</div>
      </div>
      <button
        type="button"
        className={`${styles.printButton} no-print`}
        onClick={() => window.print()}
      >
        Print / Export PDF
      </button>
    </header>
  )
}
