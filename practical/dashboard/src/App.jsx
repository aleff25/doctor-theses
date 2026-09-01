import { useState } from 'react'
import { useData } from './data/DataContext'
import Learning from './views/Learning'
import Metrics from './views/Metrics'
import Overview from './views/Overview'
import Rules from './views/Rules'
import Systems from './views/Systems'

const VIEWS = [
  { id: 'overview', label: 'Overview' },
  { id: 'systems', label: 'Systems' },
  { id: 'metrics', label: 'Metrics' },
  { id: 'rules', label: 'Rules' },
  { id: 'learning', label: 'Learning' },
]

export default function App() {
  const state = useData()
  const [view, setView] = useState('overview')

  if (state.status === 'loading') {
    return <div className="main">Loading the profile…</div>
  }

  if (state.status === 'error') {
    return (
      <div className="main">
        <h1>No data to show</h1>
        <p className="lede">
          <span className="mono">public/dashboard.json</span> could not be read ({state.error}).
        </p>
        <div className="card">
          <p style={{ marginTop: 0 }}>Generate it from the repository root:</p>
          <pre className="mono small">
            {`./.venv/bin/python run_pipeline.py --system petclinic
./.venv/bin/python run_pipeline.py --system teastore
./.venv/bin/python run_pipeline.py --system trainticket
./.venv/bin/python metrics/derive_thresholds.py
./.venv/bin/python models/build_dataset.py
./.venv/bin/python models/train_baseline.py --task oversized-service
./.venv/bin/python dashboard/build_dashboard_data.py`}
          </pre>
          <p className="small muted" style={{ marginBottom: 0 }}>
            The dashboard reads what the pipeline stored and computes nothing of its own, so it
            needs the pipeline to have run at least once.
          </p>
        </div>
      </div>
    )
  }

  const { data } = state
  const counts = {
    systems: data.systems.length,
    metrics: data.catalogue.metrics.length,
    rules: data.rules.length,
    learning: data.learning.available ? data.learning.tasks.length : 0,
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          AAM4J
          <small>
            Architecture-aware metrics for Java. Practical track of the PhD, Iscte-IUL.
          </small>
        </div>

        <nav className="nav">
          {VIEWS.map((entry) => (
            <button
              key={entry.id}
              aria-current={view === entry.id}
              onClick={() => setView(entry.id)}
            >
              {entry.label}
              {counts[entry.id] ? <span className="count">{counts[entry.id]}</span> : null}
            </button>
          ))}
        </nav>

        <div className="stamp">
          <dl>
            <dt>trust</dt>
            <dd>{data.meta.trust_level}</dd>
            <dt>metamodel</dt>
            <dd>{data.meta.metamodel_version}</dd>
            <dt>catalogue</dt>
            <dd>{data.meta.catalogue_version}</dd>
            <dt>thresholds</dt>
            <dd>{data.meta.threshold_set_version}</dd>
          </dl>
          <p style={{ marginBottom: 0 }}>
            Every number on this page carries these versions. Nothing here is recomputed: the page
            renders what the pipeline stored.
          </p>
        </div>
      </aside>

      <main className="main">
        {view === 'overview' ? <Overview go={setView} /> : null}
        {view === 'systems' ? <Systems /> : null}
        {view === 'metrics' ? <Metrics /> : null}
        {view === 'rules' ? <Rules /> : null}
        {view === 'learning' ? <Learning /> : null}
      </main>
    </div>
  )
}
