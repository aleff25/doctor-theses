import { useData } from '../data/DataContext'

function Stat({ n, k }) {
  return (
    <div className="card stat">
      <span className="n">{n}</span>
      <span className="k">{k}</span>
    </div>
  )
}

export default function Overview({ go }) {
  const { data } = useData()
  const totals = data.meta.totals
  const refused = Object.entries(data.thresholds.by_smell.GOD || {}).filter(
    ([, entry]) => !entry.determined,
  )
  const thinnest = [...data.systems].sort(
    (a, b) =>
      a.counts.graph_edges - b.counts.graph_edges ||
      b.counts.services_functional - a.counts.services_functional,
  )[0]

  return (
    <>
      <h1>Architecture-aware metrics, three Java microservice systems</h1>
      <p className="lede">
        Everything here was computed by the pipeline in <span className="mono">practical/</span> and
        is served exactly as it was stored: this page recomputes nothing. Numbers are stamped with
        the metamodel, catalogue and threshold-set versions that produced them, and a metric that
        could not be computed appears as <span className="mono">n/d</span>, never as zero.
      </p>

      <div className="grid three">
        <Stat n={totals.systems} k="subject systems, at pinned commits" />
        <Stat n={totals.functional_services} k={`functional services (${totals.services} modelled)`} />
        <Stat n={totals.metrics_implemented} k={`metrics implemented (${totals.metrics_absent} documented as absent)`} />
        <Stat n={totals.graph_edges} k="edges in the graph those metrics are computed over" />
      </div>

      <h2>The constraint that governs everything downstream</h2>
      <div className="card">
        <p style={{ marginTop: 0 }}>
          Put the two numbers above side by side: {totals.functional_services} functional services
          and {totals.graph_edges} edges between them. The static analyser is a regex pass behind a
          swappable seam, and from source it recovers{' '}
          {data.systems
            .map((s) => `${s.counts.static_dependencies} call sites in ${s.name}`)
            .join(', ')}
          . After DD-002 filtering, the graph the coupling and centrality metrics are actually
          computed over holds{' '}
          {data.systems.map((s) => `${s.counts.graph_edges} in ${s.name}`).join(', ')}.
        </p>
        <p className="small muted">
          Counting is where this is easy to overstate: the models hold{' '}
          {data.systems.reduce((n, s) => n + s.counts.model_dependencies, 0)} dependency elements in
          total, but most of those are docker-compose start ordering to config and discovery
          servers, which DD-002 keeps out of the metric graph on purpose. The number that governs
          the metrics is the last one.
        </p>
        <p>Three consequences follow, and none of them is hidden anywhere in this dashboard:</p>
        <ul className="small">
          <li>
            <b>AIS has a degenerate distribution</b>, so the threshold derivation{' '}
            <b>refuses</b> to emit a value for it, and <span className="mono">GOD</span> reports
            undetermined on every service of every system.
            {refused.map(([metric, entry]) => (
              <div key={metric} className="note warn small">
                <span className="chip mono">GOD.{metric}</span> {entry.reason}
              </div>
            ))}
          </li>
          <li>
            <b>Two of the three learning tasks have labels for one system only</b>, so they cannot
            be evaluated leave-one-system-out at all.
          </li>
          <li>
            <b>Any centrality figure outside PetClinic is a picture of missing evidence.</b>{' '}
            {thinnest.name} contributes {thinnest.counts.services_functional} services and{' '}
            {thinnest.counts.graph_edges} edges to the graph, so its DEG and BTW are zero for
            structural reasons, not architectural ones.
          </li>
        </ul>
        <p className="small" style={{ marginBottom: 0 }}>
          A JVM analyser behind the existing seam is therefore the highest-value next piece of work,
          ahead of any new metric or model. The seam exists precisely so that swapping it changes
          nothing else: <span className="mono">extractor/aam4j_extractor/spi.py</span>.
        </p>
      </div>

      <h2>Per system</h2>
      <div className="grid two">
        {data.systems.map((system) => (
          <div key={system.name} className="card">
            <h3 className="mono">{system.name}</h3>
            <p className="small muted" style={{ marginTop: 0 }}>
              {system.branch} · <span className="mono">{system.snapshot.slice(0, 12)}</span>
            </p>
            <div className="badges">
              <span className="chip">
                {system.counts.services_functional} functional / {system.counts.services_total}
              </span>
              <span className="chip">{system.counts.endpoints} endpoints</span>
              <span className="chip">{system.counts.entities} entities</span>
              <span className={`chip ${system.counts.graph_edges === 0 ? 'stop' : ''}`}>
                {system.counts.graph_edges} graph edges
              </span>
              <span className="chip">{system.counts.static_dependencies} from source</span>
              {system.counts.evidence_gaps > 0 ? (
                <span className="chip warn">{system.counts.evidence_gaps} gaps</span>
              ) : null}
            </div>
            <p className="small" style={{ marginBottom: 0 }}>
              <button className="chip" onClick={() => go('systems')}>
                open the services →
              </button>
            </p>
          </div>
        ))}
      </div>

      <h2>What this dashboard cannot tell you</h2>
      <div className="card">
        <ul className="small" style={{ margin: 0 }}>
          <li>
            <b>Whether any of these systems has a quality problem.</b> There is no trained quality
            model, so there is no verdict. The API returns{' '}
            <span className="mono">assessment.available: false</span> for the same reason (DD-007).
          </li>
          <li>
            <b>Anything about runtime behaviour.</b> No subject system is instrumented in this
            configuration, so the whole of metric group B, and the volume weighting that{' '}
            <span className="mono">BTW</span> and <span className="mono">PR</span> are defined
            with, are absent rather than approximated.
          </li>
          <li>
            <b>Whether the metrics predict real-world failure.</b> The labels are synthetic, by
            construction. They show whether a metric responds to an injected architectural change,
            which is a different and weaker claim (DD-008).
          </li>
        </ul>
      </div>
    </>
  )
}
