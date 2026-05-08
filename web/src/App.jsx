import { useEffect, useState } from 'react'

import Header from './components/Header.jsx'
import CostStack from './components/CostStack.jsx'
import './App.css'

const SOURCES = ['meta', 'cost_summary']

function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all(
      SOURCES.map((name) =>
        fetch(`./data/${name}.json`).then((r) => {
          if (!r.ok) throw new Error(`${name}.json: ${r.status}`)
          return r.json()
        }),
      ),
    )
      .then((results) => {
        setData(Object.fromEntries(SOURCES.map((n, i) => [n, results[i]])))
      })
      .catch(setError)
  }, [])

  if (error) {
    return (
      <main className="page">
        <p className="status">Failed to load data: {error.message}</p>
      </main>
    )
  }

  if (!data) {
    return (
      <main className="page">
        <p className="status">Loading&hellip;</p>
      </main>
    )
  }

  return (
    <>
      <Header />
      <main className="page">
        <CostStack meta={data.meta} summary={data.cost_summary} />
      </main>
      <footer className="footer">
        <span>
          Data window: {data.meta.time_window.start} to{' '}
          {data.meta.time_window.end}. Synthetic order data &mdash;
          methodology in <code>docs/cost-engine-docs.md</code>.
        </span>
        <span>Lailara LLC portfolio piece</span>
      </footer>
    </>
  )
}

export default App
