import { useMemo, useState } from 'react'
import MetricBadge from '../ui/MetricBadge'
import ServiceCard from './ServiceCard'
import { useData } from '../data/DataContext'

const FILTERS = [
  { id: 'graph', label: 'In the graph' },
  { id: 'all', label: 'All services' },
  { id: 'undetermined', label: 'With undetermined metrics' },
  { id: 'gaps', label: 'With evidence gaps' },
]

export default function Systems() {
  const { data } = useData()
  const [systemName, setSystemName] = useState(data.systems[0].name)
  const [filter, setFilter] = useState('graph')
  const [query, setQuery] = useState('')

  const system = data.systems.find((s) => s.name === systemName)

  const services = useMemo(() => {
    const text = query.trim().toLowerCase()
    return system.services
      .filter((service) => {
        if (filter === 'graph' && !service.in_graph) return false
        if (filter === 'undetermined' && !service.metrics.some((m) => !m.determined)) return false
        if (filter === 'gaps' && service.gaps.length === 0) return false
        return !text || service.name.toLowerCase().includes(text)
      })
      .sort((a, b) => a.name.localeCompare(b.name))
  }, [system, filter, query])

  return (
    <>
      <h1>Systems</h1>
      <p className="lede">
        Every service of every pinned subject system, with its metric profile and the source code
        each number came from. Open a service, then open a dependency, an endpoint or an entity
        inside it to see the statement the extractor read.
      </p>

      <div className="toolbar">
        <div className="seg">
          {data.systems.map((entry) => (
            <button
              key={entry.name}
              aria-pressed={entry.name === systemName}
              onClick={() => setSystemName(entry.name)}
            >
              {entry.name}
            </button>
          ))}
        </div>
        <div className="seg">
          {FILTERS.map((entry) => (
            <button
              key={entry.id}
              aria-pressed={entry.id === filter}
              onClick={() => setFilter(entry.id)}
            >
              {entry.label}
            </button>
          ))}
        </div>
        <input
          type="search"
          placeholder="Filter by name"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>

      <div className="card">
        <div className="badges">
          <span className="chip mono">{system.snapshot.slice(0, 12)}</span>
          <span className="chip">{system.branch}</span>
          <span className="chip">
            {system.counts.services_functional} functional / {system.counts.services_total} services
          </span>
          <span className="chip">{system.counts.endpoints} endpoints</span>
          <span className="chip">{system.counts.entities} entities</span>
          <span className={`chip ${system.counts.graph_edges === 0 ? 'stop' : ''}`}>
            {system.counts.graph_edges} edges in G
          </span>
          <span className="chip">{system.counts.static_dependencies} call sites from source</span>
          <span className="chip">{system.counts.model_dependencies} dependency elements modelled</span>
          {system.counts.evidence_gaps > 0 ? (
            <span className="chip warn">{system.counts.evidence_gaps} evidence gaps</span>
          ) : null}
          {system.url ? (
            <a className="chip" href={system.url} target="_blank" rel="noreferrer">
              source
            </a>
          ) : null}
        </div>
        {system.system_metrics.length > 0 ? (
          <p className="small" style={{ marginBottom: 0, marginTop: 10 }}>
            System level:{' '}
            {system.system_metrics.map((m) => (
              <MetricBadge key={m.metric} {...m} />
            ))}
          </p>
        ) : null}
        {system.counts.graph_edges === 0 ? (
          <div className="note stop small">
            <strong>Read this system's coupling metrics as zero-by-absence.</strong> The regex
            analyser recovered {system.counts.static_dependencies} call site
            {system.counts.static_dependencies === 1 ? '' : 's'} from source here, and after DD-002
            filtering the graph has no edges at all. AIS, ADS, ACS, DEG, BTW and CYC are therefore 0
            for every service for structural reasons rather than architectural ones. Only NOE, NOD
            and SHARED_DB carry information about this system today.
          </div>
        ) : null}
      </div>

      <p className="small muted" style={{ margin: '16px 0 8px' }}>
        {services.length} of {system.services.length} services shown
      </p>
      {services.map((service) => (
        <ServiceCard key={service.id} service={service} />
      ))}
      {services.length === 0 ? <p className="muted">Nothing matches that filter.</p> : null}
    </>
  )
}
