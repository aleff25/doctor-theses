import { useMemo, useState } from 'react'
import Expandable from '../ui/Expandable'
import Reference from './Reference'
import { formatValue, useData } from '../data/DataContext'

/**
 * The catalogue, read as a glossary.
 *
 * Every metric shown anywhere in this dashboard has an entry here: the
 * generator refuses to build if `aam4j_metrics.catalogue.METRICS` and
 * `content/metrics.json` disagree, so the glossary cannot silently fall behind
 * the code.
 */
export default function Metrics() {
  const { data } = useData()
  const [query, setQuery] = useState('')

  const distribution = useMemo(() => {
    const byMetric = {}
    for (const system of data.systems) {
      for (const service of system.services) {
        if (!service.in_graph) continue
        for (const m of service.metrics) {
          const slot = (byMetric[m.metric] ||= { values: [], undetermined: 0 })
          if (m.determined) slot.values.push(m.value)
          else slot.undetermined += 1
        }
      }
      for (const m of system.system_metrics) {
        const slot = (byMetric[m.metric] ||= { values: [], undetermined: 0 })
        if (m.determined) slot.values.push(m.value)
        else slot.undetermined += 1
      }
    }
    return byMetric
  }, [data])

  const text = query.trim().toLowerCase()
  const metrics = data.catalogue.metrics.filter(
    (m) => !text || `${m.id} ${m.name} ${m.group}`.toLowerCase().includes(text),
  )

  return (
    <>
      <h1>Metric catalogue</h1>
      <p className="lede">
        Twelve metrics implemented, ten documented as absent. Absent is a state, not a backlog
        entry: a metric computed from evidence the pipeline does not have would be a fabrication.
        Hover any badge anywhere in this dashboard for the short version; the long version, with the
        limitation that matters, is here.
      </p>

      <div className="toolbar">
        <input
          type="search"
          placeholder="Filter metrics"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>

      {metrics.map((metric) => {
        const stats = distribution[metric.id] || { values: [], undetermined: 0 }
        const determined = stats.values.length
        const min = determined ? Math.min(...stats.values) : null
        const max = determined ? Math.max(...stats.values) : null
        return (
          <Expandable
            key={metric.id}
            title={<span className="mono">{metric.id}</span>}
            subtitle={metric.name}
            badges={
              <span className="badges">
                <span className="chip">{metric.group}</span>
                <span className="chip">{metric.level}</span>
                {metric.status === 'undetermined' ? (
                  <span className="chip warn">undetermined everywhere</span>
                ) : null}
                <span className="chip mono">
                  {determined
                    ? `${formatValue(min)} … ${formatValue(max)} over n=${determined}`
                    : 'no determined values'}
                </span>
                {stats.undetermined > 0 ? (
                  <span className="chip warn">{stats.undetermined} n/d</span>
                ) : null}
              </span>
            }
          >
            <div className="t-formula" style={{ maxWidth: 640 }}>
              {metric.formula}
            </div>
            <p className="small">{metric.plain}</p>

            <div className="section-label">A high value means</div>
            <p className="small">{metric.high_means}</p>

            <div className="section-label">Hypothesised effect on quality</div>
            <p className="small">{metric.hypothesis}</p>

            <div className="section-label">Limitation, and threat to construct validity</div>
            <div className="note warn small">{metric.limitation}</div>

            <div className="section-label">Evidence it reads</div>
            <p className="badges">
              {metric.reads.map((r) => (
                <span key={r} className="chip mono">
                  {r}
                </span>
              ))}
            </p>

            {metric.refs.length > 0 ? (
              <>
                <div className="section-label">Where it comes from</div>
                {metric.refs.map((key) => (
                  <Reference key={key} id={key} />
                ))}
              </>
            ) : null}
          </Expandable>
        )
      })}

      <h2>Documented as absent</h2>
      <p className="small muted">
        The catalogue in <span className="mono">docs/03-metric-catalogue.md</span> defines these,
        and the pipeline does not compute them. The reason is recorded per metric so the gap stays a
        decision rather than an oversight.
      </p>
      <div className="scroll-x">
        <table>
          <thead>
            <tr>
              <th>Metric</th>
              <th>Group</th>
              <th>Why it is absent</th>
            </tr>
          </thead>
          <tbody>
            {data.catalogue.absent.map((metric) => (
              <tr key={metric.id}>
                <td className="mono">{metric.id}</td>
                <td className="muted small">{metric.group}</td>
                <td className="small">{metric.why_absent}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
