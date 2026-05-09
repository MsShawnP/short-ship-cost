import { useState } from 'react'

import { fmtPct } from '../lib/format.js'
import { useTimeRange } from '../lib/timeRange.jsx'
import styles from './ParameterPanel.module.css'

const GROUPS = [
  {
    title: 'OTIF fines',
    fields: [
      { key: 'otif_walmart_rate', label: 'Walmart rate', type: 'pct', min: 0, max: 0.1, step: 0.001 },
      { key: 'otif_costco_flat_fee', label: 'Costco flat fee', type: 'usd', min: 0, max: 1000, step: 25 },
      { key: 'otif_whole_foods_rate', label: 'Whole Foods rate', type: 'pct', min: 0, max: 0.1, step: 0.001 },
      { key: 'otif_unfi_rate', label: 'UNFI rate', type: 'pct', min: 0, max: 0.1, step: 0.001 },
      { key: 'otif_kehe_rate', label: 'KeHE rate', type: 'pct', min: 0, max: 0.1, step: 0.001 },
      { key: 'otif_regional_rate', label: 'Regional rate', type: 'pct', min: 0, max: 0.1, step: 0.001 },
    ],
  },
  {
    title: 'Deauthorization thresholds',
    fields: [
      { key: 'deauth_velocity_walmart', label: 'Walmart velocity', type: 'units', min: 0.5, max: 6, step: 0.1, suffix: ' u/store/wk' },
      { key: 'deauth_velocity_costco', label: 'Costco velocity', type: 'units', min: 1, max: 12, step: 0.1, suffix: ' u/store/wk' },
      { key: 'deauth_velocity_whole_foods', label: 'Whole Foods velocity', type: 'units', min: 0.25, max: 4, step: 0.1, suffix: ' u/store/wk' },
      { key: 'deauth_velocity_regional', label: 'Regional velocity', type: 'units', min: 0.25, max: 4, step: 0.1, suffix: ' u/store/wk' },
      { key: 'deauth_distributor_fill_rate', label: 'Distributor fill threshold', type: 'pct', min: 0.7, max: 1.0, step: 0.005, hint: 'shifts the cliff' },
    ],
  },
  {
    title: 'Margins',
    fields: [
      { key: 'dtc_margin_pct', label: 'DTC margin', type: 'pct', min: 0.3, max: 0.8, step: 0.005 },
      { key: 'wholesale_margin_pct', label: 'Wholesale margin', type: 'pct', min: 0.2, max: 0.6, step: 0.005 },
    ],
  },
  {
    title: 'Triage labor',
    fields: [
      { key: 'triage_minutes_per_order', label: 'Minutes per edit', type: 'units', min: 0, max: 60, step: 1, suffix: ' min' },
      { key: 'triage_hourly_rate', label: 'Hourly rate', type: 'usd', min: 0, max: 100, step: 1 },
      { key: 'triage_share_of_orders', label: 'Share of orders', type: 'pct', min: 0, max: 1, step: 0.01 },
    ],
  },
  {
    title: 'Chargebacks',
    fields: [
      { key: 'chargeback_rate_walmart_costco', label: 'Walmart/Costco', type: 'pct', min: 0, max: 0.05, step: 0.001 },
      { key: 'chargeback_rate_other', label: 'Other retailers', type: 'pct', min: 0, max: 0.05, step: 0.001 },
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
  return (
    <div className={styles.field}>
      <div className={styles.fieldHead}>
        <span className={styles.fieldLabel}>{field.label}</span>
        <span
          className={`${styles.fieldValue} ${changed ? styles.fieldValueChanged : ''}`}
        >
          {formatValue(field, value)}
        </span>
      </div>
      <input
        type="range"
        className={styles.slider}
        min={field.min}
        max={field.max}
        step={field.step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
      <div className={styles.fieldDefault}>
        baseline {formatValue(field, baseline)}
        {field.hint ? ` · ${field.hint}` : ''}
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
