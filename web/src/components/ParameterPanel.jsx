import { fmtPct } from '../lib/format.js'
import { useTimeRange } from '../lib/timeRange.jsx'
import styles from './ParameterPanel.module.css'

const GROUPS = [
  {
    title: 'Compliance fine rates',
    fields: [
      { key: 'fine_walmart', label: 'Walmart (line COGS)', type: 'pct', min: 0, max: 0.1, step: 0.001 },
      { key: 'fine_costco', label: 'Costco (flat per PO)', type: 'usd', min: 0, max: 1000, step: 25 },
      { key: 'fine_whole_foods', label: 'Whole Foods (PO COGS)', type: 'pct', min: 0, max: 0.1, step: 0.001 },
      { key: 'fine_unfi', label: 'UNFI (shorted value)', type: 'pct', min: 0, max: 0.1, step: 0.001 },
      { key: 'fine_kehe', label: 'KeHE (PO COGS)', type: 'pct', min: 0, max: 0.1, step: 0.001 },
      { key: 'fine_sprouts', label: 'Sprouts (PO COGS)', type: 'pct', min: 0, max: 0.1, step: 0.001 },
      { key: 'fine_kroger', label: 'Kroger (PO COGS)', type: 'pct', min: 0, max: 0.1, step: 0.001 },
      { key: 'fine_regional', label: 'Regional (PO COGS)', type: 'pct', min: 0, max: 0.1, step: 0.001 },
      { key: 'fine_dpi_northwest', label: 'DPI Northwest (PO COGS)', type: 'pct', min: 0, max: 0.1, step: 0.001 },
    ],
  },
]

function formatValue(field, value) {
  if (field.type === 'pct') return fmtPct(value)
  if (field.type === 'usd') return `$${value}`
  if (field.type === 'units') return `${(+value).toFixed(field.step < 1 ? 2 : 0)}${field.suffix || ''}`
  return value
}

function ParameterField({ field, value, baseline, onChange }) {
  const changed = value !== baseline
  const formatted = formatValue(field, value)
  return (
    <div className={styles.field}>
      <div className={styles.fieldHead}>
        <label htmlFor={`param-${field.key}`} className={styles.fieldLabel}>
          {field.label}
        </label>
        <span
          className={`${styles.fieldValue} ${changed ? styles.fieldValueChanged : ''}`}
        >
          {formatted}
        </span>
      </div>
      <input
        id={`param-${field.key}`}
        type="range"
        className={styles.slider}
        min={field.min}
        max={field.max}
        step={field.step}
        value={value}
        aria-valuetext={`${formatted}, baseline ${formatValue(field, baseline)}`}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
      <div className={styles.fieldDefault}>
        baseline {formatValue(field, baseline)}
      </div>
    </div>
  )
}

export function ParameterToggleButton({ open, onToggle, modified }) {
  return (
    <button
      type="button"
      className={`${styles.toggleButton} ${open ? styles.toggleButtonActive : ''} no-print`}
      onClick={onToggle}
      aria-expanded={open}
    >
      {modified && <span className={styles.modifiedDot} aria-hidden="true" />}
      Adjust parameters
    </button>
  )
}

export default function ParameterPanel({ open, onClose, validation }) {
  const {
    params,
    baselineParams,
    setParam,
    resetParams,
    paramsModified,
  } = useTimeRange()

  if (!open) return null
  if (!params || !baselineParams) return null

  return (
    <>
      <div className={styles.scrim} onClick={onClose} />
      <aside className={styles.panel}>
        <div className={styles.panelHead}>
          <span className={styles.panelTitle}>Parameters</span>
          <button
            type="button"
            className={styles.closeButton}
            onClick={onClose}
            aria-label="Close parameters panel"
          >
            ×
          </button>
        </div>
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.resetButton}
            disabled={!paramsModified}
            onClick={resetParams}
          >
            Reset to baseline
          </button>
          {validation === null ? (
            <span className={styles.validationOk}>✓ Validated</span>
          ) : Array.isArray(validation) ? (
            <span
              className={styles.validationFail}
              title={validation
                .map(
                  (m) =>
                    `${m.dim}: want ${Math.round(m.want)}, got ${Math.round(m.got)}`,
                )
                .join('\n')}
            >
              ⚠ Mismatch
            </span>
          ) : null}
        </div>
        <div className={styles.body}>
          {GROUPS.map((g) => (
            <div key={g.title} className={styles.group}>
              <p className={styles.groupTitle}>{g.title}</p>
              {g.fields.map((f) => (
                <ParameterField
                  key={f.key}
                  field={f}
                  value={params[f.key]}
                  baseline={baselineParams[f.key]}
                  onChange={(v) => setParam(f.key, v)}
                />
              ))}
            </div>
          ))}
        </div>
      </aside>
    </>
  )
}
