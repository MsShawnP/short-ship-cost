import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LabelList,
} from 'recharts'
import './App.css'

const bufferScenarios = [
  { scenario: '80% fill', costRecoveredM: 7.6 },
  { scenario: '85% fill', costRecoveredM: 9.7 },
  { scenario: '90% fill', costRecoveredM: 15.8 },
  { scenario: '95% fill', costRecoveredM: 22.0 },
]

function App() {
  return (
    <main>
      <header>
        <h1>Cinderhaven Provisions &mdash; Cost of Short-Shipping Analysis</h1>
        <button
          type="button"
          className="print-button no-print"
          onClick={() => window.print()}
        >
          Print / Export PDF
        </button>
      </header>

      <section>
        <h2>Buffer simulation: cost recovered by target fill rate</h2>
        <p className="caption">
          Print compatibility spike. Dummy data &mdash; values approximate the
          arc 1 buffer scenarios ($M of cost-of-shorts recovered).
        </p>
        <div className="chart">
          <ResponsiveContainer width="100%" height={360}>
            <BarChart
              data={bufferScenarios}
              margin={{ top: 24, right: 24, bottom: 24, left: 24 }}
            >
              <CartesianGrid stroke="#e6e6e6" vertical={false} />
              <XAxis
                dataKey="scenario"
                tick={{ fill: '#1a1a1a', fontSize: 13 }}
                stroke="#1a1a1a"
              />
              <YAxis
                tick={{ fill: '#1a1a1a', fontSize: 13 }}
                stroke="#1a1a1a"
                label={{
                  value: 'Cost recovered ($M)',
                  angle: -90,
                  position: 'insideLeft',
                  style: { fill: '#1a1a1a', fontSize: 13 },
                }}
              />
              <Tooltip cursor={{ fill: 'rgba(0,0,0,0.04)' }} />
              <Bar dataKey="costRecoveredM" fill="#0f4c81" isAnimationActive={false}>
                <LabelList
                  dataKey="costRecoveredM"
                  position="top"
                  formatter={(v) => `$${v.toFixed(1)}M`}
                  style={{ fill: '#1a1a1a', fontSize: 12 }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </main>
  )
}

export default App
