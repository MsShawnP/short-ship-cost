import { useEffect } from 'react'

import FilterBar from './FilterBar.jsx'
import styles from './Header.module.css'

const PRINT_TITLE = 'Cost_of_Short-Shipping_Analysis_Cinderhaven'

function handlePrint() {
  const original = document.title
  document.title = PRINT_TITLE
  document.body.classList.add('printing')
  const restore = () => {
    document.title = original
    document.body.classList.remove('printing')
    window.removeEventListener('afterprint', restore)
  }
  window.addEventListener('afterprint', restore)
  window.print()
}

export default function Header({ rightSlot }) {
  // Belt-and-suspenders: if afterprint never fires (some browsers under
  // automation), restore the title on next paint.
  useEffect(() => {
    return () => document.body.classList.remove('printing')
  }, [])

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
          onClick={handlePrint}
        >
          Print / Export PDF
        </button>
      </div>
    </header>
  )
}
